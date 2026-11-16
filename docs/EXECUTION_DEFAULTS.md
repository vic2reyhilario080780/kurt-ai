# Default AI model and CLI

Kurt stores execution defaults in `~/.kurt/persona.json`. Existing users
retain `auto` for both fields until they choose a default. This change
does not select a paid provider or CLI on the user's behalf.

## Choose from the menu

Run **`kurt setting`** in an interactive terminal, or open **`/setting`**
inside chat, for four separate pickers: **Chat AI**, **CLI**, **Image AI**
and **Video AI**. Arrow keys select, typing filters, Enter opens/saves,
Esc goes back/cancels, and Tab returns to the four categories.
`kurt setting model`, `cli`, `image` and `video` open that role directly.
Noninteractive calls still report settings without opening a prompt.

In `kurt chat`, type `/`, open `/config`, then **model** or **cli**.
The model menu offers provider/model entry, routing-table models and the
OpenRouter catalog. CLI choices show installation status; installation
does not prove working authentication or available credits.

CLI choices include `auto`, `codex`, `claude`, `gemini`, `openclaw`, and
`vibe` (Mistral Vibe). Vibe uses headless `--agent ask` mode with bounded turns
and execution time, supports `MISTRAL_API_KEY` or its own macOS Keychain login,
and does not automatically approve editing tools. The trusted Vibe adapter can
read its public CA bundles without disabling TLS verification. Installed Vibe
3.1.2 passed a live response check through this adapter. Select it through the CLI
picker or `/cli default vibe`; use `vibe --setup` if authentication is missing.
Your existing default is preserved until you select a different one.

Both session `/model` and saved Chat AI pickers now list text-output
conversation models only. Models accepting images as input remain valid
chat choices; image/audio/video outputs and transcription/generation
routes are excluded. Entries with unknown output metadata are omitted
instead of guessing. OpenRouter entries show **Paid**, **Free**, or
**pricing unavailable** from catalog metadata; typing `paid` filters the
priced entries. Account credits and current availability remain separate.
The cached catalog inspected on 2026-11-15 had 470 entries, of which 451
qualified for the chat picker and 19 were excluded.

Media pickers cover the supported fal text-to-image/text-to-video catalog
and bundled presets; Replicate IDs can be entered manually. These lists
do not claim to contain every model from every AI vendor. Chat defaults
cannot be saved with a media-only provider such as fal/Replicate.

Default CLI choices currently wired: **Codex, Claude Code, Gemini CLI and
OpenClaw**. `auto` uses the selected API model. GitHub CLI and Peekaboo
remain explicit utility commands. Mistral Vibe, a DeepSeek CLI and GitHub
Copilot CLI are not added by this change; their adapters still need their
own installation/authentication integration.

## Commands

```text
# Save and immediately use a default model inside chat:
/model default mistral-small-latest mistral
/model default deepseek-flash deepseek
/model default <exact-openai-model-id> openai
/model default <catalog-model-id> openrouter
/model choose-default

# Use a model for this session only:
/model <model-id> <provider>
/model auto

# Save a default CLI, or override it for one session:
/cli default claude
/cli default codex
/cli use gemini
/cli use auto
/cli status

# Save defaults outside chat:
kurt setting model mistral-small-latest --provider mistral
kurt setting cli claude

# Inspect saved settings without changing them:
kurt setting model
kurt setting cli

# Start a session with explicit overrides:
kurt chat --model 'mistral-small-latest|mistral'
kurt chat --cli claude
```

Model IDs must exist and be available on the chosen provider account.
Provider examples are not a guarantee of model availability or balance.
Direct API routes exist for OpenAI, Mistral, DeepSeek and Google, alongside
the existing OpenRouter/Groq/Anthropic/Ollama routes. Google accepts Kurt's
`GOOGLE_AI_KEY` or standard `GEMINI_API_KEY` / `GOOGLE_API_KEY` variables.

Saving a model makes API mode active (`default_cli=auto`). Saving a CLI
makes it the ordinary-chat executor and retains the saved model for when
CLI mode is set back to `auto`. Explicit `--model` disables the saved CLI
for that session unless `--cli` is also supplied. Slash commands remain
available regardless of the selected executor.

## Model failover

