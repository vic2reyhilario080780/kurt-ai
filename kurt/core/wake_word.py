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
import tempfile
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger(__name__)

OS = platform.system()  # "Darwin" | "Windows" | "Linux"


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


# ─────────────────────────────────────────────────────────────
# STT — Speech to Text
# ─────────────────────────────────────────────────────────────

def transcribe_audio(audio_path: str, language: str = "en") -> tuple[str, float]:
    """
    Transcribe audio file → (text, confidence).
    Tries faster-whisper first (faster), then openai-whisper.
    """
    # Try faster-whisper
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("base", device="cpu", compute_type="int8")
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

def speak(text: str, blocking: bool = True):
    """
    Speak text out loud using best available TTS.
    Priority: edge-tts (better voice) > pyttsx3 > system TTS > log only
    """
    # edge-tts (async, better quality)
    try:
        import asyncio
        import edge_tts
        import tempfile
        import subprocess

        async def _speak():
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp = f.name
            communicate = edge_tts.Communicate(text, voice="en-US-AriaNeural")
            await communicate.save(tmp)
            # Play the file
            if OS == "Darwin":
                subprocess.run(["afplay", tmp], check=True)
            elif OS == "Windows":
                os.startfile(tmp)
            elif OS == "Linux":
                subprocess.run(["mpg123", "-q", tmp])
            os.unlink(tmp)

        if blocking:
            asyncio.run(_speak())
        else:
            threading.Thread(target=asyncio.run, args=(_speak(),), daemon=True).start()
        return
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"edge-tts failed: {e}")

    # pyttsx3 (cross-platform, offline)
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 175)
        engine.say(text)
        if blocking:
            engine.runAndWait()
        else:
            threading.Thread(target=engine.runAndWait, daemon=True).start()
        return
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"pyttsx3 failed: {e}")

    # System TTS fallback
    try:
        import subprocess
        if OS == "Darwin":
            cmd = ["say", text]
        elif OS == "Windows":
            cmd = ["powershell", "-Command", f'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{text}")']
        else:
            cmd = ["espeak", text]
        if blocking:
            subprocess.run(cmd, check=False)
        else:
            subprocess.Popen(cmd)
        return
    except Exception as e:
        logger.debug(f"System TTS failed: {e}")

    # Last resort
    logger.info(f"[KURT TTS] {text}")


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
        self._command_queue: queue.Queue = queue.Queue()

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
        self._remove_hotkey()
        logger.info("Wake word listener stopped")

    def is_running(self) -> bool:
        return self._running

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
        speak("Listening...", blocking=False)
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
        """Set up keyboard hotkey as wake word fallback"""
        hotkey = HOTKEY_TRIGGER.get(OS, "ctrl+shift+k")

        # Try pynput first — works on Mac without admin/root
        try:
            from pynput import keyboard as pynput_kb

            # Parse hotkey string into pynput keys
            _key_map = {
                "ctrl":  pynput_kb.Key.ctrl,
                "shift": pynput_kb.Key.shift,
                "alt":   pynput_kb.Key.alt,
                "cmd":   pynput_kb.Key.cmd,
            }
            parts = hotkey.lower().split("+")
            trigger_keys = set()
            for p in parts:
                if p in _key_map:
                    trigger_keys.add(_key_map[p])
                elif len(p) == 1:
                    trigger_keys.add(pynput_kb.KeyCode.from_char(p))

            current_keys: set = set()
            callback = self._on_hotkey_pressed

            def on_press(key):
                current_keys.add(key)
                if trigger_keys and trigger_keys.issubset(current_keys):
                    callback()

            def on_release(key):
                current_keys.discard(key)

            listener = pynput_kb.Listener(on_press=on_press, on_release=on_release)
            listener.daemon = True
            listener.start()
            logger.info(f"Hotkey registered (pynput): {hotkey}")
            self._hotkey_active = True
            return
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"pynput hotkey failed: {e}")

        # Fallback: try keyboard library (needs admin on Mac)
        try:
            import keyboard
            keyboard.add_hotkey(hotkey, self._on_hotkey_pressed)
            logger.info(f"Hotkey registered (keyboard lib): {hotkey}")
            self._hotkey_active = True
        except ImportError:
            logger.info("keyboard library not installed — hotkey disabled")
        except Exception as e:
            logger.warning(f"Hotkey setup failed: {e}")

    def _remove_hotkey(self):
        """Remove keyboard hotkey"""
        try:
            import keyboard
            keyboard.unhook_all()
        except Exception:
            pass

    def _on_hotkey_pressed(self):
        """Handle hotkey press — same as wake word"""
        speak("Listening...", blocking=False)
        cmd_path = record_until_silence(max_duration=10.0)
        if cmd_path:
            command = transcribe_audio_fast(cmd_path)
            _cleanup(cmd_path)
            if command:
                self._fire_command(VoiceEvent(text=command, wake_word_used="hotkey"))


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
