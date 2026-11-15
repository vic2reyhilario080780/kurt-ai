"""
KURT v3.0 — Wake Word + Voice
"Hey Kurt" triggers KURT from anywhere on the system.
Voice input → text → KURT processes → voice output.

Features:
- Wake word detection: "Hey Kurt" / "Kurt" / configurable
- Cross-platform audio capture (macOS, Windows, Linux)
- Local STT: Whisper (via faster-whisper or openai-whisper)
- TTS output: system TTS (pyttsx3) or edge-tts
- Fallback: keyboard hotkey if audio not available
"""

from __future__ import annotations

from kurt.utils.security import redact

import logging
import os
import platform
import re as _re
import tempfile
import threading
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger(__name__)

OS = platform.system()  # "Darwin" | "Windows" | "Linux"

# Set while speak() is actively playing audio — conversation-mode listening
# waits for this to clear before recording again, so Kurt doesn't pick up
# his own voice through the mic as the next "command".
_tts_speaking = threading.Event()
_tts_lock = threading.Lock()
_tts_state_lock = threading.Lock()
_tts_pending = 0
_tts_finished_at = 0.0
_microphone_lock = threading.Lock()


# ─────────────────────────────────────────────────────────────
# Data types
# ─────────────────────────────────────────────────────────────

@dataclass
class VoiceEvent:
    text: str                      # Transcribed speech
    wake_word_used: str = ""       # Which wake word triggered
    confidence: float = 1.0        # STT confidence (if available)
    audio_path: str = ""           # Temp file path (if kept)
    turn_id: int = 0


# ─────────────────────────────────────────────────────────────
# Wake word config
# ─────────────────────────────────────────────────────────────

DEFAULT_WAKE_WORDS = [
    "hey kurt",
    "ok kurt",
    "hey kart",    # common mishear
    "kurt",
]

HOTKEY_TRIGGER = {
    "Darwin": "ctrl+shift+k",
    "Windows": "ctrl+shift+k",
    "Linux": "ctrl+shift+k",
}

# F5 toggles hands-free "voice conversation mode" — press once to start
# talking back and forth without needing "Hey Kurt" each time, press again
# (or say "stop listening") to end it.
CONVERSATION_HOTKEY = "<f5>"


def _pynput_combo(hotkey: str) -> str:
    """Convert 'ctrl+shift+k' -> '<ctrl>+<shift>+k' for pynput.GlobalHotKeys"""
    modifiers = {"ctrl", "shift", "alt", "cmd"}
    parts = hotkey.lower().split("+")
    return "+".join(f"<{p}>" if p in modifiers else p for p in parts)


# ─────────────────────────────────────────────────────────────
# STT — Speech to Text
# ─────────────────────────────────────────────────────────────

_whisper_model = None  # cached faster-whisper model — loading it per chunk was dead weight


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        # "small" over "base" — noticeably better Tagalog/Taglish accuracy,
        # still fast enough on CPU for short command-length clips.
        _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
    return _whisper_model


def transcribe_audio(audio_path: str, language: Optional[str] = None) -> tuple[str, float]:
    """
    Transcribe audio file → (text, confidence).
    Tries faster-whisper first (faster), then openai-whisper.

    language=None lets Whisper auto-detect per utterance — important for
    Taglish, where forcing "en" makes it mangle Tagalog words into
    English-sounding nonsense instead of transcribing them correctly.
    """
    # Try faster-whisper
    try:
        model = _get_whisper_model()
        segments, info = model.transcribe(audio_path, language=language)
        text = " ".join(seg.text.strip() for seg in segments)
        return text.strip(), 0.9
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"faster-whisper failed: {e}")

    # Try openai-whisper
    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, language=language)
        return result["text"].strip(), 0.9
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"openai-whisper failed: {e}")

    return "", 0.0


def transcribe_audio_fast(audio_path: str) -> str:
    """Fast transcription, text only"""
    text, _ = transcribe_audio(audio_path)
    return text


# ─────────────────────────────────────────────────────────────
# TTS — Text to Speech
# ─────────────────────────────────────────────────────────────

