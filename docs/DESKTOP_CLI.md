# OpenClaw and Peekaboo orchestration

Kurt now resolves, invokes and captures results from two project-local CLIs:

- **OpenClaw 2026.11.2**: delegate an AI subtask and return its JSON result.
- **Peekaboo 4.9.8**: desktop observation and direct app/mouse/keyboard commands.

Both are available through normal `kurt chat` / `kurt ask`, the AI agent's
`delegate_cli` tool, explicit chat slash commands and the `kurt cli` commands.
Subprocess results are returned to Kurt's reasoning context. Slash command
requests/results persist in conversation history for follow-up questions.

## Examples

Inside `kurt chat`:

```text
/cli status
/cli probe
/openclaw Explain a plan for organizing my product research
/peekaboo permissions status --json
/peekaboo see --app Safari --json
```

Natural requests also work through the model tool loop:

```text
Kurt, check mo muna kung ready ang Peekaboo.
Kurt, gamitin mo ang Peekaboo para buksan ang Safari at pumunta sa example.com.
Kurt, i-delegate mo sa OpenClaw ang paggawa ng outline para sa product research report, tapos ibuod mo ang sagot niya.
```

The AI receives `desktop_cli_status` and `desktop_cli` schemas. It can inspect
installation/readiness, execute a command, read the result and continue. The
existing agent also supports:

```json
{"tool":"delegate_cli","params":{"tool":"openclaw","prompt":"Draft a product research outline"}}
```

```json
{"tool":"delegate_cli","params":{"tool":"peekaboo","args":["see","--app","Safari","--json"]}}
```

From a terminal:

```sh
kurt cli status --probe
kurt cli run openclaw 'Reply with a short research outline'
kurt cli run peekaboo 'permissions status --json'
kurt cli run peekaboo 'app launch Safari --foreground'
kurt cli run peekaboo 'see --no-elements --mode screen --path /tmp/kurt-screen.png --json'
```

For clicks and typing, first obtain a fresh Peekaboo observation and pin the
next action to its exact app/window. Read the installed command's help when
needed. Foreground actions use Peekaboo's explicit flags when the user requested
opening or activating an app. Kurt never automatically retries a timed-out
desktop action, since some effects may already have happened.

## AI and configuration

Direct Peekaboo commands use **Kurt as the AI** and require no separate Peekaboo
model configuration. Explicit upstream `peekaboo agent` mode is also available,
but needs its own provider setup.

OpenClaw has its own agent runtime. The project-local setup reuses Kurt's
existing `GROQ_API_KEY` through an environment reference, without storing a copy
of the key in the config:

```sh
kurt cli setup-openclaw
```

The setup was completed on this machine. It creates a private, git-ignored
`.openclaw-kurt/openclaw.json` and state/workspace directories, and never
overwrites an existing managed config. Custom `OPENCLAW_CONFIG_PATH` and an
existing `~/.openclaw/openclaw.json` take precedence.

For this managed setup, a default one-shot task runs through `openclaw agent
exec --local-model-lean` with a configured Groq GPT-OSS-20B model. This avoids
requiring a background Gateway and keeps prompt size within the free-tier token
limit. Custom agent/session requests use the full embedded agent; its larger
prompts may require a provider with a larger token budget. User-managed OpenClaw
configurations retain normal Gateway-backed behavior. Kurt never adds
`--deliver` to a delegated task.

`cli status --probe` checks config validity for managed embedded mode, Gateway
health for user-managed mode, and actual required permissions for Peekaboo.
Config validity does not prove provider quota/availability; individual task
results report those failures.

## Installation and runtime

```sh
npm install
```

Dependencies are pinned in `package.json`. Kurt prepends the project-local
`node_modules/.bin` to child PATH, so OpenClaw uses **Node 24.22.1** even when
the terminal's default Node is older. The OpenClaw and Peekaboo executable lookup
prefers local files, then PATH; there is no implicit `npx` download on a missing
tool. Peekaboo requires macOS 15+ and the appropriate macOS permissions.

OpenClaw's npm and Zod patch dependencies are overridden to 12.2.1 and 4.6.6.
The online npm audit still reports **34 moderate and 1 high** advisory entries
in the dependency tree, including bundled npm's Undici. These remain upstream
dependency limitations; no forced downgrade or incompatible audit fix was used.

## Verification

Recorded evidence: [desktop CLI smoke-test report](desktop-cli-verification.json).

- Real OpenClaw delegated reply returned `KURT_OPENCLAW_OK` through Kurt.
- Real Peekaboo capture wrote a local 1920×1080 PNG. The image was not sent to an
  AI provider.
- Host permission probe confirmed Screen Recording, Accessibility and Event
  Synthesizing. Sandboxed probes can report different permissions; inspect the
  actual host context when diagnosing.
- Unit/integration tests cover literal argv handling, result capture, logical
  JSON failures, missing executables, output limits, timeout cleanup, managed
  configuration and chat/agent/CLI dispatch.

Run the tests with:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

This validates the integrations and the listed smoke tests. It does not claim
every app/browser workflow, every desktop interaction or every provider has
been exercised. API quotas and upstream CLI constraints remain visible in
returned results.

Upstream references: [OpenClaw agent CLI](https://docs.openclaw.ai/cli/agent),
[Peekaboo command docs](https://github.com/openclaw/Peekaboo/tree/main/docs/commands).
