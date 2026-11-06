"""
KURT v3.0 — Memory + Habit Learning
Kurt learns from interactions and builds user habits over time.
No cloud required. Everything stored locally in JSON.

Features:
- Short-term memory: current session context
- Long-term memory: persistent JSON store
- Habit detection: finds patterns in user behavior
- Smart suggestions: "You usually open Spotify at 9am"
- App usage patterns: which apps, when, how often
"""

from __future__ import annotations

import json
import logging
import os
import threading
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Default memory store location
DEFAULT_MEMORY_DIR = Path.home() / ".kurt" / "memory"


# ─────────────────────────────────────────────────────────────
# Data types
# ─────────────────────────────────────────────────────────────

@dataclass
class MemoryEntry:
    key: str
    value: Any
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: list[str] = field(default_factory=list)
    access_count: int = 0


@dataclass
class HabitEntry:
    action: str               # e.g., "open_app:Spotify"
    hour: int                 # 0–23
    day_of_week: int          # 0=Mon … 6=Sun
    count: int = 1
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Interaction:
    timestamp: str
    command: str              # What user said/typed
    action: str               # What KURT did
    success: bool
    metadata: dict = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────
# Memory store
# ─────────────────────────────────────────────────────────────

class KURTMemory:
    """
    Persistent memory for KURT.
    Stores user preferences, habits, and context in local JSON files.
    """

    def __init__(self, memory_dir: Optional[Path] = None):
        self._dir = Path(memory_dir or DEFAULT_MEMORY_DIR)
        self._dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()

        # In-memory caches
        self._short_term: dict[str, Any] = {}       # Session only
        self._long_term: dict[str, MemoryEntry] = {}
        self._habits: list[HabitEntry] = []
        self._interactions: list[Interaction] = []

        # Load from disk
        self._load()

    # ── Short-term (session only) ────────────────────────────

    def remember_now(self, key: str, value: Any):
        """Remember something for this session only"""
        with self._lock:
            self._short_term[key] = value

    def recall_now(self, key: str, default=None) -> Any:
        """Recall a session memory"""
        return self._short_term.get(key, default)

    def clear_session(self):
        """Clear session memory (keep long-term)"""
        with self._lock:
            self._short_term.clear()

    # ── Long-term (persistent) ───────────────────────────────

    def remember(self, key: str, value: Any, tags: list[str] = None):
        """Remember something permanently"""
        with self._lock:
            if key in self._long_term:
                entry = self._long_term[key]
                entry.value = value
                entry.updated_at = datetime.now().isoformat()
                entry.access_count += 1
            else:
                self._long_term[key] = MemoryEntry(
                    key=key, value=value, tags=tags or []
                )
        self._save_long_term()

    def recall(self, key: str, default=None) -> Any:
        """Recall a long-term memory"""
        # Check short-term first
        if key in self._short_term:
            return self._short_term[key]

        with self._lock:
            entry = self._long_term.get(key)
            if entry:
                entry.access_count += 1
                return entry.value
        return default

    def forget(self, key: str):
        """Remove a long-term memory"""
        with self._lock:
            self._long_term.pop(key, None)
        self._save_long_term()

    def search_memories(self, query: str) -> list[MemoryEntry]:
        """Search memories by key or tag"""
        query_lower = query.lower()
        with self._lock:
            return [
                entry for entry in self._long_term.values()
                if query_lower in entry.key.lower()
                or any(query_lower in tag.lower() for tag in entry.tags)
            ]

    def get_all_memories(self) -> dict[str, Any]:
        """Get all long-term memories as a simple dict"""
        with self._lock:
            return {k: v.value for k, v in self._long_term.items()}

    # ── Interaction logging ──────────────────────────────────

    def log_interaction(
        self,
        command: str,
        action: str,
        success: bool,
        metadata: dict = None,
    ):
        """Log a user→KURT interaction (for habit learning)"""
        interaction = Interaction(
            timestamp=datetime.now().isoformat(),
            command=command,
            action=action,
            success=success,
            metadata=metadata or {},
        )
        with self._lock:
            self._interactions.append(interaction)
            # Keep last 1000 interactions
            if len(self._interactions) > 1000:
                self._interactions = self._interactions[-1000:]

        # Update habits
        self._update_habit(action)
        self._save_interactions()

    def _update_habit(self, action: str):
        """Update habit patterns based on action"""
        now = datetime.now()
        with self._lock:
            # Find existing habit for this action+time
            for habit in self._habits:
                if (habit.action == action
                    and habit.hour == now.hour
                    and habit.day_of_week == now.weekday()):
                    habit.count += 1
                    habit.last_seen = now.isoformat()
                    self._save_habits()
                    return

            # New habit entry
            self._habits.append(HabitEntry(
                action=action,
                hour=now.hour,
                day_of_week=now.weekday(),
            ))
            self._save_habits()

    # ── Habit suggestions ────────────────────────────────────

    def get_suggestions(self, top_n: int = 3) -> list[dict]:
        """
        Get smart suggestions based on current time and habits.
        Returns what user usually does at this hour on this day.
        """
        now = datetime.now()
        # Look at ±1 hour window
        hours = [(now.hour - 1) % 24, now.hour, (now.hour + 1) % 24]
        day = now.weekday()

        candidates = []
        with self._lock:
            for habit in self._habits:
                if habit.hour in hours and habit.count >= 2:
                    # Score by count + day match
                    day_match = 1.5 if habit.day_of_week == day else 1.0
                    score = habit.count * day_match
                    candidates.append({
                        "action": habit.action,
                        "count": habit.count,
                        "score": score,
                        "usual_hour": habit.hour,
                    })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:top_n]

    def get_habit_summary(self) -> str:
        """Human-readable summary of learned habits"""
        suggestions = self.get_suggestions(top_n=5)
        if not suggestions:
            return "No habits learned yet. Keep using KURT!"

        lines = ["📊 Your KURT habits:"]
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        with self._lock:
            top_habits = sorted(self._habits, key=lambda h: h.count, reverse=True)[:5]
            for h in top_habits:
                day_name = days[h.day_of_week]
                lines.append(
                    f"  • {h.action} — usually at {h.hour:02d}:00 on {day_name}s "
                    f"({h.count}x)"
                )
        return "\n".join(lines)

    # ── Context management ───────────────────────────────────

    def get_context(self) -> dict:
        """Get combined short + long term context for KURT"""
        with self._lock:
            ctx = {
                "session": dict(self._short_term),
                "user_name": self._long_term.get("user_name", MemoryEntry("", "KURT User")).value,
                "preferences": self._long_term.get("preferences", MemoryEntry("", {})).value,
                "last_command": self._long_term.get("last_command", MemoryEntry("", "")).value,
                "suggestions": self.get_suggestions(),
            }
        return ctx

    def save_preference(self, key: str, value: Any):
        """Save a user preference"""
        prefs = self.recall("preferences") or {}
        prefs[key] = value
        self.remember("preferences", prefs, tags=["preferences"])

    def get_preference(self, key: str, default=None) -> Any:
        prefs = self.recall("preferences") or {}
        return prefs.get(key, default)

    # ── Stats ─────────────────────────────────────────────────

    def get_stats(self) -> dict:
        with self._lock:
            total = len(self._interactions)
            successful = sum(1 for i in self._interactions if i.success)
            top_commands = defaultdict(int)
            for i in self._interactions[-100:]:
                top_commands[i.action] += 1

            return {
                "total_interactions": total,
                "success_rate": f"{(successful / total * 100):.0f}%" if total else "N/A",
                "long_term_memories": len(self._long_term),
                "habits_learned": len(self._habits),
                "top_actions": dict(sorted(top_commands.items(), key=lambda x: x[1], reverse=True)[:5]),
            }

    # ── Persistence ──────────────────────────────────────────

    def _load(self):
        """Load all memory from disk"""
        self._long_term = self._load_json("long_term.json", {})
        # Reconstruct MemoryEntry objects
        self._long_term = {
            k: MemoryEntry(**v) if isinstance(v, dict) else MemoryEntry(key=k, value=v)
            for k, v in self._long_term.items()
        }

        raw_habits = self._load_json("habits.json", [])
        self._habits = [HabitEntry(**h) if isinstance(h, dict) else h for h in raw_habits]

        raw_interactions = self._load_json("interactions.json", [])
        self._interactions = [
            Interaction(**i) if isinstance(i, dict) else i
            for i in raw_interactions[-500:]  # Load last 500
        ]

    def _load_json(self, filename: str, default):
        path = self._dir / filename
        if not path.exists():
            return default
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load {filename}: {e}")
            return default

    def _save_json(self, filename: str, data):
        path = self._dir / filename
        try:
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w") as f:
                json.dump(data, f, indent=2, default=str)
            tmp.rename(path)
        except Exception as e:
            logger.error(f"Failed to save {filename}: {e}")

    def _save_long_term(self):
        with self._lock:
            data = {k: asdict(v) for k, v in self._long_term.items()}
        self._save_json("long_term.json", data)

    def _save_habits(self):
        with self._lock:
            data = [asdict(h) for h in self._habits]
        self._save_json("habits.json", data)

    def _save_interactions(self):
        with self._lock:
            data = [asdict(i) for i in self._interactions[-500:]]
        self._save_json("interactions.json", data)

    def save_all(self):
        """Force save everything to disk"""
        self._save_long_term()
        self._save_habits()
        self._save_interactions()


