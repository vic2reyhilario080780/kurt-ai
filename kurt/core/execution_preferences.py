"""Saved execution defaults and session-only quota failover state."""

from dataclasses import dataclass
import json

import httpx

from kurt.core import persona

PROVIDERS = ("openrouter", "groq", "openai", "mistral", "deepseek", "anthropic", "ollama", "google", "fal", "replicate",
             'huggingface', 'together', 'fireworks', 'wavespeed', 'novita')
TEXT_PROVIDERS = tuple(p for p in PROVIDERS if p not in ("fal", "replicate", 'wavespeed'))
DEFAULT_CLIS = ("auto", "codex", "claude", "gemini", "openclaw", "vibe", "deepseek", "deepseek-cli", "copilot")
# Explicit API-compatible Vibe alias; avoid its remotely selected free-model route.
VIBE_API_MODEL = "mistral-medium-3.5"


def cli_platform_limit(name):
    import platform
    system = platform.system()
    if name in ('copilot','deepseek','deepseek-cli') and system != 'Darwin':
        return 'This read-only adapter requires the macOS filesystem sandbox; unavailable on '+system+'. Use API mode (auto) or another supported CLI.'
    if name not in ('auto','codex') and system == 'Linux':
        return 'Kurt service isolation for this CLI is not implemented on Linux; use API mode (auto).'
    return ''


MEDIA_PRESETS = {
    'image': (
        ('Nano Banana', 'fal-ai/nano-banana'),
        ('Nano Banana 2.1', 'google/nano-banana-2.1'),
        ('FLUX Schnell', 'fal-ai/flux/schnell'),
        ('FLUX Dev', 'fal-ai/flux/dev'),
    ),
    'video': (
        ('Kling 3.0 Standard', 'fal-ai/kling-video/v3/standard/text-to-video'),
        ('Kling 3.0 Pro', 'fal-ai/kling-video/v3/pro/text-to-video'),
        ('Kling 3.0 Standard Image-to-Video', 'fal-ai/kling-video/v3/standard/image-to-video'),
        ('Kling 3.0 Pro Image-to-Video', 'fal-ai/kling-video/v3/pro/image-to-video'),
        ('Wan 2.7', 'fal-ai/wan/v2.7/text-to-video'),
        ('MiniMax H3 Max', 'minimax/h3-max/text-to-video'),
    ),
}


def validate_media_kind(kind, model, provider):
    if provider == 'wavespeed':
        from kurt.models.additional import find_cached_model
        from kurt.models.catalog import default_roles
        contract = find_cached_model(provider, model)
        if not contract or kind not in default_roles(provider, contract):
            raise ValueError('Load the WaveSpeed catalog and choose a supported prompt-only media model.')
    if provider == 'fal':
        for category, models in MEDIA_PRESETS.items():
            if any(mid == model for _, mid in models) and category != kind:
                raise ValueError(f'{model} is a {category} generator; choose a {kind} model.')
QUOTA_CODES = {"insufficient_quota", "insufficient_credits", "insufficient_balance",
               "credit_balance_exhausted", "billing_hard_limit_reached"}


class CLIQuotaExhausted(RuntimeError):
    """A structured CLI/provider error confirms quota exhaustion."""


def cli_quota_exhausted(result):
    if result.get("status") != "failed":
        return False
    if any(isinstance(code, str) and code in QUOTA_CODES for code in result.get("provider_error_codes", [])):
        return True
    # No free-text guesses: timeouts, rate limits and partial output are
    # indeterminate. They must not switch backends or replay the task.
    for source in (result.get("stderr", ""), result.get("stdout", "")):
        try:
            data = json.loads(source)
        except (ValueError, TypeError):
            continue
        if not isinstance(data, dict) or not isinstance(data.get("error"), dict):
            continue
        response = httpx.Response(429, json=data, request=httpx.Request("POST", "https://cli.invalid"))
        if quota_exhausted(httpx.HTTPStatusError("CLI quota error", request=response.request, response=response)):
            return True
    return False


