#!/usr/bin/env python3
"""Explicit local test registry: a new test file cannot silently go unrun."""
# Install before filesystem imports can consume a shadowing bytecode module.
_bootstrap = (__file__.rpartition('/')[0] or '.') + '/../engine/source_runtime.py'
with open(_bootstrap, 'rb') as _source:
    exec(compile(_source.read(), _bootstrap, 'exec'), {'__name__': '_publication_source_runtime'})

import argparse
import json
import os
import re
import subprocess
import sys
import time
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REGISTRY = {
    'logic': ['test-publication-isolation.py','test-candidate.py','test-evidence.py','test-source-runtime.py','test-boundaries.py'],
    'adapters': ['test-reading.py'],
    'native': ['test-preview.py'],
}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group',choices=['all',*REGISTRY],default='all')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    registered={n for names in REGISTRY.values() for n in names}
    discovered={p.name for p in HERE.glob('test-*.py')}
    if registered!=discovered: raise RuntimeError('test registry mismatch: '+str(registered^discovered))
    args.output.mkdir(parents=True,exist_ok=False)
    results=[]
    def implementation():
        return {str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                for folder in ('engine','latex','tools') for p in sorted((HERE.parent/folder).rglob('*'))
                if p.is_file() and '__pycache__' not in p.parts}
    original = implementation()
    for group,names in REGISTRY.items():
        if args.group not in ('all',group): continue
        for name in names:
            start=time.monotonic()
            argv=[sys.executable,'-B',str(HERE/name)]
            proc=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=1800)
            log=proc.stdout.decode(errors='replace')
            (args.output/(name+'.log')).write_text(log)
            count=re.search(r'Ran (\d+) tests?',log)
            item={'group':group,'file':name,'argv':argv,'exit_code':proc.returncode,
                  'seconds':round(time.monotonic()-start,3),'tests':int(count[1]) if count else 0,
                  'skips':len(re.findall(r'\.\.\. skipped ',log)),
                  'status':'PASS' if proc.returncode==0 and count else 'FAIL'}
            if implementation() != original:
                current = implementation()
                item.update(status='FAIL', diagnostic='implementation changed during test run',
                            changed_files=[p for p in original.keys() | current.keys() if original.get(p) != current.get(p)])
            results.append(item)
            print(json.dumps(item),flush=True)
    report={'status':'PASS' if results and all(r['status']=='PASS' for r in results) else 'FAIL',
            'python':sys.version,'optimization':sys.flags.optimize,'results':results,
            'not_run':sorted(registered-{r['file'] for r in results}),
            'human_reading':'NOT_RUN_BY_TEST_RUNNER','ci':False}
    (args.output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__': raise SystemExit(main())
