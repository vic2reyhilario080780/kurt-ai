"""Thread-safe voice handoff to a running prompt_toolkit input application."""

from collections import deque
import threading

VOICE_READY = object()


class VoiceInputBridge:
    def __init__(self):
        self._lock = threading.Lock()
        self._events = deque()
        self._binding = None
        self._draft = ""
        self.status = "Waiting for speech"

    def submit(self, event):
        with self._lock:
            self._events.append(event)
            binding = self._binding
        self._schedule(binding)

    def pop(self):
        with self._lock:
            return self._events.popleft() if self._events else None

    @property
    def has_pending(self):
        with self._lock:
            return bool(self._events)

    def bind(self, app, loop):
        binding = (app, loop, object())
        with self._lock:
            self._binding = binding
        self._schedule(binding)

    def unbind(self):
        with self._lock:
            self._binding = None

    def take_draft(self):
        with self._lock:
            draft, self._draft = self._draft, ""
            return draft

    def set_status(self, state):
        names = {"waiting": "Waiting for speech", "listening": "Listening…",
                 "transcribing": "Transcribing…", "thinking": "Thinking…",
                 "speaking": "Speaking…", "clarifying":"Unclear speech — please repeat", "off": "Voice idle — F5 to talk"}
        with self._lock:
            self.status = names.get(state, state)
            binding = self._binding
        self._schedule(binding)

    def _schedule(self, binding):
        if binding is None:
            return
        app, loop, _ = binding
        def deliver():
            with self._lock:
                if self._binding is not binding or app.is_done:
                    return
                pending = bool(self._events)
                if pending:
                    self._draft = app.current_buffer.text
            if pending:
                app.exit(result=VOICE_READY)
            else:
                app.invalidate()
        try:
            loop.call_soon_threadsafe(deliver)
        except RuntimeError:
            pass  # Closing prompt: pending events remain for the next prompt.