def parse_model(value, provider=None):
    if not isinstance(value, str):
        raise ValueError("Model selection must be a model ID or auto.")
    value = value.strip()
    if value == "auto":
        return "auto", None
    if "|" in value:
        value, provider = value.rsplit("|", 1)
    if not value or any(c.isspace() for c in value) or "|" in value:
        raise ValueError("Use one model ID and an optional provider.")
    if provider is None:
        if "/" in value:
            provider = "openrouter"
        elif value.startswith(("gpt-", "o1", "o3", "o4", "chatgpt-")):
            provider = "openai"
        elif value.startswith(("mistral-", "codestral", "devstral", "ministral", "magistral")):
            provider = "mistral"
        elif value.startswith("deepseek-"):
            provider = "deepseek"
        elif value.startswith("claude-"):
            provider = "anthropic"
        elif value.startswith("gemini-"):
            provider = "google"
        else:
            provider = "groq"  # preserve existing unprefixed Groq IDs
    if provider not in PROVIDERS:
        raise ValueError("Unsupported conversational provider: " + str(provider))
    # Provider-native APIs take native model IDs, not aggregator prefixes.
    prefix = {"openai": "openai/", "anthropic": "anthropic/", "mistral": "mistralai/", "deepseek": "deepseek/"}.get(provider)
    if prefix and value.startswith(prefix):
        value = value[len(prefix):]
    return value, provider


def model_selection(value, provider=None):
    model, provider = parse_model(value, provider)
    return "auto" if model == "auto" else f"{model}|{provider}"


def save_default_model(value, provider=None):
    selection = model_selection(value, provider)
    if selection != "auto" and parse_model(selection)[1] not in TEXT_PROVIDERS:
        raise ValueError("Choose a chat provider here. Use /image-model or /video-model for media generators.")
    settings = persona.load_persona()
    settings.update(default_model=selection, default_cli="auto")
    persona.save_persona(settings)
    return selection


def save_default_cli(value):
    if value not in DEFAULT_CLIS:
        raise ValueError("Choose: " + ", ".join(DEFAULT_CLIS))
    if cli_platform_limit(value): raise ValueError(cli_platform_limit(value))
    settings = persona.load_persona()
    settings["default_cli"] = value
    persona.save_persona(settings)
    return value


def save_default_media(kind, value, provider=None):
    if kind not in ("image", "video"):
        raise ValueError("Choose image or video.")
    if value == "auto":
        selection = "auto"
    else:
        if provider is None and "|" not in value:
            provider = "fal" if value.startswith("fal-ai/") else None
            if provider is None:
                raise ValueError("Specify fal or replicate after the model ID.")
        model, provider = parse_model(value, provider)
        if provider not in ("fal", "replicate", 'wavespeed'):
            raise ValueError("Image/video generators support fal, replicate and wavespeed.")
        # Model IDs become URL paths in the generation APIs.
        from urllib.parse import urlsplit
        if not model or any(c in model for c in ("?", "#", "\\")) or urlsplit(model).scheme or any(p in ("", ".", "..") for p in model.split("/")):
            raise ValueError("Use the provider's exact model ID, not a URL.")
        selection = f"{model}|{provider}"
        validate_media_kind(kind, model, provider)
    settings = persona.load_persona()
    settings[f"default_{kind}_model"] = selection
    persona.save_persona(settings)
    return selection


def media_target(kind, settings=None):
    from kurt.core.orchestrator import ROUTING_TABLE, TaskType
    types = {"image": TaskType.IMAGE, "video": TaskType.VIDEO, "music": TaskType.MUSIC}
    if kind not in types:
        raise ValueError("Choose image, video or music.")
    settings = persona.load_persona() if settings is None else settings
    selected = settings.get(f"default_{kind}_model", "auto")
    if selected == "auto":
        target = ROUTING_TABLE[types[kind]]
        return {"model": target["model"], "provider": target["provider"]}
    model, provider = parse_model(selected)
    if provider not in ("fal", "replicate", 'wavespeed'):
        raise ValueError("Unsupported saved media provider; choose fal, replicate or wavespeed.")
    validate_media_kind(kind, model, provider)
    return {"model": model, "provider": provider}