While a model is selected, missing credentials, authentication errors,
invalid requests, unsupported models, ordinary rate limits and server
failures do not silently change providers. Existing short rate-limit
retries may retry the same model. Secondary model/CLI delegation tools
are hidden and blocked; direct search, file and desktop tools remain
available to the selected conversational planner.

HTTP 402 or recognized structured insufficient-credit/quota codes enable
automatic routing for the rest of the session. Observed tool receipts
remain in context rather than replaying completed tool calls. The
exhausted API provider is excluded from automatic provider substitution.
The saved default stays unchanged: restart the chat, reselect the model
or change settings to retry it after topping up.

## Image/video defaults and welcome banner

Image and video have independent saved defaults. In the picker, open
`/config` → **image** / **video**, or open `/image-model` / `/video-model`.
Bundled choices include Nano Banana / Nano Banana 2.1 and FLUX Schnell/Dev
for images; Kling 3.0 Standard/Pro and Wan 2.7/MiniMax H3 Max for video. The fal catalog adds entries filtered to `text-to-image`
or `text-to-video`; editing/upscaling and reference-image models are not
offered as prompt-only generators. Exact fal or Replicate model IDs can
also be entered manually. Other providers require separate media adapters.

```text
/image-model fal-ai/flux/schnell fal
/video-model fal-ai/wan/v2.7/text-to-video fal
/image-model choose
/video-model choose
/image-model auto
/video-model auto
kurt setting image fal-ai/flux/schnell --provider fal
kurt setting video fal-ai/wan/v2.7/text-to-video --provider fal
```

These preferences do not change the chat model or CLI. The native
`generate_media` tool resolves the saved model per request and stays on
that generation provider; missing credentials block generation instead
of substituting a text model. fal responses support both `images[].url`
and `video.url`, with a longer timeout for video. Replicate polling is
bounded. Interrupted/pending generation should be checked at the provider
before submitting another paid request. The standard `FAL_KEY` variable
is accepted alongside Kurt's `FAL_API_KEY`.

The welcome banner displays **Chat default**, **CLI default**, **Image
default** and **Video default**, separately from the active executor.
`auto` media entries show the resolved model/provider. Values wrap on
narrow terminals. Newly saved defaults appear on the next welcome screen.
Media settings govern Kurt's native generation tools; external CLIs keep
their own media capabilities and configurations.

