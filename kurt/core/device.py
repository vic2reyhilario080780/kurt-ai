"""Device capability reporting and portable, credential-free preferences."""
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil

from kurt.core import persona
from kurt.utils.security import redact, require_public_file, write_private_text

PORTABLE_FIELDS = ('user_name','kurt_name','theme','icon','custom_icon','voice','language',
    'greeting_style','custom_greeting','default_model','default_cli','default_image_model',
    'default_video_model','ai_mode','show_routing_info','compact_mode',
    'speech_provider','speech_language','speech_model','speech_vocabulary','speech_pause_seconds')
MAX_SETTINGS = 64*1024


def device_status():
    system = platform.system()
    from kurt.core.execution_preferences import DEFAULT_CLIS
    from kurt.core.cli_orchestrator import _cmd_exists
    modules = {name:importlib.util.find_spec(name) is not None for name in
               ('playwright','PIL','sounddevice','pyautogui')}
    native = system == 'Darwin'
    notes = {
        'Darwin':'Accessibility, Screen Recording and microphone permissions must be granted on this Mac.',
        'Windows':'Desktop/API features need Windows testing and permissions. External CLI execution has a weaker lexical guard; macOS read-only adapters are unavailable.',
        'Linux':'Desktop support depends on X11/Wayland and permissions. External CLI service sandbox is not implemented; those delegates remain blocked.'}
    return {'os':system,'architecture':platform.machine(),'python':platform.python_version(),
        'supported_installer':system in ('Windows','Darwin','Linux'),
        'session':os.environ.get('XDG_SESSION_TYPE','') if system == 'Linux' else '',
        'features':{'api_chat':'available; configure keys/login and test provider access',
            'browser':'package installed; browser binary/session not verified' if modules['playwright'] else 'install web extra; Chromium is a separate opt-in download',
            'image_verification':'package installed' if modules['PIL'] else 'install media extra',
            'video_verification':'ffprobe found; media not tested' if shutil.which('ffprobe') else 'install ffmpeg/ffprobe separately',
            'voice':'audio package installed; microphone/provider not tested' if modules['sounddevice'] else 'install voice extra; configure online speech provider',
            'desktop':'package installed; permissions/actions not tested' if modules['pyautogui'] else 'install desktop extra and grant OS permissions',
            'peekaboo':'macOS only; installation/permissions not verified' if native else 'unavailable: macOS-only tool',
            'read_only_cli_adapters':'Copilot/DeepSeek macOS sandbox available in design; run readiness tests' if native else 'Copilot/DeepSeek adapters unavailable: requires macOS sandbox; other CLIs need separate testing'},
        'cli_executables':{name:_cmd_exists(name) for name in DEFAULT_CLIS if name != 'auto'},
        'note':notes.get(system,'Unsupported desktop OS; no execution enabled by this report.'),
        'credentials_tested':False,'model_requests_submitted':False}


def _validate(values):
    if not isinstance(values,dict) or set(values)-set(PORTABLE_FIELDS):
        raise ValueError('Settings contain unsupported or device-specific fields.')
    for key,value in values.items():
        choices={'speech_provider':('auto','groq','local'),'speech_language':('tl','auto','en'),
                 'speech_model':('whisper-large-v3','whisper-large-v3-turbo')}
        if key in choices and value not in choices[key]: raise ValueError('Invalid speech setting: '+key)
        if key=='speech_pause_seconds' and (type(value) not in (int,float) or not .6<=value<=4):
            raise ValueError('Speech pause must be between 0.6 and 4 seconds.')
        if key == 'speech_vocabulary' and (not isinstance(value,list) or len(value)>80 or
                any(not isinstance(w,str) or len(w)>48 or '\n' in w or '\0' in w for w in value)):
            raise ValueError('Invalid speech vocabulary.')
        default = persona.DEFAULT_PERSONA[key]
        if default is None:
            valid = value is None or isinstance(value,str)
        else: valid = type(value) is type(default)
        if not valid or (isinstance(value,str) and (len(value)>12000 or '\0' in value)):
            raise ValueError('Invalid portable setting: '+key)
    return values


