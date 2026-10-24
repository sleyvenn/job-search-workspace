"""Private, portable job-search workspace with optional Telegram OTP."""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import secrets
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from auth import AuthError, AuthStore

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP.parent))
from lib.records import normalize_catalog, normalize_reviews, normalize_decision, normalize_cv_review

ROOT = Path(os.environ.get('WORKSPACE_DIR', str(APP.parent / 'workspace'))).resolve()
SOURCE = ROOT
DOCUMENTS = ROOT / 'documents'
PUBLIC = APP / 'public'
POPPLER = Path(os.environ.get('PDFTOPPM', 'pdftoppm'))
IDENTITY = 'job-search-workspace-v1'


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + secrets.token_hex(4) + '.tmp')
    with temporary.open('w', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


class ReviewStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.path = self.directory / 'decisions.json'
        self.lock = threading.RLock()

    def load(self):
        with self.lock:
            if self.path.exists():
                return normalize_reviews(read_json(self.path))
            return {
                'schema_version': 1,
                'revision': 0,
                'jobs': {},
                'profile': {'ai_stack': '', 'examples': '', 'english': '', 'mobility': '', 'other': ''},
                'history': []
            }

    def update(self, kind, identifier, fields, expected_revision):
        with self.lock:
            data = self.load()
            if expected_revision != data['revision']:
                raise ValueError('Another tab has saved changes. Refresh before saving to preserve them.')
            stamp = now()
            if kind == 'job':
                previous = data['jobs'].get(identifier, {})
                new = dict(previous, **fields, updated_at=stamp, origin='app')
                changed = [key for key in fields if previous.get(key) != fields[key]]
                data['jobs'][identifier] = new
            else:
                previous = data['profile']
                changed = [key for key in fields if previous.get(key) != fields[key]]
                data['profile'] = dict(previous, **fields, updated_at=stamp)
            if changed:
                if self.path.exists():
                    backups = self.directory / 'decision-backups'
                    backups.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(self.path, backups / f"revision-{data['revision']}-{secrets.token_hex(4)}.json")
                data['revision'] += 1
                data['updated_at'] = stamp
                data['history'].append({'at': stamp, 'kind': kind, 'job_id': identifier, 'changed': changed,
                                        'decision': fields.get('decision'), 'cv_review': fields.get('cv_review')})
                atomic_json(self.path, data)
            return data


class RadarServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, data_dir, config=None, auth=None):
        config = os.environ if config is None else config
        self.public_url = config.get('WORKSPACE_PUBLIC_URL', '').rstrip('/')
        self.brand = config.get('WORKSPACE_BRAND', 'Applications')
        self.bot_name = config.get('TELEGRAM_BOT_NAME', 'Telegram')
        self.public_host = urlsplit(self.public_url).netloc
        if self.public_url and (urlsplit(self.public_url).scheme != 'https' or
                                urlsplit(self.public_url).path or not self.public_host or
                                urlsplit(self.public_url).query or urlsplit(self.public_url).fragment):
            raise RuntimeError('WORKSPACE_PUBLIC_URL must be an HTTPS origin without a path.')
        self.auth = (auth or AuthStore(data_dir, config.get('TELEGRAM_BOT_TOKEN'),
                                      config.get('TELEGRAM_CHAT_ID'), public_url=self.public_url,
                                      bot_name=self.bot_name)) if self.public_url else None
        self.content_root = Path(config.get('WORKSPACE_DIR', str(ROOT)))
        self.store = ReviewStore(data_dir)
        self.csrf = secrets.token_urlsafe(32)
        self.preview_lock = threading.RLock()
        self.preview_dir = Path(data_dir) / 'previews'
        super().__init__(address, Handler)

    def catalog(self, root=None):
        root = root or self.content_root.resolve()
        state = normalize_catalog(read_json(root / 'state.json'))
        analysis = read_json(root / 'analysis.json')
        for job in state['jobs']:
            job['analysis'] = analysis.get(job['id'], {})
        return state

    def documents(self, state):
        allowed = {state.get('master_cv')}
        for job in state['jobs']:
            for cv in [job.get('cv_prepared')] + job.get('cv_history', []):
                if cv:
                    allowed.add(cv.get('filename'))
        return {name for name in allowed if isinstance(name, str) and Path(name).name == name}

    def trial(self, root=None):
        path = (root or self.content_root.resolve()) / 'trial.json'
        return read_json(path) if path.exists() else {}

    def daily_runs(self, root=None):
        path = (root or self.content_root.resolve()) / 'runs.json'
        return read_json(path).get('runs', []) if path.exists() else []

    def reports(self, root=None):
        names = [run.get('report_filename') for run in self.daily_runs(root)]
        names.append(self.trial(root).get('summary_report_filename'))
        return {name for name in names if isinstance(name, str) and Path(name).name == name and name.endswith('.txt')}

    def preview(self, document):
        digest = hashlib.sha256(document.read_bytes()).hexdigest()[:20]
        self.preview_dir.mkdir(parents=True, exist_ok=True)
        prefix = self.preview_dir / digest
        target = prefix.with_suffix('.png')
        with self.preview_lock:
            if not target.exists():
                binary = str(POPPLER) if POPPLER.exists() else shutil.which('pdftoppm')
                if not binary:
                    raise RuntimeError('Preview is unavailable; you can open the original PDF.')
                subprocess.run([binary, '-f', '1', '-singlefile', '-scale-to', '1800', '-png', str(document), str(prefix)],
                               check=True, timeout=25, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return target


class Handler(BaseHTTPRequestHandler):
    server_version = 'Applications/1'

    def log_message(self, fmt, *args):
        print(f'{now()} {fmt % args}', flush=True)

    def valid_host(self):
        host = self.headers.get('Host', '')
        return host in {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}',
                        self.server.public_host} - {''}

    def cookie(self, name):
        try:
            cookies = SimpleCookie(self.headers.get('Cookie', ''))
            return cookies[name].value if name in cookies else ''
        except Exception:
            return ''

    def logged_in(self):
        return not self.server.auth or self.server.auth.authenticated(self.cookie('empleo_session'))

    def csrf_token(self):
        return self.server.auth.csrf(self.cookie('empleo_session')) if self.server.auth else self.server.csrf

    def redirect(self, location):
        return self.respond('', 'text/plain; charset=utf-8', 303, headers=[('Location', location)])

    def session_cookie(self, name, value, age):
        return ('Set-Cookie', f'{name}={value}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age={age}')

    def respond(self, data, mime='application/json; charset=utf-8', status=200, attachment=None, headers=()):
        if isinstance(data, (dict, list)):
            data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        elif isinstance(data, str):
            data = data.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'SAMEORIGIN')
        self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        self.send_header('X-Robots-Tag', 'noindex, nofollow, noarchive')
        if self.server.public_url:
            self.send_header('Strict-Transport-Security', 'max-age=31536000')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'self'; frame-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'self'; form-action 'self'")
        if attachment:
            self.send_header('Content-Disposition', f'attachment; filename="{attachment}"')
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def fail(self, message, status=400):
        self.respond({'error': message}, status=status)

    def do_GET(self):
        if not self.valid_host():
            return self.fail('Host not allowed.', 403)
        try:
            parts = urlsplit(self.path)
            path = unquote(parts.path)
            if path == '/api/health':
                if self.server.public_url:
                    return self.respond({'app': IDENTITY, 'status': 'ok'})
                return self.respond({'app': IDENTITY, 'status': 'ok', 'pid': os.getpid(), 'root': str(APP), 'workspace': str(self.server.content_root.resolve())})
            if path == '/auth/session':
                return self.respond({'authenticated': self.logged_in(), 'challenge': bool(self.cookie('empleo_challenge'))})
            if path == '/auth/config':
                return self.respond({'brand': self.server.brand, 'bot_name': self.server.bot_name})
            if path == '/login':
                if self.logged_in():
                    return self.redirect('/')
                return self.respond((PUBLIC / 'login.html').read_bytes(), 'text/html; charset=utf-8')
            public_assets = {'/login.js': ('login.js', 'text/javascript; charset=utf-8'),
                             '/styles.css': ('styles.css', 'text/css; charset=utf-8'),
                             '/favicon.svg': ('favicon.svg', 'image/svg+xml'),
                             '/manifest.webmanifest': ('manifest.webmanifest', 'application/manifest+json'),
                             '/icons.js': ('icons.js', 'text/javascript; charset=utf-8'),
                             '/icons.svg': ('icons.svg', 'image/svg+xml'),
                             '/app-192.png': ('app-192.png', 'image/png'),
                             '/app-512.png': ('app-512.png', 'image/png')}
            if path in public_assets:
                name, mime = public_assets[path]
                return self.respond((PUBLIC / name).read_bytes(), mime)
            if not self.logged_in():
                if path == '/':
                    return self.redirect('/login')
                return self.fail('Sign in with your Telegram code to continue.', 401)
            root = self.server.content_root.resolve()
            source = root
            documents = root / 'documents'
            if path == '/api/data':
                return self.respond({'catalog': self.server.catalog(root), 'reviews': self.server.store.load(),
                                     'profile': read_json(source / 'candidate.json'),
                                     'preferences': read_json(source / 'preferences.json'),
                                     'cv_variants': read_json(source / 'cv-versions.json'), 'csrf': self.csrf_token(),
                                     'trial': self.server.trial(root), 'daily_runs': self.server.daily_runs(root),
                                     'remote': bool(self.server.public_url)})
            if path == '/api/export':
                return self.respond({'exported_at': now(), 'catalog': self.server.catalog(root),
                                     'reviews': self.server.store.load()}, attachment='job-search-data.json')
            if path == '/api/report':
                return self.respond(self.report(), 'text/plain; charset=utf-8', attachment='application-report.txt')
            if path.startswith('/reports/'):
                name = path.split('/', 2)[2]
                if name not in self.server.reports(root):
                    return self.fail('Report not found.', 404)
                report = root / 'reports' / name
                if not report.is_file():
                    return self.fail('The report has not been saved yet.', 404)
                return self.respond(report.read_text(encoding='utf-8'), 'text/plain; charset=utf-8', attachment=name if parts.query == 'download=1' else None)
            if path.startswith('/receipts/'):
                name = path.split('/', 2)[2]
                allowed = {Path((j.get('application', {}).get('evidence_file') or '').replace('\\', '/')).name for j in self.server.catalog(root)['jobs']}
                mime = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}.get(Path(name).suffix.lower())
                if name not in allowed or Path(name).name != name or not mime:
                    return self.fail('Confirmation receipt not found.', 404)
                return self.respond((root / 'receipts' / name).read_bytes(), mime)
            if path.startswith('/files/') or path.startswith('/preview/'):
                name = path.split('/', 2)[2]
                if name not in self.server.documents(self.server.catalog(root)):
                    return self.fail('Document not found.', 404)
                document = documents / name
                if not document.is_file():
                    return self.fail('The PDF has not been prepared yet.', 404)
                if path.startswith('/preview/'):
                    return self.respond(self.server.preview(document).read_bytes(), 'image/png')
                return self.respond(document.read_bytes(), 'application/pdf', attachment=name if parts.query == 'download=1' else None)
            static = {'/': ('index.html', 'text/html; charset=utf-8'),
                      '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                      '/styles.css': ('styles.css', 'text/css; charset=utf-8'),
                      '/favicon.svg': ('favicon.svg', 'image/svg+xml')}
            if path in static:
                name, mime = static[path]
                return self.respond((PUBLIC / name).read_bytes(), mime)
            return self.fail('Page not found.', 404)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            print(f'Read error: {type(error).__name__}: {error}', file=sys.stderr, flush=True)
            return self.fail('Data could not be loaded. Your saved decisions are preserved.', 500)

    def do_POST(self):
        # Read the bounded request before rejecting headers so clients receive the
        # JSON error instead of a TCP reset while their body is still in flight.
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length < 2 or length > 100_000:
                return self.fail('Request body is too large or empty.', 413)
            self.connection.settimeout(5)
            raw_body = self.rfile.read(length)
            if len(raw_body) != length:
                return self.fail('Incomplete request body.', 400)
        except (OSError, ValueError):
            return self.fail('The request could not be read.', 400)
        origin = self.headers.get('Origin')
        allowed_origins = ({self.server.public_url} if self.server.public_url else
                           {f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'})
        if not self.valid_host() or (self.server.public_url and not origin) or (origin and origin not in allowed_origins):
            return self.fail('Request not allowed.', 403)
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.fail('Expected JSON.', 415)
        try:
            path = unquote(urlsplit(self.path).path)
            body = json.loads(raw_body)
            if self.server.auth and path == '/auth/request':
                challenge = self.server.auth.request_code(self.cookie('empleo_challenge'))
                return self.respond({'sent': True, 'expires_in': 300}, headers=[self.session_cookie('empleo_challenge', challenge, 300)])
            if self.server.auth and path == '/auth/verify':
                if not isinstance(body, dict):
                    return self.fail('Invalid content.')
                token = self.server.auth.verify(self.cookie('empleo_challenge'), body.get('code'))
                return self.respond({'authenticated': True}, headers=[
                    self.session_cookie('empleo_session', token, self.server.auth.session_seconds),
                    self.session_cookie('empleo_challenge', '', 0)])
            if not self.logged_in():
                return self.fail('Your session has ended. Sign in again with Telegram.', 401)
            if not secrets.compare_digest(self.headers.get('X-Radar-Token', ''), self.csrf_token()):
                return self.fail('Request not allowed.', 403)
            if self.server.auth and path == '/auth/logout':
                self.server.auth.logout(self.cookie('empleo_session'))
                return self.respond({'authenticated': False}, headers=[self.session_cookie('empleo_session', '', 0)])
            if not isinstance(body, dict) or not isinstance(body.get('revision'), int):
                return self.fail('Invalid data revision.')
            if path.startswith('/api/jobs/'):
                body['decision'] = normalize_decision(body.get('decision'))
                body['cv_review'] = normalize_cv_review(body.get('cv_review'))
                identifier = path.removeprefix('/api/jobs/')
                job = next((j for j in self.server.catalog()['jobs'] if j['id'] == identifier), None)
                if not job:
                    return self.fail('Job not found.', 404)
                if body.get('decision') not in {'pending', 'prioritize', 'review', 'reserve', 'discard'}:
                    return self.fail('Invalid decision.')
                if body.get('cv_review') not in {'pending', 'approved', 'changes'}:
                    return self.fail('Invalid CV review status.')
                cv = job.get('cv_prepared')
                if not cv and body['cv_review'] != 'pending':
                    return self.fail('There is no CV to review yet.')
                reference = body.get('cv_reference')
                if cv and reference != cv.get('sha256'):
                    return self.fail('The CV version has changed. Refresh before reviewing it.', 409)
                fields = {key: body.get(key, '') for key in ['decision', 'cv_review', 'notes', 'cv_notes', 'evidence_notes']}
                for key in ['notes', 'cv_notes', 'evidence_notes']:
                    if not isinstance(fields[key], str) or len(fields[key]) > 16000:
                        return self.fail('Notes must be under 16,000 characters.')
                fields['cv_reference'] = reference
                updated = self.server.store.update('job', identifier, fields, body['revision'])
            elif path == '/api/profile':
                fields = {key: body.get(key, '') for key in ['ai_stack', 'examples', 'english', 'mobility', 'other']}
                if any(not isinstance(v, str) or len(v) > 16000 for v in fields.values()):
                    return self.fail('Text must be under 16,000 characters per field.')
                updated = self.server.store.update('profile', None, fields, body['revision'])
            else:
                return self.fail('Route not found.', 404)
            return self.respond({'saved': True, 'reviews': updated})
        except AuthError as error:
            return self.fail(str(error), error.status)
        except ValueError as error:
            return self.fail(str(error), 409 if 'Another tab' in str(error) else 400)
        except OSError:
            return self.fail('Save failed. Keep this page open and try again.', 500)

    def report(self):
        state = self.server.catalog()
        reviews = self.server.store.load()
        lines = ['JOB SEARCH WORKSPACE', f'Exported: {now()}',
                 'Publication times are those observed during review, not live updates.',
                 'Preparing or approving a CV does not mean an application was submitted.', '']
        ordered = sorted(state['jobs'], key=lambda j: j['analysis'].get('rank', 99))
        for job in ordered:
            user = reviews['jobs'].get(job['id'], {})
            cv = job.get('cv_prepared')
            application = job.get('application', {})
            lines += [f"{job['company']} · {job['title']}", job['url'],
                      f"Salary: {job['salary']['label']} | Work arrangement: {job['mode']} | {job['location']}",
                      f"Reviewed: {job['verified_on']} | Observed publication: {job['published_label']}",
                      f"Recommendation: {job['analysis'].get('recommendation', job['decision'])}",
                      f"Reason: {job['why']}", 'Fit: ' + '; '.join(job['strengths']),
                      'To confirm: ' + '; '.join(job['gaps']),
                      f"Your decision: {user.get('decision', 'pending')}",
                      f"Prepared CV: {cv['filename'] if cv else 'Not prepared'}",
                      f"CV review: {user.get('cv_review', 'pending')}",
                      f"Tailoring: {cv['tailoring'] if cv else job['analysis'].get('cv_plan', 'Pending')}",
                      f"Job notes: {user.get('notes', '')}", f"Proposed CV changes: {user.get('cv_notes', '')}",
                      f"Evidence provided: {user.get('evidence_notes', '')}",
                      f"Application submitted: {'Yes' if application.get('sent') else 'No'}",
                      f"Submitted CV: {application.get('cv_sent') or 'None'}",
                      f"Submission date: {application.get('sent_at') or 'Not submitted'}",
                      f"Result: {application.get('label') or 'Pending'}",
                      f"Confirmation or reason: {application.get('evidence') or 'Unconfirmed'}",
                      f"Channel: {application.get('channel') or 'Pending'}",
                      f"Form answers: {json.dumps(application.get('answers', {}), ensure_ascii=False)}",
                      f"Next step: {job['next_step']}", '']
        lines += ['PROFILE NOTES', json.dumps(reviews['profile'], ensure_ascii=False, indent=2)]
        if self.server.trial():
            trial = self.server.trial()
            lines += ['', 'DAILY TRIAL', f"Period: {trial['start_date']} to {trial['end_date']} | {trial['time']} {trial['timezone']}",
                      'No automatic renewal. Check the authorization terms for this trial.',
                      'Recorded runs: ' + str(len(self.server.daily_runs()))]
            for run in self.server.daily_runs():
                lines += [f"{run.get('scheduled_date')} | {run.get('status')} | {run.get('summary', '')}",
                          f"Report: {run.get('report_filename') or 'Pending'}"]
        return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--data-dir', type=Path, default=Path(os.environ.get('WORKSPACE_REVIEW_DIR', str(ROOT / 'reviews'))))
    options = parser.parse_args()
    server = RadarServer(('127.0.0.1', options.port), options.data_dir)
    print(f'Job Search Workspace: http://127.0.0.1:{server.server_port}', flush=True)
    print(f'Decisions: {server.store.path}', flush=True)
    try:
        server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
