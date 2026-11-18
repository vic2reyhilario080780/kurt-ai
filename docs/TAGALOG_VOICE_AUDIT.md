# Tagalog/Taglish voice audit — November 18, 2026

Scope: repository inspection, installed-library checks, existing regression
tests and primary-source research. No microphone recording, model/dataset
download, paid transcription, voice-default change or offline expansion.

## Observed implementation

- The live listener calls `wake_word.transcribe_audio_fast` and local
  `faster-whisper` small/CPU/int8, with OpenAI Whisper base as fallback. Language
  is auto-detected per utterance. No initial prompt, hotword list or custom
  vocabulary is passed. Loading an uncached local model can download weights.
- Both successful local paths return a fixed `0.9` confidence rather than
  measured recognition reliability. Voice events are submitted as text without
  a quality-based clarification step. Do not interpret that field as 90% accuracy.
- `ModelRouter.call_groq_transcription` exists separately and uses
  `whisper-large-v3`, but the live listener does not call it. That route currently
  sends the model and audio only, without language or vocabulary context.
- End-of-utterance VAD uses trailing silence (default 1.5 seconds), which is
  adjustable via `KURT_VOICE_SILENCE_SECONDS`. Speech pauses and transcription
  errors are separate problems. TTS/turn ownership blocks capture while the
  assistant speaks; this is turn-taking, not full simultaneous conversation.
- The young-boy TTS preset selects `fil-PH-AngeloNeural`; fallback voices may
  not be Filipino. Windows online MP3 playback currently needs `ffplay`.
- On this iMac all inspected recording/transcription/VAD/TTS libraries are
  present. This does not verify microphone permissions, model-cache availability,
  actual accent accuracy or audible playback.
- The new lightweight `voice` extra omits local Whisper/ONNX packages, but
  listener startup still requires local transcription and bundled VAD. Therefore
  a fresh Windows `--features voice` install alone is not a complete voice setup.

## Dictionary and speech resources

- [Kaikki Tagalog dictionary](https://kaikki.org/dictionary/Tagalog/index.html):
  machine-readable Wiktionary-derived lexical data. Its current postprocessed
  JSONL download is about 146.3 MB and is marked deprecated in favor of raw
  extraction data. Useful as a lexical reference/selected word source, not a
  drop-in audio recognizer. Review attribution/licensing before redistribution.
- [Groq speech transcription](https://console.groq.com/docs/speech-to-text):
  multilingual Whisper large-v3/turbo, language hints and a context/spelling
  prompt of at most 224 tokens. Prompting guides style/vocabulary, not tool
  execution. Provider credits and uploaded audio are involved.
- [faster-whisper implementation](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py):
  supports `initial_prompt` and `hotwords`; verify the installed version's
  parameters rather than assuming every release supports them.
- [Google FLEURS](https://huggingface.co/datasets/google/fleurs) includes Filipino
  speech; [FilSwitch](https://huggingface.co/datasets/qwerttyuiiop/FilSwitch) is a
  Filipino-English code-switching ASR dataset. These are evaluation/training
  resources, not dictionary plug-ins. Verify dataset licensing and evaluate
  conversational speech separately from read-speech benchmarks.

## Recommended bounded follow-up

1. Separate the existing local-only listener from an explicit online speech
   backend using the saved Groq key/wallet route. Do not silently upload audio,
   retry paid requests, switch backends or download weights.
2. Add selectable Tagalog (`tl`) / automatic Taglish transcription, plus a short
   editable vocabulary prompt: Kurt, Bhe, Daddy Tito, Vibe, DeepSeek, Copilot,
   project/app names and the user's own terms. Use selected relevant terms,
   not the entire dictionary and not global spelling replacement of commands.
3. Keep real provider/decoder quality metadata distinct from calibrated
   confidence. Ask for clarification when recognition is uncertain; preserve
   the original transcript and avoid guessing actions from ambiguous audio.
4. Make voice installation/readiness truthful on Windows: speech detection,
   online recognition, Filipino playback and permission checks must all pass.
5. Measure actual Tagalog/Taglish utterances, names and pause patterns against
   expected transcripts. Compare the current local recognizer to the proposed
   online configuration before claiming an accuracy improvement.

Validation: all 19 existing `test_voice_turns.py` tests passed with fixtures.
They cover turn-taking/capture behavior and do not establish ASR accuracy.
