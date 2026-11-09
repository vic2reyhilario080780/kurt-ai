"""Explicit OpenClaw/Peekaboo subprocess adapters for Kurt orchestration.

Arguments never pass through a shell. Missing tools are reported rather than
downloaded implicitly. A timed-out desktop action is not automatically retried.
"""

from dataclasses import asdict, dataclass
from kurt.utils.security import redact, child_env
from kurt.utils.execution import service_argv

import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import tempfile

PROJECT_ROOT = Path(__file__).parents[2]
NODE_BIN = PROJECT_ROOT / "node_modules" / ".bin"
TOOLS = ("openclaw", "peekaboo")
MAX_OUTPUT = 64 * 1024
MANAGED_DIR = PROJECT_ROOT / ".openclaw-kurt"
MANAGED_CONFIG = MANAGED_DIR / "openclaw.json"


@dataclass
class CLIResult:
    tool: str
    status: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    data: object = None
    truncated: bool = False
    hint: str = ""

    def text(self):
        return json.dumps(redact(asdict(self)), ensure_ascii=False)


def resolve_cli(tool):
    if tool not in TOOLS:
        raise ValueError("Supported tools: openclaw, peekaboo.")
    local = NODE_BIN / tool
    if local.is_file() and os.access(local, os.X_OK):
        return str(local)
    return shutil.which(tool)


def cli_env(tool="openclaw"):
    # Upstream Node entrypoints and their child processes use this runtime.
    from dotenv import dotenv_values
    from kurt.utils.env_loader import ENV_PATH
    env = {k: v for k, v in dotenv_values(ENV_PATH).items() if isinstance(v, str)} if ENV_PATH.exists() else {}
    env.update(os.environ)
    allowed = ("OPENCLAW_CONFIG_PATH", "OPENCLAW_STATE_DIR", "OPENCLAW_GATEWAY_TOKEN", "GROQ_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY") if tool == "openclaw" else ()
    if tool == "openclaw" and not env.get("OPENCLAW_CONFIG_PATH") and not env.get("OPENCLAW_STATE_DIR") and not (Path.home() / ".openclaw/openclaw.json").exists() and MANAGED_CONFIG.exists():
        allowed = ("GROQ_API_KEY",)
    env = child_env(allow=allowed, source=env)
    env.update({"PATH": str(NODE_BIN) + os.pathsep + os.environ.get("PATH", ""), "NO_COLOR": "1"})
    if not env.get("OPENCLAW_CONFIG_PATH") and not env.get("OPENCLAW_STATE_DIR") and not (Path.home() / ".openclaw" / "openclaw.json").exists() and MANAGED_CONFIG.exists():
        env["OPENCLAW_CONFIG_PATH"] = str(MANAGED_CONFIG)
        env["OPENCLAW_STATE_DIR"] = str(MANAGED_DIR / "state")
    return env


def managed_openclaw():
    return cli_env().get("OPENCLAW_CONFIG_PATH") == str(MANAGED_CONFIG)


