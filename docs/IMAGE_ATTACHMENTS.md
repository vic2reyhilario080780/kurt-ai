# Local image attachments

Paste or drag a local image into Kurt chat, optionally with a question:

```text
'/Users/you/Pictures/Photos Library.photoslibrary/resources/derivatives/C/photo.jpeg'
Ano ang nasa larawan? '/Users/you/Pictures/photo with spaces.png'
/Users/you/Pictures/photo\ with\ spaces.png
file:///Users/you/Pictures/photo%20with%20spaces.png
```

An absolute file path is input data rather than a slash command. The picker
closes when slash input becomes a filesystem path, so Enter submits the path.
Normal `/help`, `/setting`, `/image` and other explicit commands retain their
own argument handling. Quoted paths, Finder shell escaping, apostrophes,
unquoted leading paths with spaces, and multiple quoted image paths are supported.

Kurt shows `Attached image: filename` and sends the actual image bytes with the
question to the selected chat provider. It does not send only a filename or
pretend that reading a path is visual analysis. The selected Chat AI must support
vision. An upstream failure produces an explicit image-analysis failure message;
pinned model selection is preserved under the existing quota policy.

OpenAI-compatible providers receive inline `image_url` content. Anthropic receives
base64 `image` blocks with the MIME type detected from the file bytes. Ollama
receives the image in `message.images`. Cloud screenshot opt-in remains unchanged;
these attachments are files the user explicitly selected and submitted.

The current external CLI adapter forwards text rather than image payloads. When
it is selected, Kurt recognizes the attachment but explains the limitation;
`/cli use auto` returns to the selected API chat model without changing the saved
CLI default. It does not silently switch execution backends for an attachment.

## Files and history

- JPEG, PNG, GIF and WebP data are supported. HEIC/TIFF/BMP paths are recognized,
  but should be exported as JPEG/PNG before sending.
- Up to four images, 5 MiB per image and 15 MiB combined, are accepted.
- Files must be regular files. Credential/private paths and symlinks into those
  paths are rejected; reads are bounded and non-image data is refused.
- Photo Library access may be blocked by macOS. Export the image from Photos
  into Pictures/Desktop and attach that copy if permission is denied.
- Only the text/question and filename marker are persisted in chat history.
  The latest attachment group stays in RAM across follow-up turns in the running
  chat, until replaced or cleared. Reattach after restarting the session.
- The image-generation default is independent of the Chat AI used for analysis.
  Reference photo animation is supported for the curated Kling image-to-video
  defaults; other reference-image editing remains unsupported. See
  [media verification](MEDIA_ARTIFACT_VERIFICATION.md).

## Verification — 2026-11-16

The full suite passed 375 tests. Focused checks cover the user's exact Photos
Library path shape, quotes/spaces/escaping, real prompt-toolkit keyboard input,
MIME detection, provider request bodies, pinned native tools, size/private-file
rejection and absence of image payloads in stored history.

`tools/verify_image_attachment.py --output /tmp/kurt-image-attachment.json` runs
the actual installed CLI with a synthetic PNG in a Photos Library-style path
against a local Ollama-protocol HTTP fixture. The attachment indicator appeared,
no unknown-command error occurred, exact PNG bytes arrived, the response was
shown and the process exited. This verifies transport, not model inference or
photo interpretation. No private image or paid AI endpoint was used.

Provider references: [Mistral vision](https://docs.mistral.ai/inference/conversations/vision),
[Anthropic vision](https://platform.claude.com/docs/en/build-with-claude/vision),
[Ollama vision](https://github.com/ollama/ollama/blob/main/docs/capabilities/vision.mdx).
