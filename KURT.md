# KURT.md — Shared Update Log

Iisang changelog para sa lahat ng AI coding tool na ginagamit sa project na ito
(Claude Code, Antigravity, Codex, o iba pa). Layunin: kahit anong tool ang
gamitin, dito dumadaan ang tala ng bawat natapos na task, para may isang
pinagsasamang kasaysayan ng mga pagbabago — hindi kanya-kanyang memory.

## Paano gamitin

- Bago magsimula ng bagong task, basahin ang mga pinakahuling entries dito
  para malaman ang huling ginawa, kung ano ang on-hold, at bakit.
- Pagkatapos matapos ang isang task (feature, fix, refactor, o decision na
  may epekto sa direksyon ng project), idagdag ang bagong entry sa **itaas**
  ng listahan sa ibaba (pinakabago sa pinakataas).
- Isang entry = isang bounded piece of work. Panatilihing maikli: ano ang
  nagawa, bakit, at ano ang susunod/pending kung meron.
- Gamitin ang format na ito:

  ```
  ## YYYY-MM-DD — <maikling titulo> (<tool na gumawa: Claude Code / Antigravity / Codex>)
  - Ano: <1-3 bullets kung ano talaga nagawa>
  - Bakit: <context/dahilan, kung hindi obvious>
  - Susunod: <kung may pending/follow-up; alisin kung walang laman>
  ```

- Huwag ilagay dito ang mga detalyeng makukuha naman sa `git log`/`git diff`
  (hal. exact line-by-line na pagbabago). Dito nakalagay ang **bakit** at ang
  **malaking larawan**, hindi ang buong diff.

---

## Behavior ni Kurt — permanenteng gabay

- Sa ordinary chat, unawain ang goal at conversation context gamit ang AI. Huwag ibalik ang keyword/regex matching bilang kailangang gate para makagamit ng app o tools; dapat gumana ang bagong paraphrase at implicit goal kahit walang app name o “open.”
- Mag-discover ng available apps/tools, ideklara ang buong goal at completion condition, saka mag-initiate ng kinakailangang actions. Gamitin ang loop na **understand → plan → act → observe → adjust**, hindi fixed na bilang ng response layers. Ang kasalukuyang budget ay hanggang 100 tool calls bawat task.
- Para sa app-only goal, huminto kapag verified na ang eksaktong foreground process. Huwag magdagdag ng clicks, bagong dokumento o pagbabago sa content para lang magpakitang kumikilos. Sa workflow, ituloy ang mga kinakailangang hakbang hanggang ma-observe ang requested result o may tunay na blocker.
- Magtanong ng isang focused question kung mahalagang detalye ang kulang. Maaaring magmungkahi ng isang kapaki-pakinabang na susunod na hakbang, pero ang suggestion ay hindi pahintulot na gawin ito. Manatili sa goal na ibinigay ng user.
- Ibase ang success sa actual tool receipts at observed effects. Huwag mag-claim ng document readiness, typing, saving o buong task completion dahil lang nabuksan ang app. Obserbahan muna ang indeterminate action bago mag-adjust; huwag basta ulitin ito.
- Panatilihin ang recent session context kahit naka-off ang disk memory. I-test ang implicit goals, contextual follow-ups, tanong na hindi dapat mag-trigger ng action, at multi-step workflows—hindi puro mga linyang kabisado ng parser.

Implementation at nasubok na scope: [docs/SEMANTIC_ASSISTANT.md](docs/SEMANTIC_ASSISTANT.md).

## 2026-11-19 — Save checkpoint: catalogs, BYOK and integration fixes (Codex)
- Saved scope: Complete primary catalogs, additional BYOK providers, masked in-picker key setup, Gemini model/error handling, compact Groq tool discovery and MCP audit/SQLite repair. Latest full regression result: 558 tests passed. Detailed evidence and remaining live-test limitations are recorded in the entries and verification reports below.
- Pending: New-provider authenticated inference needs user keys; Gemini inference remains provider-blocked in the last live tests. The user's mention of Hugging Face on GitHub versus another Hugging Face entry was not clarified, so no second HF provider or guessed integration was added. GPU hosting/offline expansion remain parked.

## 2026-11-19 — Optional BYOK providers and in-picker API setup (Codex)
- Providers: Added Hugging Face, Together, Fireworks, WaveSpeed and Novita provider definitions plus Replicate catalog browsing. Additional catalogs exclude exact IDs/declared Hugging Face identities already in OpenRouter/fal.ai; versions and unconfirmed aliases remain distinct. Pagination is bounded with Load next pages and explicit partial counts. Existing primary catalog totals remain intact.
- Flow: Chat/image/video model selection opens a provider connection menu before applying the model. Enter/replace key uses masked input in the same picker; official key/login pages open in the browser without submitting credentials. Saved keys are owner-private atomic .env updates preserving unrelated entries. Key input is never a search/chat request; undo/redo is cleared and voice draft handoff is blocked while entering secrets. Existing wallet providers offer explicit BYOK/wallet choice; new providers require BYOK. No personal keys/defaults were changed by development.
- Routing: Added direct OpenAI-compatible chat routes for HF/Together/Fireworks/Novita and a schema-gated prompt-only WaveSpeed media adapter with one submission and bounded fixed-origin polling. Unsupported contracts stay browse-only. Replicate's existing wallet route is preserved until BYOK is explicitly selected. Generation still requires verified artifacts; catalog presence or a saved key is not a successful inference claim.
- Validation: 558 isolated regression tests passed, including fourteen new BYOK tests. Live metadata checks loaded HF 163 (117 primary duplicates excluded), Novita 109 (51 excluded), and the first three Replicate pages: 75 (five excluded; more remain). Together/Fireworks/WaveSpeed need user keys for authenticated catalogs. Chat routing/secret handling/wallet isolation/WaveSpeed polling used synthetic tests; no live inference, generation, account creation or login performed. Source graph updated. Guide: docs/BYOK_PROVIDERS.md; evidence: docs/byok-provider-verification.json.

## 2026-11-19 — Complete OpenRouter/fal.ai catalog pickers (Codex)
- Change: /models now opens both complete provider catalogs with All models, mutually exclusive categories, search, model details and official setup pages. Chat/image/video default pickers link to the full catalogs. Unsupported workflows remain visible but cannot be selected as working defaults. /models routing preserves the old rule table; /models refresh and in-picker refresh reload catalogs. Memory/disk caches last an hour.
- Reliability: Model IDs are deduplicated only within their provider; versions remain distinct. HTTP errors, malformed/inconsistent fal.ai pagination, duplicate/incomplete page sets and corrupt caches cannot silently replace a complete catalog with a partial list. Cache writes are atomic. No personal defaults or keys changed.
- Validation: Fresh API reads returned 480 OpenRouter IDs and 1,356 fal.ai endpoints. All-model views and category sums matched each total. 544 isolated regression tests passed, including ten catalog tests for complete counts, unknown categories, exact-ID deduplication, failed refresh retention, compatible default actions and real picker navigation/refresh. No model inference or paid generation performed. Evidence: docs/model-catalog-verification.json; guide: docs/MODEL_CATALOGS.md.
- Later providers: User prefers optional BYOK for additional providers and excluding verified exact-model/version duplicates already offered by OpenRouter/fal.ai. These provider integrations and cross-provider alias mappings remain deferred; no extra provider or billing mode was enabled.

## 2026-11-19 — Compact Groq tool discovery and SQLite config repair (Codex)
- Fix: Groq now receives core data/app/search schemas plus an AI-driven select_tools catalog. All available tools remain discoverable by semantic name, without a user-prompt keyword gate. Selected tools retain full contracts, goal checks and pinned-model orchestration restrictions. Initial schema JSON shrank from 26,884 to 10,839 characters (about 60%); other providers retain the full catalog.
- Validation: 534 isolated regression tests passed. A live Groq synthetic workflow using the first compact variant (9,088 characters) completed inspect_native_input → search_native → inspect_native → run_native, verifying eight rows and sum 1,160. Final variant additionally keeps core app/search tools available immediately and passed all regression tests. Rate limits/cooldowns still apply; charges were not measured. Details: docs/groq-mcp-fixed-verification.json.
- SQLite: Replaced only the legacy saved SQLite package with the current mcp-sqlite-server recipe after successful initialization/list_tools (five tools). Retained the old ./data.db path in the description for explicit tool arguments; no database queried or created. Other connections/credentials and WordMint's unfunded crypto setup were unchanged.

## 2026-11-19 — Groq limits and saved MCP connection audit (Codex)
- Groq: A small direct request returned HTTP 200. A synthetic native workflow reached three discovery tools then stopped on 429 rate_limit_exceeded/type tokens. Headers/error confirmed an 8,000 TPM limit with subsequent requests of 6,400–7,174 tokens and Retry-After 30–51 seconds. This is token throttling, not evidence of depleted billing credits. Thirty-two isolated routing/native tests passed: ordinary 429 stays pinned, short pending-decision retries preserve tool receipts, and confirmed quota remains a separate condition.
- MCP: Six saved servers initialized and listed tools: filesystem (14), Replicate (35), Composio (12), GitHub (26), Puppeteer/Playwright (25), Postgres (1). These checks do not prove downstream account permissions or successful tool execution. Composio MCP connectivity is separate from the management API's earlier 401.
- Pending setup: Saved SQLite uses a removed npm package (404); the current bundled mcp-sqlite-server preset initialized with five tools without changing the saved config. WordMint startup requires X402_PRIVATE_KEY and USDC on Base, confirmed by package README; no crypto credentials or payments were provided. No database queries, app actions, defaults or saved credentials/configs changed. Details: docs/groq-mcp-nov19-verification.json.