def setup_openclaw():
    """Create an isolated embedded profile using Kurt's existing Groq credential."""
    if not cli_env().get("GROQ_API_KEY"):
        raise ValueError("Configure GROQ_API_KEY in Kurt first, or onboard OpenClaw separately.")
    MANAGED_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    config = {"gateway": {"mode": "local"}, "agents": {"defaults": {
        "workspace": str(MANAGED_DIR / "workspace"), "model": {"primary": "kurt-groq/openai/gpt-oss-20b"}}},
        "models": {"mode": "merge", "providers": {"kurt-groq": {
            "baseUrl": "https://api.groq.com/openai/v1", "apiKey": "${GROQ_API_KEY}", "api": "openai-completions",
            "models": [{"id": "openai/gpt-oss-20b", "name": "Kurt Groq GPT-OSS 20B", "reasoning": True,
                        "input": ["text"], "contextWindow": 131072, "maxTokens": 8192}]}}}}
    fd = os.open(MANAGED_CONFIG, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(config, stream, indent=2)
    return {"config": str(MANAGED_CONFIG), "mode": "embedded", "model": "kurt-groq/openai/gpt-oss-20b",
            "credentials": "Inherited from Kurt's environment; no API key stored in config."}


def _read_output(stream):
    stream.seek(0)
    content = stream.read(MAX_OUTPUT + 1)
    return content[:MAX_OUTPUT].decode("utf-8", errors="replace").strip(), len(content) > MAX_OUTPUT


def run_cli(tool, args, timeout=180):
    if not isinstance(args, list) or not all(isinstance(a, str) and "\0" not in a for a in args):
        raise ValueError("CLI args must be a list of strings without NUL bytes.")
    if type(timeout) not in (int, float) or not 1 <= timeout <= 600:
        raise ValueError("CLI timeout must be from 1 to 600 seconds.")
    executable = resolve_cli(tool)
    if executable is None:
        return CLIResult(tool, "missing", hint="Run npm install in the Kurt project, or install the upstream CLI on PATH.")
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        try:
            process = subprocess.Popen(service_argv([executable, *args], tool), stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                       env=cli_env(tool), start_new_session=True)
        except OSError as exc:
            return CLIResult(tool, "failed", stderr=str(exc), hint="Check the CLI installation and runtime requirements.")
        try:
            code = process.wait(timeout=timeout)
            status = "completed" if code == 0 else "failed"
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            except ProcessLookupError:
                process.wait()
            code, status = process.returncode, "timed_out"
        stdout, out_cut = _read_output(out)
        stderr, err_cut = _read_output(err)
    parsed = None
    if stdout and not out_cut:
        try:
            parsed = json.loads(stdout)
        except ValueError:
            pass
    if status == "completed" and isinstance(parsed, dict) and (
            parsed.get("ok") is False or parsed.get("success") is False or
            parsed.get("status") in ("error", "failed", "blocked", "cancelled", "timeout")):
        status = "failed"
    hint = ""
    if status == "timed_out":
        hint = "Command timed out; some actions may already have happened. Observe current state before retrying."
    elif status == "failed":
        hint = ("Check macOS Accessibility, Screen Recording and Event Synthesizing permissions; inspect the CLI error."
                if tool == "peekaboo" else "Check OpenClaw configuration, model quota/context budget and Gateway availability if using Gateway mode.")
    return CLIResult(tool, status, redact(stdout), redact(stderr), code, redact(parsed), out_cut or err_cut, hint)


def delegate_desktop_cli(tool, prompt="", args=None, agent="main", session_id=None, timeout=180):
    """OpenClaw accepts a task; Peekaboo defaults to direct CLI commands."""
    if args is not None:
        if prompt:
            raise ValueError("Provide a task/command string or args, not both.")
        return run_cli(tool, args, timeout)
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("A nonempty task/command is required.")
    if tool == "openclaw":
        prompt = redact(prompt)
        if not isinstance(agent, str) or not agent.strip():
            raise ValueError("OpenClaw agent must be a nonempty name.")
        if managed_openclaw() and agent == "main" and session_id is None:
            # Keep one-shot delegation lean enough for Kurt's free-tier model.
            command = ["agent", "exec", "--config", str(MANAGED_CONFIG), "--cwd", str(PROJECT_ROOT),
                       "--local-model-lean", "--json", "--", prompt]
        else:
            command = ["agent", "--agent", agent, "--message", prompt, "--json"]
            if managed_openclaw():
                command.append("--local")
        if session_id is not None:
            if not isinstance(session_id, str) or not session_id.strip():
                raise ValueError("OpenClaw session_id must be nonempty.")
            command += ["--session-id", session_id]
        return run_cli(tool, command, timeout)
    if tool == "peekaboo":
        return run_cli(tool, shlex.split(prompt), timeout)
    raise ValueError("Supported tools: openclaw, peekaboo.")


def cli_status(probe=False):
    results = []
    for tool in TOOLS:
        executable = resolve_cli(tool)
        entry = {"tool": tool, "installed": executable is not None, "executable": executable}
        if executable:
            entry["version"] = asdict(run_cli(tool, ["--version"], timeout=30))
            if probe:
                # Read-only probes. They do not onboard, grant permissions or send tasks.
                embedded = tool == "openclaw" and managed_openclaw()
                args = (["permissions", "status", "--json"] if tool == "peekaboo" else
                        ["config", "validate", "--json"] if embedded else ["health", "--json"])
                result = run_cli(tool, args, timeout=30)
                entry["probe"] = asdict(result)
                entry["mode"] = "embedded" if embedded else "gateway" if tool == "openclaw" else "desktop"
                entry["ready"] = result.status == "completed"
                if tool == "peekaboo" and isinstance(result.data, dict):
                    permissions = result.data.get("data", {}).get("permissions", [])
                    entry["missing_permissions"] = [p.get("name") for p in permissions if p.get("isRequired") and not p.get("isGranted")]
                    entry["ready"] = entry["ready"] and bool(permissions) and not entry["missing_permissions"]
        results.append(entry)
    return results


def register_commands(app, console):
    import typer
    group = typer.Typer(help="Orchestrate OpenClaw tasks and Peekaboo desktop commands")
    app.add_typer(group, name="cli")

    @group.command("status")
    def status(probe: bool = typer.Option(False, help="Also check Gateway health and desktop permissions")):
        print(json.dumps(cli_status(probe), indent=2, ensure_ascii=False))

    @group.command("setup-openclaw")
    def setup():
        """Create a project-local OpenClaw profile reusing Kurt's Groq key."""
        try:
            print(json.dumps(setup_openclaw(), indent=2))
        except (ValueError, OSError) as exc:
            raise typer.BadParameter(str(exc)) from exc

    @group.command("run")
    def run(tool: str, task: str, agent: str = typer.Option("main"),
            timeout: int = typer.Option(180, min=1, max=600)):
        """OpenClaw: a natural-language task. Peekaboo: a quoted CLI command."""
        try:
            result = delegate_desktop_cli(tool, task, agent=agent, timeout=timeout)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
        if result.status != "completed":
            raise typer.Exit(1)
