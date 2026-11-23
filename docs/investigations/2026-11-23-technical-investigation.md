# Pagsisiyasat sa maling calculus answer ni Kurt — 2026-11-23

**Resulta:** May reproducible instruction-delivery bug, ngunit hindi iyon ang
buong paliwanag. Naayos ang conditional loading at standalone voice omission.
Kahit umabot ang rigor instructions sa Mistral, pumalya pa rin ang model sa
calculus case. Hindi nakapagbigay ng maaasahang correction ang self-verification.
Walang pinalitang default model/provider at walang calculus answer sa runtime.

## Ano ang nakumpirma tungkol sa session

Ang lokal na conversation record na tumutugma sa ibinigay na problem at answer
ay may isang user turn at isang assistant turn lamang, 2026-11-23 06:34:37 at
06:34:59 sa database clock. Ang recorded assistant model ay
`mistral-small-latest`. Walang naunang saved history sa session na iyon.
Metadata at ang mismong matematikang ibinigay na rin ng user lang ang ginamit;
walang private history/profile na ipinadala sa labas.

Ang **kasalukuyang** saved selections ay `mistral-small-latest|mistral` at
CLI `auto`; inactive ang wallet, at walang custom endpoint para sa model.
Tugma ito sa record, pero hindi immutable snapshot ng settings noong failure.
Walang archived outgoing HTTP request, mode, temperature, fallback receipt,
entrypoint field, resolved model version, o hash ng instructions noong failure.
Kaya hindi maipapahayag na historical packet capture ang reconstruction.

Pinakamalakas na inference: ordinary chat path ang ginamit. Itinatala nito ang
model sa assistant record; ang standalone voice path noon ay hindi nagtatala
ng model. Ang F5 voice sa chat ay gumagamit din ng ordinary chat path.
Hindi sapat ang record para lubusang patunayan kung typed o F5 ang input.

## Na-trace na request path

1. `kurt/main.py:594` — `chat()`; `ExecutionSession.load()` sa
   `kurt/core/execution_preferences.py:230` ang nagbabasa ng selections.
   Ang pinned model ay nagiging Mistral provider + `mistral-small-latest`.
2. `kurt/main.py:876` — `KurtPersona.build(prompt, mode="auto", ...)`.
   Sa eksaktong prompt, tumama ang `function` sa **special functions** sa
   `coding` category bago maabot ang technical category. Resulta: mode
   `coding`, temperature **0.3**. Bago ang fix, `system_instructions.md` ay
   binabasa lamang kapag mode=`technical`, kaya **hindi naipadala** ang rigor.
3. Ang assembled messages ay persona/memory/context system message,
   operational CLI system message, language system message, optional skill
   system message, hanggang 20 history messages, at latest user message.
   Ang aktibong skill noong historical failure ay hindi naka-record.
4. `stream_response()` (`kurt/main.py:303`) → `NativeToolRouter.route()`
   (`kurt/capabilities/bridge.py:865`). Nagdadagdag ito ng native-tool policy
   bilang system message, schemas, media settings at discovery summary.
5. `ModelRouter.route()` → Mistral branch (`kurt/core/router.py:596`) →
   `_call_tool_chat()` (`:156`) →
   `https://api.mistral.ai/v1/chat/completions`.
   Sa verified capture, eksakto ang wire model: `mistral-small-latest`;
   walang model-name rewrite. Nananatiling system messages ang instructions.
   Ang redaction at `function_history()` ay hindi nag-omit ng synthetic policy.

Effective generation settings sa reproduction: `temperature=0.3`,
`stream=true`, `tool_choice=auto`, `parallel_tool_calls=false`.
Hindi naka-set ang `max_tokens`, `top_p`, `random_seed`, o `reasoning_effort`;
provider defaults ang ginagamit. Hindi naitala ang finish reasons ng experiments,
kaya hindi maaalis ang provider-side output truncation para sa incomplete run.
Gayunman, mayroon nang maling leading coefficient bago ang truncation sa run na iyon.

Pinned selection ang normal chat: walang fallback dahil lang mali ang sagot.
Sa ordinary error, pinananatili ang selection; confirmed quota exhaustion lang
ang nagpapahintulot ng auto routing sa session (`main.py:334–356`). May hiwalay
na error fallback ang unpinned mode. Walang fallback sa lahat ng live comparisons
na ginawa dito. Hindi direktang naoobserbahan ang historical fallback behavior.

## History, context, adapters at voice

