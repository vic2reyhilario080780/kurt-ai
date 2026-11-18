# GitHub Copilot CLI in Kurt

Kurt supports the official `@github/copilot` CLI, pinned to 1.0.113 in
`package.json`. Resolution prefers `node_modules/.bin/copilot` over PATH,
including the VS Code launcher that can exist without an installed runtime.
Run `npm install` in the project to install the pinned package.

## Pick and use

- `/setting` → CLI → copilot
- `/cli default copilot` saves the default; `/cli use copilot` selects it for
  the session. The existing welcome banner displays the selected CLI.
- `/copilot <task>` delegates one task without changing the default.
- `kurt cli probe copilot` checks the executable/version without inference.
- `kurt cli test copilot` explicitly submits a minimal model request and can
  consume credits. An installed version alone does not prove authentication.

The headless adapter exposes only `view`, `glob` and `grep`, denies shell/write
tools, disables built-in MCP servers and computer use, does not grant folder
trust, and limits each invocation to 120 seconds/64 KiB output. On the supported
macOS host its subprocess filesystem writes are restricted to CLI state,
runtime cache and a temporary directory. Project files remain read-only.
Hooks/extensions or workflows requiring other permissions belong in a separately
reviewed interactive CLI session. It is not a general-purpose editing delegate.

The adapter requires a final JSONL `result` with exit code zero and final
assistant text, rejects failed tools/session errors and partial output, and
never replays the task itself. Upstream SDKs can retry requests; the wallet's
duplicate-request protection prevents resubmitting identical billed requests.

## Authentication and payment

**Wallet off:** use your existing Copilot login/settings, or run
`node_modules/.bin/copilot login` and complete GitHub authorization yourself.
Supported explicit `COPILOT_GITHUB_TOKEN`, `GH_TOKEN` and `GITHUB_TOKEN` are
passed only to this trusted adapter. GitHub account entitlement, token
permissions and credits must be available. Existing account/settings remain
unchanged; unrelated inherited API credentials and permission overrides are
not forwarded.

**Wallet on:** Kurt creates an isolated Copilot home with a short-lived
OpenRouter-scoped gateway token, an OpenAI-compatible `/api/v1` base URL and
`COPILOT_OFFLINE=true`. GitHub authentication/telemetry and personal login
fallback are disabled. Here "offline" disables GitHub traffic; inference still
uses the network to reach the Kurt gateway and OpenRouter. This is **not local
inference**, and it does not debit GitHub subscription credits.

The default wallet profile uses `openai/gpt-oss-120b` on OpenRouter. The wallet
operator can change its model in `cli_profiles.copilot`; it must support tools
and the provider's protocol. OpenRouter `usage.cost` receipts finalize actual
costs, with zero Kurt markup. Missing/unknown actual costs remain pending.
Existing wallet configurations can add this explicit profile:

```json
"copilot": {"provider": "openrouter", "model": "openai/gpt-oss-120b"}
```

No real merchant payment, personal Copilot authorization, wallet activation or
paid inference was performed by this integration task.

## Offline candidates for future adapters

These are researched options, **not additional installed/default choices**:

| CLI | Type | Local/offline configuration |
| --- | --- | --- |
| Ollama | Model runner/chat | Download models first and use a local model, not a cloud model. Kurt already has an Ollama API provider; an Ollama CLI adapter would be separate. |
| Aider | Coding agent | Connect to local Ollama or another local OpenAI-compatible server. |
| OpenCode | Coding agent | Select local Ollama, LM Studio or another local inference provider. |
| LM Studio `lms` | Model runner/chat/server | Use downloaded local models with `lms chat` or its local server. |
| llama.cpp | Inference CLI/server | Run an already downloaded local model file. |
| Qwen Code | Coding agent | Configure its OpenAI-compatible provider to a local model server with tool support. |
| Copilot CLI | Coding agent | Supports local BYOK endpoints; a separate Kurt local profile and offline policy are future work. |

For a first offline coding setup, start with Ollama + Aider or OpenCode.
Actual model size/speed depends on the iMac's chip and RAM. Download the runtime
and models while online first. Keep inference endpoints local and disable
cloud fallbacks, telemetry, remote MCP/search and update checks when verifying
offline operation; a local model alone does not make every agent feature offline.

Primary references checked November 18, 2026:

- [GitHub programmatic CLI reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-programmatic-reference)
- [GitHub authentication and offline mode](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/authenticate-copilot-cli)
- [GitHub BYOK](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-byok-models)
- [Ollama CLI](https://docs.ollama.com/cli)
- [Aider + Ollama](https://aider.chat/docs/llms/ollama.html)
- [OpenCode local providers](https://opencode.ai/docs/models)
- [LM Studio CLI](https://lmstudio.ai/docs/cli) and [offline operation](https://lmstudio.ai/docs/app/offline)
- [llama.cpp](https://github.com/ggml-org/llama.cpp)
- [Qwen Code local providers](https://github.com/QwenLM/qwen-code/blob/main/docs/users/configuration/model-providers.md)
