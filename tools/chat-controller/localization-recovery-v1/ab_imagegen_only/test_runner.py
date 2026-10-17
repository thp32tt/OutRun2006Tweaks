import datetime as dt,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import runner
class RunnerTests(unittest.TestCase):
 def test_KST_alternates(self):
  expected={0:'A',10:'B',20:'A',30:'B',40:'A',50:'B'}
  for i in range(60):
   d=dt.datetime(2026,10,18,11,i,tzinfo=runner.KST)
   slot=runner.slot_at(d)
   self.assertEqual(slot['role'] if slot else None,expected.get(i))
 def test_UTC_converts_to_KST(self):
  t=dt.datetime(2026,10,18,1,10,tzinfo=dt.timezone.utc)
  self.assertEqual(runner.slot_at(t)['role'],'B')
 def test_reservation_persists(self):
  with tempfile.TemporaryDirectory() as root:
   with patch.object(runner,'STATE_ROOT',Path(root)):
    job=(None,{'task_id':'OUTRUN-KR-TEST-0001','input_sha256':'a'*64},None,None)
    slot={'key':'2026-10-18T11:10+0900','role':'B'}
    ok,_=runner.reserve('B',slot,job);self.assertTrue(ok)
    ok,msg=runner.reserve('B',slot,job);self.assertFalse(ok)
    self.assertEqual(msg,'ALREADY_ATTEMPTED')
 def test_no_work_at_unscheduled_minutes(self):
  self.assertIsNone(runner.slot_at(dt.datetime(2026,10,18,11,7,tzinfo=runner.KST)))
if __name__=='__main__':unittest.main()