"""Explicit media commands use exactly the same defaults as the native tool."""
import json
from urllib.parse import urlsplit

from kurt.core.execution_preferences import media_target
from kurt.utils.security import redact


def media_plan(kind):
    from kurt.core.router import ModelRouter
    target = media_target(kind)
    return {'kind': kind, **target, 'key_configured': ModelRouter()._has_key(target['provider']),
            'note': 'Configured routing only; provider credits and successful generation are not verified.'}


def generate_selected_media(kind, prompt):
    if kind not in ('image', 'video', 'music') or not isinstance(prompt, str) or not prompt.strip():
        raise ValueError('Choose image/video/music and provide a nonempty generation prompt.')
    from kurt.core.assistant_tools import invoke_assistant
    return invoke_assistant('generate_media', {'kind': kind, 'prompt': prompt.strip()})


def artifact_url(output):
    if not isinstance(output, str): return False
    parsed = urlsplit(output)
    return parsed.scheme in ('https', 'http') and bool(parsed.hostname) and not parsed.username and not parsed.password


def register_commands(app):
    import typer
    @app.command('generate')
    def generate(kind: str, prompt: str = typer.Argument(''), dry_run: bool = typer.Option(False, '--dry-run')):
        """Generate with saved image/video defaults, or inspect routing without a paid request."""
        from kurt.utils.env_loader import load_env
        load_env()
        try:
            result = media_plan(kind) if dry_run else generate_selected_media(kind, prompt)
        except Exception as exc:
            result = {'status': 'error', 'reason': redact(str(exc))}
        typer.echo(json.dumps(result, indent=2))
        if result.get('status') in ('blocked', 'error', 'unverified'): raise typer.Exit(1)
