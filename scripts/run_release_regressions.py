"""Run declared official unittest CLIs with hash-bound fixtures; fail on any SKIP.

This is a test gate, not a scheduler or a scientific-quality assessment. Fixture
configuration stays outside the skill, because it may contain private papers.
"""
import argparse,ast,hashlib,json,os,re,subprocess,sys
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def declared_tests(path):
    tree=ast.parse(Path(path).read_text('utf-8-sig'))
    return {c.name+'.'+f.name for c in tree.body if isinstance(c,ast.ClassDef)
            for f in c.body if isinstance(f,(ast.FunctionDef,ast.AsyncFunctionDef)) and f.name.startswith('test_')}

def assess(text,exit_code,expected):
    ran=re.search(r'^Ran (\d+) tests? in ',text,re.M)
    found=set(re.findall(r'^test_\w+ \((?:__main__\.)?([\w.]+)\)',text,re.M))
    # unittest reports skips both per-test and in its summary. Never trust just
    # the process exit code (all-skipped suites exit zero).
    skipped=len(re.findall(r'\.\.\. skipped\b',text))
    summary=re.search(r'\bskipped=(\d+)',text)
    skipped=max(skipped,int(summary.group(1)) if summary else 0)
    errors=[]
    if exit_code:errors.append('TEST_EXIT_NONZERO')
    if ran is None or int(ran.group(1))!=len(expected):errors.append('TEST_COUNT_MISMATCH')
    if found!=set(expected):errors.append('TEST_IDENTITY_MISMATCH')
    if skipped:errors.append('TEST_SKIPPED')
    if not re.search(r'^OK(?:\s|$)',text,re.M):errors.append('TEST_SUCCESS_SUMMARY_MISSING')
    return dict(valid=not errors,errors=errors,ran=int(ran.group(1)) if ran else None,skipped=skipped,expected=sorted(expected),observed=sorted(found),exit_code=exit_code)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True,type=Path);p.add_argument('--outdir',required=True,type=Path);a=p.parse_args()
    cfg=json.loads(a.config.read_text('utf-8-sig'));root=Path(__file__).resolve().parents[1]
    if a.outdir.exists():p.error('OUTPUT_EXISTS: keep prior failures and choose a new output directory')
    a.outdir.mkdir(parents=True);errors=[]
    for r in cfg['fixtures']:
        try:
            if sha(r['path'])!=r['sha256']:errors.append('FIXTURE_SHA_DRIFT:'+r['path'])
        except OSError:errors.append('FIXTURE_MISSING:'+r['path'])
    suites=cfg['suites'];names={r['test'] for r in suites}
    for required,count in [('test_ooxml_merge_integrity.py',7),('test_logic_navigation_contract.py',20),('test_native_freeform_contract.py',14)]:
        row=next((r for r in suites if r['test']==required),None)
        if row is None or len(declared_tests(root/'tests'/required))!=count:errors.append('MANDATORY_REGRESSION_IDENTITY:'+required)
    if len(names)!=len(suites):errors.append('DUPLICATE_SUITE')
    report=dict(valid=False,errors=errors,config_sha256=sha(a.config),runs=[],scientific_review='NOT_ASSESSED')
    env={**os.environ,**cfg['environment'],'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'}
    if not errors:
        for suite in suites:
            f=root/'tests'/suite['test'];expected=declared_tests(f)
            if sha(f)!=suite['sha256']:errors.append('TEST_SOURCE_DRIFT:'+suite['test']);break
            cmd=[sys.executable,'-B',str(f),'-v'];r=subprocess.run(cmd,cwd=root,env=env,capture_output=True)
            prefix=a.outdir/f.stem
            prefix.with_suffix('.stdout.log').write_bytes(r.stdout);prefix.with_suffix('.stderr.log').write_bytes(r.stderr)
            result=assess((r.stdout+r.stderr).decode('utf-8','replace'),r.returncode,expected)
            result.update(test=suite['test'],command=cmd,source_sha256=sha(f),stdout_sha256=sha(prefix.with_suffix('.stdout.log')),stderr_sha256=sha(prefix.with_suffix('.stderr.log')))
            report['runs'].append(result)
            if not result['valid']:errors.append('REGRESSION_REJECTED:'+suite['test'])
    report.update(valid=not errors,errors=errors,total_ran=sum(r['ran'] or 0 for r in report['runs']),total_skipped=sum(r['skipped'] for r in report['runs']))
    (a.outdir/'regression_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='runs'},ensure_ascii=False));return 0 if report['valid'] else 2
if __name__=='__main__':raise SystemExit(main())
