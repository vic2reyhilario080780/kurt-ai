"""Owner-only encrypted .env migration; never part of a SaaS client bundle."""
import base64
from io import StringIO
import json
import os
from pathlib import Path
import re

from kurt.utils.security import register_secrets, write_private_text

MAGIC = b'KURT-ENV-TRANSFER\x01'
MAX_ENV = 128*1024
MAX_FILE = 256*1024


def _cipher(password, salt):
    if not isinstance(password,str) or len(password)<12 or len(password.encode())>1024:
        raise ValueError('Use a transfer passphrase of at least 12 characters (maximum 1024 bytes).')
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    except ImportError:
        raise ValueError('Install the migration extra: python -m pip install -e ".[migration]".') from None
    key = PBKDF2HMAC(algorithm=hashes.SHA256(),length=32,salt=salt,iterations=1_200_000).derive(password.encode())
    return Fernet(base64.urlsafe_b64encode(key))


def _values(raw):
    if not raw or len(raw)>MAX_ENV or b'\0' in raw: raise ValueError('Invalid or oversized credential data.')
    try: text = raw.decode('utf-8-sig')
    except UnicodeError: raise ValueError('Credential data must be UTF-8.') from None
    from dotenv.parser import parse_stream
    values = {}
    for binding in parse_stream(StringIO(text)):
        if binding.error: raise ValueError('Invalid .env syntax; nothing was changed.')
        if binding.key is None: continue
        if binding.key in values: raise ValueError('Duplicate .env variable; nothing was changed.')
        values[binding.key]=binding.value
    if not values or any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',key) or not isinstance(value,str) for key,value in values.items()):
        raise ValueError('Invalid credential variable names or values.')
    register_secrets(values.values())
    return values


def export_credentials(destination,password):
    from kurt.utils.env_loader import ENV_PATH
    target = Path(destination).expanduser()
    if target.suffix != '.kurt-credentials': raise ValueError('Use a .kurt-credentials destination; keep it separate from source code.')
    with ENV_PATH.open('rb') as stream: raw = stream.read(MAX_ENV+1)
    values = _values(raw)
    salt = os.urandom(16)
    data = MAGIC+salt+_cipher(password,salt).encrypt(raw)
    fd = os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as stream: stream.write(data)
    return {'file':str(target),'encrypted':True,'variables':len(values),
            'note':'Personal-device transfer only. Copy privately; never distribute this file to SaaS users.'}


def import_credentials(source,password,*,replace=False):
    from kurt.utils.env_loader import ENV_PATH
    with Path(source).expanduser().open('rb') as stream: data = stream.read(MAX_FILE+1)
    if len(data)>MAX_FILE or not data.startswith(MAGIC) or len(data)<len(MAGIC)+16+100:
        raise ValueError('Unsupported or oversized encrypted credential file.')
    offset = len(MAGIC)
    cipher = _cipher(password,data[offset:offset+16])
    from cryptography.fernet import InvalidToken
    try: raw = cipher.decrypt(data[offset+16:])
    except InvalidToken: raise ValueError('Incorrect passphrase or damaged credential file; nothing was changed.') from None
    incoming = _values(raw)
    if ENV_PATH.is_symlink(): raise ValueError('Refusing to replace a symlinked credential file.')
    existing = {}
    if ENV_PATH.exists():
        with ENV_PATH.open('rb') as stream: old = stream.read(MAX_ENV+1)
        if old.strip(): existing = _values(old)
    imported, kept = 0, 0
    for key,value in incoming.items():
        current = existing.get(key,'')
        placeholder = current.startswith(('your-','your_','sk-your','sk-or-v1-your','gsk_your','AIzaSy-your','r8_your','sk-ant-your'))
        if current and not placeholder and not replace:
            kept += 1; continue
        existing[key]=value; imported += 1
    content = ''.join(key+'='+json.dumps(value,ensure_ascii=False)+'\n' for key,value in existing.items())
    if len(content.encode())>MAX_ENV: raise ValueError('Merged credentials exceed size limit; nothing was changed.')
    write_private_text(ENV_PATH,content)
    return {'imported_variables':imported,'existing_variables_preserved':kept,
            'note':'Restart Kurt to use imported .env credentials. CLI OAuth logins remain device-specific.'}


def register_commands(group):
    import sys
    import typer

    def password(confirm=False):
        if not sys.stdin.isatty(): raise ValueError('Run this command in an interactive terminal for hidden passphrase entry.')
        return typer.prompt('Transfer passphrase (12+ characters)',hide_input=True,confirmation_prompt=confirm)

    @group.command('export-credentials')
    def export(path:str):
        """Encrypt this owner's Kurt .env for a private move to another device."""
        try: result = export_credentials(path,password(confirm=True))
        except (ValueError,OSError) as exc: raise typer.BadParameter(str(exc)) from exc
        typer.echo(json.dumps(result,indent=2))

    @group.command('import-credentials')
    def restore(path:str,replace:bool=typer.Option(False,'--replace')):
        """Decrypt owner's transfer; preserve configured target values by default."""
        try: result = import_credentials(path,password(),replace=replace)
        except (ValueError,OSError) as exc: raise typer.BadParameter(str(exc)) from exc
        typer.echo(json.dumps(result,indent=2))
