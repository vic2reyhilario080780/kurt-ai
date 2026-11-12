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
import queue
import re as _re
import tempfile
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger(__name__)

OS = platform.system()  # "Darwin" | "Windows" | "Linux"

# Set while speak() is actively playing audio — conversation-mode listening
# waits for this to clear before recording again, so Kurt doesn't pick up
# his own voice through the mic as the next "command".
_tts_speaking = threading.Event()


# ─────────────────────────────────────────────────────────────
# Data types
# ─────────────────────────────────────────────────────────────

@dataclass
class VoiceEvent:
    text: str                      # Transcribed speech
    wake_word_used: str = ""       # Which wake word triggered
    confidence: float = 1.0        # STT confidence (if available)
    audio_path: str = ""           # Temp file path (if kept)


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
            communicate = edge_tts.Communicate(
                text, voice=edge_voice, rate=edge_rate, pitch=edge_pitch
            )
            await communicate.save(tmp)
            # Play the file
            if OS == "Darwin":
                subprocess.run(["afplay", tmp], check=True)
            elif OS == "Windows":
                os.startfile(tmp)
            elif OS == "Linux":
                subprocess.run(["mpg123", "-q", tmp])
            os.unlink(tmp)

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
            cmd = ["powershell", "-Command", f'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{text}")']
        else:
            cmd = ["espeak", text]
        subprocess.run(cmd, check=False)
        return
    except Exception as e:
        logger.debug(f"System TTS failed: {e}")

    # Last resort
    logger.info(f"[KURT TTS] {text}")