- Hindi history compaction ang nakita sa reproduction: walang prior saved
  turns, at mali rin ang clean neutral sessions. Hindi nito naaalis ang posibleng
  epekto ng historical persona/memory/system skill, na hindi externally replayed.
- `KurtPersona` ay maaaring maglagay ng limang recent turn pairs sa system
  context kapag `include_history=True`; normal chat ay nagpapadala rin ng
  history roles. Hindi ito kailangan sa two-row case. Hindi ito binago rito.
- Native desktop compaction (`bridge.py:934`) ay nag-aalis ng lumang desktop
  tool/result pairs pagkatapos ng desktop use; hindi nito pinuputol ang
  ordinary math system instructions. Hindi ito na-trigger sa captured math run.
- Agent compaction (`agent_loop.py:1170`) ay nagpapanatili ng first two messages
  at last 16. Sariling system prompt ang agent path; hindi iyon ang natukoy na
  path ng failing exchange. Agent/scheduled workflows ay hindi ginawang global
  persona consumers sa fix na ito.
- External CLI context (`execution_preferences.py:254`) ay nag-aalis ng buong
  lumang turns sa 30 KB budget, pinananatili ang systems at latest user o
  nag-e-error kung hindi kasya. Hindi ginamit ang CLI sa selected API reproduction.
- Anthropic adapter (`router.py:402`) ay pinagsasama ang system messages sa
  top-level `system`; Mistral ay gumagamit ng `messages`. Walang live Anthropic
  comparison dahil ibang provider/model iyon.
- **Standalone voice bug:** noon ay sarili nitong short system prompt lang,
  walang `KurtPersona`, walang custom file, at walang explicit temperature.
  May hard cap pa itong “1–2 sentences max” na salungat sa requested full proof.
  Ngayon ay ginagamit nito ang parehong persona builder at mode temperature;
  concise ang preference pero pinapayagan ang requested full derivation.
  Na-verify sa mocked voice callback, walang microphone/STT upload.

## Independent mathematical scoring

Nauna ang independent oracle sa pagbasa/paghuhusga sa live outputs. Nasa
[buong derivation](2026-11-23-calculus-oracle.md) ang convergence, Tonelli,
finite decompositions, exact remainder at uniform estimate.

Tamang constants, γ ang Euler–Mascheroni constant:

    a = 2√π, b = −1/4, c = log 2 − 1 − γ/2,
    d = −2 − γ + γ log 2 − γ²/4 − 5π²/24,
    e = √π, f = 0.

    Rₙ = −1/(2n²) + O(n^(−5/2)),
    |Rₙ| ≤ 7/n²  (lahat ng real n≥2),
    lim n²Rₙ/log n = 0,  lim n²Rₙ = −1/2.

Samakatuwid valid pero **hindi sharp** ang requested logarithmic bound.
Ang direct lower bound na Iₙ≥1/(2e√n) ay agad nagpapabulaan sa a=0.
Hindi ipinasok ang lower bound, constants o oracle sa baseline prompts o verifier.

Mga independently fatal error sa supplied answer:

- Maling sign: H(t)=γ+log t−Ei(−t), hindi +Ei(−t).
- ∫₀¹1/[z²(1+z)]dz=+∞ at ang log-z counterpart ay −∞; hindi finite constants.
  Divergent din ang hiwalay nitong Jₙ. Hindi valid ang subtraction ng mga ito.
- Ginamit ang large-argument Ei expansion hanggang sa zero; nonuniform ito.
- Divergent ang ∫₀∞e⁻ᵘ/u^(k+1)du para sa bawat k≥0; hindi 1/k!.
- Hindi tugma sa requested powers ang labels ng coefficients at final formula.
- Walang proof ng uniform remainder; hindi napapatunayan ng pangalang
  “Watson's lemma” ang hindi nasuring hypotheses.

Numerical cross-check (support, hindi kapalit ng proof): split-interval
Gauss–Legendre quadrature na may independently evaluated H. Sa n=100,
1000,10000, ang n²Rₙ ay −0.47272246, −0.49090026, −0.49707065.
Ang 128-vs-256 node differences ng Iₙ ay ≤4.5e−16 sa tested n=2…10000;
hindi ito certified floating-point error bound.

## Controlled comparisons: 20 completed API requests

Iisang explicit Mistral model at temperature 0.3; bawat condition ay dalawang
run. Neutral persona, empty history/memory, walang private discovery summary,
walang active private skill. Hindi eksaktong historical full prompt replay:
sadyang inalis ang personal profile at hindi kailangan na wrappers sa live fixture.
Ang end-to-end chat assembly naman ay hiwalay na na-capture gamit ang mock HTTP.

