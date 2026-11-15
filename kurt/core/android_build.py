"""Scoped Android build adapter. No implicit installs, uploads or signing secrets."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import zipfile

from kurt.utils.execution import sandbox_profile
from kurt.utils.process import run_bounded
from kurt.utils.security import child_env, redact, require_secure_endpoint
from kurt.utils.workspace import current_workspace, workspace_path, workspace


def _jdk():
    candidates = [Path(os.environ.get('JAVA_HOME', '/nonexistent'))]
    candidates += [Path('/opt/homebrew/opt/openjdk@17'), Path('/opt/homebrew/opt/openjdk@21'),
                   Path('/Applications/Android Studio.app/Contents/jbr/Contents/Home')]
    candidates += list(Path('/Library/Java/JavaVirtualMachines').glob('*/Contents/Home'))
    return next((p.resolve() for p in candidates if (p/'bin/java').is_file()), None)


def _sdk(project=None):
    candidates = []
    if project is not None and (project/'local.properties').is_file():
        local = workspace_path(project/'local.properties')
        with local.open() as stream: text = stream.read(16384)
        match = re.search(r'^\s*sdk\.dir\s*=\s*(.+?)\s*$', text, re.M)
        if match:
            value = match.group(1).replace('\\ ', ' ').replace('\\:', ':').replace('\\\\', '\\')
            candidate = Path(value).expanduser()
            candidates.append(candidate if candidate.is_absolute() else project/candidate)
    candidates += [Path(os.environ.get(k, '/nonexistent')) for k in ('ANDROID_HOME', 'ANDROID_SDK_ROOT')]
    candidates += [Path.home()/'Library/Android/sdk', Path('/opt/homebrew/share/android-commandlinetools')]
    return next((p.resolve() for p in candidates if (p/'platforms').is_dir() and (p/'build-tools').is_dir()), None)


def _project(project='.'):
    root = workspace_path(project)
    if not root.is_dir():
        raise ValueError('Android project directory does not exist.')
    if not (root/'gradlew').is_file() and (root/'android/gradlew').is_file():
        root = workspace_path(root/'android')
    return root


def android_profile(root, sdk, *, network=False):
    """Only this adapter grants self-process inspection needed by the JVM."""
    profile = sandbox_profile(workspace=current_workspace())
    profile += '\n(allow process-info* (target self))\n'
    profile += '(allow file-write* (literal "/dev/null"))\n'
    # Gradle uses a local single-use daemon even with --no-daemon. These
    # loopback sockets do not permit offline builds to fetch dependencies.
    profile += '(allow network-bind (local ip "localhost:*"))\n'
    profile += '(allow network-outbound (remote ip "localhost:*"))\n'
    profile += '(allow network-inbound (local ip "localhost:*"))\n'
    # SDK under Library is normally hidden from generated commands. Read-only,
    # exact SDK access does not grant access to the rest of the user's Library.
    profile += '(allow file-read* (subpath ' + json.dumps(str(sdk)) + '))\n'
    if network:
        profile = profile.replace('(deny network*)', '')
    return profile


def _run(argv, root, sdk, jdk, *, timeout=60, network=False):
    if platform.system() != 'Darwin' or not shutil.which('sandbox-exec'):
        return {'status': 'blocked', 'exit_code': None, 'stderr': 'Android build adapter currently requires the tested macOS sandbox.'}
    state = workspace_path(current_workspace()/'.kurt-build')
    state.mkdir(exist_ok=True)
    for name in ('gradle', 'android'):
        workspace_path(state/name).mkdir(exist_ok=True)
    env = child_env(extra={'JAVA_HOME': str(jdk), 'ANDROID_HOME': str(sdk), 'ANDROID_SDK_ROOT': str(sdk),
                           'GRADLE_USER_HOME': str(state/'gradle'), 'ANDROID_USER_HOME': str(state/'android'),
                           'PATH': str(jdk/'bin') + os.pathsep + os.environ.get('PATH', '')})
    return redact(run_bounded(['/usr/bin/sandbox-exec', '-p', android_profile(root, sdk, network=network), *argv],
                              env=env, cwd=str(root), timeout=timeout, max_output=1024*1024))


def android_doctor(project='.'):
    root = _project(project)
    sdk, jdk = _sdk(root), _jdk()
    missing = []
    if not (root/'gradlew').is_file(): missing.append('Project Gradle wrapper (gradlew) not found.')
    else: workspace_path(root/'gradlew')  # reject escaped symlinks
    if sdk is None: missing.append('Android SDK platforms/build-tools not found.')
    if jdk is None: missing.append('JDK not found; install/configure JAVA_HOME.')
    probe = _run([str(jdk/'bin/java'), '-version'], root, sdk, jdk) if sdk and jdk else None
    if probe and probe['status'] != 'completed': missing.append('JVM sandbox probe failed; inspect java_probe.')
    return {'status': 'blocked' if missing else 'ready', 'project': str(root), 'jdk': str(jdk) if jdk else None,
            'sdk': str(sdk) if sdk else None, 'blockers': missing, 'java_probe': probe,
            'platforms': sorted(p.name for p in (sdk/'platforms').iterdir()) if sdk else [],
            'build_tools': sorted(p.name for p in (sdk/'build-tools').iterdir()) if sdk else [],
            'note': 'Ready means prerequisites found; it does not prove dependencies are cached or signing configured.'}


def _artifact(path, kind, root, sdk, jdk):
    path = workspace_path(path)
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        required = {'AndroidManifest.xml'} if kind == 'apk' else {'BundleConfig.pb', 'base/manifest/AndroidManifest.xml'}
        if not required <= names:
            raise ValueError('Build output lacks required Android package entries.')
        signed_bundle = any(re.fullmatch(r'META-INF/[^/]+\.(RSA|DSA|EC)', n, re.I) for n in names)
    if kind == 'apk':
        tools = sorted((sdk/'build-tools').iterdir(), key=lambda p: tuple(int(n) for n in re.findall(r'\d+', p.name)), reverse=True)
        signer = next((p/'apksigner' for p in tools if (p/'apksigner').is_file()), None)
        receipt = _run(['/bin/sh', str(signer), 'verify', str(path)], root, sdk, jdk) if signer else {'status': 'blocked'}
        signature = receipt['status'] == 'completed'
    else:
        receipt = _run([str(jdk/'bin/jarsigner'), '-verify', str(path)], root, sdk, jdk)
        signature = signed_bundle and receipt['status'] == 'completed' and 'jar verified.' in receipt.get('stdout', '')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''): digest.update(chunk)
    return {'path': str(path), 'size': path.stat().st_size, 'sha256': digest.hexdigest(),
            'signature_verified': signature, 'signature_check': receipt}


def android_build(project='.', kind='apk', variant='debug', module='app', timeout=900, *, fetch_dependencies=False):
    if kind not in ('apk', 'aab') or variant not in ('debug', 'release'):
        raise ValueError('Expected kind apk/aab and variant debug/release.')
    if not isinstance(module, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', module):
        raise ValueError('Module must be a single Gradle module name.')
    if type(timeout) is not int or not 1 <= timeout <= 1800 or type(fetch_dependencies) is not bool:
        raise ValueError('Build timeout must be 1–1800 seconds; dependency fetch must be boolean.')
    doctor = android_doctor(project)
    if doctor['status'] != 'ready': return doctor
    root, sdk, jdk = Path(doctor['project']), Path(doctor['sdk']), Path(doctor['jdk'])
    output = workspace_path(root/module/'build/outputs'/('apk' if kind == 'apk' else 'bundle')/variant)
    def snapshot():
        return {workspace_path(p): (p.stat().st_mtime_ns, p.stat().st_size) for p in output.glob('**/*.'+kind) if p.is_file()}
    before = snapshot()
    task = ':' + module + ':' + ('assemble' if kind == 'apk' else 'bundle') + variant.title()
    argv = ['/bin/sh', str(workspace_path(root/'gradlew')), task, '--no-daemon', '--console=plain',
            '-Dorg.gradle.daemon=false', '-Dorg.gradle.java.home='+str(jdk)]
    if not fetch_dependencies: argv += ['--offline']
    receipt = _run(argv, root, sdk, jdk, timeout=timeout, network=fetch_dependencies)
    artifacts, errors = [], []
    if receipt['status'] == 'completed':
        for path, stamp in snapshot().items():
            try:
                item = _artifact(path, kind, root, sdk, jdk)
                item['fresh'] = before.get(path) != stamp
                artifacts.append(item)
            except (ValueError, OSError, zipfile.BadZipFile) as exc: errors.append(str(exc))
        if not artifacts and not errors:
            errors.append('Gradle exited zero but no package output was found.')
        if any(not a['signature_verified'] for a in artifacts):
            errors.append('Package signature verification failed or signing is not configured.')
    success = receipt['status'] == 'completed' and bool(artifacts) and not errors and all(a['signature_verified'] for a in artifacts)
    status = ('completed' if any(a['fresh'] for a in artifacts) else 'up_to_date') if success else 'incomplete'
    return {'status': status, 'kind': kind, 'variant': variant,
            'task': task, 'network_enabled': fetch_dependencies, 'build': receipt, 'artifacts': artifacts,
            'errors': errors, 'note': 'Artifacts are signature-checked; fresh records whether each output changed during this build. up_to_date means only existing output was verified. Configure release signing locally; signature validity alone does not establish Play Store readiness. If offline dependencies are missing, run the CLI with --fetch-dependencies. No upload or device installation performed.'}


def generate_qr(url, output='apk-download.png'):
    require_secure_endpoint(url)
    path = workspace_path(output)
    if path.suffix.lower() != '.png': raise ValueError('QR output must end with .png.')
    if path.exists(): raise ValueError('QR output exists; choose a new path.')
    binary = shutil.which('qrencode')
    if not binary: return {'status': 'blocked', 'reason': 'qrencode is not installed.'}
    path.parent.mkdir(parents=True, exist_ok=True)
    from kurt.core.coding_tools import run_checks
    receipt = run_checks([binary, '-o', str(path), '--', url])
    valid = receipt['status'] == 'passed' and path.is_file() and path.read_bytes()[:8] == bytes.fromhex('89504e470d0a1a0a')
    return {'status': 'completed' if valid else 'incomplete', 'path': str(path), 'command': receipt,
            'note': 'QR encodes the supplied URL. Hosting, URL reachability and QR decoding are not verified.'}


def register_commands(app):
    import typer
    android = typer.Typer(help='Inspect Android setup and build verified APK/AAB artifacts.')
    app.add_typer(android, name='android')
    def report(cwd, operation):
        try:
            with workspace(cwd): result = operation()
        except (ValueError, OSError, RuntimeError) as exc:
            result = {'status': 'blocked', 'reason': redact(str(exc))}
        typer.echo(json.dumps(result, indent=2))
        if result['status'] not in ('ready', 'completed', 'up_to_date'): raise typer.Exit(1)
    @android.command('doctor')
    def doctor(cwd: Path = typer.Option(Path('.'), '--cwd'), project: str = '.'):
        """Check project wrapper, SDK and actual Java startup."""
        report(cwd, lambda: android_doctor(project))
    @android.command('build')
    def build(cwd: Path = typer.Option(Path('.'), '--cwd'), project: str = '.', kind: str = 'apk',
              variant: str = 'debug', module: str = 'app', timeout: int = 900,
              fetch_dependencies: bool = typer.Option(False, '--fetch-dependencies', help='Allow network for project build scripts and dependency downloads.')):
        """Build offline by default; verify package files and signatures."""
        report(cwd, lambda: android_build(project, kind, variant, module, timeout, fetch_dependencies=fetch_dependencies))
    @android.command('qr')
    def qr(url: str, output: str = 'apk-download.png', cwd: Path = typer.Option(Path('.'), '--cwd')):
        """Encode a download URL in a new PNG; does not host the APK."""
        report(cwd, lambda: generate_qr(url, output))