def speak(text: str, blocking: bool = True, voice_preset: Optional[dict] = None):
    """
    Speak text out loud using best available TTS.
    Priority: edge-tts (better voice) > pyttsx3 > system TTS > log only

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

    def _run():
        _tts_speaking.set()
        try:
            _speak_sync(text, voice_preset)
        finally:
            _tts_speaking.clear()

    if blocking:
        _run()
    else:
        threading.Thread(target=_run, daemon=True).start()


# ─────────────────────────────────────────────────────────────
# Audio recorder
# ─────────────────────────────────────────────────────────────

def record_audio(duration: float = 5.0, sample_rate: int = 16000) -> Optional[str]:
    """
    Record audio for duration seconds.
    Returns path to .wav temp file, or None on failure.
    """
    try:
        import sounddevice as sd
        import soundfile as sf
        import numpy as np

        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
        )
        sd.wait()

        tmp = tempfile.mktemp(suffix=".wav")
        sf.write(tmp, recording, sample_rate)
        return tmp
    except ImportError:
        logger.warning("sounddevice/soundfile not installed. Run: pip install sounddevice soundfile")
        return None
    except Exception as e:
        logger.error(f"Audio recording failed: {e}")
        return None


def record_until_silence(
    max_duration: float = 15.0,
    silence_threshold: float = 0.01,
    silence_duration: float = 1.5,
    sample_rate: int = 16000,
) -> Optional[str]:
    """
    Record until user stops speaking (silence detected) or max_duration.
    More natural than fixed-duration recording.
    """
    try:
        import sounddevice as sd
        import soundfile as sf
        import numpy as np

        chunk_size = int(sample_rate * 0.1)  # 100ms chunks
        buffer = []
        silent_chunks = 0
        required_silent_chunks = int(silence_duration / 0.1)

        with sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32") as stream:
            start = time.time()
            while time.time() - start < max_duration:
                chunk, _ = stream.read(chunk_size)
                buffer.append(chunk.copy())
                rms = np.sqrt(np.mean(chunk ** 2))
                if rms < silence_threshold:
                    silent_chunks += 1
                    if silent_chunks >= required_silent_chunks and len(buffer) > required_silent_chunks:
                        break
                else:
                    silent_chunks = 0

        if not buffer:
            return None

        audio = np.concatenate(buffer).astype(np.int16)
        # Scale float → int16
        audio = (np.concatenate(buffer) * 32767).astype(np.int16)
        tmp = tempfile.mktemp(suffix=".wav")
        sf.write(tmp, audio, sample_rate)
        return tmp
    except Exception as e:
        logger.error(f"record_until_silence failed: {e}")
        return record_audio(duration=5.0, sample_rate=sample_rate)


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
    ):
        self.wake_words = [w.lower() for w in (wake_words or DEFAULT_WAKE_WORDS)]
        self._callbacks: list[Callable[[VoiceEvent], None]] = []
        if callback:
            self._callbacks.append(callback)
        self.use_hotkey = use_hotkey
        self.speak_confirmation = speak_confirmation

        self._running = False
        self._listen_thread: Optional[threading.Thread] = None
        self._hotkey_thread: Optional[threading.Thread] = None
        self._hotkey_listener = None
        self._keyboard_fallback_active = False
        self._command_queue: queue.Queue = queue.Queue()

        # F5 hands-free conversation mode
        self._conversation_mode = False
        self._conversation_thread: Optional[threading.Thread] = None

    def on_command(self, callback: Callable[[VoiceEvent], None]):
        """Register a callback for when a command is received"""
        self._callbacks.append(callback)
        return callback

    def start(self):
        """Start wake word listening"""
        if self._running:
            return
        self._running = True

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
        self._remove_hotkey()

        # Let any in-flight sd.rec() chunk finish on its own instead of
        # force-aborting it — forcing a stop mid-recording is what makes
        # CoreAudio print the harmless-but-noisy "PaMacCore (AUHAL) err=-50"
        # message to stderr. A plain join lets the chunk (max ~2s for the
        # idle wake-word poll) end naturally and exit quietly.
        for t in (self._listen_thread, self._conversation_thread):
            if t and t.is_alive():
                t.join(timeout=3.0)

        logger.info("Wake word listener stopped")

    def is_running(self) -> bool:
        return self._running

    def is_in_conversation_mode(self) -> bool:
        return self._conversation_mode

    def _wait_while_speaking(self, settle: float = 0.4):
        """Pause recording while Kurt is talking, then let mic echo settle.
        No-op (zero added delay) when he isn't currently speaking."""
        if _tts_speaking.is_set():
            while _tts_speaking.is_set() and self._running:
                time.sleep(0.1)
            time.sleep(settle)

    # ── Continuous audio listener ────────────────────────────

    def _listen_loop(self):
        """
        Continuously listen for wake word.
        Records short chunks, checks for wake word, then records full command.
        """
        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            logger.warning(
                "sounddevice not installed — wake word audio disabled.\n"
                "Install with: pip install sounddevice soundfile\n"
                f"Using hotkey only: {HOTKEY_TRIGGER.get(OS, 'ctrl+shift+k')}"
            )
            return

        logger.info("Listening for wake word...")
        while self._running:
            try:
                self._wait_while_speaking()
                # Record a short chunk to check for wake word
                chunk_path = record_audio(duration=2.0)
                if not chunk_path:
                    time.sleep(0.5)
                    continue

                # Transcribe the chunk
                text = transcribe_audio_fast(chunk_path)
                _cleanup(chunk_path)

                if not text:
                    continue

                # Check for wake word
                text_lower = text.lower().strip()
                triggered = None
                for wake_word in self.wake_words:
                    if wake_word in text_lower:
                        triggered = wake_word
                        break

                if triggered:
                    self._handle_wake(triggered, text_lower)

            except Exception as e:
                logger.error(f"Listen loop error: {e}")
                time.sleep(1)

    def _handle_wake(self, wake_word: str, context_text: str):
        """Handle wake word detection"""
        logger.info(f"Wake word detected: '{wake_word}'")

        if self.speak_confirmation:
            speak("Yes?", blocking=False)

        # Check if command was in same utterance (e.g., "Hey Kurt, open Spotify")
        command = _extract_command(context_text, wake_word)
        if command and len(command) > 3:
            self._fire_command(VoiceEvent(text=command, wake_word_used=wake_word))
            return

        # Otherwise record the command
        speak("Listening...", blocking=True)
        self._wait_while_speaking()
        cmd_path = record_until_silence(max_duration=10.0)
        if cmd_path:
            command = transcribe_audio_fast(cmd_path)
            _cleanup(cmd_path)
            if command:
                self._fire_command(VoiceEvent(text=command, wake_word_used=wake_word))
            else:
                speak("Sorry, I didn't catch that.", blocking=False)

    def _fire_command(self, event: VoiceEvent):
        """Fire all registered callbacks"""
        logger.info(f"Voice command: '{redact(event.text)}'")
        for cb in self._callbacks:
            try:
                cb(event)
            except Exception as e:
                logger.error(f"Voice callback error: {e}")

    # ── Hotkey fallback ──────────────────────────────────────

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
        """Handle single-command hotkey press — same as wake word, one command only"""
        speak("Listening...", blocking=True)
        self._wait_while_speaking()
        cmd_path = record_until_silence(max_duration=10.0)
        if cmd_path:
            command = transcribe_audio_fast(cmd_path)
            _cleanup(cmd_path)
            if command:
                self._fire_command(VoiceEvent(text=command, wake_word_used="hotkey"))

    # ── F5 conversation mode ─────────────────────────────────

    def _on_conversation_hotkey(self):
        """F5 pressed — toggle hands-free voice conversation mode"""
        if self._conversation_mode:
            self._stop_conversation_mode()
        else:
            self._start_conversation_mode()

    def _start_conversation_mode(self):
        if self._conversation_mode:
            return
        self._conversation_mode = True
        speak("Voice activated! Usapan na tayo.", blocking=True)
        self._conversation_thread = threading.Thread(
            target=self._conversation_loop,
            daemon=True,
            name="KURT-Conversation",
        )
        self._conversation_thread.start()
        logger.info("Voice conversation mode started (F5)")

    def _stop_conversation_mode(self):
        if not self._conversation_mode:
            return
        self._conversation_mode = False
        speak("Sige, tigil na muna.", blocking=False)
        logger.info("Voice conversation mode stopped (F5)")

    def _conversation_loop(self):
        """Keep listening and firing commands until F5 toggles this off."""
        while self._conversation_mode and self._running:
            try:
                # Kurt's spoken reply to the previous turn (fired from
                # main.py after the AI responds) sets this same event —
                # wait it out so the mic doesn't re-hear his own answer.
                self._wait_while_speaking()
                if not self._conversation_mode:
                    break
                cmd_path = record_until_silence(max_duration=12.0)
                if not cmd_path:
                    time.sleep(0.3)
                    continue
                command = transcribe_audio_fast(cmd_path)
                _cleanup(cmd_path)
                if command and self._conversation_mode:
                    self._fire_command(VoiceEvent(text=command, wake_word_used="f5-conversation"))
            except Exception as e:
                logger.error(f"Conversation loop error: {e}")
                time.sleep(1)


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

    for dep in ["faster_whisper", "whisper", "pyttsx3", "edge_tts", "keyboard"]:
        try:
            __import__(dep.replace("-", "_"))
            deps[dep] = True
        except ImportError:
            deps[dep] = False

    deps["can_record"] = deps.get("sounddevice", False) and deps.get("soundfile", False)
    deps["can_transcribe"] = deps.get("faster_whisper", False) or deps.get("whisper", False)
    deps["can_speak"] = deps.get("edge_tts", False) or deps.get("pyttsx3", False)
    deps["fully_functional"] = deps["can_record"] and deps["can_transcribe"] and deps["can_speak"]

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


def get_listener(callback: Optional[Callable] = None) -> WakeWordListener:
    global _listener
    if _listener is None:
        _listener = WakeWordListener(callback=callback)
    elif callback:
        _listener.on_command(callback)
    return _listener


def start_listening(callback: Optional[Callable] = None) -> WakeWordListener:
    """Start the global wake word listener"""
    listener = get_listener(callback)
    if not listener.is_running():
        listener.start()
    return listener


def stop_listening():
    global _listener
    if _listener and _listener.is_running():
        _listener.stop()
