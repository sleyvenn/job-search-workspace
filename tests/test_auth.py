from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from auth import AuthStore, AuthError


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.codes=[]; self.time=[1000.0]
        self.auth=AuthStore(self.temp.name,'test','test',self.codes.append,lambda:self.time[0])
    def tearDown(self): self.temp.cleanup()

    def test_one_use_and_persistent_session(self):
        challenge=self.auth.request_code(); code=self.codes[-1]
        token=self.auth.verify(challenge,code)
        with self.assertRaises(AuthError): self.auth.verify(challenge,code)
        other=AuthStore(self.temp.name,'test','test',self.codes.append,lambda:self.time[0])
        self.assertTrue(other.authenticated(token))
        other.logout(token)
        self.assertFalse(self.auth.authenticated(token))

    def test_rate_limit_expiry_and_attempt_limit(self):
        challenge=self.auth.request_code()
        with self.assertRaises(AuthError): self.auth.request_code()
        code=self.codes[-1]; wrong='000000' if code!='000000' else '111111'
        for _ in range(5):
            with self.assertRaises(AuthError): self.auth.verify(challenge,wrong)
        with self.assertRaises(AuthError): self.auth.verify(challenge,code)
        self.time[0]+=61; challenge=self.auth.request_code()
        self.time[0]+=301
        with self.assertRaises(AuthError): self.auth.verify(challenge,self.codes[-1])


if __name__=='__main__': unittest.main()