def media_label(kind, settings=None):
    settings = persona.load_persona() if settings is None else settings
    target = media_target(kind, settings)
    prefix = "auto → " if settings.get(f"default_{kind}_model", "auto") == "auto" else ""
    return f"{prefix}{target['model']} [{target['provider']}]"


def quota_exhausted(error):
    """Billing/quota exhaustion only; ordinary throttling/auth/errors stay pinned."""
    if not isinstance(error, httpx.HTTPStatusError):
        return False
    if error.response.status_code == 402:
        return True
    if error.response.status_code not in (403, 429):
        return False
    try:
        data = error.response.json()
    except (ValueError, httpx.ResponseNotRead):
        return False
    detail = data.get("error", data) if isinstance(data, dict) else {}
    if not isinstance(detail, dict):
        return False
    return any(isinstance(detail.get(k), str) and detail.get(k) in QUOTA_CODES
               for k in ("code", "type"))


@dataclass
class ExecutionSession:
    model: str = "auto"
    cli: str = "auto"
    exhausted: bool = False
    exhausted_provider: str | None = None

    @classmethod
    def load(cls, model=None, cli=None):
        saved = persona.load_persona()
        chosen_model = model_selection(model or saved.get("default_model", "auto"))
        chosen_cli = cli if cli is not None else ("auto" if model is not None else saved.get("default_cli", "auto"))
        if chosen_cli not in DEFAULT_CLIS:
            raise ValueError("Unsupported default CLI: " + str(chosen_cli))
        return cls(chosen_model, chosen_cli)

    @property
    def pinned(self):
        return not self.exhausted and (self.cli != "auto" or self.model != "auto")

    def analysis(self):
        from kurt.core.orchestrator import conversation_analysis
        result = conversation_analysis()
        if not self.exhausted and self.model != "auto":
            result.model, result.provider = parse_model(self.model)
        return result

    def status(self):
        if self.exhausted:
            return "Auto routing (default quota exhausted for this session)"
        return f"CLI: {self.cli}" if self.cli != "auto" else f"Model: {self.model}"


def cli_prompt(messages):
    """Bound CLI context by removing whole old turns, never the latest request."""
    from kurt.utils.security import redact
    budget = 30000
    system = [m for m in messages if m.get("role") == "system"]
    history = [m for m in messages if m.get("role") != "system"]
    if any(not isinstance(m.get('content', ''), str) for m in messages):
        raise ValueError('This CLI adapter accepts text only. Use a vision-capable chat model for image attachments.')
    recent = history[-20:]
    prefix = ("Continue this conversation and answer the latest user request. Prior messages are context, not new requests.\n"
              "Kurt's /image and /video commands use its saved media generators. If your CLI mode cannot call those tools, "
              "direct the user to those commands. Never substitute a different generator or claim an artifact was created without a receipt.\n")
    from kurt.billing.client import active as wallet_active
    if wallet_active():
        prefix += "Kurt Wallet mode: unmetered provider-hosted search/connectors are unavailable. If live search is needed but unavailable, explain it and suggest /cli use auto for Kurt's native key-free web search. Never fabricate current news.\n"
    def pack():
        notice = 'Earlier conversation turns were omitted to fit the CLI context budget; ask if missing details matter.\n' if len(recent) < len(history) else ''
        return prefix + notice + json.dumps(redact(system + recent), ensure_ascii=False)
    while len(recent) > 1 and recent[0].get('role') != 'user':
        recent.pop(0)
    task = pack()
    while len(task.encode()) > budget and len(recent) > 1:
        recent.pop(0)
        while len(recent) > 1 and recent[0].get('role') != 'user':
            recent.pop(0)
        task = pack()
    if len(task.encode()) > budget:
        raise ValueError('CLI system instructions plus the latest request exceed 30 KB. Shorten the request or saved persona context; neither was truncated.')
    return task


