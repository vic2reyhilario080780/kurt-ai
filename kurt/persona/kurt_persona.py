"""KurtPersona — loads persona.md + memory.md, picks a mode from the user's
message, and builds the system prompt + sampling temperature for that turn."""

from datetime import datetime
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
PERSONA_PATH = BASE_DIR / "persona.md"
MEMORY_PATH = BASE_DIR / "memory.md"

_DEFAULT_PERSONA = (
    "You are KURT, Daddy Tito's personal AI assistant. Speak in Taglish, call "
    "the user Daddy Tito or boss, and keep things casual and friendly."
)

# Keyword triggers for "mode=auto" — Taglish + English, lowercase substrings.
MODE_KEYWORDS = {
    "coding": [
        "bug", "error", "exception", "traceback", "stack trace", "debug",
        "code", "script", "function", "variable", "compile", "syntax",
        "crash", "null pointer", "undefined", "api", "backend", "frontend",
        "deploy", "git", "merge conflict", "unit test",
    ],
    "business": [
        "negosyo", "benta", "binebenta", "kita", "tubo", "puhunan", "presyo",
        "customer", "tindahan", "sari-sari store", "profit", "margin",
        "supplier", "resibo", "invoice", "marketing", "promo", "paninda",
    ],
}

MODE_TEMPERATURE = {
    "casual": 0.9,
    "coding": 0.3,
    "business": 0.6,
}

HISTORY_LIMIT = 20
HISTORY_IN_PROMPT = 5


class KurtPersona:
    """One instance per chat session. `build()` is pure (no side effects);
    call `remember()` yourself once you actually have the model's reply."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir) if base_dir else BASE_DIR
        self.history: list[tuple[str, str]] = []

    def _read(self, path: Path, default: str) -> str:
        try:
            return path.read_text(encoding="utf-8").strip()
        except OSError:
            return default

    def _persona_text(self) -> str:
        path = self.base_dir / "persona.md"
        return self._read(path, _DEFAULT_PERSONA)

    def _memory_text(self) -> str:
        path = self.base_dir / "memory.md"
        return self._read(path, "(wala pang laman — gamitin ang `kurt memory add` para magdagdag.)")

    def detect_mode(self, user_input: str, mode: str = "auto") -> str:
        if mode != "auto":
            return mode
        text = (user_input or "").casefold()
        for name, keywords in MODE_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                return name
        return "casual"

    def build(self, user_input: str, mode: str = "auto") -> dict:
        """Returns {"system_prompt": str, "temperature": float, "mode": str}."""
        resolved_mode = self.detect_mode(user_input, mode)
        now = datetime.now().strftime("%Y-%m-%d (%A), %H:%M")

        parts = [
            self._persona_text(),
            f"=== MEMORY TUNGKOL KAY DADDY TITO ===\n{self._memory_text()}",
            f"=== CONTEXT ===\nPetsa/oras ngayon: {now}\nKasalukuyang mode: {resolved_mode}",
        ]
        if self.history:
            recent = "\n".join(
                f"Daddy Tito: {u}\nKURT: {r}" for u, r in self.history[-HISTORY_IN_PROMPT:]
            )
            parts.append(f"=== KAMAKAILANG USAPAN ===\n{recent}")

        return {
            "system_prompt": "\n\n".join(parts),
            "temperature": MODE_TEMPERATURE.get(resolved_mode, MODE_TEMPERATURE["casual"]),
            "mode": resolved_mode,
        }

    def remember(self, user_input: str, response: str) -> None:
        if not user_input or not response:
            return
        self.history.append((user_input, response))
        self.history = self.history[-HISTORY_LIMIT:]