_MD_CODE_BLOCK_RE = _re.compile(r"```.*?```", _re.DOTALL)
_MD_INLINE_CODE_RE = _re.compile(r"`([^`]*)`")
_MD_LINK_RE = _re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MD_EMPHASIS_RE = _re.compile(r"(\*\*\*|\*\*|\*|___|__|_)(.*?)\1")
_MD_HEADER_RE = _re.compile(r"^#{1,6}\s*", _re.MULTILINE)
_MD_BULLET_RE = _re.compile(r"^\s*[-*+]\s+", _re.MULTILINE)


def strip_markdown_for_speech(text: str) -> str:
    """Strip markdown so TTS doesn't read out asterisks, hashes, backticks, etc."""
    text = _MD_CODE_BLOCK_RE.sub(" code block omitted ", text)
    text = _MD_INLINE_CODE_RE.sub(r"\1", text)
    text = _MD_LINK_RE.sub(r"\1", text)
    text = _MD_EMPHASIS_RE.sub(r"\2", text)
    text = _MD_HEADER_RE.sub("", text)
    text = _MD_BULLET_RE.sub("", text)
    return text.strip()


def _speak_sync(text: str, voice_preset: dict):
    """Actually play `text` out loud, blocking until done. edge-tts > pyttsx3 > system > log."""
    edge_voice = voice_preset.get("edge_voice", "en-US-AriaNeural")
    edge_rate = voice_preset.get("edge_rate", "+0%")
    edge_pitch = voice_preset.get("edge_pitch", "+0Hz")
    mac_say_voice = voice_preset.get("mac_say_voice")
    pyttsx3_rate = voice_preset.get("pyttsx3_rate", 175)

    # edge-tts (async, better quality)
    try:
        import asyncio
        import edge_tts
        import tempfile
        import subprocess

        async def _speak():
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp = f.name
            try:
                communicate = edge_tts.Communicate(
                    text, voice=edge_voice, rate=edge_rate, pitch=edge_pitch
                )
                await communicate.save(tmp)
                # Play the file
                if OS == "Darwin":
                    subprocess.run(["afplay", tmp], check=True)
                elif OS == "Windows":
                    import shutil
                    player = shutil.which("ffplay")
                    if not player:
                        raise RuntimeError("No blocking MP3 player; use the offline TTS fallback")
                    subprocess.run([player, "-nodisp", "-autoexit", "-loglevel", "quiet", tmp], check=True)
                elif OS == "Linux":
                    subprocess.run(["mpg123", "-q", tmp], check=True)
            finally:
                _cleanup(tmp)

        asyncio.run(_speak())
        return
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"edge-tts failed: {e}")

    # pyttsx3 (cross-platform, offline)
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", pyttsx3_rate)
        engine.say(text)
        engine.runAndWait()
        return
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"pyttsx3 failed: {e}")

    # System TTS fallback
    try:
        import subprocess
        if OS == "Darwin":
            cmd = ["say"] + (["-v", mac_say_voice] if mac_say_voice else []) + [text]
        elif OS == "Windows":
            cmd = ["powershell", "-NoProfile", "-Command", 'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak([Console]::In.ReadToEnd())']
        else:
            cmd = ["espeak", text]
        options = {"input": text, "text": True} if OS == "Windows" else {}
        try:
            subprocess.run(cmd, check=True, **options)
        except subprocess.CalledProcessError:
            if OS != "Darwin" or not mac_say_voice:
                raise
            subprocess.run(["say", text], check=True)
        return
    except Exception as e:
        logger.debug(f"System TTS failed: {e}")

    raise RuntimeError("No working text-to-speech output is available.")


