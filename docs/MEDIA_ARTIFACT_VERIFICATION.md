# Verified media output — 2026-11-16

The reported fal.media MP4 returned HTTP 404 (`Specified object does not exist`)
when checked. Historical chat stored the assistant's claim and URL, but no job
receipt. That cannot establish whether a provider request ever ran, or whether
an earlier artifact expired or was removed. It is not proof of a finished video.

## Changed behavior

- Native chat buffers the final reply before displaying it. Newly invented
  fal.media/Replicate/video URLs absent from observed tool/user context are
  replaced by an explicit missing-receipt message. This is a structural URL
  provenance guard, not a keyword classifier or a universal semantic claim checker.
- `generate_media` only reports `completed` after an HTTPS provider-CDN download
  succeeds, within 150 MiB. Every redirect must remain on an allowed CDN.
  HTML/JSON, empty files, invalid images, and missing video/audio streams fail.
- Images are checked with Pillow; video/audio require `ffprobe`, positive
  duration and the corresponding stream. Outputs are saved under
  `~/Downloads/Kurt`, with SHA-256 and a JSON file-verification receipt.
- Native chat formats the generation receipt directly; it does not ask the
  chat model to invent a completion story. A provider/download timeout or error
  returns `unverified`, `retry_safe: false`; it does not escape into provider
  fallback or automatically repeat a potentially charged request.
- A verified playable file does **not** verify the intended person, scene,
  exact words, audio quality or lip sync. The completion message says so.

## Reference photos

The latest attachment group remains in RAM for the running chat and is restored
into follow-up context. A new attachment replaces it; `clear` or `/clear` clears
it. Image bytes are not written into conversation memory. Restarted sessions
require reattachment. A non-vision chat model still cannot interpret a photo.

`/video-model` now includes separate Kling 3 Standard/Pro **Image-to-Video**
choices. These curated fal endpoints accept `start_image_url`. The model selects
an attached image using `generate_media.reference_image` (zero-based). If images
are present, this choice must be explicit; `-1` means text-only. A saved
text-to-video/unsupported model blocks reference generation before a paid request.
Kurt never silently replaces the saved generator. Image-to-video models also
block when no reference is supplied. Reference-image editing with image models
and other video vendors remains unsupported.

For this photo workflow: use `/cli use auto`, select a vision-capable Chat AI,
choose Kling Image-to-Video in `/video-model`, attach the exported photo, and
request the animation in chat. A playable artifact alone does not establish that
it says “I love you”; preview the output. Native audio settings/speech verification
are not implemented by this fix. No automatic paid retry is performed.

## Validation

Regression checks cover 404/HTML/truncated image responses, rejected redirects,
real PNG download/hash/receipt, a synthetic MP4 downloaded and inspected with
ffprobe, invented streamed links, attachment follow-up and clear, exact Kling
reference payload, no silent default replacement, and no repeat after failure.
The isolated full suite passed **400 tests**; the final focused run passed **35 tests**.
Provider calls use HTTP fixtures; no private photo was uploaded and no paid
render was submitted. Endpoint schema reference:
[Kling 3 Standard image-to-video](https://fal.ai/models/fal-ai/kling-video/v3/standard/image-to-video/api),
[Kling 3 Pro image-to-video](https://fal.ai/models/fal-ai/kling-video/v3/pro/image-to-video/api).
