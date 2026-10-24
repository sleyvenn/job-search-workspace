from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from lib.workspace import Workspace, WorkspaceError, read, save
from lib.cv import validate_content

BASE=Path(__file__).resolve().parents[1]
# A PNG signature is sufficient for these record-boundary tests; no claim is made
# that it is a real portal confirmation. Every test uses an isolated temp folder.
PROOF=b'\x89PNG\r\n\x1a\nTEST ONLY'


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.workspace=Workspace(Path(self.temp.name)/'private')
        self.profile=read(BASE/'examples/candidate.demo.json')
        self.preferences=read(BASE/'examples/preferences.template.json')
        self.workspace.initialize(self.profile,self.preferences)
        self.job=read(BASE/'examples/job.demo.json')
        self.workspace.add_job(self.job)

    def tearDown(self): self.temp.cleanup()

    def cv(self):
        return self.workspace.register_cv(self.job['id'],BASE/'examples/cv.demo.pdf','Example adaptation based on confirmed facts.')

    def test_init_never_overwrites_existing_workspace(self):
        before=(self.workspace.root/'state.json').read_bytes()
        with self.assertRaises(WorkspaceError): self.workspace.initialize({}, {})
        self.assertEqual(before,(self.workspace.root/'state.json').read_bytes())

    def test_dedup_by_url_and_employer_role_location(self):
        duplicate={**self.job,'id':'another-id','external_ids':[], 'url':self.job['url']+'?utm_source=another'}
        with self.assertRaisesRegex(WorkspaceError,'already registered'): self.workspace.add_job(duplicate)
        duplicate['url']='https://example.com/different-ats'
        duplicate['company']=' HARBOR EXAMPLE '
        with self.assertRaisesRegex(WorkspaceError,'already registered'): self.workspace.add_job(duplicate)
        self.assertEqual(len(self.workspace.state()['jobs']),1)

    def test_private_login_urls_cannot_become_offer_urls(self):
        with self.assertRaisesRegex(WorkspaceError,'tokens'):
            self.workspace.add_job({**self.job,'id':'bad-url','url':'https://example.com/jobs?tmp_ctoken=secret'})

    def test_source_refs_must_point_to_confirmed_facts(self):
        content=read(BASE/'examples/cv.demo.json')
        self.assertGreater(validate_content(self.profile,content),0)
        content['headline']['source_refs']=['invented-skill']
        with self.assertRaises(WorkspaceError): validate_content(self.profile,content)
        self.assertEqual(len(list((self.workspace.root/'documents').iterdir())),0)

    def test_versions_are_immutable_and_new_cv_resets_approval(self):
        first=self.cv()
        self.workspace.approve(self.job['id'],'Test-only user approval for this exact PDF.')
        self.assertTrue(self.workspace.ready(self.job['id'])['ready'])
        second=self.cv()
        self.assertNotEqual(first['filename'],second['filename'])
        with self.assertRaisesRegex(WorkspaceError,'authorization'): self.workspace.ready(self.job['id'])
        self.assertTrue(self.workspace.validate()['valid'])

    def test_salary_filter_and_uncertain_results_block_retry(self):
        self.cv(); self.workspace.approve(self.job['id'],'Test-only user approval for this exact PDF.')
        self.workspace.record_outcome(self.job['id'],'uncertain','The form did not show confirmation.')
        with self.assertRaisesRegex(WorkspaceError,'uncertain'): self.workspace.ready(self.job['id'])
        self.workspace.record_outcome(self.job['id'],'pending','The portal confirms there is no existing application.')
        preferences=read(self.workspace.root/'preferences.json')
        preferences['salary']['minimum_eur_gross_annual']=50000
        from lib.workspace import save
        save(self.workspace.root/'preferences.json',preferences)
        with self.assertRaisesRegex(WorkspaceError,'salary minimum'): self.workspace.ready(self.job['id'])

    def test_exact_pdf_and_receipt_required_and_sent_not_duplicated(self):
        cv=self.cv(); proof=Path(self.temp.name)/'proof.png'; proof.write_bytes(PROOF)
        args=(self.job['id'],'TEST: confirmation observed on a fake portal',proof,'Test only',
              datetime.now(timezone.utc).isoformat(),cv['filename'],cv['sha256'])
        recorded=self.workspace.record_application(*args)
        self.assertTrue(recorded['sent'])
        again=self.workspace.record_application(*args)
        self.assertTrue(again['already_recorded'])
        self.assertEqual(self.workspace.validate()['sent'],1)
        with self.assertRaises(WorkspaceError): self.workspace.record_application(*args[:-1],'0'*64)
        with self.assertRaisesRegex(WorkspaceError,'preserved'):
            self.workspace.record_outcome(self.job['id'],'pending','Do not remove an actual submission.')

    def test_document_tampering_is_detected(self):
        cv=self.cv()
        (self.workspace.root/'documents'/cv['filename']).write_bytes(b'%PDF- changed')
        self.assertFalse(self.workspace.validate()['valid'])
        with self.assertRaisesRegex(WorkspaceError,'changed'): self.workspace.approve(self.job['id'],'Test-only permission before submit.')

    def test_cli_operations_preserve_user_notes(self):
        notes=self.workspace.root/'reviews/decisions.json'
        original=notes.read_bytes()
        self.cv()
        self.workspace.record_outcome(self.job['id'],'reserved','Wait for the conditions to be confirmed.')
        self.workspace.report()
        self.assertEqual(original,notes.read_bytes())

    def test_legacy_uncertain_status_still_blocks_submission_without_rewriting_files(self):
        cv=self.cv()
        self.workspace.approve(self.job['id'],'Test-only user approval for this exact PDF.')
        state_path=self.workspace.root/'state.json'
        legacy=read(state_path)
        legacy['jobs'][0]['application']['status']='incierta'
        legacy['jobs'][0]['decision']='revisar'
        save(state_path,legacy)
        original=state_path.read_bytes()
        self.assertEqual(self.workspace.job(self.job['id'])['decision'],'review')
        with self.assertRaisesRegex(WorkspaceError,'uncertain'):
            self.workspace.ready(self.job['id'])
        self.assertEqual(original,state_path.read_bytes())
        self.assertEqual(self.workspace.job(self.job['id'])['cv_prepared']['sha256'],cv['sha256'])


if __name__=='__main__': unittest.main()
