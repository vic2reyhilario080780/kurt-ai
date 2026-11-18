# Tagalog and Taglish conversation

Kurt's live voice listener now supports Groq Whisper large-v3/turbo with the
same saved Groq API key or wallet gateway used by Kurt. Auto selects Groq when
configured, otherwise an existing cached local recognizer. Failed requests
pause hands-free mode; they are not replayed or sent to another provider.

## Start talking

The source installer now includes the lightweight voice extra by default.
Existing isolated installs can add it with:

```sh
python bootstrap.py --features web,media,voice
```

Configure the Groq key once through `/setup` or use the configured wallet.
Choose Tagalog or automatic Taglish recognition:

```text
/speech provider groq
/speech language tl
/speech pause 2
/speech word-add pangalan ng project
/speech status
```

Use `/speech language auto` for mixed-language auto-detection, or `en` for
English. The terminal equivalent is:

```sh
kurt speech configure --provider groq --language tl --pause 2
kurt speech word-add "pangalan ng project"
kurt speech status
```

In `kurt chat`, press **F5 once** to enter hands-free conversation. Kurt waits
for speech, waits for the trailing pause, transcribes, handles the request,
speaks its reply and listens again. Press F5 or say **tigil muna** to pause.
Ctrl+Shift+K records one utterance. `kurt voice --hotkey` also suppresses
background wake-word capture. Standalone voice now keeps twelve recent
user/assistant pairs in RAM for follow-up references, alongside its existing
session message storage. Chat F5 already uses the normal chat context.

"Hey Kurt" is detected **locally** only when an existing cached local model
is available. A fresh installation can use F5/hotkeys without downloading
Whisper weights. No background cloud transcription is used to search for the
wake phrase. Once a wake phrase is recognized or F5/hotkey activates capture,
Groq receives that recorded utterance and may charge the configured account.
Vocabulary hints include your selected names. This is not zero-cost/offline
recognition. Typed chat remains available without voice dependencies.

## Recognition quality and vocabulary

- Language, spelling/name hints and `verbose_json` metadata are sent to the
  multilingual speech endpoint, not to a chat model pretending to hear audio.
- An editable short vocabulary includes Kurt, Bhe, Daddy Tito, Vibe, DeepSeek
  and common task words. New custom names have priority. Prompts stay within
  208 UTF-8 bytes, below the provider's 224-token limit; they do not contain
  an entire dictionary, past chats or automatic command replacements.
- Decoder log probability, non-speech estimates, compression and repetition
  checks flag uncertain results. They are heuristics, **not calibrated accuracy
  probabilities**. Missing metadata also requires clarification. The old
  hardcoded `0.9` confidence is removed.
- Uncertain speech is not dispatched to the AI/tools. Kurt asks for repetition;
  three consecutive unclear utterances pause capture. A provider failure also
  pauses hands-free mode. F5 restarts it after the issue is fixed.
- The default listener pause is now two seconds, adjustable from 0.6–4 seconds.
  Existing `KURT_VOICE_SILENCE_SECONDS` environment settings take precedence.
  Longer pauses reduce premature endings but add reply latency.
- Cancelled/stale captures are discarded. Utterance WAV files are deleted on
  completion/error/cancellation. No background recording dataset is created.
  Application cleanup does not promise secure deletion or provider-side
  deletion; the selected provider's processing/retention policy still applies.

Test one existing **16 kHz mono PCM16 WAV** without allowing it to execute a
command:

```sh
kurt speech test sample.wav
```

In Groq mode this explicitly uploads the file and can use credits. Output
contains the transcript and quality flags, without performing app/tool actions.

## Playback and installation

WebRTC VAD handles speech boundaries using small native wheels; it does not
need Whisper model weights or a local GPU. Existing Silero installations remain
a detection fallback. Local ASR loads cached files only and never silently
downloads a model. GPU hosting/offline expansion remain parked.

The existing young-boy preset uses the Filipino `fil-PH-AngeloNeural` voice
with rate/pitch changes. macOS uses `afplay`; Windows/Linux use an isolated
soundfile/sounddevice worker with blocking playback and a time limit. No
separate `ffplay`/`mpg123` is required for this path. TLS uses a verified CA
bundle. Failed online speech can still fall back to available system voices,
whose language/accent depends on OS voice installation.

Microphone/output-device permissions and working hardware are still required.
Linux may need its distro's PortAudio package. CI tests do not verify audible
playback, actual microphone access or the user's accent.

## Evidence and limits

Twenty-one focused speech tests cover API language/hints/key routing, no paid
fallback, quality gating, stale-turn cancellation, bounded unclear-speech loops,
no background upload, standalone follow-up context, VAD framing and isolated
Windows playback. Existing turn-taking tests remain in the suite.

The explicit `tools/verify_tagalog_speech.py` benchmark generated two public
Filipino TTS sentences, made two live Groq transcription requests and executed
no app commands. Both had zero word errors after case/punctuation normalization,
including Kurt, Bhe, Vibe and DeepSeek. This small **synthetic** test does not
establish accuracy for the user's own voice, accent, pauses or room noise.
See [speech verification](speech-verification.json).

References: [Groq speech parameters and prompting](https://console.groq.com/docs/speech-to-text),
[WebRTC VAD wheels](https://github.com/daanzu/py-webrtcvad-wheels),
[soundfile MP3 support](https://python-soundfile.readthedocs.io/en/latest/).
