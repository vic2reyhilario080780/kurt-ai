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