## 2026-11-19 — Gemini direct API comparison (Codex)
- Test: One synthetic gemini-3.8-flash prompt through Kurt ModelRouter's direct Google OpenAI-compatible endpoint, strict provider selection, wallet disabled and no automatic retry. Result: ReadTimeout with no verified answer. The CLI previously returned 503 for this model; direct API therefore did not provide a working alternative in this run. This does not prove a Google-wide outage or invalid credentials. No user defaults or keys changed; charges were not measured.
- Next: Keep the working Mistral chat default; Gemini inference remains pending a successful later test. Details appended to docs/gemini-cli-nov19-verification.json.

## 2026-11-19 — Gemini CLI model selection and overload diagnostics (Codex)
- Findings: Google model-list authentication returned HTTP 200 from Python and Node inside the Gemini service sandbox. Default CLI generation repeatedly returned 503 high demand. Explicit gemini-2.5-flash generation was rejected as unavailable to new users (404), despite appearing in the model list; Google recommended gemini-3.8-flash. That current model also returned 503 and timed out, so successful inference remains unverified.
- Change: Direct Gemini CLI calls now explicitly select gemini-3.8-flash, with KURT_GEMINI_MODEL override and explicit caller model precedence. Wallet-managed routing and version/help probes are preserved. Slash/default CLI failures explain 503 availability separately from authentication and keep the no-replay behavior. Workspace trust and tool approvals remain enforced. See docs/GEMINI_CLI.md.
- Validation: All 531 isolated regression tests passed, including model precedence, wallet isolation and overload diagnostics; code graph refreshed. Live synthetic attempts produced no verified final answer; provider charges were not measured. Follow-up: retry a small test when Google capacity recovers. No Gemini-specific personal settings or credentials were changed.

## 2026-11-19 — Integration smoke checks (Codex)
- Validation: All 529 isolated local tests passed. Live synthetic delegation through Kurt passed for Claude Code and Codex. Gemini CLI failed with fetch/network errors and internal retry messages; this does not establish an invalid API key. No automatic task replay by Kurt.
- Validation: Live Groq native workflow reached inspect_native_input and search_native, then stopped on HTTP 429 before completion. OpenClaw and Peekaboo version checks passed outside the nested development sandbox. Eight CLI choices are installed; eight MCP configurations are saved/enabled, which does not verify their remote connections.
- Scope: Speech readiness reports configured Groq and a cached local model. Actual microphone, audible playback, desktop actions, remote MCP accounts, remaining CLI inference and paid image/video generation were not tested in this run. Provider charges were not measured. Follow up on Gemini connectivity and Groq rate limits.

## 2026-11-18 — Copy-paste USB credential import command (Codex)
- User request: Put the import command on GitHub so it can be copied into PowerShell after plugging in the USB.
- Ano: Added a visible README section and migration-guide instructions for importing directly from USB. The command prompts for the full file path, accepts File Explorer Copy as path quotes/spaces, and uses the default installed virtual environment. Documented the separate hidden transfer password, restart and optional crypto dependency fix. No Downloads copy or reinstall required.
- Scope: Documentation only; no credentials exported, imported or published. Existing credential preservation/encryption behavior is unchanged.

