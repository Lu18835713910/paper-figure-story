"""Local unit regressions for the existing host notes interface, no paper parsing."""
from pathlib import Path
import json,subprocess,unittest,os,shutil
ROOT=Path(__file__).resolve().parents[1]
NODE=os.environ.get('PFS_TEST_NODE') or shutil.which('node')
class NotesContract(unittest.TestCase):
    def notes(self,scene):
        if not NODE:self.skipTest('Explicit compatible Node runtime not supplied')
        source=(ROOT/'scripts/speaker_notes.mjs').as_uri()
        script='import {humanSpeakerNotes} from '+json.dumps(source)+';console.log(JSON.stringify(humanSpeakerNotes('+json.dumps(scene,ensure_ascii=False)+',{statements:[],nodes:[]},"balanced")));'
        p=subprocess.run([NODE,'--input-type=module','-e',script],capture_output=True,encoding='utf-8',check=True)
        return json.loads(p.stdout)
    def test_full_scene_snapshot(self):
        text=self.notes({'title':'q','elements':[],'logic_snapshot':'a'*64,'citation':'model aaaaaaaaaaaa'})
        self.assertIn('模型快照：'+'a'*64,text)
    def test_notes_snapshot_fallback(self):
        text=self.notes({'title':'q','elements':[],'notes':{'logic_model_snapshot':'b'*64}})
        self.assertIn('b'*64,text)
    def test_legacy_does_not_invent_snapshot(self):
        text=self.notes({'title':'q','elements':[]})
        self.assertNotIn('模型快照：',text)
    def test_explicit_script_and_boundary_preserved(self):
        text=self.notes({'title':'q','elements':[],'notes':{'speaker_script':'相关，不证明因果。'}})
        self.assertIn('相关，不证明因果。',text)
    def test_partial_not_upgraded(self):
        text=self.notes({'title':'q','elements':[],'notes':{'speaker_script':'科学终审PARTIAL'}})
        self.assertIn('PARTIAL',text);self.assertNotIn('科学终审PASS',text)
if __name__=='__main__':unittest.main()
