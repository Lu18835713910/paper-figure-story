"""Packaging-root, exact Unicode name and byte identity regressions."""
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,unittest,warnings
from zipfile import ZipFile,ZIP_STORED,BadZipFile

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'scripts'))
import candidate_fingerprint as cf


class CandidateFingerprint(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.source=self.root/'source';self.source.mkdir()
        (self.source/'VERSION').write_text('1.1.1-synthetic\n','utf8')
        d=self.source/'marketing';d.mkdir();(d/'小红书文案.md').write_text('合成示例，不是论文结果。\n','utf8')

    def archive(self,wrapper='paper-figure-story'):
        z=self.root/'candidate.zip'
        with ZipFile(z,'w') as archive:
            for p in self.source.rglob('*'):
                if p.is_file():archive.write(p,wrapper+'/'+p.relative_to(self.source).as_posix())
        return z

    def test_matches_legacy_closeout_formula_exactly(self):
        files={p.relative_to(self.source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in self.source.rglob('*') if p.is_file()}
        expected=hashlib.sha256('\n'.join(f'{p} {files[p]}' for p in sorted(files)).encode()).hexdigest()
        r=cf.directory_fingerprint(self.source)
        self.assertEqual(r['aggregate_sha256'],expected)
        self.assertNotEqual(expected,hashlib.sha256(('\n'.join(f'{p} {files[p]}' for p in sorted(files))+'\n').encode()).hexdigest())

    def test_utf8_zip_names_crc_extract_hash_and_aggregate_match(self):
        z=self.archive()
        with ZipFile(z) as archive:
            self.assertIsNone(archive.testzip())
            member=archive.getinfo('paper-figure-story/marketing/小红书文案.md')
            self.assertTrue(member.flag_bits & 0x800)
            archive.extractall(self.root/'extracted')
        a=cf.directory_fingerprint(self.source)
        b=cf.zip_fingerprint(z,'paper-figure-story')
        c=cf.directory_fingerprint(self.root/'extracted'/'paper-figure-story')
        self.assertEqual(a,b);self.assertEqual(a,c)

    def test_root_is_explicit_and_absolute_location_is_not_hashed(self):
        target=self.root/'other'/'wrapper';target.mkdir(parents=True)
        for p in self.source.rglob('*'):
            if p.is_file():
                q=target/p.relative_to(self.source);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
        self.assertEqual(cf.directory_fingerprint(self.source),cf.directory_fingerprint(target))
        r=subprocess.run([sys.executable,'-B',str(BASE/'scripts/candidate_fingerprint.py')],capture_output=True,text=True,encoding='utf8')
        self.assertNotEqual(r.returncode,0)

    def test_cli_directory_and_wrapper_zip_match(self):
        script=str(BASE/'scripts/candidate_fingerprint.py');z=self.archive()
        a=subprocess.run([sys.executable,'-B',script,'--root',str(self.source)],capture_output=True,text=True,encoding='utf8')
        b=subprocess.run([sys.executable,'-B',script,'--zip',str(z),'--zip-root','paper-figure-story'],capture_output=True,text=True,encoding='utf8')
        self.assertEqual(a.returncode,0,a.stderr);self.assertEqual(b.returncode,0,b.stderr)
        self.assertEqual(json.loads(a.stdout),json.loads(b.stdout))

    def test_wrong_wrapper_rejected(self):
        with self.assertRaisesRegex(ValueError,'CANDIDATE_ZIP_WRAPPER_MISMATCH'):
            cf.zip_fingerprint(self.archive(),'different-wrapper')

    def test_duplicate_and_traversal_member_names_rejected(self):
        for names in [['root/../outside'],['root/same','root/same']]:
            with self.subTest(names=names):
                z=self.root/'invalid.zip'
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore',UserWarning)
                    with ZipFile(z,'w') as archive:
                        for name in names:archive.writestr(name,b'body')
                with self.assertRaisesRegex(ValueError,'CANDIDATE_ZIP_(PATH_INVALID|DUPLICATE)'):
                    cf.zip_fingerprint(z,'root')

    def test_changed_file_changes_aggregate(self):
        before=cf.directory_fingerprint(self.source)
        (self.source/'VERSION').write_text('changed\n','utf8')
        after=cf.directory_fingerprint(self.source)
        self.assertNotEqual(before['aggregate_sha256'],after['aggregate_sha256'])

    def test_corrupted_member_fails_crc_and_cli(self):
        z=self.root/'corrupt.zip'
        with ZipFile(z,'w',compression=ZIP_STORED) as archive:archive.writestr('root/a.txt',b'content')
        data=bytearray(z.read_bytes());offset=30+len('root/a.txt');data[offset]^=1;z.write_bytes(data)
        with self.assertRaises((BadZipFile,ValueError)):cf.zip_fingerprint(z,'root')
        r=subprocess.run([sys.executable,'-B',str(BASE/'scripts/candidate_fingerprint.py'),'--zip',str(z),'--zip-root','root'],capture_output=True,text=True,encoding='utf8')
        self.assertEqual(r.returncode,2)
        self.assertFalse(json.loads(r.stdout)['valid'])

    def test_office_lock_files_excluded_like_baseline(self):
        before=cf.directory_fingerprint(self.source)
        (self.source/'~$working.docx').write_bytes(b'temporary office lock')
        self.assertEqual(before,cf.directory_fingerprint(self.source))
        self.assertEqual(before,cf.zip_fingerprint(self.archive(),'paper-figure-story'))


if __name__=='__main__':unittest.main()
