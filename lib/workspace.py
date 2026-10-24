"""Local records, immutable documents and explicit submission evidence.

This module never contacts employers or sends job applications.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import unicodedata
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from .records import normalize_application_status, normalize_catalog


class WorkspaceError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + secrets.token_hex(4) + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8', newline='\n') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists(): temporary.unlink()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalized(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', value.casefold())
                           if not unicodedata.combining(c)).split())


def canonical_url(value):
    parts = urlsplit(value)
    if parts.scheme not in {'http', 'https'} or not parts.hostname or parts.username or parts.password:
        raise WorkspaceError('The job needs a valid web URL without credentials.')
    if parts.hostname in {'linkedin.com', 'www.linkedin.com'}:
        match = re.search(r'/jobs/view/(\d+)', parts.path)
        if match: return 'https://www.linkedin.com/jobs/view/' + match[1] + '/'
    removed = {'source','ref','referrer','referral','trackingid','trk','gh_src','fbclid','gclid'}
    query = [(k,v) for k,v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in removed]
    if any(re.search(r'token|password|secret|session|auth', k, re.I) for k,_ in query):
        raise WorkspaceError('Store the public job URL without login links or tokens.')
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip('/') or '/', urlencode(sorted(query)), ''))


class Workspace:
    def __init__(self, root):
        self.root = Path(root).resolve()

    @contextmanager
    def lock(self):
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root / '.writer.lock').open('a+b') as handle:
            if os.name == 'nt':
                import msvcrt
                handle.seek(0); handle.write(b'0'); handle.flush(); handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX)
            try: yield
            finally:
                if os.name == 'nt':
                    handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else: fcntl.flock(handle, fcntl.LOCK_UN)

    def state(self):
        return normalize_catalog(read(self.root / 'state.json'))

    def write_state(self, state):
        state['updated_at'] = now()
        save(self.root / 'state.json', state)

    def job(self, identifier, state=None):
        match = next((j for j in (state or self.state())['jobs'] if j['id'] == identifier), None)
        if not match: raise WorkspaceError('Unknown job: ' + identifier)
        return match

    def initialize(self, candidate, preferences, demo=False):
        with self.lock():
            if (self.root / 'state.json').exists():
                raise WorkspaceError('This workspace already exists and will not be overwritten.')
            if any(p.name != '.writer.lock' for p in self.root.iterdir()):
                raise WorkspaceError('Choose an empty folder for the private workspace.')
            facts = candidate.get('facts', [])
            if len({f['id'] for f in facts}) != len(facts):
                raise WorkspaceError('Profile fact IDs must be unique.')
            for folder in ['documents','receipts','reports','reviews','cv-content']:
                (self.root / folder).mkdir(mode=0o700)
            for name, value in {
                'candidate.json': candidate, 'preferences.json': preferences,
                'state.json': {'schema_version':1,'demo':demo,'updated_at':now(),'master_cv':None,'jobs':[]},
                'analysis.json': {}, 'cv-versions.json': {'schema_version':1,'variants':[]},
                'runs.json': {'schema_version':1,'runs':[]}, 'trial.json': {},
                'reviews/decisions.json': {'schema_version':1,'revision':0,'jobs':{},'profile':{},'history':[]},
            }.items(): save(self.root / name, value)
        return {'initialized':str(self.root),'demo':demo}

    def add_job(self, incoming):
        identifier = incoming.get('id', '')
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{1,100}', identifier):
            raise WorkspaceError('Use a stable ID containing letters, numbers, hyphens or underscores.')
        for field in ['company','title','url','location','mode','why','verified_on']:
            if not isinstance(incoming.get(field), str) or not incoming[field].strip():
                raise WorkspaceError('Missing field: ' + field)
        datetime.fromisoformat(incoming['verified_on'])
        canonical = canonical_url(incoming['url'])
        external_ids = set(incoming.get('external_ids', []))
        if any(not isinstance(v, str) for v in external_ids):
            raise WorkspaceError('external_ids must contain text identifiers.')
        if incoming.get('application', {}).get('sent'):
            raise WorkspaceError('Use record-application with the PDF and receipt to record a submission.')
        with self.lock():
            state = self.state()
            triplet = tuple(normalized(incoming[k]) for k in ['company','title','location'])
            for previous in state['jobs']:
                if (previous['id'] == identifier or previous.get('canonical_url', canonical_url(previous['url'])) == canonical
                    or tuple(normalized(previous[k]) for k in ['company','title','location']) == triplet
                    or external_ids.intersection(previous.get('external_ids', []))):
                    raise WorkspaceError('Job already registered: ' + previous['id'])
            job = {**incoming, 'canonical_url':canonical, 'url':canonical,
                   'published_label':incoming.get('published_label','Publication date needs confirmation'),
                   'salary':incoming.get('salary',{'label':'Not disclosed','minimum':None,'maximum':None}),
                   'strengths':incoming.get('strengths',[]), 'gaps':incoming.get('gaps',[]),
                   'decision':'review', 'next_step':incoming.get('next_step','Review the fit and prepare a CV.'),
                   'cv_prepared':None, 'cv_history':[], 'application':{'sent':False,'status':'pending','label':'Awaiting review'}}
            state['jobs'].append(job)
            analysis = read(self.root / 'analysis.json')
            analysis[identifier] = incoming.get('analysis', {})
            save(self.root / 'analysis.json', analysis)
            self.write_state(state)
        return job

    def record_outcome(self, identifier, status, reason):
        status = normalize_application_status(status)
        if status not in {'reserved','discarded','blocked','uncertain','pending'}:
            raise WorkspaceError('Unsupported status.')
        if not reason.strip(): raise WorkspaceError('Describe the observed reason.')
        with self.lock():
            state = self.state(); job = self.job(identifier, state)
            if job.get('application', {}).get('sent'):
                raise WorkspaceError('A confirmed submission is preserved; record follow-up separately.')
            job['application'] = {'sent':False,'status':status,'label':reason,'updated_at':now()}
            job['next_step'] = reason
            self.write_state(state)
        return job['application']

    def register_cv(self, identifier, source, tailoring, language='en', content=None):
        source = Path(source)
        if not source.read_bytes().startswith(b'%PDF-'):
            raise WorkspaceError('The file is not a PDF.')
        if not tailoring.strip(): raise WorkspaceError('Explain what was tailored and why.')
        with self.lock():
            state = self.state(); job = self.job(identifier, state)
            version = 1
            stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            while (self.root/'documents'/f'{identifier}_{stamp}_v{version}.pdf').exists(): version += 1
            filename = f'{identifier}_{stamp}_v{version}.pdf'
            target = self.root / 'documents' / filename
            with target.open('xb') as handle: handle.write(source.read_bytes())
            cv = {'filename':filename,'sha256':digest(target),'version':f'v{version}',
                  'language':language,'created_on':now(),'tailoring':tailoring}
            if job.get('cv_prepared'): job['cv_history'].append(job['cv_prepared'])
            job['cv_prepared'] = cv
            job.pop('authorization', None)
            versions = read(self.root / 'cv-versions.json')
            versions['variants'].append({'job_id':identifier,**cv})
            if content is not None: save(self.root / 'cv-content' / (filename+'.json'), content)
            save(self.root / 'cv-versions.json', versions)
            self.write_state(state)
        return cv

    def approve(self, identifier, note):
        if len(note.strip()) < 10:
            raise WorkspaceError('Record the actual user instruction authorizing this submission.')
        with self.lock():
            state=self.state(); job=self.job(identifier,state)
            if job.get('application',{}).get('sent'): raise WorkspaceError('The application is already recorded as submitted.')
            cv=job.get('cv_prepared')
            if not cv: raise WorkspaceError('Prepare and review the PDF before recording authorization.')
            if digest(self.root/'documents'/cv['filename']) != cv['sha256']:
                raise WorkspaceError('The PDF has changed since it was registered.')
            job['authorization']={'note':note,'recorded_at':now(),'cv_sha256':cv['sha256'],
                                  'expires_at':(datetime.now(timezone.utc)+timedelta(hours=24)).isoformat()}
            self.write_state(state)
        return job['authorization']

    def ready(self, identifier):
        job=self.job(identifier)
        if job.get('application',{}).get('sent'): raise WorkspaceError('Already submitted. Do not repeat the form.')
        if job.get('application',{}).get('status')=='uncertain':
            raise WorkspaceError('The submission outcome is uncertain. Check the portal before retrying.')
        cv=job.get('cv_prepared'); approval=job.get('authorization',{})
        if not cv or approval.get('cv_sha256') != cv['sha256']:
            raise WorkspaceError('User authorization is missing for this PDF version.')
        if datetime.fromisoformat(approval['expires_at']) <= datetime.now(timezone.utc):
            raise WorkspaceError('Authorization has expired; check the posting and the current user instruction.')
        if digest(self.root/'documents'/cv['filename']) != cv['sha256']:
            raise WorkspaceError('The registered PDF has changed.')
        preferences=read(self.root/'preferences.json')
        minimum=preferences.get('salary',{}).get('minimum_eur_gross_annual')
        maximum=job.get('salary',{}).get('maximum')
        if minimum is not None and maximum is not None and maximum < minimum:
            raise WorkspaceError('The published maximum is below the configured salary minimum.')
        return {'ready':True,'job_id':identifier,'cv':cv,
                'reminder':'Verify that the job is open, its work arrangement and conditions, and the portal session before submitting.'}

    def record_application(self, identifier, confirmation, receipt, channel, observed_at, cv_filename, cv_sha256, answers=None):
        if len(confirmation.strip()) < 10 or not channel.strip():
            raise WorkspaceError('Record the visible confirmation and the channel.')
        observed=datetime.fromisoformat(observed_at)
        if observed.tzinfo is None: raise WorkspaceError('The submission timestamp must include a time zone.')
        if observed > datetime.now(timezone.utc)+timedelta(minutes=5):
            raise WorkspaceError('The observed timestamp cannot be in the future.')
        receipt=Path(receipt)
        raw=receipt.read_bytes()
        suffix='.png' if raw.startswith(b'\x89PNG\r\n\x1a\n') else '.jpg' if raw.startswith(b'\xff\xd8\xff') else None
        if not suffix: raise WorkspaceError('Save an actual PNG or JPEG screenshot as a receipt.')
        with self.lock():
            state=self.state(); job=self.job(identifier,state)
            if job.get('application',{}).get('sent'):
                if job['application'].get('cv_sha256')!=cv_sha256 or job['application'].get('cv_sent')!=cv_filename:
                    raise WorkspaceError('A submission with another PDF already exists and will not be overwritten.')
                return {'already_recorded':True,'application':job['application']}
            cv=next((cv for cv in [job.get('cv_prepared')]+job.get('cv_history',[]) if cv and cv['filename']==cv_filename and cv['sha256']==cv_sha256),None)
            if not cv or digest(self.root/'documents'/cv['filename']) != cv_sha256:
                raise WorkspaceError('The exact application PDF is missing or has changed.')
            # Recording observed reality must remain possible after a late confirmation.
            # Authorization is checked before submission by check-ready, not fabricated here.
            proof=f'{identifier}_{secrets.token_hex(4)}{suffix}'
            with (self.root/'receipts'/proof).open('xb') as handle: handle.write(raw)
            application={'sent':True,'sent_at':observed.isoformat(),'status':'sent','label':'Submission confirmed',
                         'cv_sent':cv['filename'],'cv_sha256':cv['sha256'],'channel':channel,
                         'evidence':confirmation,'evidence_file':proof,'evidence_sha256':hashlib.sha256(raw).hexdigest(),
                         'answers':answers or {},'updated_at':now()}
            if job.get('authorization',{}).get('cv_sha256') != cv['sha256']:
                application['audit_note']='No authorization is recorded for this PDF. Review the process without hiding the observed submission.'
            job['application']=application
            job['next_step']='Check actual replies from the portal or email; do not resubmit the application.'
            self.write_state(state)
        return application

    def validate(self):
        state=self.state(); problems=[]; ids=set(); sent=0
        for name in ['candidate','preferences','analysis','cv-versions','runs','trial']:
            read(self.root/(name+'.json'))
        for job in state['jobs']:
            if job['id'] in ids: problems.append('Duplicate ID: '+job['id'])
            ids.add(job['id'])
            for cv in [job.get('cv_prepared')]+job.get('cv_history',[]):
                if not cv: continue
                path=self.root/'documents'/cv['filename']
                if Path(cv['filename']).name != cv['filename'] or not path.exists() or digest(path)!=cv['sha256']:
                    problems.append('Missing or modified PDF: '+cv['filename'])
            app=job.get('application',{})
            if app.get('sent'):
                sent+=1
                for folder,key,hashkey in [('documents','cv_sent','cv_sha256'),('receipts','evidence_file','evidence_sha256')]:
                    name=app.get(key,''); path=self.root/folder/name
                    if Path(name).name!=name or not path.is_file() or digest(path)!=app.get(hashkey):
                        problems.append('Submission without a verifiable document: '+job['id']+' / '+key)
        return {'valid':not problems,'jobs':len(ids),'sent':sent,'problems':problems}

    def report(self):
        state=self.state(); today=datetime.now(timezone.utc).date().isoformat()
        lines=['JOB SEARCH WORKSPACE', 'Generated: '+now(),
               'Report of recorded observations; it does not imply an automated search has run.', '']
        for job in state['jobs']:
            app=job.get('application',{}); cv=job.get('cv_prepared')
            lines += [job['company']+' · '+job['title'],job['url'],
                      'Status: '+('Submitted' if app.get('sent') else app.get('status','pending')),
                      'Reason: '+job['why'],'To confirm: '+'; '.join(job['gaps']),
                      'CV: '+(app.get('cv_sent') or (cv or {}).get('filename','Not prepared')),
                      'Confirmation: '+app.get('evidence','No confirmed submission'),
                      'Next step: '+job['next_step'],'']
        filename='Report_'+today+'_'+datetime.now(timezone.utc).strftime('%H%M%S_%f')+'_'+secrets.token_hex(3)+'.txt'
        with self.lock():
            with (self.root/'reports'/filename).open('x',encoding='utf-8') as handle:
                handle.write('\n'.join(lines))
            runs=read(self.root/'runs.json')
            runs['runs'].append({'id':'report-'+secrets.token_hex(5),'scheduled_date':today,'status':'report',
                                 'summary':'Report generated from the current records.', 'report_filename':filename})
            save(self.root/'runs.json',runs)
        return {'report':str(self.root/'reports'/filename),'jobs':len(state['jobs'])}