def speak(text: str, blocking: bool = True, voice_preset: Optional[dict] = None):
    """
    Speak text out loud using best available TTS.
    Priority: edge-tts (better voice) > pyttsx3 > system TTS; report failure.

    voice_preset: dict with edge_voice/edge_rate/edge_pitch/mac_say_voice/pyttsx3_rate.
    Defaults to the user's configured persona voice (kurt.core.persona.get_voice_preset()).

    Sets the module-level `_tts_speaking` event for the duration of playback
    so WakeWordListener's conversation-mode loop knows not to record while
    Kurt is talking (otherwise the mic picks up his own voice).
    """
    if voice_preset is None:
        try:
            from kurt.core.persona import get_voice_preset
            voice_preset = get_voice_preset()
        except Exception:
            voice_preset = {}

    global _tts_pending
    # Reserve speech before spawning: a listener must not sneak in while
    # the playback thread is waiting to start or another TTS is queued.
    with _tts_state_lock:
        _tts_pending += 1
        _tts_speaking.set()

    def _run():
        global _tts_pending, _tts_finished_at
        try:
            with _tts_lock, _microphone_lock:
                _speak_sync(text, voice_preset)
        except Exception:
            if blocking:
                raise
            logger.error("Voice playback unavailable")
        finally:
            with _tts_state_lock:
                _tts_pending -= 1
                _tts_finished_at = time.monotonic()
                if not _tts_pending:
                    _tts_speaking.clear()

    if blocking:
        _run()
    else:
        try:
            threading.Thread(target=_run, daemon=True).start()
        except Exception:
            with _tts_state_lock:
                _tts_pending -= 1
                if not _tts_pending:
                    _tts_speaking.clear()
            raise


# ─────────────────────────────────────────────────────────────
# Audio recorder
# ─────────────────────────────────────────────────────────────

def _write_audio(chunks, sample_rate):
    import numpy as np
    import soundfile as sf
    audio = (np.clip(np.concatenate(chunks), -1, 1) * 32767).astype(np.int16)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as stream:
        path = stream.name
    try:
        sf.write(path, audio, sample_rate)
    except Exception:
        _cleanup(path)
        raise
    return path


@contextmanager
def _input_stream(sd, sample_rate):
    """Discard queued input on close; never drain it during chat shutdown.

    PortAudio's graceful stop can block on macOS and race its atexit
    termination. Input recording has no output buffers to preserve.
    """
    stream = sd.InputStream(samplerate=sample_rate, channels=1, dtype='float32')
    try:
        stream.start()
        yield stream
    finally:
        try:
            stream.abort(ignore_errors=True)
        finally:
            stream.close(ignore_errors=True)


def record_audio(duration: float = 5.0, sample_rate: int = 16000, should_cancel=None) -> Optional[str]:
    """Short wake-word capture, cancellable before playback or a mode switch."""
    try:
        import sounddevice as sd
        frames = max(1, int(duration * sample_rate / 512))
        buffer = []
        with _microphone_lock:
            if _tts_speaking.is_set() or (should_cancel and should_cancel()):
                return None
            with _input_stream(sd, sample_rate) as stream:
                for _ in range(frames):
                    if _tts_speaking.is_set() or (should_cancel and should_cancel()):
                        return None
                    chunk, overflow = stream.read(512)
                    if overflow:
                        return None  # A dropped chunk is not a complete command.
                    buffer.append(chunk.copy())
        if _tts_speaking.is_set() or (should_cancel and should_cancel()):
            return None
        from .voice_activity import SileroSpeechDetector
        detector = SileroSpeechDetector()
        consecutive = 0
        for chunk in buffer:
            consecutive = consecutive + 1 if detector(chunk) >= 0.5 else 0
            if consecutive >= 5:
                break
        else:
            return None  # Do not send silent wake-word clips to Whisper.
        if _tts_speaking.is_set() or (should_cancel and should_cancel()):
            return None
        return _write_audio(buffer, sample_rate)
    except Exception as exc:
        logger.error("Audio recording unavailable: %s", type(exc).__name__)
        return None