Kurt transport vs direct HTTP: **identical wire payload** (kasama ang parehong
60 schemas), stream at generation settings. Ang pagbabago sa instruction arm ay
dagdag na rigor section lamang. Unchanged ang temperature/tools/model.
First completion lang ang kinuhanan; walang tool na pinaandar o fabricated receipt.
Ang direct SSE responses ay nag-ulat din ng `mistral-small-latest`, na alias pa
rin at hindi patunay ng immutable historical model version.

| Experiment | Resulta |
|---|---|
| Calculus, Kurt baseline | 0/2 tama: a=√π at a=0 |
| Calculus, direct same payload | 0/2 tama: a=0 at a=√π/2; incomplete ang ikalawa |
| Calculus, Kurt + delivered rigor | 0/2 tama: a=π/2 at a=√π/2 |
| Generic verification ng unang baseline | 0/2 kumpletong tamang solution; may error detection pero bagong maling claims |
| Verification ng mismong supplied wrong answer | 0/2 tama; parehong nanatiling a=0, isa ay tinawag pang finite ang divergent integral |
| Fresh Jₙ problem, baseline + tools | 2/2 nag-request ng code; hindi pinaandar, kaya **unscored**, hindi mathematical failures |
| Fresh Jₙ problem, rigor + tools | 2/2 tamang exact expression, three terms, bound at limit |
| Fresh baseline verification | 1 incomplete tool request; 1 may terms/remainder mismatch, hindi full pass |
| Fresh Jₙ, no-tools ablation, baseline | 1/2 full pass; ikalawa tama ang exact/limit pero four-term bound ang ibinigay sa three-term request |
| Fresh Jₙ, no-tools ablation, rigor | 0/2 full pass; maling final remainder/O order kahit tama ang exact formula/limit |

Fresh control: Jₙ=∫₀¹x/(1+nx²)dx=log(1+n)/(2n), requested three terms
L/(2n)+1/(2n²)−1/(4n³), remainder ≤1/(6n⁴), scaled limit −1/4.
Ito ay bagong independent control, hindi kapalit ng complex calculus challenge.

Maliit ang sample at may stochastic variation. Walang pinapatunayang universal
accuracy rate o independent judge model. Ang malinaw na finding ay:
**request bug + reasoning failure**, at hindi maaasahang default correction
ang same-model self-verification. Hindi sapat ang evidence para magpalit ng
default sampling/model o magdagdag ng mandatory extra paid inference pass.

## Fixes at verification

- `kurt/persona/kurt_persona.py:82`: kasama lagi ang persona **at** custom
  instructions; binabasa kada build kaya puwedeng i-edit habang ginagamit.
  Mode temperature mapping ay hindi binago. Wala nang mode-dependent omission.
- `kurt/main.py:1069`: standalone voice uses the same builder and explicit
  temperature; wala nang arbitrary 1–2 sentence cap sa requested derivations.
- `pyproject.toml:76`: package ang `system_instructions.md`. Built wheel before:
  **absent**; after: **present**. Hindi isinama ang private `memory.md`.
- `tests/test_instruction_delivery.py`: auto-mode false classification,
  every-mode instruction inclusion/reload, real chat entrypoint → native
  bridge → router → mock HTTP payload, at standalone voice instructions/temp.

Before fix: unang dalawang regression tests ay failed, 7 failed assertions/subtests.
After fix: **4 focused tests passed; final full suite: 582/582 passed, 28.863s**.
Compile, diff checks at graphify update ay passed din. Ang sandbox-only failures
mula sa nested `sandbox-exec` at local MCP transport ay ni-rerun sa approved
environment. Hindi sila itinago bilang application fixes.

[Sanitized request evidence + run hashes](2026-11-23-technical-evidence.json).
Public generated outputs ay nasa `/tmp/kurt-technical-comparison.json` at
`/tmp/kurt-technical-supplement.json` sa working machine, hindi private logs.
Repro harness: `PYTHONPATH=. python3 tools/investigate_technical_delivery.py`
(mock-only by default); `--live` ay explicit paid network inference.

Hindi pa verified: historical exact HTTP/settings/instruction versions,
historical personal-context effect, original STT text accuracy kung F5,
provider-side historical alias resolution/finish reason, at generalization sa
ibang complex technical domains. Pinanatili ang ibang preexisting worktree edits;
walang commit/push o pagbabago sa credentials.
