# Hands-free voice conversation

Run `kurt chat` and press **F5** once. Speak normally, then pause. Kurt
transcribes the utterance, processes it with the selected model/CLI,
speaks the answer, and automatically listens for the next utterance.
The voice listener starts before the opening animation: F5 or a queued
wake-word request can leave that animation without a separate Enter.

Press F5 again, or say **“stop listening”** / **“tigil muna”** while Kurt
is listening, to leave conversation mode. Wake-word mode remains available.
“Hey Kurt” and Ctrl+Shift+K support one-shot requests. Wake-word capture
now waits for a full utterance rather than dispatching a two-second slice.

## How Kurt knows when to answer

- Local **Silero VAD**, bundled with faster-whisper, detects speech rather
  than comparing microphone loudness to one fixed threshold. It does not
  identify a speaker or understand whether their thought is complete.
- Capture waits for a sustained speech onset; silence and brief clicks do
  not create a turn. A short pre-roll preserves the beginning of the word.
- After speech begins, **1.5 seconds of trailing non-speech** ends the
  utterance. Shorter pauses allow the same utterance to continue.
- A silent waiting period restarts capture without creating/transcribing
  an empty audio file. Speech can continue beyond the old 12-second cap.
- The default utterance limit is **60 seconds**. Reaching it discards the
  partial command and asks for shorter parts instead of executing a cut
  request. Capture errors, dropped input frames and cancellation also
  discard incomplete audio rather than falling back to fixed recording.

Optional environment settings, loaded when a listener is created:

```text
KURT_VOICE_SILENCE_SECONDS=1.5
KURT_VOICE_MAX_SPEECH_SECONDS=60
```

Silence may be configured from 0.6 to 4 seconds; the utterance limit from
15 to 180 seconds. Longer pauses reduce interruptions but delay replies.

## Turn coordination

One worker owns wake-word, conversation and one-shot capture. The input
toolbar shows waiting, listening, transcribing, thinking and speaking.
Voice input wakes the active prompt directly without Enter, preserves an
unfinished typed draft, and remains queued if it arrives between prompts.

The microphone stays paused from command submission until the matching
response has finished playing. Successful answers, slash commands and
error paths all release the turn. TTS calls are serialized; the playback
guard is reserved before a thread starts and stays set until all queued
speech finishes, followed by a short echo-settling delay.

This is **half-duplex turn-taking**: Kurt does not record interruptions
while thinking or speaking. Spoken stop phrases work while listening.
F5 can disable the mode while a task is running, but does not cancel or
replay already-dispatched AI/tool actions or stop active playback midway.
Queued, unconsumed voice turns and in-flight capture are invalidated on
mode changes/stop. Restarting the listener does not retain old callbacks.

## Dependencies and practical limits

Voice capture needs sounddevice, soundfile and NumPy; speech detection
needs faster-whisper and ONNX Runtime. Silero uses local bundled model
assets without a new VAD download. Whisper transcription can still need
its model downloaded on first use. Existing TTS preferences/fallbacks are
retained; edge-tts may require a network connection.

Microphone/Input Monitoring/Accessibility permissions and hotkey handling
still depend on the terminal and macOS settings. No OS permissions were
changed in this fix. Background speech/TV can be recognized as speech;
this is not acoustic echo cancellation or user voice identification.

## Verification — 2026-11-15

All **314 tests passed**. Nineteen new voice tests cover silence, onset
debouncing, pauses, quiet/long utterances, capture cancellation/errors,
one-worker behavior, response acknowledgments, stop phrases, queued TTS,
real prompt_toolkit input interruption and draft preservation, and chat
completion/error/slash paths waiting through speech playback.

Also exercised the installed Silero ONNX detector with a local macOS
TTS-generated speech file (8.55 seconds), padded with silence. At full
volume and 15% gain, onset was detected around 1.25 seconds and the
utterance ended around 10.94 seconds. The full capture/WAV pipeline with
the real detector, a simulated microphone stream and 15% gain produced
a speech-containing clip and stopped around 10.98 seconds.

No paid AI/TTS API request or live microphone recording was used for
verification. Real-room acoustics, the user's actual voice, F5 delivery
and speaker/mic interaction still require a live conversation check.

## Exit and microphone cleanup (2026-11-15)

Chat now releases voice resources on every exit path, including `/exit`, EOF
and Ctrl+C. Input streams explicitly abort queued input and close; graceful
PortAudio stop previously hung intermittently during interpreter termination.
Exit does not play a goodbye response. Six real terminal sessions returned to
the shell in about 1.3 seconds; see `chat-exit-verification.json`.

## Follow-up: native microphone process isolation (2026-11-16)

The prior abort/close fix did not eliminate native CoreAudio stop hangs. A live
terminal process still had a microphone thread blocked in FinishStoppingStream.
A three-second join cannot safely unwind that native call, and importing
sounddevice in the parent also registers a PortAudio termination callback.

On macOS, recording now runs in an owned child process. Only that child imports
sounddevice. Kurt receives 512-sample float32 frames through a pipe with bounded
startup/read waits and cancellation checks. The worker first gets a normal stop
request; a stuck worker is terminated, then killed and reaped with bounded waits.
Provider keys are excluded from its environment. Dependency discovery uses
find_spec so it does not initialize audio in the parent. Other platforms keep
the existing in-process recording implementation.

Regression coverage includes a real child deliberately ignoring SIGTERM, plus
PCM transport, credential filtering, cancellation and failed startup. A live
microphone frame was received and the worker reaped, with sounddevice absent
from the parent. Full suite: **356 tests passed**.

Run the terminal check explicitly (it starts owned shells and microphone sessions):

```sh
python3 tools/verify_chat_exit.py --live --idle-seconds 8 --output /tmp/kurt-exit-check.json
```

This covers bare kurt from the home directory, picker text replacement, nested
exit, Ctrl+D, explicit chat and F5 conversation mode. The shell prompt itself is
required for success. Already-running Kurt sessions need restarting to load the
new implementation. No existing user terminal process was killed by this change.