def record_until_silence(
    max_duration: float = 60.0,
    silence_threshold: float = 0.01,  # retained for API compatibility; VAD replaces RMS
    silence_duration: float = 1.5,
    sample_rate: int = 16000,
    *, should_cancel=None, speech_detector=None, state_callback=None,
    start_timeout: float = 15.0,
) -> Optional[str]:
    """Wait for speech, then finish after trailing silence. Never submit silence
    or a cancelled/truncated utterance. Duration is measured after speech onset.
    """
    from .voice_activity import VoiceSettings, SpeechEndpoint, SileroSpeechDetector, SpeechLimitReached
    if sample_rate != 16000:
        raise ValueError("Voice activity detection requires 16000 Hz audio.")
    settings = VoiceSettings(silence_seconds=silence_duration, max_speech_seconds=max_duration,
                             start_timeout=start_timeout)
    endpoint = SpeechEndpoint(settings)
    buffer = []
    preroll = deque(maxlen=12)  # 384 ms retains the first syllable before onset confirmation.
    try:
        import sounddevice as sd
        detector = speech_detector if speech_detector is not None else SileroSpeechDetector()
        with _microphone_lock:
            if _tts_speaking.is_set() or (should_cancel and should_cancel()):
                return None
            with _input_stream(sd, sample_rate) as stream:
                while True:
                    if _tts_speaking.is_set() or (should_cancel and should_cancel()):
                        return None
                    chunk, overflow = stream.read(512)
                    if overflow:
                        return None
                    was_started = endpoint.started
                    outcome = endpoint.feed(detector(chunk))
                    if was_started:
                        buffer.append(chunk.copy())
                    else:
                        preroll.append(chunk.copy())
                        if endpoint.started:
                            buffer.extend(preroll)
                            if state_callback:
                                state_callback("listening")
                    if outcome == "idle":
                        return None
                    if outcome == "complete":
                        break
        if _tts_speaking.is_set() or (should_cancel and should_cancel()):
            return None
        return _write_audio(buffer, sample_rate)
    except SpeechLimitReached:
        raise
    except Exception as exc:
        logger.error("Speech capture unavailable: %s", type(exc).__name__)
        return None  # No fixed-length fallback that could execute silence/partial speech.


# ─────────────────────────────────────────────────────────────
# Wake Word Listener
# ─────────────────────────────────────────────────────────────

