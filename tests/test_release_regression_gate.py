from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_release_regressions import assess,declared_tests

class ReleaseGate(unittest.TestCase):
    def good(self):return 'test_one (__main__.Suite.test_one) ... ok\n\nRan 1 test in 0.001s\n\nOK\n'
    def test_real_success_id_and_count(self):self.assertTrue(assess(self.good(),0,{'Suite.test_one'})['valid'])
    def test_all_skipped_zero_exit_rejected(self):
        text=self.good().replace('... ok','... skipped \'fixture missing\'').replace('OK\n','OK (skipped=1)\n')
        r=assess(text,0,{'Suite.test_one'});self.assertFalse(r['valid']);self.assertEqual(r['skipped'],1)
    def test_missing_test_rejected(self):self.assertFalse(assess(self.good(),0,{'Suite.test_one','Suite.test_two'})['valid'])
    def test_wrong_test_identity_rejected(self):self.assertFalse(assess(self.good(),0,{'Other.test_one'})['valid'])
    def test_zero_without_ran_rejected(self):self.assertFalse(assess('OK\n',0,{'Suite.test_one'})['valid'])
    def test_nonzero_even_with_ok_rejected(self):self.assertFalse(assess(self.good(),2,{'Suite.test_one'})['valid'])
    def test_required_real_cli_fixture_tests_present(self):
        root=Path(__file__).resolve().parent
        self.assertEqual(len(declared_tests(root/'test_ooxml_merge_integrity.py')),7)
        self.assertEqual(len(declared_tests(root/'test_logic_navigation_contract.py')),20)
if __name__=='__main__':unittest.main()
