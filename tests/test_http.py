"""Exercise the HTTP boundary without sending any real Telegram messages."""
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest

from lib.workspace import Workspace, read

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'app'))
from auth import AuthStore
from server import RadarServer


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Workspace(Path(self.temp.name)/'private')
        self.workspace.initialize(read(BASE/'examples/candidate.demo.json'),read(BASE/'examples/preferences.template.json'))
        self.job = read(BASE/'examples/job.demo.json'); self.workspace.add_job(self.job)
        self.cv = self.workspace.register_cv(self.job['id'],BASE/'examples/cv.demo.pdf','Test adaptation only.')
        self.codes = []
        self.auth = AuthStore(self.workspace.root/'reviews','test','test',self.codes.append)
        self.server = RadarServer(('127.0.0.1',0),self.workspace.root/'reviews',
                                 config={'WORKSPACE_PUBLIC_URL':'https://jobs.example.com',
                                         'WORKSPACE_DIR':str(self.workspace.root)},auth=self.auth)
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
        self.cookie = ''

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(); self.temp.cleanup()

    def request(self,path,body=None,headers=None):
        connection = http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        request_headers = {'Cookie':self.cookie,'Origin':'https://jobs.example.com','Content-Type':'application/json'}
        request_headers.update(headers or {})
        connection.request('GET' if body is None else 'POST',path,
                           body=None if body is None else json.dumps(body),headers=request_headers)
        response = connection.getresponse(); content = response.read(); status = response.status
        result_headers = response.getheaders(); connection.close()
        return status,content,result_headers

    def login(self):
        status,_,headers = self.request('/auth/request',{})
        self.assertEqual(status,200)
        self.cookie = next(v.split(';')[0] for k,v in headers if k.lower()=='set-cookie')
        status,_,headers = self.request('/auth/verify',{'code':self.codes[-1]})
        self.assertEqual(status,200)
        cookie = next(v for k,v in headers if k.lower()=='set-cookie' and v.startswith('empleo_session='))
        self.assertIn('HttpOnly',cookie); self.assertIn('Secure',cookie); self.assertIn('SameSite=Strict',cookie)
        self.cookie = cookie.split(';')[0]

    def test_private_routes_require_login_and_health_hides_paths(self):
        self.assertEqual(self.request('/')[0],303)
        for route in ['/api/data','/api/export','/api/report','/files/'+self.cv['filename'],
                      '/preview/'+self.cv['filename'],'/reports/private.txt','/receipts/proof.png','/app.js']:
            with self.subTest(route=route): self.assertEqual(self.request(route)[0],401)
        health = json.loads(self.request('/api/health')[1])
        self.assertEqual(set(health),{'app','status'})

    def test_host_origin_and_missing_config_fail_closed(self):
        self.assertEqual(self.request('/api/data',headers={'Host':'evil.example'})[0],403)
        self.assertEqual(self.request('/auth/request',{},headers={'Origin':'https://evil.example'})[0],403)
        self.assertEqual(self.request('/auth/request',{},headers={'Origin':''})[0],403)
        self.assertEqual(self.codes,[])
        with self.assertRaises(RuntimeError):
            RadarServer(('127.0.0.1',0),Path(self.temp.name)/'bad',config={'WORKSPACE_PUBLIC_URL':'https://jobs.example.com'})

    def test_login_pdf_notes_conflict_and_path_allowlist(self):
        self.login()
        data = json.loads(self.request('/api/data')[1]); csrf = data['csrf']
        status,pdf,_ = self.request('/files/'+self.cv['filename'])
        self.assertEqual(status,200); self.assertTrue(pdf.startswith(b'%PDF-'))
        self.assertEqual(self.request('/files/../candidate.json')[0],404)
        self.assertEqual(self.request('/files/%2e%2e%2fcandidate.json')[0],404)
        self.assertEqual(self.request('/.env')[0],404)
        body = {'revision':data['reviews']['revision'],'decision':'priorizar','cv_review':'pendiente',
                'cv_reference':self.cv['sha256'],'notes':'Fictional test note.'}
        self.assertEqual(self.request('/api/jobs/'+self.job['id'],body)[0],403)
        status,raw,_ = self.request('/api/jobs/'+self.job['id'],body,{'X-Radar-Token':csrf})
        self.assertEqual(status,200); self.assertTrue(json.loads(raw)['saved'])
        self.assertEqual(self.request('/api/jobs/'+self.job['id'],body,{'X-Radar-Token':csrf})[0],409)
        notes = read(self.workspace.root/'reviews/decisions.json')
        self.assertEqual(notes['jobs'][self.job['id']]['notes'],'Fictional test note.')
        self.assertEqual(self.request('/auth/logout',{}, {'X-Radar-Token':csrf})[0],200)
        self.assertEqual(self.request('/api/data')[0],401)


if __name__ == '__main__': unittest.main()