## 2026-11-18 — Windows voice prompt output scope (Codex)
- Observed: Native Windows CI passed the new speech tests, then the existing real-prompt handoff test hit NoConsoleScreenBufferError when patch_stdout selected a default Windows console despite the prompt using an explicit redirected output.
- Fix: Bind stdout patching to the active PromptSession output through create_app_session, preserving the no-Enter voice handoff test rather than skipping it.
- Validation: 529 isolated full-suite tests passed on macOS. The corrected hosted workflow passed on Windows, macOS and Ubuntu for source 2b5a679, including the real prompt handoff test and all twenty-one speech tests. [CI run](https://github.com/vic2reyhilario080780/kurt-ai/actions/runs/44304407683). The live synthetic benchmark made two provider requests; actual charges were not verified or inferred. Actual user-mic and audible device checks remain separate.

## 2026-11-18 — Tagalog/Taglish voice pipeline and conversation fixes (Codex)
- Ano: Wired live voice to shared-setup Groq Whisper large-v3/turbo or an existing cached local recognizer, with explicit Tagalog/auto-Taglish settings, bounded personalized vocabulary hints and real decoder-quality checks. Removed fabricated 0.9 confidence. Added `/speech` and `kurt speech` commands; uncertain transcripts ask for repetition instead of executing actions, and repeated uncertainty/provider failure pauses hands-free mode.
- Ano: Background wake recognition stays local; no cloud upload without a wake/F5/hotkey activation. Cached ASR loaders refuse model downloads. New installs include lightweight online-voice dependencies and model-free WebRTC VAD. Windows/Linux Filipino MP3 playback uses an isolated bounded worker; no ffplay dependency. Online audio upload/credit behavior is shown before listening.
- Ano: Standalone voice retains twelve recent message pairs for follow-ups, strips spoken Markdown and respects persona language. Two-second default pause is configurable; spoken stop, stale-turn cancellation and matching TTS acknowledgments remain enforced. Speech preferences/vocabulary are portable through settings export/import.
- Validation: 529 isolated full-suite tests passed, including twenty-one focused speech checks and nineteen existing voice-turn tests. A clean environment passed VAD/readiness without local Whisper packages or model weights. Two explicit live synthetic Filipino TTS→Groq tests had zero normalized word errors, including Kurt/Bhe/Vibe/DeepSeek; no microphone recording or app actions. This is not proof of the user's accent/room accuracy. Code graph refreshed. Details: [docs/TAGALOG_VOICE.md](docs/TAGALOG_VOICE.md), [docs/speech-verification.json](docs/speech-verification.json).
- Remaining: Actual user-mic/accent and audible device tests. Hosted Windows/macOS/Linux voice smoke checks passed in the later verification entry above. GPU hosting and offline expansion remain parked. No large dictionary/dataset/model weights were downloaded.

## 2026-11-18 — Tagalog voice/dictionary audit (Codex)
- Findings: Live voice still uses local Whisper small/base with language auto-detection, no vocabulary hints and hardcoded 0.9 confidence. The separate Groq Whisper transcription route is not wired into the listener. Fresh Windows voice extras also omit the local STT/VAD dependencies still required at startup.
- Research: Found downloadable Kaikki Tagalog lexical data and Filipino/Taglish speech datasets. Recommend a short personalized vocabulary prompt, explicit Tagalog/automatic Taglish selection, an opt-in online STT route and quality-based clarification; a dictionary alone does not improve acoustic recognition or train the model.
- Validation: 19 voice-turn fixture tests passed; this iMac has the inspected voice libraries. No actual microphone/recognition-accuracy test, download, paid request or voice setting change was performed. Offline expansion remains parked. Details: [docs/TAGALOG_VOICE_AUDIT.md](docs/TAGALOG_VOICE_AUDIT.md).

## 2026-11-18 — Native Windows CI Unicode output fix (Codex)
- Observed: GitHub's real Windows runner passed dependency installation, fourteen portability tests, eight encrypted credential tests, PowerShell installer syntax and device status, then failed CLI help with a CP1252 UnicodeEncodeError on the robot icon. Linux smoke checks passed; macOS runner was still queued at observation time.
- Fix: Configure Windows stdout/stderr as UTF-8 before Rich/Typer initialization, including redirected output, without changing OS code pages or non-Windows stream settings.
- Validation: 508 isolated project tests passed on macOS, including two encoding regressions. Native Windows CI rerun on source 76cef71 passed all sixteen portability tests, eight credential-transfer tests, PowerShell syntax, dependency install, bootstrap dry-run, device status, CLI help and version. Linux smoke job passed; macOS hosted job was still queued when recorded. [Windows CI job](https://github.com/vic2reyhilario080780/kurt-ai/actions/runs/44280126643/job/134718286587). Code graph updated. No personal credentials exported or hosting activated.
- Remaining: Actual user-PC desktop/audio/CLI-account checks and end-to-end one-command download/install with owner input are still distinct from CI smoke verification.

## 2026-11-18 — One-command GitHub installer and encrypted owner credentials (Codex)
- User request: Install from GitHub in one command and reuse the owner's configured provider credentials without entering each key again; future SaaS should use the owner's provider accounts through Kurt billing.
- Ano: Added a public-source PowerShell installer that resolves main to an immutable source revision, downloads the GitHub archive without requiring Git, and runs the isolated bootstrap. Optional `-CredentialsFile` imports a separately copied private owner backup after one hidden transfer passphrase. Python 3.10+ remains required; existing install directories are not overwritten.
- Ano: Added `device export-credentials` / `import-credentials`, using authenticated Fernet encryption with a random salt and PBKDF2-HMAC-SHA256 (1,200,000 iterations). Wrong passwords, modified files, malformed/oversized data fail before writes. Configured target keys are preserved unless replacement is explicit. Actual credentials were not exported during development.
- Boundary: Verified this repository is public. The real .env and encrypted owner backups stay outside Git/installer bundles. Personal-device transfer is distinct from SaaS: SaaS provider keys stay server-side and users receive Kurt tokens. The existing gateway still needs deployment; no hosting, GPU/offline work or account authorization was activated.
- Validation: 506 isolated project tests passed on macOS, including eight synthetic credential-transfer checks and fourteen portability checks. Three-OS CI now includes encryption tests and a Windows PowerShell syntax check. Native Windows execution remains to be verified. Updated [docs/OS_MIGRATION.md](docs/OS_MIGRATION.md); code graph refreshed.

## 2026-11-18 — Windows-first migration, isolated installers and portable settings (Codex)
- User direction: Prioritize moving Kurt to Windows first; retain macOS/Linux portability work. Cloud GPU hosting and offline expansion remain parked.
- Ano: Replaced global pip/all-tools setup with a stdlib bootstrap and project-local `.venv`, default web/media extras, optional voice/desktop/npm/browser installs, double-click Windows/macOS install/start launchers and platform-specific dependency selection. Peekaboo is optional because it is macOS-only. Python 3.10+ remains a prerequisite; this is not a bundled/signed EXE installer.
- Ano: Added `kurt device status` and validated preference export/import for persona and AI/media defaults. Credentials, wallet activation/tokens, local project paths and history are excluded. Missing/unsupported CLI defaults reset to auto with a visible warning. Picker and CLI selection block known unsupported OS adapters.
- Ano: Windows subprocess output now uses bounded pipe-reader threads and process-tree timeout cleanup; known npm launchers use native Node/JS argv and Windows `.cmd`/`.exe` resolution instead of Unix shims. Added three-OS CI smoke jobs; no hosted CI run is claimed.
- Validation: 498 isolated full-suite tests passed on macOS. Fresh temporary `.venv` successfully installed `.[web,media]`, passed dependency checks, loaded CLI help/device commands and passed portability tests. Code graph updated. No new models, cloud services, global package changes, login changes or paid inference. Details: [docs/OS_MIGRATION.md](docs/OS_MIGRATION.md).
- Pending: Actual Windows installer/launcher, native CLI/audio/desktop tests and CI execution. Copilot/DeepSeek read-only adapters still require macOS enforcement; signed installers/bundled Python and equivalent Windows/Linux kernel isolation remain future work.

## 2026-11-18 — Cloud GPU hosting and offline mode parked (Codex)
- User decision: Park cloud GPU/server selection and provisioning, and local/offline model/CLI mode, until explicitly resumed. Keep the research and architecture notes for later; do not start downloads, installations or cloud purchases for these items.
- Scope: Documentation/status update only; existing Copilot integration, API/CLI defaults and wallet implementation are preserved. Cross-platform distribution remains a recorded future plan, not completed work.

## 2026-11-18 — Cloud-first desktop distribution direction (Codex)
- User direction: Keep large model downloads and server-compatible AI CLI dependencies in Kurt's cloud; aim for simple Windows/macOS/Linux installs and automatic supported-platform selection, with optional local/offline execution.
- Audit: Existing installers still install heavy dependencies locally. Hosted foundations are not deployed and their current deterministic worker does not execute arbitrary AI CLIs. Windows/Linux desktop and isolation parity remain incomplete; macOS-only tools need replacement adapters or explicit unavailable status.
- Plan: Recorded cloud/local component placement, thin-client packaging, platform/CPU capability checks, workspace transfer, paired local desktop bridge and phased implementation in [docs/CLOUD_DESKTOP_PLAN.md](docs/CLOUD_DESKTOP_PLAN.md). Cloud inference needs internet and hosted compute/storage; true offline inference still needs a local runtime/model.
- Scope: Planning/repository review only. No model downloads, new installations, cloud provisioning, paid resources, installer implementation or migration of existing tools in this task. Cloud host/account/service configuration and real per-OS builds/tests are still required.

## 2026-11-18 — GitHub Copilot CLI picker, read-only adapter and wallet route (Codex)
- Ano: Installed/pinned the official Copilot CLI 1.0.113 locally and added picker/default/session selection, `/copilot`, readiness checks and agent delegation. Version probes do not claim working login/credits; existing defaults and personal account authorization were preserved.
- Ano: Read-only headless adapter exposes file viewing/search, requires successful final JSONL completion, rejects failed tools/partial output, bounds runtime/output and enforces macOS project write restrictions. No global tool approval or automatic task replay. Other runners now protect Copilot credential files too.
- Ano: Wallet mode uses isolated state, short-lived OpenRouter-scoped credentials and actual-cost receipt settlement, with no GitHub subscription fallback. Copilot's offline flag disables GitHub traffic in this mode; paid inference still uses the network. Documented future offline CLI candidates separately from installed choices.
- Validation: 484 isolated full-suite tests passed, including an actual kernel-blocked project write. Installed Copilot passed version probing and the real-local-wallet/mock-provider fixture, including a two-request file-reading tool round trip. Nine native provider routes also passed in that fixture; no real payment, provider key or paid inference used. Code graph updated. Details: [docs/COPILOT_CLI.md](docs/COPILOT_CLI.md), [docs/copilot-verification.json](docs/copilot-verification.json).
- Pending: Personal Copilot login/entitlement and live paid inference remain unverified. Offline candidates (Ollama CLI, Aider, OpenCode, LM Studio CLI, llama.cpp and Qwen Code) are researched options, not installed adapters. Existing wallet activation/merchant setup and DeepSeek balance blockers remain as recorded below.

## 2026-11-17 — Saved Vibe, DeepSeek at wallet checkpoint (Codex)
- Ano: Saved the shared-setup Vibe credential/model/search fixes, both installed DeepSeek adapters and picker/shortcut integration, and the centralized USD wallet/payment gateway. Detailed task entries and verification reports follow below.
- User decision: Actual provider costs only, 0% markup, USD; prepare payment integration because no processor account is configured yet.
- Validation: 475 isolated project tests passed. Local wallet protocol checks passed for nine provider routes and all seven installed CLI adapters, using synthetic credits and mocked upstreams. Real Vibe reply/search checks are separately documented; wallet fixture checks are not claimed as real paid inference.
- Pending: DeepSeek live reply remains blocked by insufficient API balance; payment integration/wallet mode are not activated in the user's account. Provider funding, real merchant checkout and invoices without automatic cost receipts require the documented setup/reconciliation steps. No real payment or provider top-up was performed.

## 2026-11-17 — Central USD wallet, actual cost, zero markup (Codex)
- User decision: USD, actual provider costs only, no markup; no payment processor account yet, prepare integration first.
- Ano: Added a private integer-money ledger, atomic reservations, idempotent settlement/corrections, scoped CLI credentials, provider-key gateway and wallet commands/banner. Native paid AI, media, transcription and optional cloud vision route through it; all seven CLI API adapters have gateway profiles. No silent direct-provider/subscription fallback in wallet mode.
- Ano: OpenRouter and matching fal billed events finalize actual reported costs; other/unknown bills stay pending until verified reconciliation. Token-rate estimates are not debited as actual costs. Unmetered paid search/tool routes are blocked or use native key-free search; standalone CLI usage remains separate.
- Ano: Prepared Stripe Checkout and signed/idempotent paid-webhook credits, refunds/disputes and private local operator commands. Manual credits are clearly not purchases. No real payment, merchant account, provider funding, deployment or automatic activation was performed.
- Validation: 475 tests passed in the isolated full suite. Nine native provider routes and all seven installed CLIs passed the real-local-server/mock-upstream protocol test with synthetic credits. Financial/security regressions cover precision, replay, concurrency, scope/tenant boundaries, key custody and payment verification. Details: [docs/KURT_WALLET.md](docs/KURT_WALLET.md).

## 2026-11-17 — DeepSeek Agent at Terminal CLI setup (Codex)
- Ano: Connected the already installed Python DeepSeek Agent 0.6.6 (`deepseek`) and Node Terminal CLI 1.3.0 (`deepseek-cli`) to shared Kurt setup credentials, CLI pickers/defaults, direct slash shortcuts, readiness checks and agent delegation. Official API endpoint and `deepseek-flash`; native chat picker also includes `deepseek-v4-pro`. Existing defaults/accounts/installations were not changed.
- Ano: Python worker omits the package CLI's unsolicited auto-test follow-ups and disables SDK retries/thinking for its legacy tool history. Node stdin adapter rejects step-limit/unfinished output. Both use isolated temporary state, bounded execution and enforced read-only project files; no global approval bypass.
- Bakit: The packages have different protocols; Node piped mode lacks interactive confirmations and Python read-only flags do not cover arbitrary shell writes. Local fixtures verified actual tool round trips and kernel blocking of attempted writes. Exact-command picker priority also prevents `/cli` selecting the new `/deepseek-cli` substring match.
- Validation: 419 isolated full-suite tests and 64 focused checks passed; both installed adapters passed local two-request tool fixtures with project writes blocked.
- Pending: Live Terminal CLI API test returned 402 Insufficient Balance; no verified live reply from either adapter. API top-up is required before explicit live readiness retests. Details: [docs/DEEPSEEK_SETUP.md](docs/DEEPSEEK_SETUP.md).

## 2026-11-17 — Headless Vibe read-only search permissions (Codex)
- Bakit: News request reached the model but ask-mode connector calls required interactive approval; repeated tool denials hit the turn limit. This was not an authentication failure.
- Ano: Invocation-only permissions for the exact web_search and news_search connector tools. No wildcard/global auto-approval; other permissions and standalone Vibe config remain unchanged. Approval errors no longer show unrelated invalid-key guidance.
- Validation: 50 focused tests passed; actual read-only web search finished successfully with official source URL, journal-confirmed successful tool effects and no approval denial. News permission is fixture-tested; no independent live news test or shell/file write authorization.

## 2026-11-17 — Vibe false invalid-key error traced to model access (Codex)
- Bakit: Saved Mistral key passed models lookup and exact Vibe API model request (200). Actual Vibe child used that same key but chose `zai-glm-5-3-flash-vibe-free`, receiving 404 on model lookup and 403 on completion. Vibe maps 403 to its generic invalid-key message.
- Ano: Kurt default Vibe invocation explicitly selects `mistral-medium-3.5` (API-compatible built-in alias), retaining ask mode and shared setup key. Standalone Vibe defaults and Chat AI selection are unchanged. Failure guidance now mentions model access instead of assuming the key is invalid.
- Validation: 48 focused tests passed; final installed `kurt cli test vibe` returned verified with the exact expected reply. No failed user task replay or credential replacement. API usage can consume credits. Detailed evidence: [docs/EXECUTION_DEFAULTS.md](docs/EXECUTION_DEFAULTS.md).

## 2026-11-17 — Shared setup API key for Vibe CLI (Codex)
- Ano: Vibe requests through Kurt read the current Mistral API key directly from Kurt setup, overriding stale inherited shell credentials. Key rotation applies on the next invocation; no duplicate Vibe credential copy or standalone login change.
- Ano: Missing/blank saved key blocks inference before launch; version probes remain available. Vibe failures identify Kurt setup as the shared credential source. Invalid saved credentials still require a valid replacement; no silent login fallback or paid retry.
- Validation: 47 focused tests passed across shared-key, defaults, adapters and orchestration; no paid inference or key replacement. Details: [docs/EXECUTION_DEFAULTS.md](docs/EXECUTION_DEFAULTS.md).

## 2026-11-17 — Saved development checkpoint (Codex)
- Ano: Pinagsamang checkpoint ng November 16 fixes: reliable exit via isolated microphone process, saved media-default routing/pickers, real local-image attachments with RAM follow-up context, at default CLI compatibility/diagnostics para sa Codex, Claude, Gemini, OpenClaw at Vibe.
- Ano: Kasama ang verified media downloads/receipts, guard laban sa invented artifact links, explicit Kling image-to-video reference support, regression tests at verification reports. Detalye nasa mga November 16 entries at linked docs.
- Validation: Latest isolated full suite: 400 tests passed; final focused media/attachment suite: 35 passed. Walang bagong paid render o personal photo upload sa media verification.
- Pending: Gemini live reply remained unverified dahil sa provider HTTP 503/high demand. Video file verification does not verify exact dialogue/lip sync. SaaS billing/shared-provider-credit design remains parked.

## 2026-11-16 — Media receipts at photo follow-up (Codex)
- Bakit: Ang reported video link ay HTTP 404; walang historical job receipt para patunayang nag-render. Image bytes ay nawawala rin sa follow-up at text-only ang dating generator contract.
- Ano: Latest photo retained in RAM across follow-up (cleared with session); explicit Kling Standard/Pro image-to-video picker choices and exact `start_image_url` reference dispatch. Unsupported defaults block before payment, without silently changing selection.
- Ano: Download, bounded size, image/container/stream verification, local file plus SHA-256 receipt before completion. Deterministic native media result and structural guard against newly invented video/CDN links. Failed/indeterminate paid requests are not automatically replayed. File verification does not establish exact dialogue/lip sync.
- Validation: 400 tests passed in isolated full suite; 35 final focused checks passed. Fixture-based provider tests, synthetic PNG/MP4 download/inspection, 404 failure, reference payload, RAM follow-up/clear, no repeat. No paid render or private photo upload. Details: [docs/MEDIA_ARTIFACT_VERIFICATION.md](docs/MEDIA_ARTIFACT_VERIFICATION.md).

## graphify

Ang codebase na ito ay me-queryable knowledge graph via [graphify](https://github.com/safishamsi/graphify)
(`graphify-out/graph.json`). Kahit anong AI tool — Claude Code, Antigravity,
Codex — ay dapat gamitin ito bago manual na mag-grep/mag-read ng maraming
files para sa tanong tungkol sa architecture, dependencies, o relasyon ng mga
module.

- **Bago sagutin ang tanong tungkol sa codebase** ("paano gumagana ang X",
  "ano ang tumatawag sa Y", "trace ang data flow ng Z"): check muna kung may
  `graphify-out/graph.json`. Kung meron, `graphify query "<tanong>"` muna
  bago mag-manual explore.
- **Pagkatapos ng malaking code change** (bagong module, inalis na file,
  malaking refactor): i-rebuild/update ang graph —
  `graphify update .` para sa code-only incremental update (walang LLM,
  mabilis), o buong `/graphify .` kung may bago o nabagong docs/papers.
- Kung walang `graphify-out/graph.json` pa, hindi mandatory i-build agad —
  itanong muna sa user kung gusto niyang i-run ang `/graphify .` sa buong
  repo (gumagamit ng subagents/tokens, hindi instant).
- Huwag palitan ang entry format sa itaas ng graphify output — magkaibang
  layunin: ang Log ay para sa **bakit** ng mga pagbabago, ang graph ay para
  sa **structure** ng codebase.

---

## Log

<!-- Bagong entries dito, pinakabago sa pinakataas. -->

## 2026-11-16 — All default CLI adapters audited and fixed; Gemini provider unavailable (Codex)
- Live results: Codex, Claude, OpenClaw and Vibe returned expected replies through actual default adapters. Gemini is installed and reached Google, but returned HTTP 503/high demand and timed out during upstream retries; its model/account was not changed and response readiness is not claimed.
- Fixes: Codex non-Git/home startup with permission profile retained; exact OpenClaw SDK credentials-directory read access; structured Claude/Gemini final-response decoding; empty/error/queued responses no longer masquerade as success; private helper PATH isolation; clear provider diagnostics and waiting spinner. Uninstalled picker options are disabled.
- Checks: Added /cli probe all|name and kurt cli probe for non-billable version checks; /cli test name and kurt cli test submit one minimal live request and may use credits. Probes/tests preserve saved defaults. Legacy desktop probes remain available.
- Validation: 391 tests passed plus actual version probes for all five and live reply tests. Details: docs/DEFAULT_CLI_AUDIT.md and docs/all-cli-default-verification.json. No CLI/account login, configured model, or saved user default was changed.

## 2026-11-16 — Default Vibe CLI diagnostics and bounded conversation context (Codex)
- Findings: Current Vibe default adapter returned KURT_VIBE_DEFAULT_OK; full Kurt chat --cli vibe from home returned KURT_VIBE_CHAT_OK and exited normally. The reported earlier error text is still unknown; no claim that every possible original error was reproduced.
- Reproduced/fixed: Long conversations exceeded the old 30 KB CLI limit before Vibe could run. CLI requests now drop complete oldest turns to fit while preserving system instructions and the latest request. CLI persona prompts no longer embed the same history twice. Oversized policy/latest request still fail explicitly rather than truncating instructions.
- Diagnostics: Failures retain exit code, actionable stderr tail and partial stdout, without replaying the task or switching providers. Added /cli probe vibe for a version-only non-billable check. Removed local json import shadowing that could obscure media/probe receipts.
- Validation: 381 tests passed; actual default Vibe answered KURT_VIBE_TRIM_OK after oversized old history was reduced to a 610-byte request. Version probe reported Vibe 3.1.2. Existing saved defaults were not changed. Details: docs/EXECUTION_DEFAULTS.md and docs/vibe-default-verification.json.

## 2026-11-16 — Pasted local image paths become real chat attachments (Codex)
- Fix: Filesystem paths no longer enter slash-command dispatch or trap Enter in the picker. Supports quoted Photos Library paths, spaces, Finder escaping/file:// URLs and questions with image paths; shows an attachment indicator.
- Execution: Sends bounded JPEG/PNG/GIF/WebP bytes to the selected vision-capable Chat AI with correct provider formats (OpenAI-compatible, Anthropic, Ollama). Only question/filename markers enter stored history; image payloads stay transient. Protected paths, invalid data, oversized files and Photo Library permissions have explicit handling. A selected external CLI is not silently replaced; its current attachment limitation is explained.
- Validation: 375 tests passed; final attachment/native/security focused checks passed. Actual installed CLI plus local HTTP fixture received exact synthetic image bytes from a Photos Library-style path and returned a response. No private photo upload, paid API call or live model image-understanding claim. Details: docs/IMAGE_ATTACHMENTS.md and docs/image-attachment-verification.json.

## 2026-11-16 — Media defaults: named pickers, exact dispatch and no generic bypass (Codex)
- Ano: Added bundled Nano Banana/Nano Banana 2.1 and Kling 3.0 Standard/Pro choices; fixed case-insensitive picker search. Known image/video models cannot be saved under the wrong role. Generic call_model can no longer bypass saved fal/Replicate media selections; native/coding agents use generate_media.
- Execution: Added /image and /video plus kurt generate image|video; these use the same saved targets even with a CLI selected. --dry-run reports model/provider/key configuration without paid generation. CLI context explains that external CLI permissions may not support native media tools.
- Validation: 365 tests passed. Picker -> saved settings -> banner -> real HTTP request serialization tested with Nano Banana 2.1 and Kling 3.0 Standard, plus pinned Mistral planner plumbing, no duplicate/alternate POST on failure, missing keys, wrong roles, and empty prompts. All provider HTTP generation responses were mocked; no billable job or live balance/output-quality test.
- Details: docs/EXECUTION_DEFAULTS.md and docs/media-default-routing-verification.json. Tests used temporary persona files; choose the preferred model/version through /setting.

## 2026-11-16 — Isolate microphone driver so exit cannot hang in PortAudio (Codex)
- Problema: Yesterday's abort/close fix and short terminal tests were insufficient. A sample of an actual terminal Kurt process still showed its microphone worker stuck in CoreAudio FinishStoppingStream; a timed thread join cannot safely prevent PortAudio's interpreter-exit callback from hanging.
- Fix: On macOS, only a dedicated child process imports sounddevice/PortAudio. The main process receives bounded float32 frames over a pipe, checks cancellation, and closes/reaps only its owned microphone worker with graceful stop then bounded terminate/kill escalation. Dependency checks discover packages without importing native audio libraries into the parent. Voice turn/VAD logic remains in Kurt.
- Validation: 356 tests passed, including real subprocess PCM transport, stripped credentials, cancellation, startup failure and forced shutdown of a worker ignoring SIGTERM. Live microphone returned 512 samples and parent sounddevice remained unloaded; worker was reaped. Real terminal coverage now includes bare kurt from home, idle recording cycles, nested pickers, Ctrl+D and F5. Reproducible harness: `tools/verify_chat_exit.py`.
- Note: Already-running sessions retain the older imported code and need restarting. No existing user session was terminated. Results: `docs/chat-exit-isolation-verification.json`.

## 2026-11-15 — End-of-session checkpoint: defaults, connectors, automation and Android (Codex)
- Na-save: Connector setup/API/source links and Composio/n8n/Zapier flows; Chat/CLI/Image/Video defaults and pickers/banner; hands-free voice; computer/web execution fixes; Android APK/AAB/QR tools; working Vibe CLI integration; reliable exit cleanup.
- Final validation: 351 tests passed; live APK/AAB signature checks, Vibe Keychain-authenticated response and six real terminal exit sessions passed. Individual entries and docs below preserve the exact tested scope and limitations.
- Para bukas: Improve planner resilience under persistent rate limits; optional persistent browser login; broader Android flavors/framework support and project-specific release signing. SaaS shared-provider credits/pricing remains parked; no production deployment or publishing was performed.

## 2026-11-15 — Exit reliably returns to the shell; picker and microphone shutdown fixes (Codex)
- Ano: Deleted/replaced slash text now closes the chat picker; exit shortcuts also work inside nested pickers. All chat exit paths (text, slash, EOF, Ctrl+C, exceptions) share final cleanup for voice, browser and proactive resources; goodbye does not trigger TTS.
- Root cause: Real terminal tests exposed intermittent hangs after Bye. Thread dump showed PortAudio termination racing a microphone worker stuck in graceful InputStream.stop. Capture now aborts and closes input explicitly rather than draining it.
- Validation: Six real installed-Kurt/zsh PTY sessions returned to the actual shell prompt in 1.27–1.30 seconds across plain exit, deleted slash and nested picker cases. 351 tests passed, including real keyboard regressions and cleanup/voice tests. Results: `docs/chat-exit-verification.json`.

## 2026-11-15 — Mistral Vibe CLI picker and working headless adapter (Codex)
- Ano: Added installed Vibe to `/setting` / `kurt setting cli`, `/cli default vibe`, session overrides and CLI help. Uses bounded headless ask mode without auto-approving edits; existing saved default unchanged.
- Auth: Grants only MISTRAL_API_KEY or Vibe's own Keychain/state access. Added narrow read-only exceptions for the public TLS CA bundles (including Homebrew symlink and target); generic commands and other services cannot read Vibe private state.
- Validation: Installed Vibe 3.1.2 returned KURT_VIBE_OK through Kurt's actual sandboxed adapter using existing Keychain login with TLS verification enabled. Full suite 349 tests passed before final public-CA symlink correction; focused suites rechecked afterward.

## 2026-11-15 — Scoped Android builds, QR tools and bounded coding recovery (Codex)
- Ano: Added chat/coding tools and `kurt android doctor|build|qr`. Android-only sandbox allows JVM self-process metadata, read-only SDK and local Gradle sockets; generic coding restrictions remain intact. Builds capture bounded logs, hashes, package/signature checks, and distinguish fresh outputs from verified up-to-date files. Dependency networking is explicit CLI-only.
- Validation: 345 tests passed. Actual Gradle debug APK and offline release AAB built and signature-verified in a disposable fixture using a test certificate; repeat AAB correctly reported up_to_date. Doctor and QR CLI passed. No device install/upload or system-wide JDK installation/config change.
- Coding: Provider argument rejection now gets one correction attempt before execution. Latest live debug task fixed code and ran passing checks; final review remained incomplete under persistent rate limits.
- Details: `docs/ANDROID_BUILDS.md`, `docs/android-build-verification.json`. Production release still needs the project's upload/signing setup; flavored/nested modules and Flutter generation are not implemented.

## 2026-11-15 — Coding, QR and Android build readiness audit (Codex)
- Ano: Live AI corrected a disposable project bug; independent test and Git diff passed. Actual restricted command runner generated a demo QR PNG and preserved a failing command's exit code. Coding/security suites: 36 tests passed.
- Limitasyon: AI run remained incomplete after provider invalid timeout arguments. SDK/JDK 17 exist, but Java crashes in Kurt's generic sandbox; no actual APK/AAB build was performed and no dedicated Android workflow exists.
- Susunod: Android setup doctor and scoped build adapter, verified artifacts, explicit signing configuration, real APK download URL/QR flow, and bounded invalid-argument recovery. Details: `docs/CODING_ANDROID_AUDIT.md`.

## 2026-11-15 — Computer/web capability audit and execution fixes (Codex)
- Ano: Live-verified host app opening, Safari desktop input, headless Chrome form automation and external HTTPS fetch. Fixed browser thread ownership, installed-browser fallback, bounded page fetching, focus verification, legacy goal bypass, duplicate native tool prompts and masked streaming quota errors.
- Validation: 332 tests passed. Natural-chat Calculator/TextEdit activation passed; contextual follow-up remains inconsistent under provider rate limits/invalid tool arguments. Direct tool success is recorded separately from AI planning.
- Susunod: Bounded planner recovery, opt-in persistent browser sessions and broader workflow fixtures. Evidence and limitations: `docs/COMPUTER_WEB_AUDIT.md`.

## 2026-11-15 — Four role-specific default pickers in `/setting` and native `kurt setting` (Codex)
- Ano: Interactive `kurt setting` at `/setting` now group Chat AI, CLI, Image AI and Video AI into separate pickers. Native `kurt setting model|cli|image|video` opens a role directly; `/config` and existing slash shortcuts remain available. Tab returns to the four categories; Esc cancels/back.
- Ano: Chat pickers filter output modalities and omit media/transcription routes, while preserving vision-input chat models. OpenRouter rows show Paid/Free/unknown pricing labels. Media providers cannot be saved as Chat AI defaults; media lists remain generation-category-specific.
- Validation: 323 tests passed, including real keyboard navigation and saved CLI selection. Inspected cached OpenRouter catalog: 451 chat-qualified of 470 entries; 19 filtered out. No paid model calls. Code graph updated. Details: [docs/EXECUTION_DEFAULTS.md](docs/EXECUTION_DEFAULTS.md).

## 2026-11-15 — Hands-free voice turn-taking fix: VAD, one mic worker, automatic prompt handoff (Codex)
- Ano: Local bundled Silero VAD replaces fixed-volume speech detection. Waits for real speech, preserves onset audio, ends after 1.5s trailing silence, and supports up to 60s utterances. Silence/cancel/overflow/limit do not submit empty or truncated commands. Wake-word requests also capture a full utterance.
- Ano: Iisang worker na ang mic owner. Pending voice turns stay blocked through AI processing and serialized TTS, with matching response acknowledgments on success/error/slash paths. Voice input automatically wakes prompt_toolkit without Enter and preserves typed drafts. F5 works from the opening banner; spoken stop controls and stale-turn invalidation are implemented.
- Ano: Voice toolbar shows listening/transcribing/thinking/speaking states. TTS reservations cover queued playback, echo settling, failures and cleanup; listener stop clears old callbacks for a fresh restart. Existing model/CLI defaults remain in use.
- Validation: 314 tests passed, including 19 new voice checks. Real installed Silero VAD plus full WAV capture tested against a local TTS speech file at full and 15% gain; no live microphone or paid AI calls. Code graph updated. Usage, settings and half-duplex limitations: [docs/HANDS_FREE_VOICE.md](docs/HANDS_FREE_VOICE.md).

## 2026-11-15 — Image/video model choices at apat na defaults sa welcome banner (Codex)
- Ano: Independent saved image/video generators, picker menus sa `/config image|video` at `/image-model` / `/video-model`, at `kurt setting image|video`. May FLUX Schnell/Dev at Wan 2.7/MiniMax H3 Max choices, fal catalog filtered by generation category, at manual fal/Replicate IDs. Hindi pinapalitan ang chat/CLI default.
- Ano: Native `generate_media` uses the saved generator and stays on its generation provider. Naayos ang default fal FLUX endpoint ID at fal video artifact parsing; may video timeout, bounded Replicate polling at standard `FAL_KEY` alias.
- Ano: Welcome banner shows Chat, CLI, Image at Video defaults with provider labels, wrapping long values independently of the active executor.
- Validation: 295 tests passed, plus 7 media/banner tests after the final layout adjustment. Verified text layout at 60/80/120 columns; mocked provider generation responses, no paid media calls. Usage and source schemas: [docs/EXECUTION_DEFAULTS.md](docs/EXECUTION_DEFAULTS.md). Code graph updated.

## 2026-11-15 — Saved default AI model/CLI at quota-only auto failover (Codex)
- Ano: May persistent `default_model`/`default_cli`, settings menus, `/model default <id> [provider]`, `/cli default|use <name>`, `kurt setting model|cli`, at session `--model`/`--cli` overrides. Current CLI choices: Codex, Claude Code, Gemini CLI, OpenClaw; `auto` uses API mode. Recent context is passed to the default CLI. F5 chat/standalone voice follow saved defaults.
- Ano: Piniling model stays on its provider; disabled ang secondary model/CLI orchestration habang pinned. Confirmed billing/quota errors lang ang nag-e-enable ng auto routing for the session, retaining tool receipts and excluding the exhausted provider. Auth/ordinary rate-limit/request/server errors do not silently change the selected model. Structured CLI quota failures enable auto on the next request; failed CLI tasks are never automatically replayed.
- Ano: Na-wire ang direct OpenAI/Mistral/DeepSeek/Google API routes. Existing CLI permission adapters remain; Codex defaults to read-only. Saved preferences are unchanged until the user selects defaults; SaaS billing remains parked.
- Bakit: Gusto ng user na sariling piniling model o CLI muna ang gamitin, na naaalala sa bagong chat, at orchestrator lang kapag naubos ang credits/quota.
- Validation: 288 tests passed, including persistence, session override, provider routing, failure classification, CLI-context and no-replay checks; details in [docs/EXECUTION_DEFAULTS.md](docs/EXECUTION_DEFAULTS.md). No paid live model calls. Code graph updated.
- Susunod: Mistral Vibe/DeepSeek/Copilot CLI adapters remain separate pending integrations; hindi sila ipinakitang ready/default choices sa pagbabagong ito.

## 2026-11-14 — Connector setup menus, website/API/source links, Composio hosted auth at platform MCP setup (Codex)
- Ano: Bawat MCP/Composio/Zapier/n8n entry ay may setup submenu; nabubuksan ang website, API/setup instructions at source repo habang nananatili sa picker. Composio/Zapier/n8n ay reachable din sa mismong MCP list. May recipe choices, malinaw na missing-metadata messages at npm/PyPI fallback pages.
- Ano: Guided MCP credential entry supports embedded variables/URL templates at exported credentials, may cancellation at actual connection test. Saved config ay hindi na automatic na “connected”; buong catalog namespace ang ginagamit para walang collision sa magkapangalan na server.
- Ano: Composio reuses existing auth configs, humihingi ng missing project key sa parehong flow, at gumagamit ng current hosted `/connected_accounts/link` endpoint. Hindi na nagpapanggap na active ang account kapag walang redirect. Zapier/n8n ay may guided MCP URL/token setup sa menu, bukod sa app integration pages.
- Bakit: Gusto ng user na sa listahan mismo manggaling ang buong setup, kasama ang totoong links kung saan kukuha ng credentials o babasahin ang GitHub instructions. Sa audit, may mga catalog entry na walang links/recipe; hindi maaaring imbentuhin ang eksaktong API-key page.
- Validation: 271 tests passed, kasama ang keyboard-driven picker interaction, mocked Composio auth at localhost MCP/OAuth protocol tests. Metadata audit: 58,869 MCP, 1,633 Composio, 10,090 Zapier, 2,635 n8n. Details at limitations: [docs/CONNECTOR_SETUP.md](docs/CONNECTOR_SETUP.md). Code graph updated.
- Susunod: Actual account sign-in per external service remains user/account-dependent; hindi live-verified ang lahat ng catalog links o connectors. 2,442 MCP entries ay walang published website/repo/package page at 3,117 ay walang recipe.

## 2026-11-13 — Unified MCP/Composio/Zapier/n8n connect flow, 4 sirang default preset na-fix (Claude Code)
- Ano: Bagong `kurt/core/mcp_oauth.py` — generic MCP Authorization flow (RFC 9728 protected-resource discovery → RFC 8414 auth-server metadata → Dynamic Client Registration (RFC 7591) → PKCE) para direktang maka-connect ang Kurt sa SARILING OAuth ng kahit sinong server sa 58K+ public MCP catalog, walang middleman platform — tulad mismo ng ginagawa ni Claude sa sarili niyang MCP connectors. Na-verify laban sa totoong production server (mcp.context7.com, Clerk-hosted).
- Ano: Bagong unified na `connect_entry()`/`/mcp authorize <preset-or-id>` (`kurt/core/mcp_commands.py`) — isang flow para sa parehong presets at catalog entries: subukan muna ang totoong OAuth sign-in (browser), kung wala → magpakita ng "🔌 Connect" panel na nagtatanong lang ng eksaktong field na kulang (hal. "Authorization"), kasama ang totoong link kung saan kukuha ng API key (catalog website/repo, o hardcoded para sa presets) — hindi na raw JSON template. Laging tine-test ang koneksyon after i-save (dating "just saves" na walang verification).
- Ano: Pinalawak ang `/connect` (Composio) papuntang BUONG 1,633 toolkits (dating ~40 curated lang) sa command palette; idinagdag ang `/zapier` (10,090 apps) at `/n8n` (2,635 integrations) bilang hiwalay na browsable na listahan — pareho galing sa totoong public sitemaps ng kani-kanilang website (bundled sa `kurt/data/*.json`). Dahil walang per-app OAuth API ang Zapier/n8n para sa third party tulad ni Kurt, ang "pagpili" doon ay nagbubukas ng totoong integration page sa browser imbes na magpanggap na may connect button.
- Ano: Inayos ang `composio_connect()` para makilala ang dalawang magkaibang error: sariling Composio API key na invalid (dati nang nahandle) laban sa **toolkit na walang Composio-managed OAuth app** (bago — kinukumpirma ng Composio docs mismo, hal. PostHog/Tavily/Perplexity/marami pang iba) — sa huling kaso, ngayon awtomatikong bubukas ang `dashboard.composio.dev` kasama ang step-by-step (register OAuth app sa provider, redirect URI, saan ilalagay ang Client ID/Secret).
- Ano: Natuklasang 4 sa 6 default MCP presets (`kurt/core/mcp_client.py`) ay sira/deprecated — hindi lang napansin sa docs kundi aktwal na pinatakbo isa-isa: **github** (archived npx package → pinalitan ng totoong GitHub remote server `api.githubcopilot.com/mcp/` via Bearer PAT), **sqlite** (npm package 404 completely removed; "official" PyPI replacement crash pala sa modern MCP SDK — `mcp-sqlite-server` ang napatunayang gumagana), **brave-search** (pinull na sa npm → `@brave/brave-search-mcp-server`, opisyal na successor), **puppeteer** (archived → `@playwright/mcp`, Microsoft's actively maintained). Lahat na-verify via totoong process spawn + tools/list, hindi lang pagbasa ng changelog.
- Bakit: Humingi ang user ng Claude-style na "pumili ng app → connect → browser login → authorize" na karanasan para sa LAHAT ng 58K+ MCP + Composio + Zapier + n8n, hindi lang yung dati nang Composio-only na flow; at hiniling na i-verify talaga (patakbuhin) ang mga konektor imbes na basta ipagpalagay na gumagana.
- Susunod: Pinabayaan muna ang `postgres` preset (archived warning pero totoong gumagana pa rin, 1 tool lang talaga "query" — hindi bug) at ang display quirk sa palette kung saan ang echo sa terminal ("You › /spotify") ay yung literal na-type na filter text, hindi yung aktwal na pinatakbong command ("/connect spotify") — cosmetic lang, tama pa rin ang pinatakbo.
- Validation: 257 tests passed (dating 251).

## 2026-11-12 — Composio connect fix at pagkatuklas ng API key corruption bug (Claude Code)
- Ano: Nirewrite ang `kurt/hub/composio.py` papuntang Composio `v3.1` API (retirado na ng Composio ang dating `v1` na ginamit nito) — bagong `auth_configs` → `connected_accounts` na daloy para sa totoong "open link, mag-login, i-authorize" na karanasan (tulad ng Claude) imbes na manual na JSON/token pasting.
- Ano: Natuklasang seryosong pre-existing bug: ang `/setup` wizard (`kurt/utils/setup.py`) ay gumagamit ng naive na `.env` parser na hindi nag-aalis ng quote characters sa existing values. Tuwing pinapatakbo ulit ang setup (hal. para ayusin ang isang key), bawat ibang key na hindi hinawakan ay nadadagdagan ng isa pang layer ng escaped quotes — kaya nasira ang LAHAT ng AI provider keys (Groq, OpenRouter, OpenAI, Anthropic, atbp.) ng user pagkatapos ng ilang beses na pag-rerun, dahilan ng "Walang gumaganang API key!" sa chat. Na-ayos ang parser (ginagamit na ang `dotenv_values()`) at na-repair ang live `.env` ng user sa pamamagitan ng pag-extract ng malinis na value mula sa gulo.
- Ano: Nalaman na may hiwalay na API surface si Composio para sa MCP connections (`x-consumer-api-key` header sa `https://connect.composio.dev/mcp`), iba sa dev REST API (`x-api-key`/`x-user-api-key`). Ikinonekta si Kurt dito bilang isa pang MCP server gamit ang existing na `kurt mcp connect` pathway, at na-verify nang live end-to-end ang Spotify connection (totoong search result mula sa Spotify catalog ng user via `COMPOSIO_MANAGE_CONNECTIONS` + `COMPOSIO_MULTI_EXECUTE_TOOL`).
- Ano: Inayos din ang `kurt setup`'s password-masked key prompt (`password=True` → `getpass`) na sanhi ng hindi gumaganang paste sa maraming terminal; idinagdag ang `/setup` slash command sa loob ng chat (dati, nagiging vague/hallucinated na AI reply ang literal na pag-type ng "kurt setup" sa loob ng chat session).
- Bakit: Humingi ang user ng Claude-style na "login at authorize" na MCP/app connection flow; nahantong ito sa paghahanap ng ugat ng isang hindi inaasahang "ayaw sumagot si Kurt" na symptom na nagmula pala sa quote-corruption bug, hindi sa Composio.
- Susunod: May 2 duplicate Active Spotify account sa Composio dashboard ng user — opsyonal niyang linisin. Pending pa rin ang mas malaking generic OAuth MCP client project (PKCE + Dynamic Client Registration) para sa arbitrary na MCP servers mula sa public registry, hiwalay sa Composio.

## 2026-11-12 — F5 hands-free voice conversation mode, boy voice persona, Tagalog STT fix (Claude Code)
- Ano: Binago ang wake-word hotkey system (`kurt/core/wake_word.py`) papuntang `pynput.GlobalHotKeys` — idinagdag ang `F5` bilang toggle para sa buong two-way na voice conversation mode (dating `Ctrl+Shift+K` lang, isang beses na command capture). Nagsasalita na ngayon si Kurt pabalik gamit ang TTS (`speak()` + bagong `strip_markdown_for_speech()`) pagkatapos ng bawat AI response kapag galing sa boses ang tanong (`kurt/main.py`) — dati, text-only ang sagot kahit sa voice mode.
- Ano: Idinagdag ang shared `_tts_speaking` threading Event bilang barge-in guard — hinihintay muna ng lahat ng listening loops (`_listen_loop`, `_conversation_loop`, hotkey handlers) na matapos magsalita si Kurt bago ulit mag-record, para hindi niya marinig ang sarili niyang boses bilang bagong command.
- Ano: Pinalitan ang default na TTS voice papuntang Filipino "batang lalaki" persona (`fil-PH-AngeloNeural`, pinataas ang pitch/rate, macOS "Junior" bilang fallback) — nasa `kurt/core/persona.py`'s bagong `VOICE_PRESETS`. Inayos ang STT language-forcing bug (`language="en"` palaging naka-hardcode → `None` para sa auto-detect) na sanhi ng kabaliwang hallucinated na Ingles sa halip na totoong Tagalog transcription; in-upgrade din ang Whisper model mula "base" papuntang "small" para mas tumpak, at na-cache na ang model instance (dating nirereload kada 2-second chunk).
- Ano: Inayos ang noisy `PaMacCore (AUHAL) err=-50` sa exit (hinahayaan na lang matapos nang natural ang in-flight recording imbes na puwersahang i-abort) at ang unawaited `keyboard` lib `OSError: Error 13` (dati, tinatawag pa rin ang `keyboard.unhook_all()` kahit pynput ang talagang ginamit). Tinawag na ang `stop_listening()` sa lahat ng exit/Ctrl+C paths ng `kurt chat` at `kurt voice`.
- Bakit: Gusto ng user ng totoong hands-free na "usapan" (maretesan) sa pagitan niya at ni Kurt sa F5 mode, hindi lang one-shot na voice commands, at reklamo niyang hindi maintindihan ni Kurt ang Tagalog at "slang" ang boses nito.
- Validation: Na-verify nang live gamit ang TTS-generated na Tagalog audio bago/pagkatapos ng fix (dating hallucinated na Ingles → tamang Tagalog transcription), at live na pag-trigger ng conversation-mode toggle/barge-in guard.

## 2026-11-12 — Pag-consolidate ng kurt ask/do/agent papuntang kurt chat, bagong KurtPersona system (Claude Code)
- Ano: Tinanggal ang `kurt ask`, `kurt do`, `kurt agent`, `kurt read/edit/run/ls/grep/find/doctor` bilang hiwalay na commands — ang lahat ng kakayahan nila (coding/file tools, computer-use, web automation, orchestration) ay na-wire na sa parehong tool router ng `kurt chat` (`kurt/capabilities/bridge.py`), delegating sa existing `agent_loop.execute_tool()` engine (walang duplicated logic). `kurt chat "<prompt>"` na ang bagong one-off shorthand (dating `kurt ask`).
- Ano: Idinagdag ang `kurt/persona/` (persona.md + memory.md + `kurt_persona.py`) — bagong `KurtPersona` class na bumubuo ng system prompt + temperature per turn base sa personality file, memory ni Daddy Tito, at detected mode (casual/coding/business). Pinalitan nito ang hardcoded system prompt sa chat loop. Idinagdag ang `kurt memory show/add/edit`. Pinalitan ang `kurt config` → `kurt setting` para hindi mag-collide sa bagong persona identity.
- Ano: Idinagdag ang 11 bagong standalone CLI commands (`kurt gh/codex/claude/gemini/subagent/plan/tasks/zip/web/browser/computer`) na manipis na wrapper lang sa parehong `handle_slash()` dispatcher ng "/" commands sa loob ng chat — para magkatugma ang `kurt --help` sa mga capability na dati ay slash-only.
- Bakit: Gusto ng user ng iisang unified na interface (`kurt chat`) para sa lahat ng gawain imbes na maraming hiwalay na commands, at gusto rin niyang discoverable sa `kurt --help` ang lahat ng puwedeng gawin.
- Validation: 245 tests passed; live verification sa tatlong required na test case (`kamusta ka kurt` → casual/"boss", `may bug sa code ko` → coding mode, `magkano kaya ang kita ng sari-sari store` → business mode may totoong numero).

## 2026-11-12 — Glowing opening screen at malinis na chat output (Claude Code)
- Ano: Bagong big block-letter "KURT" wordmark (ANSI-Shadow font via `pyfiglet`) bilang opening screen ng `kurt chat`, may rotating/pulsing rainbow glow habang idle (hanggang mag-type ka) — kapalit ng dating simpleng icon+pangalan na linya.
- Ano: Nahanap ang totoong ugat ng "white background" bug sa "/" command palette — hindi pala sapat ang empty-string style para i-cancel ang built-in `reverse` default ni `prompt_toolkit` para sa `class:bottom-toolbar`; kailangan ng explicit na `"noreverse"`. Na-verify via direct style-merge inspection (`kurt/core/command_palette.py`).
- Ano: Idinagdag ang `mac_doctor`/`system_doctor` bilang chat tool (disk/CPU/RAM/network diagnostics) — dati, kaya lang ito ng `kurt doctor` CLI, walang access ang ordinary chat.
- Ano: Tinago ang internal na error/fallback text (hal. "❌ Error: 413...", "↩ Trying fallback...") at tool-call status lines ("🔧 tool_name", "Desktop action: status") mula sa normal na chat view — naka-gate na ngayon sa `verbose` flag (default False sa `kurt chat`), para malinis ang tingnan.
- Bakit: Nais ng user na "hindi boring" at "malinis" ang itsura ng pakikipag-usap kay Kurt — hindi dapat lumalabas ang internal na mekanika/errors habang nag-rerecover naman.
- Validation: 245 tests passed; live verification sa `kurt chat` (walang error/tool-status noise sa output, totoong glow animation).

## 2026-11-11 — Vision/coordinate-click fallback para sa AX-tree failures (Claude Code)
- Ano: Idinagdag ang `analyze_screen` at `click_at_coordinates` bilang bagong tools na kayang gamitin ni Kurt mismo sa autonomous chat loop (`kurt/core/assistant_tools.py`) — dati, reachable lang ang vision analysis via manual `/computer analyze` o sa `/subagent` loop; walang access dito ang ordinary chat. `click_at_coordinates` ay totoong raw pixel mouse click (reuse ng existing `computer_use.py`), naka-gate sa `set_task_goal` at may screen-bounds check.
- Ano: Binago ang `ASSISTANT_POLICY` — kapag sunod-sunod na nabigo ang `observe_application` (accessibility-tree reading) sa parehong app/window, dapat lumipat sa `analyze_screen` muna (hal. mode=find para sa coordinates), saka sa `click_at_coordinates` bilang huling resort — hindi na dapat mag-re-declare ng bagong `set_task_goal` lang dahil nabigo ang observation.
- Ano: Inayos ang `kurt/core/vision.py` (shared `_vision_call()` helper) para automatic na mag-fallback sa Claude API (`KURT_ALLOW_CLOUD_VISION=1`) kapag walang local Ollama+llava — dati, palaging nabibigo ang vision kung walang Ollama kahit may existing cloud-fallback function (`describe_screen_claude`) na hindi pala ginagamit ng mode functions (describe/ocr/find/context/answer).
- Ano: Itinaas ang `NativeToolRouter.max_tools` mula 24 papuntang 100 (shared tool-call budget ng web search/computer use/app navigation sa chat). Pinalawak ang `set_task_goal`'s `suggestion` field para lumabas pagkatapos ng KAHIT ANONG natapos na task, hindi lang app-foreground goals.
- Bakit: Totoong na-log na pagkabigo nang hiningi ng user na patugtugin ang isang Lady Gaga album — naubos ang buong tool-call budget sa paulit-ulit na AX-tree observation failure (Music.app, mahina ang accessibility support) dahil walang Plan B si Kurt: walang vision, walang coordinate-click access sa autonomous loop, at nag-re-reset ng goal 3x imbes na lumipat ng approach.
- Susunod: Hindi pa na-verify sa totoong `kurt chat` session laban sa parehong Lady Gaga/music-app scenario — manual verification lang gamit ang mocks (10 bagong tests, `tests/test_vision_fallback_actions.py`).

## 2026-11-11 — Interactive `/` command palette sa chat (Claude Code)
- Ano: Bagong `/` command palette gamit ang `prompt_toolkit` (`kurt/core/command_palette.py`) — ↑↓←→ navigation, nested dropdowns para sa `/skills` (buong native catalog), `/mcp` (connected servers + 6 presets + buong 58,857-entry public catalog), `/agents`/`/plugins` (buong 10,000 bawat isa), `/model` (routing-table defaults + buong 400+ OpenRouter + 1,400+ fal.ai kung naka-configure ang `FAL_API_KEY`), at `/config` (theme/name/icon/language/aimode/projects/setup/reset). `?` para sa flat show-all, Esc para bumalik ng isang antas (o cancel sa root), Tab para diretso sa home.
- Ano: Bagong `/mcp connect-preset <name>` at `/zip export|import <folder>` slash commands (`kurt/core/cli_orchestrator.py`, bagong `kurt/core/archive.py` na may zip-slip path-traversal protection). Fix sa isang tunay na ambiguity bug: pareho ang "shape" ng fal.ai at OpenRouter model IDs (`vendor/name`), kaya idinagdag ang explicit na `/model <id> fal` tag (`id|provider` encoding sa `kurt/main.py`) imbes na manghula base sa pangalan.
- Ano: Falls back sa plain `console.input()` kapag hindi tunay/interactive na terminal (piped input, CliRunner tests, CI) — kinakailangan ito dahil hindi makaka-basa si `prompt_toolkit` sa simulated stdin.
- Bakit: Gusto ng user ng Claude-Code-style na command palette (keyboard navigation + nested menus, walang white background) imbes na puro typing ng buong slash commands.
- Validation: 245 total tests passed (dating 221 bago ang session na ito), kasama ang mga bagong test para sa palette data providers, model-provider tagging, zip export/import, at MCP preset-connect.

## 2026-11-10 — Semantic chat goals at observed workflow execution (Codex)
- Ano: Ordinary chat always reaches a tool-capable conversational planner; removed keyword intent execution, regex web triggers and prompt-word-dependent tool gating. AI discovers apps and declares the full goal before acting through required-field tools.
- Ano: Runtime app-only completion stops at an exact foreground receipt and returns a receipt-based status; optional proposals are not executed. Workflow goals can continue through observation/action. RAM context supports follow-ups with disk memory off, and Cocoa helpers avoid stale activation in worker threads.
- Validation: 4/4 live implicit-goal/context/read-only chat cases, plus a multi-step Safari `INPUT_OK` workflow. 216 tests and 318 subtests passed. Reports, historical failures and limitations are in `docs/SEMANTIC_ASSISTANT.md`.

## 2026-11-10 — Live natural-language web knowledge sa chat at ask (Antigravity)
- Ano: Inayos ang `search_web()` sa `kurt/core/web_browse.py` gamit ang DuckDuckGo HTML POST + Google News RSS para sa real-time 2024–2026+ facts at dated news nang walang kailangang slash command o bayad na API key.
- Ano: Idinagdag ang `search_web` at `read_webpage` bilang native function tools sa `CHAT_TOOLS` (`kurt/capabilities/bridge.py`), nilagyan ng current local date ang system prompt, at inayos ang `intent.py` / `main.py` para kusang mag-search at sumagot si Kurt sa Tagalog/Taglish/English natural language.
- Bakit: June 2024 ang pre-training cutoff ng `openai/gpt-oss-120b` at sira ang dating `ddgs` / GET scraper kaya hindi updated ang sagot ni Kurt sa mga pangyayari pagkatapos ng June 2024.

## 2026-11-10 — Native app opening at mas natural na phrasing (Codex)
- Ano: Kinilala ang “mag open,” “paki bukas,” “app na Calculator,” suffix na “sa iMac ko,” at “Calculator app.” Simple installed-app launches use LaunchServices and exact foreground-process verification, without screen/Accessibility inspection.
- Ano: Kinabit ang direct local executor sa standalone voice at `do`, bukod sa chat/ask. Kasama ang activation notification processing para sa tuloy-tuloy na chat; compound tasks remain in the AI flow.
- Validation: 6/6 actual requests passed in one installed Kurt chat with an invalid AI model, independently verifying Calculator/TextEdit/Notes foreground after each switch. 203 tests and 314 subtests passed. Evidence: `docs/app-opening-native-verification.json`.

## 2026-11-10 — Observed mouse/keyboard execution at provider continuity (Codex)
- Ano: Dinugtong ang exact-window keyboard chords, mouse hover/movement sa observed elements, at bounded scrolling sa normal chat tools. Keyboard delivery para sa text filling ay sinubok laban sa totoong browser Enter handler.
- Ano: OpenRouter native function calls at cross-provider desktop fallback; compact execution ledger; invalid-request feedback at guard laban sa parehong rejected call. Hindi ito pagkopya ng private model internals o weights.
- Validation: Actual Chrome chat passed the combined local-page workflow; Safari at Edge direct tool sequences passed. AI-planned Safari/Edge runs exposed repeated invalid target arguments and reached bounds; retained reports distinguish these from successful direct execution. Scope nasa `docs/DESKTOP_BEHAVIOR.md`.
- Validation: Final 199 tests at 309 subtests passed; live final Safari check confirmed the duplicate invalid-request guard. Reliable end-to-end planning in Safari/Edge remains unfinished.

## 2026-11-10 — Local app, Mail, Music, at download requests (Codex)
- Ano: Direct natural-language routes para sa installed apps, Apple Mail unread counts, Music play/pause, at explicit HTTP(S) downloads na may size/time bounds at no-overwrite behavior.
- Bakit: Ang Notes opening ay napupunta sa memory intent, ang play request ay app-opening lang, at walang totoong email/download executor. Native Mail/Music adapter ay fixed selectors, walang arbitrary scripts at walang pagbabago sa OS permissions.
- Validation: 7/7 live cases sa actual installed chat, kabilang ang verified Music `playing` at exact downloaded bytes. Scope at evidence nasa `docs/LOCAL_NATURAL_LANGUAGE.md`; ibang mail/music services at compound workflows ay hindi pa saklaw ng live proof.

## 2026-11-10 — Natural-language browser opening sa actual chat (Codex)
- Ano: Dinagdag ang direct, complete-match browser opening sa chat/ask, macOS default-browser lookup, canonical browser names, at `open_app` na hindi nangangailangan ng URL o AI credits.
- Ano: Exact-window focus verification, read-only startup checks, at URL/address matching para hindi profile picker ang piliing Chrome window. Compound tasks ay nagpapatuloy sa AI loop.
- Bakit: Maling app names at task classification ang resulta ng karaniwang Tagalog/English requests; hindi sapat ang dating `ask` smoke tests para patunayan ang actual chat path.
- Validation: 8/8 live requests sa installed `kurt chat`; 184 tests at 282 subtests passed. Nasa `docs/BROWSER_NATURAL_LANGUAGE.md` ang evidence at restart note.
