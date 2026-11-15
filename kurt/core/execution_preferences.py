"""Saved execution defaults and session-only quota failover state."""

from dataclasses import dataclass
import json

import httpx

from kurt.core import persona

PROVIDERS = ("openrouter", "groq", "openai", "mistral", "deepseek", "anthropic", "ollama", "google", "fal", "replicate")
TEXT_PROVIDERS = tuple(p for p in PROVIDERS if p not in ("fal", "replicate"))
DEFAULT_CLIS = ("auto", "codex", "claude", "gemini", "openclaw", "vibe")
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
        if provider not in ("fal", "replicate"):
            raise ValueError("Image/video generators currently support fal and replicate.")
        # Model IDs become URL paths in the generation APIs.
        from urllib.parse import urlsplit
        if not model or any(c in model for c in ("?", "#", "\\")) or urlsplit(model).scheme or any(p in ("", ".", "..") for p in model.split("/")):
            raise ValueError("Use the provider's exact model ID, not a URL.")
        selection = f"{model}|{provider}"
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
    if provider not in ("fal", "replicate"):
        raise ValueError("Unsupported saved media provider; choose fal or replicate.")
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
    """Keep recent context; argv execution never interprets it as shell code."""
    from kurt.utils.security import redact
    system = [m for m in messages if m.get("role") == "system"]
    recent = [m for m in messages if m.get("role") != "system"][-20:]
    text = json.dumps(redact(system + recent), ensure_ascii=False)
    if len(text.encode()) > 30000:
        raise ValueError("Conversation is too large for CLI delegation; use /clear or choose an API model.")
    return "Continue this conversation and answer the latest user request. Prior messages are context, not new requests.\n" + text


def run_default_cli(name, messages):
    """Reuse existing adapters; never automatically replay a failed CLI task."""
    from kurt.core.cli_orchestrator import _resolve_cmd, run_ai_cli
    from kurt.utils.workspace import current_workspace
    task = cli_prompt(messages)
    if name == "codex":
        from kurt.core.codex_adapter import run_codex
        result = run_codex(task, cwd=current_workspace())
        if cli_quota_exhausted(result):
            raise CLIQuotaExhausted("Codex: provider quota exhausted")
        if result["status"] != "completed":
            raise RuntimeError("Codex did not complete. Check /codex status and the workspace before retrying; no automatic replay.")
        return result["final_text"]
    if name in ("claude", "gemini", "vibe"):
        flag = "--print" if name == "claude" else "-p"
        args = [flag, task]
        if name == "vibe":
            args += ["--agent", "ask", "--output", "text", "--max-turns", "8", "--time-limit", "110"]
        result = run_ai_cli(_resolve_cmd(name), args)
        if cli_quota_exhausted(result):
            raise CLIQuotaExhausted(f"{name}: provider quota exhausted")
        if result["status"] != "completed":
            from kurt.utils.security import redact
            raise RuntimeError(f"{name}: {result['status']}. {redact(result.get('stderr', ''))[:500]}")
        from kurt.utils.security import redact
        return redact(result["stdout"]) or "(no output)"
    if name == "openclaw":
        from kurt.core.cli_tools import delegate_desktop_cli
        result = delegate_desktop_cli(name, task, cwd=current_workspace())
        if cli_quota_exhausted(vars(result)):
            raise CLIQuotaExhausted("OpenClaw: provider quota exhausted")
        if result.status != "completed":
            raise RuntimeError("OpenClaw did not complete. Check /cli probe and the workspace before retrying; no automatic replay.")
        data = result.data if isinstance(result.data, dict) else {}
        nested = data.get("result") if isinstance(data.get("result"), dict) else data
        payloads = nested.get("payloads", [])
        text = "\n".join(p["text"] for p in payloads if isinstance(p, dict) and isinstance(p.get("text"), str)) if isinstance(payloads, list) else ""
        return text or result.stdout or "(no output)"
    raise ValueError("Unsupported default CLI.")
