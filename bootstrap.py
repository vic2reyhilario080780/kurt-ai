"""Portable, stdlib-only setup. Run with Python 3.10+; never install globally."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent
FEATURES = ('web', 'media', 'voice', 'desktop', 'migration')


def installation_plan(root, system, features, *, cli_tools=False, browser=False):
    if system not in ('Windows','Darwin','Linux'):
        raise ValueError('Supported desktop systems: Windows, macOS and Linux.')
    if any(f not in FEATURES for f in features): raise ValueError('Unknown optional feature.')
    environment = root/'.venv'
    python = environment/('Scripts/python.exe' if system == 'Windows' else 'bin/python')
    selection = sorted(set(features) | ({'web'} if browser else set()))
    target = str(root) + ('['+','.join(selection)+']' if selection else '')
    commands = [[str(python),'-m','pip','install','-e',target],
                [str(python),'-m','pip','check'],
                [str(python),'-m','kurt.main','device','status']]
    if browser: commands.insert(1,[str(python),'-m','playwright','install','chromium'])
    return {'os':system,'architecture':platform.machine(),'environment':str(environment),
            'python':str(python),'features':selection,'commands':commands,'cli_tools':cli_tools,
            'downloads_local_models':False,'global_python_install':False}


def install(args):
    if sys.version_info < (3,10): raise ValueError('Install Python 3.10 or newer from https://www.python.org/downloads/.')
    features = [f.strip() for f in args.features.split(',') if f.strip()]
    if getattr(args,'credentials_file',None):
        if not Path(args.credentials_file).expanduser().is_file(): raise ValueError('Encrypted credential transfer file not found.')
        features.append('migration')
    plan = installation_plan(ROOT,platform.system(),features,cli_tools=args.cli_tools,browser=args.browser)
    if args.dry_run:
        print(json.dumps(plan,indent=2)); return
    environment = Path(plan['environment'])
    marker = environment/'kurt-install.json'
    if environment.exists():
        if not (environment/'pyvenv.cfg').is_file() or not Path(plan['python']).is_file():
            raise ValueError('This .venv is incomplete or from another OS. Use a fresh project copy without .venv; do not copy environments between computers.')
        if marker.is_file():
            previous = json.loads(marker.read_text())
            if (previous.get('os') != plan['os'] or previous.get('architecture') != plan['architecture'] or
                    previous.get('project') != str(ROOT)):
                raise ValueError('This .venv belongs to another OS, CPU or project location. Install into a fresh project copy.')
    else:
        venv.EnvBuilder(with_pip=True).create(environment)
    if args.cli_tools and not shutil.which('npm'):
        raise ValueError('Optional CLI tools require Node.js/npm. Install a supported Node.js LTS first or rerun without --cli-tools.')
    for command in plan['commands']:
        subprocess.run(command,cwd=ROOT,check=True)
    if args.cli_tools:
        # npm.cmd is a batch file on Windows. Only fixed, trusted arguments are
        # passed; no task text or user-supplied command enters this invocation.
        subprocess.run([shutil.which('npm'),'install','--prefix',str(ROOT)],cwd=ROOT,check=True)
    if getattr(args,'credentials_file',None):
        subprocess.run([plan['python'],'-m','kurt.main','device','import-credentials',
                        str(Path(args.credentials_file).expanduser().resolve())],cwd=ROOT,check=True)
    marker.write_text(json.dumps({'os':plan['os'],'architecture':plan['architecture'],'project':str(ROOT),
                                 'features':plan['features']},indent=2)+'\n')
    print('\nKurt installed in '+str(environment)+'. No model weights were downloaded.')
    if getattr(args,'credentials_file',None): print('Personal .env transfer imported. CLI OAuth logins still require this device\'s authorization.')
    else: print('API keys/login on this computer: '+str(Path(plan['python']))+' -m kurt.main setup')
    if args.launch: subprocess.run([plan['python'],'-m','kurt.main','chat'],cwd=ROOT,check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--features',default='web,media,voice',help='Optional comma-separated web,media,voice,desktop,migration; empty means core only')
    parser.add_argument('--cli-tools',action='store_true',help='Also install project-local npm AI CLIs; requires Node/npm')
    parser.add_argument('--browser',action='store_true',help='Also download Chromium for browser automation')
    parser.add_argument('--credentials-file',help='Private encrypted .env transfer; prompts for its passphrase after install')
    parser.add_argument('--launch',action='store_true',help='Launch chat after successful installation')
    parser.add_argument('--dry-run',action='store_true',help='Print the plan without writing files or installing packages')
    try: install(parser.parse_args())
    except (ValueError,OSError,subprocess.CalledProcessError) as exc:
        print('Setup incomplete: '+str(exc),file=sys.stderr); return 1
    return 0


if __name__ == '__main__': raise SystemExit(main())
