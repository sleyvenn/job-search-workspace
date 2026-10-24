"""Single-owner Telegram OTP login. Secrets and session tokens never enter logs."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from contextlib import contextmanager
from pathlib import Path
import secrets
import sqlite3
import threading
import time
from urllib.request import Request, urlopen


class AuthError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


class AuthStore:
    session_seconds = 30 * 24 * 3600
    code_seconds = 5 * 60

    def __init__(self, directory, telegram_token, telegram_chat, deliver=None, clock=time.time,
                 public_url='', bot_name='Telegram'):
        if not telegram_token or not telegram_chat:
            raise RuntimeError('Telegram is not configured. Public access remains disabled.')
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.database = directory / 'auth.sqlite'
        self.lock = threading.RLock()
        self.clock = clock
        self.telegram_token = telegram_token
        self.telegram_chat = telegram_chat
        self.public_url = public_url
        self.bot_name = bot_name
        self.deliver = deliver or self._telegram
        key_file = directory / 'auth.key'
        if not key_file.exists():
            try:
                fd = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                pass
            else:
                with os.fdopen(fd, 'wb') as handle:
                    handle.write(secrets.token_bytes(32))
        self.key = key_file.read_bytes()
        if len(self.key) != 32:
            raise RuntimeError('Invalid authentication key.')
        with self._db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS challenges (
                    id TEXT PRIMARY KEY, code TEXT NOT NULL, expires REAL NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, expires REAL NOT NULL, created REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS requests (created REAL NOT NULL);
            ''')
        if os.name != 'nt':
            self.database.chmod(0o600)

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.database, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def digest(self, value):
        return hmac.new(self.key, value.encode(), hashlib.sha256).hexdigest()

    def _telegram(self, code):
        body = json.dumps({
            'chat_id': self.telegram_chat,
            'text': (f'{self.bot_name} · Sign in to {self.public_url}\n\n'
                     f'Your code is: {code}\n\n'
                     'It expires in 5 minutes and can only be used once.\n'
                     'If you did not request this, ignore this message.'),
            'disable_notification': False,
        }).encode()
        request = Request(f'https://api.telegram.org/bot{self.telegram_token}/sendMessage',
                          data=body, headers={'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=15) as response:
                result = json.load(response)
            if not result.get('ok'):
                raise ValueError('Telegram delivery failed')
        except Exception:
            # Network errors can contain the secret-bearing Telegram URL.
            raise AuthError('Telegram could not send the code. Try again in a minute.', 502) from None

    def request_code(self, previous=None):
        stamp = self.clock()
        code = f'{secrets.randbelow(1_000_000):06d}'
        challenge = secrets.token_urlsafe(32)
        with self.lock, self._db() as db:
            db.execute('DELETE FROM requests WHERE created < ?', (stamp - 3600,))
            db.execute('DELETE FROM challenges WHERE expires < ?', (stamp,))
            db.execute('DELETE FROM sessions WHERE expires < ?', (stamp,))
            count, last = db.execute('SELECT COUNT(*), MAX(created) FROM requests').fetchone()
            if count >= 10:
                raise AuthError('Too many codes have been requested. Try again in an hour.', 429)
            if last is not None and stamp - last < 60:
                raise AuthError('Wait one minute before requesting another code.', 429)
            db.execute('INSERT INTO requests VALUES (?)', (stamp,))
            db.commit()
            self.deliver(code)
            if previous:
                db.execute('DELETE FROM challenges WHERE id = ?', (self.digest(previous),))
            db.execute('INSERT INTO challenges (id, code, expires) VALUES (?, ?, ?)',
                       (self.digest(challenge), self.digest(challenge + ':' + code), stamp + self.code_seconds))
        return challenge

    def verify(self, challenge, code):
        if not isinstance(code, str) or len(code) != 6 or not code.isascii() or not code.isdigit():
            raise AuthError('Enter the six digits from the Telegram message.')
        if not challenge or len(challenge) > 128:
            raise AuthError('Request a code from this browser before continuing.', 401)
        stamp = self.clock()
        failure = None
        with self.lock, self._db() as db:
            row = db.execute('SELECT code, expires, attempts FROM challenges WHERE id = ?',
                             (self.digest(challenge),)).fetchone()
            if not row or row[1] <= stamp or row[2] >= 5:
                failure = 'The code has expired or is no longer valid. Request a new one.'
            elif not hmac.compare_digest(row[0], self.digest(challenge + ':' + code)):
                db.execute('UPDATE challenges SET attempts = attempts + 1 WHERE id = ?', (self.digest(challenge),))
                failure = 'The code does not match. Check your Telegram message.'
            else:
                db.execute('DELETE FROM challenges WHERE id = ?', (self.digest(challenge),))
                token = secrets.token_urlsafe(32)
                db.execute('INSERT INTO sessions VALUES (?, ?, ?)',
                           (self.digest(token), stamp + self.session_seconds, stamp))
        if failure:
            raise AuthError(failure, 401)
        return token

    def authenticated(self, token):
        if not token or len(token) > 128:
            return False
        with self._db() as db:
            row = db.execute('SELECT expires FROM sessions WHERE id = ?', (self.digest(token),)).fetchone()
        return bool(row and row[0] > self.clock())

    def csrf(self, token):
        return self.digest('csrf:' + token)

    def logout(self, token):
        with self.lock, self._db() as db:
            db.execute('DELETE FROM sessions WHERE id = ?', (self.digest(token or ''),))
