# Default CLI compatibility audit — 2026-11-16

| CLI | Installed version | Live default-adapter response |
| --- | --- | --- |
| Codex | 0.169.0 | Passed from the home directory after non-Git startup fix |
| Claude Code | 2.1.319 | Passed with parsed structured result |
| Gemini CLI | 0.67.0 | Not verified: Google returned HTTP 503/high demand and upstream retries reached Kurt's time limit |
| OpenClaw | 2026.11.2 | Passed in Kurt's current embedded configuration after SDK directory access fix |
| Mistral Vibe | 3.1.2 | Passed, including the final live test command |

These are minimal read-only response tests, not proof of every CLI tool, coding
workflow, balance or future provider availability. Existing accounts, models and
saved defaults were not changed. Gemini was not silently switched to another
model/CLI to manufacture a passing result.

## Fixes

- Codex chat now starts outside a Git repository with `--skip-git-repo-check`.
  Its explicit read-only/workspace permission profile remains enforced; no trust
  persistence or sandbox bypass flag is added. Vibe private state is also denied
  to Codex-generated commands.
- OpenClaw can read metadata/listing of the exact installed SDK source directory
  `@anthropic-ai/sdk/lib/credentials`. This literal read-only exception does not
  grant access to user credential files or arbitrary credentials directories.
- Claude/Gemini defaults request structured JSON output. The adapter extracts a
  final response and rejects error/empty envelopes even when the process exits
  zero. Vibe empty text and OpenClaw acknowledgments without final text also
  fail explicitly. OpenClaw payload and final-text envelopes are supported.
- Another CLI no longer inherits PATH entries inside private state such as
  `~/.codex`; public runtime paths remain available. Gemini's private ripgrep
  lookup error disappeared; its remaining error was Google's 503 response.
- Error display preserves useful startup/error details and renders structured
  provider failures readably. Partial output stays unverified; failed actions
  are not automatically replayed. A busy provider is not treated as exhausted
  credits or authorization to change the selected executor.
- The chat shows a waiting spinner while the chosen CLI runs. Missing CLIs are
  disabled in the picker. Installed rows explicitly say authentication/credits
  are not established by installation alone.

## Check readiness

```text
/cli status
/cli probe all
/cli probe codex
/cli test codex
/cli default codex
/cli use auto
```

Equivalent terminal commands:

```sh
kurt cli probe all
kurt cli probe gemini
kurt cli test gemini
```

`probe` checks versions/executables without model inference. `test` submits one
minimal response request and **may consume provider credits**. A successful test
means that request returned the expected final answer. Neither command changes
the saved default. Existing `kurt cli status --probe` and `/cli probe` retain the
OpenClaw/Peekaboo desktop-health/permission checks for compatibility.

`auto` uses the saved chat API model. Choosing a CLI uses that CLI's own account,
model settings and permission policy. Codex and Vibe remain read-only by default;
other CLI actions depend on upstream approval/tool configuration. OpenClaw's
Gateway mode requires its own running/configured Gateway; the live test used the
current embedded profile. Saved chat/image/video defaults are retained.

Full suite: **391 tests passed**, including persistence for every supported
choice, headless protocol decoding, non-Git Codex, empty/error response rejection,
OpenClaw envelopes, private PATH isolation, disabled missing choices and no model
requests during version probes. Live summaries: `all-cli-default-verification.json`.
Restart already-running Kurt sessions to load the updated adapters.