Preset schema references: [FLUX Schnell](https://fal.ai/models/fal-ai/flux/schnell/api),
[FLUX Dev](https://fal.ai/models/fal-ai/flux/dev/api),
[Wan 2.7](https://fal.ai/models/fal-ai/wan/v2.7/text-to-video/api),
[MiniMax H3 Max](https://fal.ai/models/minimax/h3-max/text-to-video/api).

## CLI behavior

Ordinary chat goes directly to the chosen CLI with recent conversation
context and the existing credentials/permission adapter. Claude/Gemini
execution is bounded; Codex keeps its existing read-only default.
OpenClaw receives the current workspace and displays returned text when
its response includes text payloads.

A structured CLI quota error enables auto routing for the **next** user
request. The failed CLI task is never automatically replayed, since it
may already have changed files or application state. Timeouts, output
limits, missing executables, login failures and unstructured error text
retain the CLI choice and report incomplete execution. Human-readable
"out of credits" text alone is not treated as a verified quota receipt.

F5 chat and standalone voice use the same saved execution defaults.
Specialized explicit commands and scheduled jobs retain their existing
execution paths.

## Validation

On 2026-11-15, all **288 tests passed** outside the restricted sandbox.
The final diff also passed `git diff --check`.

After adding media defaults/banner support, all **295 tests passed**;
seven media/banner checks also passed after the final layout adjustment.
Those cover independent persistence, model/category selection, runtime
generation routing, missing-key behavior, fal image/video output parsing
and complete banner values at 60/80/120 columns. No paid media calls were
made; provider generation responses are mocked.

After separating the role pickers and adding interactive native settings,
all **323 tests passed**, including actual keyboard navigation from the
four-category picker through CLI selection and persistent saving.

Tests cover persistence across fresh sessions, explicit override
precedence, slash settings, CLI context/failure handling, structured
quota detection, direct-provider endpoint routing, model pinning,
delegation blocking and preservation of tool receipts during failover.
Provider responses and default CLI tasks are mocked; no paid live model
requests or new CLI logins were performed for this change.

API references: [Mistral](https://docs.mistral.ai/api/endpoint/chat),
[DeepSeek](https://api-docs.deepseek.com/),
[DeepSeek error codes](https://api-docs.deepseek.com/quick_start/error_codes/),
[Google compatibility](https://ai.google.dev/gemini-api/docs/openai),
[OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).

## Media execution checks (2026-11-16)

The picker, saved setting, banner and request dispatcher were tested together
with named Nano Banana 2.1 and Kling 3.0 Standard selections. Their exact fal
model IDs become the requested endpoint paths; the generation router is strict
and cannot silently substitute another provider. Known bundled models cannot
be saved under the wrong image/video role. Advanced manually entered endpoints
are not universally schema-validated; prompt-only compatibility still matters.

Examples of the official endpoint IDs:

- [Nano Banana](https://fal.ai/models/fal-ai/nano-banana/api): `fal-ai/nano-banana`
- [Nano Banana 2.1](https://fal.ai/models/google/nano-banana-2.1): `google/nano-banana-2.1`
- [Kling 3.0 Standard](https://fal.ai/models/fal-ai/kling-video/v3/standard/text-to-video/api): `fal-ai/kling-video/v3/standard/text-to-video`

Use `/setting` → Image AI / Video AI to select them. Empty catalogs still
include these bundled choices. Picker search is case-insensitive.

Explicit generation commands bypass chat/CLI model selection and call the same
saved-default generation tool:

```text
/image A blue bird sitting on a branch
/video A blue bird flying through a forest
kurt generate image "A blue bird sitting on a branch"
kurt generate video "A blue bird flying through a forest"
kurt generate image --dry-run
kurt generate video --dry-run
```

The dry run prints the resolved model/provider and key-configuration status
without submitting a paid job. Key configuration does not prove available credits.
Actual generation uses the selected API provider's credits, not a consumer
subscription on a model's website. No user defaults are changed by these commands.

Native chat uses `generate_media` even when a chat model is pinned. Generic
`call_model` cannot bypass media defaults through fal/Replicate; the coding agent
also exposes the saved-default generation tool. An external CLI has its own
tools and permissions: if it cannot invoke media generation, use `/image` or
`/video` for deterministic dispatch rather than assuming it has generated media.
CLI prompts now explain this distinction.

Validation used mocked provider HTTP responses with real request serialization,
including exact endpoint/prompt and a failure with no alternate model or duplicate
POST. No billable image/video job was submitted. No live provider balance or
artifact quality claim is made.

## Default CLI troubleshooting (2026-11-16)

`/cli probe vibe` checks the installed Vibe executable/version through Kurt's
service adapter. It does not submit a model request or prove authentication,
credits or task completion. `/cli status` shows the active and saved CLI.

Long CLI conversations are now reduced by dropping complete oldest turns until
the full prompt fits within 30 KB. System instructions and the latest request
are never truncated. A notice in the CLI context says that earlier turns were
omitted. CLI persona construction does not repeat conversation history inside
the system prompt, since that same history is already sent as separate context.
Oversized instructions/latest requests still fail with a specific error.

CLI failures show the process status/exit code, the useful end of stderr and any
partial answer, marked unverified. This does not auto-replay a failed task or
change the selected CLI. Restart a running Kurt session to load code updates.

The live default adapter and a full chat from the home directory both returned
expected Vibe response markers. A deliberately oversized old history also passed
a real Vibe response after compaction. Full suite: 381 tests passed. The user's
original error text was not supplied during these checks, so its exact cause is
not established.

## All default CLI adapters (2026-11-16)

See [the full CLI audit](DEFAULT_CLI_AUDIT.md) for current live results and fixes.
Use `/cli probe all` for version checks and `/cli test <name>` for a minimal
response test that may consume credits. Missing executables cannot be selected
from the picker; installed does not mean authenticated or funded. Claude and
Gemini structured replies are parsed, and zero-exit errors/empty responses are
not accepted as final answers. Existing saved defaults remain unchanged by tests.

Codex, Claude, OpenClaw and Vibe passed live response tests. Gemini returned
Google HTTP 503/high demand, so its provider readiness remains unverified.
