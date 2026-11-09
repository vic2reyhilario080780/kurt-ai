"""
KURT v3.0 — Always-On Screen Watcher
Background monitor that watches the screen and notifies Kurt of changes.
Kurt becomes proactive — notices things without being asked.

Features:
- Detects screen changes (new windows, notifications, errors)
- Triggers callbacks on specific conditions
- Lightweight: only analyzes when screen actually changes
- Runs in background thread
"""

from __future__ import annotations

import base64
import hashlib
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from typing import Callable, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Event types
# ─────────────────────────────────────────────────────────────

@dataclass
class ScreenEvent:
    event_type: str          # "change" | "notification" | "error" | "app_switch" | "idle"
    timestamp: datetime
    description: str = ""
    screenshot_b64: str = ""
    metadata: dict = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────
# Screen Watcher
# ─────────────────────────────────────────────────────────────

class ScreenWatcher:
    """
    Runs in background, watches screen for changes.
    Calls registered handlers when interesting things happen.
    """

    def __init__(
        self,
        interval: float = 2.0,          # seconds between checks
        change_threshold: float = 0.05,  # 5% pixel change = "changed"
        use_vision: bool = True,         # analyze changes with vision model
        vision_model: Optional[str] = None,
    ):
        self.interval = interval
        self.change_threshold = change_threshold
        self.use_vision = use_vision
        self.vision_model = vision_model

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_hash: Optional[str] = None
        self._last_screenshot_b64: Optional[str] = None
        self._handlers: list[Callable[[ScreenEvent], None]] = []
        self._event_history: list[ScreenEvent] = []
        self._lock = threading.Lock()

        # Notification patterns to watch for
        self._watch_patterns: list[dict] = []

    # ── Handler registration ─────────────────────────────────

    def on_event(self, handler: Callable[[ScreenEvent], None]):
        """Register a callback for any screen event"""
        self._handlers.append(handler)
        return handler  # Allow use as decorator

    def watch_for(self, keyword: str, callback: Callable[[ScreenEvent], None]):
        """
        Watch for a specific keyword/pattern on screen.
        Calls callback when keyword appears in screen description.
        """
        self._watch_patterns.append({
            "keyword": keyword.lower(),
            "callback": callback,
        })

    # ── Start / Stop ─────────────────────────────────────────

    def start(self):
        """Start background screen watching"""
        if self._running:
            logger.warning("ScreenWatcher already running")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._watch_loop,
            daemon=True,
            name="KURT-ScreenWatcher",
        )
        self._thread.start()
        logger.info(f"ScreenWatcher started (interval={self.interval}s)")

    def stop(self):
        """Stop background screen watching"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("ScreenWatcher stopped")

    def is_running(self) -> bool:
        return self._running and (self._thread is not None) and self._thread.is_alive()

    # ── Main loop ────────────────────────────────────────────

    def _watch_loop(self):
        """Main background loop"""
        while self._running:
            try:
                self._check_screen()
            except Exception as e:
                logger.error(f"ScreenWatcher error: {e}")
            time.sleep(self.interval)

    def _check_screen(self):
        """Take screenshot, compare to last, fire events if changed"""
        try:
            from kurt.core.computer_use import screenshot as take_screenshot
            result = take_screenshot()
            if not result.success:
                return

            img_b64 = result.data["image_b64"]
            current_hash = self._hash_image(img_b64)

            if self._last_hash is None:
                # First run — just store
                self._last_hash = current_hash
                self._last_screenshot_b64 = img_b64
                return

            # Check if screen changed significantly
            change_ratio = self._compute_change(
                self._last_screenshot_b64, img_b64
            )

            if change_ratio >= self.change_threshold:
                self._on_screen_changed(img_b64, change_ratio)
                self._last_hash = current_hash
                self._last_screenshot_b64 = img_b64

        except ImportError:
            logger.warning("PyAutoGUI not available for screen watching")
            self.stop()

    def _on_screen_changed(self, img_b64: str, change_ratio: float):
        """Handle a detected screen change"""
        description = ""

        # Optionally analyze the change with vision
        if self.use_vision:
            try:
                from kurt.core.vision import smart_vision
                result = smart_vision(
                    img_b64,
                    "What changed on this screen? Be brief. Any notifications, errors, new windows?",
                    prefer_local=True,
                    allow_cloud=False,
                )
                if result.success:
                    description = result.description
            except Exception as e:
                logger.debug(f"Vision analysis failed: {e}")

        event = ScreenEvent(
            event_type=self._classify_event(description),
            timestamp=datetime.now(),
            description=description,
            screenshot_b64="",  # Do not retain/transmit background screenshots in events.
            metadata={"change_ratio": change_ratio},
        )

        # Store in history (keep last 50)
        with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > 50:
                self._event_history.pop(0)

        # Fire all handlers
        for handler in self._handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler error: {e}")

        # Check watch patterns
        if description:
            desc_lower = description.lower()
            for pattern in self._watch_patterns:
                if pattern["keyword"] in desc_lower:
                    try:
                        pattern["callback"](event)
                    except Exception as e:
                        logger.error(f"Pattern callback error: {e}")

    def _classify_event(self, description: str) -> str:
        """Classify event type from description"""
        desc = description.lower()
        if any(w in desc for w in ["error", "failed", "crash", "exception", "warning"]):
            return "error"
        if any(w in desc for w in ["notification", "alert", "popup", "message", "ping"]):
            return "notification"
        if any(w in desc for w in ["opened", "launched", "switched", "new window", "new tab"]):
            return "app_switch"
        return "change"

    # ── Image comparison ─────────────────────────────────────

    def _hash_image(self, img_b64: str) -> str:
        """Fast hash of image for change detection"""
        return hashlib.md5(img_b64.encode()).hexdigest()

    def _compute_change(self, old_b64: str, new_b64: str) -> float:
        """
        Compute ratio of changed pixels (0.0 = no change, 1.0 = completely different).
        Uses downsampled comparison for speed.
        """
        try:
            from PIL import Image, ImageChops
            import struct

            def b64_to_img(b64):
                data = base64.b64decode(b64)
                return Image.open(BytesIO(data)).convert("RGB").resize((160, 90))

            img1 = b64_to_img(old_b64)
            img2 = b64_to_img(new_b64)

            diff = ImageChops.difference(img1, img2)
            pixels = list(diff.getdata())
            changed = sum(1 for p in pixels if max(p) > 20)  # threshold = 20/255
            return changed / len(pixels)

        except ImportError:
            # Fallback: hash comparison (binary — changed or not)
            return 1.0 if self._hash_image(old_b64) != self._hash_image(new_b64) else 0.0
        except Exception:
            return 0.0

    # ── History / State ──────────────────────────────────────

    def get_recent_events(self, limit: int = 10) -> list[ScreenEvent]:
        with self._lock:
            return list(self._event_history[-limit:])

    def get_last_screenshot(self) -> Optional[str]:
        return self._last_screenshot_b64

    def current_screen_description(self) -> str:
        """Get a description of what's currently on screen"""
        if not self._last_screenshot_b64:
            return "No screenshot taken yet"
        try:
            from kurt.core.vision import describe_screen
            result = describe_screen(self._last_screenshot_b64)
            return result.description if result.success else "Could not describe screen"
        except Exception:
            return "Vision not available"