# ─────────────────────────────────────────────────────────────
# Global singleton
# ─────────────────────────────────────────────────────────────

_memory: Optional[KURTMemory] = None


def get_memory(memory_dir: Optional[Path] = None) -> KURTMemory:
    global _memory
    if _memory is None:
        _memory = KURTMemory(memory_dir)
    return _memory


# ── Convenience top-level functions ─────────────────────────

def remember(key: str, value: Any, tags: list[str] = None):
    get_memory().remember(key, value, tags)

def recall(key: str, default=None) -> Any:
    return get_memory().recall(key, default)

def forget(key: str):
    get_memory().forget(key)

def remember_now(key: str, value: Any):
    get_memory().remember_now(key, value)

def recall_now(key: str, default=None) -> Any:
    return get_memory().recall_now(key, default)

def log_interaction(command: str, action: str, success: bool, metadata: dict = None):
    get_memory().log_interaction(command, action, success, metadata)

def get_suggestions(top_n: int = 3) -> list[dict]:
    return get_memory().get_suggestions(top_n)

def save_preference(key: str, value: Any):
    get_memory().save_preference(key, value)

def get_preference(key: str, default=None) -> Any:
    return get_memory().get_preference(key, default)

def get_context() -> dict:
    return get_memory().get_context()

def get_stats() -> dict:
    return get_memory().get_stats()

def get_habit_summary() -> str:
    return get_memory().get_habit_summary()