def export_settings(destination):
    target = Path(destination).expanduser()
    require_public_file(target)
    if target.exists(): raise ValueError('Export destination already exists; choose a new file.')
    saved = persona.load_persona()
    values = _validate({key:saved[key] for key in PORTABLE_FIELDS if key in saved})
    payload = {'format':'kurt-portable-settings','version':1,'source_os':platform.system(),
               'settings':redact(values)}
    content = json.dumps(payload,ensure_ascii=False,indent=2)+'\n'
    if len(content.encode())>MAX_SETTINGS: raise ValueError('Portable settings exceed 64 KiB.')
    # Exclusive creation avoids overwriting another file, including symlinks.
    fd = os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as stream: stream.write(content)
    return {'file':str(target),'credentials_included':False,'projects_or_history_included':False}


def import_settings(source):
    source = Path(source).expanduser()
    with source.open('rb') as stream: raw = stream.read(MAX_SETTINGS+1)
    if len(raw)>MAX_SETTINGS: raise ValueError('Settings file exceeds 64 KiB.')
    def unique(pairs):
        result = {}
        for key,value in pairs:
            if key in result: raise ValueError('Duplicate setting field.')
            result[key]=value
        return result
    payload = json.loads(raw,object_pairs_hook=unique)
    if not isinstance(payload,dict) or payload.get('format')!='kurt-portable-settings' or type(payload.get('version')) is not int or payload['version']!=1:
        raise ValueError('Unsupported portable settings format/version.')
    if set(payload)-{'format','version','source_os','settings'}: raise ValueError('Unexpected export fields.')
    values = _validate(payload.get('settings'))
    warnings = []
    chosen = values.get('default_cli','auto')
    from kurt.core.execution_preferences import DEFAULT_CLIS, parse_model, cli_platform_limit
    from kurt.core.cli_orchestrator import _cmd_exists
    if chosen not in DEFAULT_CLIS: raise ValueError('Unsupported default CLI.')
    if 'default_model' in values: parse_model(values['default_model'])
    if chosen != 'auto' and (not _cmd_exists(chosen) or cli_platform_limit(chosen)):
        values['default_cli']='auto'
        warnings.append('Saved CLI '+chosen+' is missing or unsupported on this host; CLI default set to auto. Install/check a supported CLI before selecting it.')
    merged = {**persona.load_persona(),**values}
    write_private_text(persona.PERSONA_PATH,json.dumps(merged,ensure_ascii=False,indent=2)+'\n')
    return {'imported_fields':list(values),'warnings':warnings,
            'next':'Run kurt setup for API credentials; sign in to CLIs and reconnect apps on this device. Remap project paths separately.'}


def register_commands(app):
    import typer
    group = typer.Typer(help='Check this OS and transfer portable preferences between computers')
    app.add_typer(group,name='device')
    from kurt.core.credential_transfer import register_commands as register_credential_commands
    register_credential_commands(group)

    @group.command('status')
    def status():
        """Report installed capabilities without paid requests or granting permissions."""
        typer.echo(json.dumps(device_status(),ensure_ascii=False,indent=2))

    @group.command('export-settings')
    def export(path:str):
        """Export persona and defaults only, excluding credentials and local paths."""
        try: result = export_settings(path)
        except (ValueError,OSError) as exc: raise typer.BadParameter(str(exc)) from exc
        typer.echo(json.dumps(result,ensure_ascii=False,indent=2))

    @group.command('import-settings')
    def restore(path:str):
        """Merge preferences; keep this device's keys, tokens, projects and history."""
        try: result = import_settings(path)
        except (ValueError,OSError) as exc: raise typer.BadParameter(str(exc)) from exc
        typer.echo(json.dumps(result,ensure_ascii=False,indent=2))
