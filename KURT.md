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

## 2026-11-10 — Natural-language browser opening sa actual chat (Codex)
- Ano: Dinagdag ang direct, complete-match browser opening sa chat/ask, macOS default-browser lookup, canonical browser names, at `open_app` na hindi nangangailangan ng URL o AI credits.
- Ano: Exact-window focus verification, read-only startup checks, at URL/address matching para hindi profile picker ang piliing Chrome window. Compound tasks ay nagpapatuloy sa AI loop.
- Bakit: Maling app names at task classification ang resulta ng karaniwang Tagalog/English requests; hindi sapat ang dating `ask` smoke tests para patunayan ang actual chat path.
- Validation: 8/8 live requests sa installed `kurt chat`; 184 tests at 282 subtests passed. Nasa `docs/BROWSER_NATURAL_LANGUAGE.md` ang evidence at restart note.