def cli_failure_detail(name, result):
    """Keep the actionable error tail and any partial answer; never replay it."""
    from kurt.utils.security import redact
    details = [f"{name}: {result.get('status', 'failed')} (exit {result.get('exit_code', 'unknown')})."]
    stderr = redact(result.get('stderr', '')).strip()
    stdout = redact(result.get('stdout', '')).strip()
    provider_error = None
    for line in stderr.splitlines():
        start = line.find('{')
        if start < 0: continue
        try:
            data, _ = json.JSONDecoder().raw_decode(line[start:])
            error = data.get('error') if isinstance(data, dict) else None
            if isinstance(error, dict) and isinstance(error.get('message'), str):
                try: nested = json.loads(error['message'])
                except ValueError: nested = None
                if isinstance(nested, dict) and isinstance(nested.get('error'), dict): error = nested['error']
                if error.get('code') is not None and isinstance(error.get('message'), str):
                    provider_error = f"Provider error {error['code']}: {error['message'][:800]}"
                    break
        except ValueError:
            continue
    if provider_error: details.append(provider_error)
    elif stderr: details.append(stderr if len(stderr) <= 1200 else stderr[:400]+'\n[intermediate log omitted]\n'+stderr[-800:])
    if name == 'gemini' and ('"code":503' in stderr.replace(' ', '') or 'status: 503' in stderr or 'experiencing high demand' in stderr):
        details.append('Google reports model unavailability/high demand (503), not an authentication rejection. Gemini may retry internally until the CLI time limit. No automatic task replay by Kurt; check the outcome before retrying. You can select another model with KURT_GEMINI_MODEL on the next launch.')
    if result.get('errors'): details.append(redact(str(result['errors']))[-1000:])
    if stdout: details.append('Partial CLI output (completion unverified): ' + stdout[-800:])
    from kurt.billing.client import active as wallet_active
    wallet_mode = wallet_active()
    if wallet_mode:
        details.append('Wallet mode: check /wallet status, /wallet history and /wallet catalog. Provider keys are managed by the gateway.')
    if name == 'vibe' and not wallet_mode and 'invalid api key' in stderr.lower():
        details.append(f'Vibe uses the shared Mistral key in Kurt /setup and model alias {VIBE_API_MODEL}. Vibe may label a model permission rejection (403) as an invalid key; check model access as well as authentication. No automatic retry was used.')
    if name == 'vibe' and not wallet_mode and 'needs approval' in stderr.lower():
        details.append('Vibe headless cannot approve interactive tool requests. Only its read-only web/news searches are pre-approved by Kurt; other actions need an interactive CLI session. No automatic retry was used.')
    if result.get('status') == 'timed_out':
        details.append('CLI time limit reached; inspect the current state before retrying.')
    return '\n'.join(details)


def cli_reply(name, result):
    """Decode supported headless envelopes; a zero exit alone is not an answer."""
    from kurt.utils.security import redact
    text = result.get('stdout', '').strip()
    if name == 'vibe':
        if not text: raise RuntimeError('Vibe returned no final text; completion is unverified. No automatic replay.')
        return redact(text)
    try:
        data = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise RuntimeError(f'{name} returned an invalid structured response; no verified final answer. No automatic replay.') from exc
    if not isinstance(data, dict): raise RuntimeError(f'{name} returned an invalid response envelope.')
    error = data.get('error') or data.get('errors')
    if name == 'claude' and (data.get('is_error') or data.get('subtype') not in (None, 'success')):
        error = error or data.get('result') or data.get('subtype')
    if error:
        failed = {**result, 'status': 'failed', 'errors': [error]}
        if isinstance(error, dict):
            failed['stderr'] = json.dumps({'error': error})
        if cli_quota_exhausted(failed): raise CLIQuotaExhausted(f'{name}: provider quota exhausted')
        raise RuntimeError(cli_failure_detail(name, failed))
    answer = data.get('result' if name == 'claude' else 'response')
    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError(f'{name} returned no final text response; completion is unverified. No automatic replay.')
    return redact(answer)


