"""Local speech detection and explicit utterance boundaries (16 kHz mono)."""

from collections import deque
from dataclasses import dataclass
import math
import os


class SpeechLimitReached(RuntimeError):
    """A long utterance was discarded rather than submitting a partial command."""


def _seconds(name, default, minimum, maximum):
    try:
        value = float(os.getenv(name, str(default)))
        return min(maximum, max(minimum, value)) if math.isfinite(value) else default
    except ValueError:
        return default


@dataclass(frozen=True)
class VoiceSettings:
    silence_seconds: float = 1.5
    max_speech_seconds: float = 60.0
    start_timeout: float = 15.0
    min_speech_seconds: float = 0.16
    frame_seconds: float = 512 / 16000

    @classmethod
    def from_env(cls):
        from kurt.core.persona import load_persona
        pause=load_persona().get('speech_pause_seconds',2.0)
        if type(pause) not in (int,float) or not math.isfinite(pause): pause=2.0
        return cls(
            silence_seconds=_seconds("KURT_VOICE_SILENCE_SECONDS", min(4.,max(.6,pause)), 0.6, 4.0),
            max_speech_seconds=_seconds("KURT_VOICE_MAX_SPEECH_SECONDS", 60, 15, 180),
        )


class SpeechEndpoint:
    """Debounced onset + trailing silence; silence alone never creates a turn."""

    def __init__(self, settings):
        self.settings = settings
        self.started = False
        self.voiced = 0
        self.silent = 0
        self.elapsed = 0
        self.waited = 0

    def feed(self, probability):
        frame = self.settings.frame_seconds
        if not self.started:
            self.waited += 1
            self.voiced = self.voiced + 1 if probability >= 0.5 else 0
            if self.voiced * frame >= self.settings.min_speech_seconds:
                self.started = True
                return "speech"
            if self.waited * frame >= self.settings.start_timeout:
                return "idle"
            return "waiting"
        self.elapsed += 1
        self.silent = self.silent + 1 if probability < 0.35 else 0
        if self.silent * frame >= self.settings.silence_seconds:
            return "complete"
        if self.elapsed * frame >= self.settings.max_speech_seconds:
            raise SpeechLimitReached("Utterance limit reached; no partial command submitted.")
        return "speech"


class SileroSpeechDetector:
    """Use faster-whisper's bundled Silero ONNX VAD, without a network download.

    A rolling context window works with the installed VAD's stateless batch
    interface. Recompute every ~96 ms and retain onset/offset context.
    """

    def __init__(self):
        from faster_whisper.vad import get_vad_model
        self.model = get_vad_model()
        self.frames = deque(maxlen=32)
        self.count = 0
        self.probability = 0.0

    def __call__(self, samples):
        import numpy as np
        self.frames.append(np.asarray(samples, dtype=np.float32).reshape(-1))
        self.count += 1
        if self.count % 3 == 0:
            values = np.asarray(self.model(np.concatenate(self.frames))).reshape(-1)
            self.probability = float(np.max(values[-3:])) if len(values) else 0.0
        return self.probability


class WebRTCSpeechDetector:
    """Model-free VAD; reframe 512-sample capture into 30 ms PCM16 frames."""
    def __init__(self):
        import webrtcvad
        self.model=webrtcvad.Vad(2)
        self.pending=bytearray()
        self.probability=0.0

    def __call__(self,samples):
        import numpy as np
        values=np.nan_to_num(np.asarray(samples,dtype=np.float32).reshape(-1),nan=0.,posinf=1.,neginf=-1.)
        self.pending.extend((np.clip(values,-1,1)*32767).astype('<i2').tobytes())
        decisions=[]
        while len(self.pending)>=960:
            frame=bytes(self.pending[:960]);del self.pending[:960]
            decisions.append(self.model.is_speech(frame,16000))
        if decisions: self.probability=1.0 if any(decisions) else 0.0
        return self.probability


def speech_detector():
    try: return WebRTCSpeechDetector()
    except ImportError: return SileroSpeechDetector()
