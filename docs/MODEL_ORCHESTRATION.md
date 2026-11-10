# Model and CLI orchestration audit

Checked on 2026-11-10 using Kurt's actual `execute_tool` dispatcher in a
disposable synthetic Git workspace. Provider calls and CLI responses were live;
provider credits or subscription quotas may be consumed by reproducing them.

| Integration | Live result | Evidence |
| --- | --- | --- |
| OpenRouter | Passed | `call_model` with `openai/gpt-oss-120b` returned exactly `KURT_OPENROUTER_OK`. |
| Claude CLI | Passed after auth fix | `delegate_cli` returned exactly `KURT_CLAUDE_OK` through the existing Claude CLI login. |
| Codex CLI | Passed | `delegate_cli` returned a completed Codex turn and `KURT_CODEX_OK` in read-only mode, with no reported file changes. |
| Gemini CLI | Not passed | Key mapping and workspace setup repaired; the live request encountered fetch errors and provider HTTP 503 high demand, then hit the 120-second timeout. |
| fal.ai | Account blocked | HTTP 403; a separate diagnostic returned `User is locked. Reason: TOP_UP.` No top-up or billing changes were made. |

Reports: [OpenRouter/Codex](model-orchestration-verification.json),
[Claude CLI retry](model-cli-fixed-verification.json), and
[Gemini retry](model-gemini-verification.json). Earlier errors remain in those
reports as evidence; use the table above for the latest per-integration result.

## What Kurt can currently orchestrate

Agent mode exposes `call_model` for provider calls and `delegate_cli` for
Claude, Gemini, Codex, and other supported tools. Tool outputs are fed back
into the agent's next decision, allowing sequential delegation and synthesis.
The slash commands `/claude`, `/gemini`, and `/codex` also return delegated
results to the conversation.

These checks verify individual live delegations through the real tools. They
do not establish that one autonomous parent model successfully planned and
completed a workflow using all five services. Ordinary chat's native bridge
currently exposes native data and desktop tools; it does not expose this full
provider/CLI orchestration toolset. Use agent mode for model chaining.

OpenRouter verification covers one representative text model, not every model
in its catalog. Kurt's current fal adapter sends a prompt to a synchronous model
endpoint and returns an image URL. It does not yet support arbitrary model input
schemas, video/audio result formats, or long-running fal queue jobs.

## Fixes made during the audit

- Gemini CLI expects `GEMINI_API_KEY` or `GOOGLE_API_KEY`; Kurt stored the key as
  `GOOGLE_AI_KEY`. The adapter now maps that alias without leaking unrelated
  provider credentials or replacing an explicit Gemini key.
- The inherited Anthropic API key overrode the existing Claude CLI subscription
  login and produced a low-credit error. The adapter now probes the CLI's own
  login without the API key and prefers a valid `claude.ai` login. Set
  `KURT_CLAUDE_AUTH=api` to require API-key authentication, or `login` to omit
  the API key. No login files or stored account settings are changed.
- Trusted CLI commands now execute in the selected task workspace.
- Claude/Gemini execution uses the bounded runner: 120-second timeout, 64-KiB
  output cap, and process-group cleanup. Failed exits with stdout are errors,
  rather than apparently successful responses.
- fal errors retain a sanitized server `detail`, allowing account/credit errors
  to be distinguished from generic HTTP failures. The tool description now
  lists the implemented fal image route.
- The verifier initializes its disposable Git repository for Codex. Gemini's
  workspace trust is process-scoped to that known synthetic repository; no
  persisted trusted-folder entries are changed. Service sandbox restrictions
  remain enabled, including protection of other CLIs' credential directories.

Reproduce explicitly:

```sh
python3 tools/verify_model_orchestration.py --live --output /tmp/kurt-model-audit.json
python3 tools/verify_model_orchestration.py --live --only claude gemini --output /tmp/kurt-cli-audit.json
```