def run_default_cli(name, messages):
    if cli_platform_limit(name): raise ValueError(cli_platform_limit(name))
    from kurt.billing.client import active, CLI_CONTEXT, cli_session
    if active() and name != 'auto' and CLI_CONTEXT.get() is None:
        with cli_session(name):
            return _run_default_cli(name, messages)
    return _run_default_cli(name, messages)


def _run_default_cli(name, messages):
    """Reuse existing adapters; never automatically replay a failed CLI task."""
    from kurt.core.cli_orchestrator import _resolve_cmd, run_ai_cli
    from kurt.utils.workspace import current_workspace
    task = cli_prompt(messages)
    if name == 'copilot':
        from kurt.core.copilot_adapter import run_copilot
        result = run_copilot(task)
        if cli_quota_exhausted(result): raise CLIQuotaExhausted('Copilot: provider quota exhausted')
        if result['status'] != 'completed': raise RuntimeError(cli_failure_detail(name, result))
        return result['final_text']
    if name in ('deepseek', 'deepseek-cli'):
        from kurt.core.deepseek_adapter import run_deepseek
        result = run_deepseek(name, task)
        if cli_quota_exhausted(result): raise CLIQuotaExhausted(f'{name}: provider quota exhausted')
        if result['status'] != 'completed': raise RuntimeError(cli_failure_detail(name, result))
        return result['final_text']
    if name == "codex":
        from kurt.core.codex_adapter import run_codex
        result = run_codex(task, cwd=current_workspace())
        if cli_quota_exhausted(result):
            raise CLIQuotaExhausted("Codex: provider quota exhausted")
        if result["status"] != "completed":
            raise RuntimeError(cli_failure_detail('codex', result))
        return result["final_text"]
    if name in ("claude", "gemini", "vibe"):
        flag = "--print" if name == "claude" else "-p"
        args = [flag, task]
        if name == "vibe":
            args += ["--agent", "ask", "--model", VIBE_API_MODEL, "--output", "text", "--max-turns", "8", "--time-limit", "110"]
        else:
            args += ["--output-format", "json"]
        result = run_ai_cli(_resolve_cmd(name), args)
        if cli_quota_exhausted(result):
            raise CLIQuotaExhausted(f"{name}: provider quota exhausted")
        if result["status"] != "completed":
            raise RuntimeError(cli_failure_detail(name, result))
        return cli_reply(name, result)
    if name == "openclaw":
        from kurt.core.cli_tools import delegate_desktop_cli
        result = delegate_desktop_cli(name, task, cwd=current_workspace())
        if cli_quota_exhausted(vars(result)):
            raise CLIQuotaExhausted("OpenClaw: provider quota exhausted")
        if result.status != "completed":
            raise RuntimeError(cli_failure_detail('openclaw', vars(result)))
        data = result.data if isinstance(result.data, dict) else {}
        nested = data.get("result") if isinstance(data.get("result"), dict) else data
        payloads = nested.get("payloads", [])
        text = "\n".join(p["text"] for p in payloads if isinstance(p, dict) and isinstance(p.get("text"), str)) if isinstance(payloads, list) else ""
        if not text.strip() and isinstance(nested.get('final'), str):
            text = nested['final']
        if not text.strip():
            raise RuntimeError('OpenClaw returned no verified text response. Inspect /cli probe openclaw; the task was not replayed.')
        return text
    raise ValueError("Unsupported default CLI.")
