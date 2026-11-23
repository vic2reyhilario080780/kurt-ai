# Automatic conversational model routing

Kapag **model=auto at CLI=auto**, pumipili na si Kurt ng conversational model
bago sagutin ang bawat task. Parehong path ang typed chat, F5 chat voice at
standalone voice. Para gamitin sa chat:

```text
/model auto
/cli use auto
```

## Image at video Auto routing

```text
/image-model auto
/video-model auto
```

Sa `generate_media` tool at `/image`/`/video` commands, pumipili na rin ang
Auto ng compatible generator ayon sa prompt. Hiwalay ang image at video pools;
existing fal presets at cached supported fal/WaveSpeed/Hugging Face contracts
lang ang ginagamit. Nananatiling compatible fallback ang existing Auto target.
Hindi binabago ang specific saved generator. May hanggang 32 cached candidates
at isang bounded semantic selector request bago ang actual generation; kapag
walang selector o invalid ang decision, malinaw sa receipt ang compatible fallback.

Kung reference photo ang gagamitin sa video, supported Kling image-to-video
contracts lang ang eligible. Hindi ipinapadala ang image bytes sa selector;
ipinapasa ang reference sa actual generator. Hindi ipinagpapalagay na kaya ng
text-only endpoint ang image editing o lip sync. Unsupported contracts ay blocked.

Isang generation submission lang ang ginagawa. Walang automatic retry o model
switch pagkatapos ng uncertain/failed paid generation. Kailangan pa rin ng
verified artifact file bago tawaging completed ang task. Kasama sa receipt ang
actual model/provider at routing mode. Ang dry run at welcome banner ay
nililinaw na fallback lang ang nakalistang target kapag Auto.

Validation: six focused media Auto tests plus existing media integration tests,
including reference forwarding and no replay after a charged-request timeout.
Mocked ang generation; walang paid image/video render na ginawa para sa tests.

Kapag naka-pin ang specific model o CLI, hindi tumatakbo ang selector at hindi
binabago ang selection. Nananatili ang dating session-only quota failover policy.
Hindi binabago ng Auto decision ang saved default.

## Paano pumipili

`kurt/core/auto_routing.py` ang semantic selector. Ibinibigay nito sa isang
configured lightweight planner ang latest request at hanggang anim na recent
user/assistant messages. Walang keyword/regex task classifier, desktop action,
media generation o tool execution sa selection request. Hindi isinasama rito
ang system persona/memory o image bytes. Hindi pinuputol ang original problem.
Ang selected answer model ay tumatanggap pa rin ng buong assembled instructions,
history at attachments sa normal native-tool planner.

Ang candidate pool ay mula sa existing chat presets ng configured Groq, Mistral,
Google at DeepSeek, at cached OpenRouter catalog na may explicit tool support at
text output. May hanggang 12 reasoning-capable at 8 general OpenRouter entries;
160 characters ang maximum description. Hindi ito pagbabawas sa picker catalog
o benchmark ranking ng lahat ng models. Ang ibang providers/custom endpoints
ay nananatili sa existing explicit selection/delegation paths.

Structured JSON lang ang desisyon: allow-listed candidate ID, task category at
complexity. Hindi puwedeng magtakda ang classifier ng arbitrary endpoint/model,
baguhin ang instructions, o mag-trigger ng image/video/coding action. Ang media
tasks ay patuloy na dumadaan sa generation tools at saved image/video defaults.

Iniisip ng classifier ang reasoning depth, coding, research, writing, images,
at catalog capability/cost metadata. May 15-second selection timeout at 24 KB
context budget. Isang dagdag na provider request ito sa Auto kung may higit sa
isang compatible candidate; maaari itong gumamit ng credits at dagdag na oras.
Kapag isa lang ang candidate, iyon ang gagamitin nang walang classifier call.

May independent image compatibility filter. Kung walang eligible vision model,
humihinto ito nang may malinaw na mensahe sa halip na ipadala ang image sa
known-incompatible planner. Sa malformed JSON, timeout, HTTP error o unavailable
catalog, malinaw na ipinapakita ang fallback planner/status. Hindi ginagarantiya
ng API-key presence o cached catalog ang credits, entitlement o model uptime.

Sa terminal lalabas, halimbawa:

```text
Auto: reasoning/complex → deepseek/deepseek-v4-pro
```

Visible rin ang actual error fallback, at ang model na talagang sumagot ang
naise-save sa assistant message record.

## Validation at practical limits

Na-reproduce sa unang live implementation ang HTTP 413 dahil masyadong malaki
ang catalog payload, at HTTP 429 sa bootstrap planner. Pinaikli ang catalog at
gumamit ng configured lightweight selector (Mistral kapag available).

Sa final live smoke test, apat na public/synthetic requests ang nagkaroon ng
valid semantic selection:

| Task | Selected model |
|---|---|
| Simple Tagalog greeting | Google / gemini-3.5-flash-lite |
| Original calculus challenge | DeepSeek / deepseek-v4-pro |
| Async cache race-condition debugging | DeepSeek / deepseek-v4-pro |
| Tagalog follow-up sa unfinished proof | DeepSeek / deepseek-v4-pro |

[Sanitized evidence](auto-routing-verification.json) contains hashes, decision
labels and response-shape diagnostics; walang credentials o private history.
Selector-only ito: hindi pinaandar ang selected tasks at hindi ito accuracy
benchmark ng selected models. Maaaring mag-iba ang choice sa susunod na run.
Hindi ginagarantiya ng routing ang tamang proof o technical answer.

Regression coverage: semantic decision → actual selected-model invocation and
saved record, pinned model/CLI bypass, invalid decisions/network errors, missing
credentials, non-tool/media exclusion, image compatibility, context follow-up,
oversized prompts, bounded large catalog, and visible/accurate fallback records.

```sh
python3 -m unittest tests.test_auto_routing -q
# Explicit live selector-only check, using API credits:
PYTHONPATH=. python3 tools/verify_auto_routing.py --live
```