# ─────────────────────────────────────────────────────────────
# Proactive notification system
# ─────────────────────────────────────────────────────────────

class KURTProactive:
    """
    Kurt's proactive awareness — built on top of ScreenWatcher.
    Gives Kurt the ability to notice and report things unprompted.
    """

    def __init__(self, watcher: ScreenWatcher):
        self.watcher = watcher
        self._notifications: list[str] = []
        self._lock = threading.Lock()

        # Register our handler
        watcher.on_event(self._handle_event)

        # Watch for common important patterns
        watcher.watch_for("error", self._handle_error)
        watcher.watch_for("notification", self._handle_notification_pattern)
        watcher.watch_for("battery", self._handle_battery)

    def _handle_event(self, event: ScreenEvent):
        """Main event handler"""
        if event.event_type in ("error", "notification"):
            msg = f"[{event.event_type.upper()}] {event.description[:200]}"
            with self._lock:
                self._notifications.append(msg)

    def _handle_error(self, event: ScreenEvent):
        self._add_notification(f"⚠️ Daddy Tito, may nakitang error sa screen: {event.description[:150]}")

    def _handle_notification_pattern(self, event: ScreenEvent):
        self._add_notification(f"🔔 May notification: {event.description[:150]}")

    def _handle_battery(self, event: ScreenEvent):
        self._add_notification(f"🔋 Battery update detected: {event.description[:100]}")

    def _add_notification(self, msg: str):
        with self._lock:
            self._notifications.append(msg)
            if len(self._notifications) > 100:
                self._notifications.pop(0)

    def get_pending_notifications(self) -> list[str]:
        """Get and clear pending notifications"""
        with self._lock:
            notifs = list(self._notifications)
            self._notifications.clear()
        return notifs

    def has_notifications(self) -> bool:
        with self._lock:
            return bool(self._notifications)


# ─────────────────────────────────────────────────────────────
# Global singleton (lazy init)
# ─────────────────────────────────────────────────────────────

_watcher: Optional[ScreenWatcher] = None
_proactive: Optional[KURTProactive] = None


def get_watcher(
    auto_start: bool = False,
    interval: float = 2.0,
    use_vision: bool = True,
) -> ScreenWatcher:
    """Get or create the global ScreenWatcher"""
    global _watcher, _proactive
    if _watcher is None:
        _watcher = ScreenWatcher(interval=interval, use_vision=use_vision)
        _proactive = KURTProactive(_watcher)
        if auto_start:
            _watcher.start()
    return _watcher


def get_proactive() -> Optional[KURTProactive]:
    """Get the global proactive notification system"""
    return _proactive


def start_watching(interval: float = 2.0, use_vision: bool = True):
    """Start background screen watching"""
    watcher = get_watcher(interval=interval, use_vision=use_vision)
    if not watcher.is_running():
        watcher.start()
    return watcher


def stop_watching():
    """Stop background screen watching"""
    global _watcher
    if _watcher and _watcher.is_running():
        _watcher.stop()