class WakeWordListener:
    """
    Background listener for "Hey Kurt" and similar wake words.
    When triggered, records the command and fires callbacks.
    """

    def __init__(
        self,
        wake_words: Optional[list[str]] = None,
        callback: Optional[Callable[[VoiceEvent], None]] = None,
        use_hotkey: bool = True,
        speak_confirmation: bool = True,
        deferred: bool = False,
        state_callback=None,
    ):
        self.wake_words = [w.lower() for w in (wake_words or DEFAULT_WAKE_WORDS)]
        self._callbacks: list[Callable[[VoiceEvent], None]] = []
        self._deferred_callbacks = set()
        self._state_callback = state_callback
        self.state = "off"
        self._state_lock = threading.RLock()
        self._turn_busy = threading.Event()
        self._assistant_busy = threading.Event()
        self._capture_requested = threading.Event()
        self._revision = 0
        self._turn_number = 0
        self._pending_turn = None
        from .voice_activity import VoiceSettings
        self.settings = VoiceSettings.from_env()
        if callback:
            self._callbacks.append(callback)
            if deferred:
                self._deferred_callbacks.add(callback)
        self.use_hotkey = use_hotkey
        self.speak_confirmation = speak_confirmation

        self._running = False
        self._listen_thread: Optional[threading.Thread] = None
        self._hotkey_listener = None
        self._keyboard_fallback_active = False

        # F5 hands-free conversation mode
        self._conversation_mode = False

    def on_command(self, callback: Callable[[VoiceEvent], None], deferred=False):
        """Register a callback for when a command is received"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
        if deferred:
            self._deferred_callbacks.add(callback)
        return callback

    def start(self):
        """Start wake word listening"""
        if self._running:
            return
        self._running = True
        self._set_state("off")

        # Start continuous audio listener
        self._listen_thread = threading.Thread(
            target=self._listen_loop,
            daemon=True,
            name="KURT-WakeWord",
        )
        self._listen_thread.start()

        # Also set up keyboard hotkey as fallback
        if self.use_hotkey:
            self._setup_hotkey()

        logger.info(f"Wake word listener started. Say: {self.wake_words[:3]}")

    def stop(self):
        """Stop wake word listening"""
        self._running = False
        self._conversation_mode = False
        self._revision += 1
        self._turn_busy.clear()
        self._pending_turn = None
        self._set_state("off")
        self._remove_hotkey()

        # Recording checks cancellation between 32 ms frames. An in-flight
        # STT call may finish later, but its revision is invalid and cannot
        # dispatch a command after stop/restart.
        thread = self._listen_thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=3.0)

        logger.info("Wake word listener stopped")

    def is_running(self) -> bool:
        return self._running

    def is_in_conversation_mode(self) -> bool:
        return self._conversation_mode

    def _set_state(self, state):
        self.state = state
        if self._state_callback:
            try:
                self._state_callback(state)
            except Exception:
                logger.exception("Voice status callback failed")

    def set_processing(self, active):
        if active:
            self._assistant_busy.set()
            self._set_state("thinking")
        else:
            self._assistant_busy.clear()
            if not self._turn_busy.is_set():
                self._set_state("waiting" if self._conversation_mode else "off")

    def is_current_turn(self, turn_id):
        with self._state_lock:
            return self._pending_turn == turn_id

    def finish_turn(self, turn_id):
        with self._state_lock:
            if self._pending_turn != turn_id:
                return
            self._pending_turn = None
            self._turn_busy.clear()
        self._set_state("waiting" if self._conversation_mode else "off")

    def _busy(self):
        return self._turn_busy.is_set() or self._assistant_busy.is_set()

    def _cancel_capture(self, revision):
        return not self._running or revision != self._revision or self._busy()

    def _wait_while_speaking(self, settle: float = 0.35):
        while _tts_speaking.is_set() and self._running:
            time.sleep(0.03)
        remaining = settle - (time.monotonic() - _tts_finished_at)
        if remaining > 0 and self._running:
            time.sleep(remaining)

    def _listen_loop(self):
        """One worker owns all wake-word, F5 and one-shot microphone capture."""
        while self._running:
            try:
                if self._busy():
                    time.sleep(0.03)
                    continue
                self._wait_while_speaking()
                if not self._running:
                    break
                if self._conversation_mode or self._capture_requested.is_set():
                    origin = "f5-conversation" if self._conversation_mode else "hotkey"
                    self._capture_requested.clear()
                    self._capture_command(origin)
                    continue
                revision = self._revision
                from .voice_activity import SpeechLimitReached
                try:
                    # Capture the full utterance before checking the wake word;
                    # a two-second clip can cut an inline command in half.
                    chunk_path = record_until_silence(
                        max_duration=self.settings.max_speech_seconds,
                        silence_duration=self.settings.silence_seconds, start_timeout=2.0,
                        should_cancel=lambda: self._cancel_capture(revision),
                    )
                except SpeechLimitReached:
                    continue
                if not chunk_path:
                    time.sleep(0.05)
                    continue
                try:
                    if self._cancel_capture(revision):
                        continue
                    text = transcribe_audio_fast(chunk_path)
                finally:
                    _cleanup(chunk_path)
                if self._cancel_capture(revision):
                    continue
                text_lower = text.lower().strip()
                triggered = next((w for w in self.wake_words if w in text_lower), None)
                if triggered:
                    self._handle_wake(triggered, text_lower)
            except Exception:
                logger.exception("Voice listener failed")
                time.sleep(0.2)

    def _capture_command(self, origin):
        from .voice_activity import SpeechLimitReached
        revision = self._revision
        self._set_state("waiting")
        try:
            path = record_until_silence(
                max_duration=self.settings.max_speech_seconds,
                silence_duration=self.settings.silence_seconds,
                start_timeout=self.settings.start_timeout,
                should_cancel=lambda: self._cancel_capture(revision), state_callback=self._set_state,
            )
        except SpeechLimitReached:
            if not self._cancel_capture(revision):
                speak("Mahaba na ang sinabi mo. Hatiin natin sa mas maiikling bahagi; wala pa akong ipinasa.", blocking=True)
            return
        if not path:
            time.sleep(0.05)
            return
        try:
            if self._cancel_capture(revision):
                return
            self._set_state("transcribing")
            command = transcribe_audio_fast(path).strip()
        finally:
            _cleanup(path)
        if command and not self._cancel_capture(revision):
            # Local mode controls do not require an AI call or credits.
            control = command.casefold().strip(" .!?,")
            if origin == "f5-conversation" and control in {
                "stop listening", "stop listening kurt", "kurt stop listening",
                "tigil muna", "tigil muna kurt", "tama na muna", "tumigil ka muna",
            }:
                self._stop_conversation_mode()
                return
            self._fire_command(VoiceEvent(text=command, wake_word_used=origin))
        elif not self._busy():
            self._set_state("waiting" if self._conversation_mode else "off")

    def _handle_wake(self, wake_word: str, context_text: str):
        if self._busy() or self._conversation_mode:
            return
        command = _extract_command(context_text, wake_word)
        if command and len(command) > 3:
            self._fire_command(VoiceEvent(text=command, wake_word_used=wake_word))
            return
        if self.speak_confirmation:
            speak("Nakikinig ako.", blocking=True)
        self._capture_command(wake_word)

    def _fire_command(self, event: VoiceEvent):
        if not event.text.strip():
            return
        with self._state_lock:
            if not self._running or self._busy():
                return
            self._turn_number += 1
            event.turn_id = self._turn_number
            self._pending_turn = event.turn_id
            self._turn_busy.set()
        self._set_state("thinking")
        deferred = False
        try:
            for cb in list(self._callbacks):
                try:
                    cb(event)
                    deferred = deferred or cb in self._deferred_callbacks
                except Exception:
                    logger.exception("Voice callback failed")
        finally:
            if not deferred:
                self.finish_turn(event.turn_id)

    def _setup_hotkey(self):
        """Set up keyboard hotkeys: F5 (conversation mode toggle) + single-command fallback"""
        hotkey = HOTKEY_TRIGGER.get(OS, "ctrl+shift+k")

        # Try pynput first — works on Mac without admin/root
        try:
            from pynput import keyboard as pynput_kb

            listener = pynput_kb.GlobalHotKeys({
                CONVERSATION_HOTKEY: self._on_conversation_hotkey,
                _pynput_combo(hotkey): self._on_hotkey_pressed,
            })
            listener.daemon = True
            listener.start()
            self._hotkey_listener = listener
            logger.info(f"Hotkeys registered (pynput): F5 (conversation mode), {hotkey} (single command)")
            self._hotkey_active = True
            return
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"pynput hotkey failed: {e}")

        # Fallback: try keyboard library (needs admin on Mac)
        try:
            import keyboard
            keyboard.add_hotkey("f5", self._on_conversation_hotkey)
            keyboard.add_hotkey(hotkey, self._on_hotkey_pressed)
            logger.info(f"Hotkeys registered (keyboard lib): f5, {hotkey}")
            self._hotkey_active = True
            self._keyboard_fallback_active = True
        except ImportError:
            logger.info("keyboard library not installed — hotkey disabled")
        except Exception as e:
            logger.warning(f"Hotkey setup failed: {e}")

    def _remove_hotkey(self):
        """Remove keyboard hotkeys"""
        if self._hotkey_listener is not None:
            try:
                self._hotkey_listener.stop()
            except Exception:
                pass
            self._hotkey_listener = None
        # Only touch the `keyboard` lib if it was actually the one registered
        # — calling keyboard.unhook_all() unconditionally starts its own
        # (unused) OS listener thread, which throws an unawaited "Error 13 -
        # Must be run as administrator" on macOS without Accessibility access.
        if self._keyboard_fallback_active:
            try:
                import keyboard
                keyboard.unhook_all()
            except Exception:
                pass
            self._keyboard_fallback_active = False

    def _on_hotkey_pressed(self):
        if not self._running or self._busy():
            return
        self._capture_requested.set()
        self._revision += 1  # Abort any wake-word clip; the same worker takes over.

    def _on_conversation_hotkey(self):
        if self._conversation_mode:
            self._stop_conversation_mode()
        else:
            self._start_conversation_mode()

    def _start_conversation_mode(self):
        if not self._running or self._conversation_mode:
            return
        self._conversation_mode = True
        self._revision += 1
        self._set_state("waiting")
        speak("Voice activated! Usapan na tayo.", blocking=False)

    def _stop_conversation_mode(self):
        if not self._conversation_mode:
            return
        self._conversation_mode = False
        self._revision += 1
        # Invalidate queued, unconsumed speech. An already-running AI/tool
        # request is not cancelled or replayed by toggling voice mode.
        with self._state_lock:
            self._pending_turn = None
            self._turn_busy.clear()
        self._set_state("off")
        speak("Sige, tigil na muna.", blocking=False)


# ─────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────

def _extract_command(text: str, wake_word: str) -> str:
    """Extract command from text after wake word"""
    idx = text.lower().find(wake_word)
    if idx == -1:
        return ""
    after = text[idx + len(wake_word):].strip()
    # Remove punctuation like comma after wake word
    after = after.lstrip(",.!? ")
    return after


def _cleanup(path: str):
    """Delete temp audio file"""
    try:
        if path and os.path.exists(path):
            os.unlink(path)
    except Exception:
        pass


def check_dependencies() -> dict[str, bool]:
    """Check which voice dependencies are available"""
    deps = {}

    for dep in ["sounddevice", "soundfile", "numpy"]:
        try:
            __import__(dep.replace("-", "_"))
            deps[dep] = True
        except ImportError:
            deps[dep] = False

    for dep in ["faster_whisper", "whisper", "onnxruntime", "pyttsx3", "edge_tts", "keyboard"]:
        try:
            __import__(dep.replace("-", "_"))
            deps[dep] = True
        except ImportError:
            deps[dep] = False

    deps["can_record"] = deps.get("sounddevice", False) and deps.get("soundfile", False) and deps.get("numpy", False)
    deps["can_transcribe"] = deps.get("faster_whisper", False) or deps.get("whisper", False)
    deps["can_detect_speech"] = deps.get("faster_whisper", False) and deps.get("onnxruntime", False)
    deps["can_speak"] = deps.get("edge_tts", False) or deps.get("pyttsx3", False)
    deps["fully_functional"] = deps["can_record"] and deps["can_transcribe"] and deps["can_speak"] and deps["can_detect_speech"]

    return deps


def install_dependencies() -> dict[str, str]:
    """Install voice dependencies"""
    import subprocess
    packages = [
        "sounddevice",
        "soundfile",
        "faster-whisper",
        "pyttsx3",
        "keyboard",
        "edge-tts",
    ]
    results = {}
    for pkg in packages:
        result = subprocess.run(
            ["pip", "install", pkg, "--break-system-packages", "-q"],
            capture_output=True, text=True
        )
        results[pkg] = "ok" if result.returncode == 0 else result.stderr[:100]
    return results


# ─────────────────────────────────────────────────────────────
# Global singleton
# ─────────────────────────────────────────────────────────────

_listener: Optional[WakeWordListener] = None


def get_listener(callback: Optional[Callable] = None, *, deferred=False, state_callback=None) -> WakeWordListener:
    global _listener
    if _listener is None:
        _listener = WakeWordListener(callback=callback, deferred=deferred, state_callback=state_callback)
    elif callback:
        _listener.on_command(callback, deferred=deferred)
        if state_callback:
            _listener._state_callback = state_callback
    return _listener


def start_listening(callback: Optional[Callable] = None, *, deferred=False, state_callback=None) -> WakeWordListener:
    """Start the global wake word listener"""
    listener = get_listener(callback, deferred=deferred, state_callback=state_callback)
    if not listener.is_running():
        listener.start()
    return listener


def stop_listening():
    global _listener
    if _listener:
        _listener.stop()
        _listener = None
