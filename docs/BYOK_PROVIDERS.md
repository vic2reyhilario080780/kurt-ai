# Provider keys inside the model picker

Restart Kurt, open `/models`, and choose a provider. New optional catalogs are
Hugging Face, Together AI, Fireworks AI, Replicate, WaveSpeedAI and Novita AI.
The existing OpenRouter/fal.ai catalogs remain complete.

When selecting a model from a chat/image/video picker, Kurt opens a connection
menu before applying it:

1. **Enter / replace API key** opens masked input inside the picker. Paste the
   API key and press Enter. Esc cancels.
2. **Open official API key / login page** opens the provider website and keeps
   Kurt's menu available. Sign in on that website, create/copy the key, and return
   to Kurt. Kurt does not collect the account password or automate website login.
3. **Load / refresh this provider catalog** checks catalog access without
   generating content. A saved key alone is not labeled authenticated.
4. **Use my saved provider key (BYOK) and select model** explicitly applies the
   selected model. For existing wallet-supported providers, an active wallet
   also offers **Use Kurt wallet instead**.

Saving a key alone does not change the selected model or billing mode. Confirming
BYOK opts that provider into direct requests using its own balance. New optional
providers require BYOK. Replicate keeps its previous routing until BYOK is
explicitly selected. These choices are separate from subscription/store billing.

Keys are saved atomically to the existing private `~/.kurt/.env` (owner-only
permissions). Other entries are preserved. Secret input is not a model query or
submitted chat command; it is cleared from undo/redo on leaving the input view.
Voice events remain queued while a key is entered so they cannot capture it as
a draft. Keys are sent only to fixed official provider endpoints. Browser key
pages do not receive the saved key in their URL.

## Catalog scope and counts

| Provider | Scope |
| --- | --- |
| Hugging Face | Hosted chat API catalog, not the millions of downloadable Hub repositories |
| Together | Catalog returned by the authenticated models API |
| Fireworks | Paginated public Fireworks account catalog; some entries require deployment |
| Replicate | Public paginated API catalog; **Load next catalog pages** continues browsing |
| WaveSpeed | Authenticated media catalog, including input schemas |
| Novita | LLM API catalog, not every image/video API on the marketing site |

Counts show source records loaded, exact duplicates excluded, and visible models.
Incomplete pagination is explicitly marked; loaded counts are not presented as
complete provider totals. Catalogs that need a key show connection instructions
instead of invented model counts. Failed refreshes retain previous saved data.

Deduplication uses exact provider IDs and declared Hugging Face IDs/URLs from
model metadata. It does not use fuzzy display-name matching or strip version,
quantization, turbo or other suffixes. Unconfirmed aliases remain visible.

## Execution support

OpenAI-compatible chat routing is implemented for Hugging Face, Together,
Fireworks and Novita. Only declared chat/text-output models expose chat defaults;
Fireworks also requires the catalog's serverless-support metadata.

WaveSpeed prompt-only text-to-image/video models can expose media defaults when
their published input schema requires no additional inputs. Submission happens
once, followed by bounded polling of the fixed official result endpoint. Media
must still pass Kurt's existing artifact verification; an unknown CDN, missing
file, pending job or failure is not reported as completed generation.

More complex image editing, speech, 3D, training and unknown contracts remain
browsable with setup links and key entry. They do not gain a working default
merely because a key was entered. Replicate's existing exact-model media adapter
remains available; public catalog metadata alone does not prove every input
contract.

## Validation

Tests use synthetic keys and mocked provider replies for credential handling,
chat routing, wallet separation and WaveSpeed submission/polling. Live checks
read public Hugging Face/Novita catalogs and the saved Replicate account's catalog;
no inference or paid generation was requested. Together/Fireworks/WaveSpeed
authenticated calls remain pending the user's keys. See
[verification report](byok-provider-verification.json).

Official references: [HF API](https://huggingface.co/docs/inference-providers/hub-api),
[Together models](https://docs.together.ai/docs/serverless/models),
[Fireworks API](https://docs.fireworks.ai/api-reference/list-models),
[Replicate API](https://replicate.com/docs/reference/http),
[WaveSpeed models](https://wavespeed.ai/docs/list-models),
[WaveSpeed results](https://wavespeed.ai/docs/get-result),
[Novita models](https://docs.novita.ai/api-reference/model-apis-llm-list-models).
