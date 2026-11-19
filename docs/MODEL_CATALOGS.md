# Complete OpenRouter and fal.ai catalogs

In Kurt chat, type `/models` and select it in the command picker:

1. Choose OpenRouter or fal.ai; each row shows its complete catalog count.
2. Open **All models**, or choose a category. Category counts sum to the provider total.
3. Type a model name or ID to search, including models outside the usual default pickers.
4. Open a model for supported default actions and its official model/setup page.
5. Selecting a chat/image/video model opens its connection menu. Enter a key
   with masked input, open the official key/login page, then explicitly choose
   BYOK or the existing Kurt wallet where supported. The key is not a chat message.

The chat/image/video settings pickers also link to their provider's full catalog.
Browsing a model or opening its page does not select it, run inference, generate
media, or spend credits. The picker stays open when a model page is opened.

On November 19, 2026, fresh catalog requests returned **480 OpenRouter IDs** and
**1,356 fal.ai endpoints**. These are a dated snapshot, not hardcoded totals.
OpenRouter's output-modality categories included 461 text-only, 13 image/text,
four audio/text and two text/video models. All were retained in the browser.
fal.ai includes image/video transformations, audio, 3D, training and other tasks;
these categories are retained even when Kurt has no execution adapter for them.

## Defaults and support

Only compatible workflows expose a default-setting action. Current catalog
actions support OpenRouter text-only chat, fal.ai text-to-image, text-to-video,
and the existing supported Kling image-to-video contracts. Other entries are
marked **browse only**, with official setup links. A catalog entry is not proof
of account access, credit balance, required inputs or successful generation.

Each provider ID belongs to exactly one category. Multiple output modalities
form a combined category; a missing/new category is retained. Only repeated
exact IDs within the same provider are deduplicated. Model versions are never
merged by similar names. Menu-row totals include navigation and status rows;
the provider/category headers contain actual model counts.

## Refresh and connection failures

Use **Refresh provider catalogs** inside the picker, or type
`/models refresh`. Caches normally last one hour, including the in-memory picker
cache. On failure, the last complete disk cache is retained and reported as
cached data. A failed/malformed fal.ai page, inconsistent pagination or an
incomplete/duplicate page set cannot overwrite a complete cache with a partial
list. A missing catalog is shown as unavailable, not as successful inference.

Outside the interactive picker, `/models` prints provider/category totals.
`/models routing` retains the routing-rule table. Existing `kurt models list`
and `kurt models fal` terminal commands still work with their search/limit flags.

## Additional BYOK catalogs

The picker now includes Hugging Face, Together AI, Fireworks AI, Replicate,
WaveSpeedAI and Novita AI. Their additional-model views exclude exact IDs and
explicit Hugging Face identities already offered by OpenRouter/fal.ai. Similar
names, families, unconfirmed aliases and different versions are not merged.
Primary catalog counts are unchanged. See [BYOK setup](BYOK_PROVIDERS.md) for
the key flow, API scopes, pagination and verified versus pending checks.
