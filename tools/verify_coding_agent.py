"""Opt-in live Kurt coding smoke test on a disposable synthetic repository."""
import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kurt.core.coding import run_coding_task
from kurt.utils.env_loader import load_env


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true',required=True,help='Use the configured AI provider; may consume quota')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    load_env()
    with tempfile.TemporaryDirectory(prefix='kurt-coding-live-') as folder:
        root=Path(folder)
        (root/'calc.py').write_text('def add(a, b):\n    return a - b\n')
        (root/'test_calc.py').write_text('import unittest\nfrom calc import add\nclass TestAdd(unittest.TestCase):\n def test_add(self): self.assertEqual(add(1, 2), 3)\n')
        subprocess.run(['git','init','-q',folder],check=True,capture_output=True)
        subprocess.run(['git','-C',folder,'add','calc.py','test_calc.py'],check=True,capture_output=True)
        subprocess.run(['git','-C',folder,'-c','user.name=Kurt Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture baseline'],check=True,capture_output=True)
        task=('In this synthetic fixture workspace only, read calc.py and test_calc.py, fix the incorrect add implementation, '
              'run the test using run_checks, inspect the diff and finish with done. Do not delegate to other agents/CLIs, '
              'use web/desktop tools, install packages, or modify files outside this workspace.')
        result=run_coding_task(task,cwd=root,max_steps=8,checks=[[sys.executable,'-m','unittest','-q','test_calc']])
        report={'tested_at':datetime.now(timezone.utc).isoformat(),'backend':result['backend'],'status':result['status'],
                'verification':result['verification'],'git_diff_status':result['diff']['status'],'actual_fix_present':'return a + b' in (root/'calc.py').read_text(),
                'checks':[{'status':c['status'],'exit_code':c['exit_code']} for c in result['checks']],
                'fixture':'disposable synthetic arithmetic repository','production_files_modified':False,
                'delegated_agents':False}
    if args.output:args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if report['status']=='completed' and report['verification']=='passed' and report['actual_fix_present'] else 1


if __name__=='__main__':raise SystemExit(main())
