"""
KURT v3.0 — Computer Use Engine
Cross-platform computer control: screenshot, mouse, keyboard, app launcher.
Works on macOS, Windows, and Linux.
"""

from __future__ import annotations

import base64
import logging
import platform
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

OS = platform.system()  # "Darwin" | "Windows" | "Linux"


# ─────────────────────────────────────────────────────────────
# Result types
# ─────────────────────────────────────────────────────────────

@dataclass
class ActionResult:
    success: bool
    message: str = ""
    data: dict = field(default_factory=dict)

    def __bool__(self):
        return self.success


class Key(str, Enum):
    """Common keys — platform-agnostic names"""
    ENTER      = "enter"
    ESCAPE     = "escape"
    TAB        = "tab"
    SPACE      = "space"
    BACKSPACE  = "backspace"
    DELETE     = "delete"
    UP         = "up"
    DOWN       = "down"
    LEFT       = "left"
    RIGHT      = "right"
    CMD        = "command"   # Mac: ⌘  |  Win/Linux: ctrl
    CTRL       = "ctrl"
    ALT        = "alt"
    SHIFT      = "shift"
    F5         = "f5"


# ─────────────────────────────────────────────────────────────
# Lazy import guard for PyAutoGUI
# ─────────────────────────────────────────────────────────────

def _get_pyautogui():
    try:
        import pyautogui
        pyautogui.FAILSAFE = True       # move mouse to corner to abort
        pyautogui.PAUSE = 0.05          # small delay between actions
        return pyautogui
    except ImportError:
        raise ImportError(
            "PyAutoGUI not installed. Run: pip install pyautogui pillow"
        )


def _get_pil():
    try:
        from PIL import Image
        return Image
    except ImportError:
        raise ImportError("Pillow not installed. Run: pip install pillow")


# ─────────────────────────────────────────────────────────────
# Screenshot
# ─────────────────────────────────────────────────────────────

def screenshot(save_path: Optional[str] = None, region: Optional[tuple] = None) -> ActionResult:
    """
    Take a screenshot of the full screen or a region.
    region = (left, top, width, height)
    Returns base64-encoded PNG in result.data["image_b64"]
    """
    try:
        pag = _get_pyautogui()
        img = pag.screenshot(region=region)

        buf = BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()

        if save_path:
            img.save(save_path)
            logger.debug(f"Screenshot saved: {save_path}")

        size = img.size
        return ActionResult(
            success=True,
            message=f"Screenshot taken ({size[0]}x{size[1]})",
            data={"image_b64": b64, "width": size[0], "height": size[1]},
        )
    except Exception as e:
        return ActionResult(success=False, message=str(e))


def get_screen_size() -> tuple[int, int]:
    """Return (width, height) of primary screen"""
    pag = _get_pyautogui()
    return pag.size()


# ─────────────────────────────────────────────────────────────
# Mouse
# ─────────────────────────────────────────────────────────────

def click(x: int, y: int, button: str = "left", clicks: int = 1, interval: float = 0.1) -> ActionResult:
    """Click at screen coordinates"""
    try:
        pag = _get_pyautogui()
        pag.click(x, y, button=button, clicks=clicks, interval=interval)
        return ActionResult(success=True, message=f"Clicked ({x}, {y}) [{button}]")
    except Exception as e:
        return ActionResult(success=False, message=str(e))


def double_click(x: int, y: int) -> ActionResult:
    return click(x, y, clicks=2)


def right_click(x: int, y: int) -> ActionResult:
    return click(x, y, button="right")


def move_to(x: int, y: int, duration: float = 0.2) -> ActionResult:
    """Move mouse to coordinates"""
    try:
        pag = _get_pyautogui()
        pag.moveTo(x, y, duration=duration)
        return ActionResult(success=True, message=f"Moved to ({x}, {y})")
    except Exception as e:
        return ActionResult(success=False, message=str(e))


def drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> ActionResult:
    """Click and drag from (x1,y1) to (x2,y2)"""
    try:
        pag = _get_pyautogui()
        pag.mouseDown(x1, y1)
        time.sleep(0.05)
        pag.moveTo(x2, y2, duration=duration)
        pag.mouseUp()
        return ActionResult(success=True, message=f"Dragged ({x1},{y1}) → ({x2},{y2})")
    except Exception as e:
        return ActionResult(success=False, message=str(e))


def scroll(x: int, y: int, amount: int = 3, direction: str = "down") -> ActionResult:
    """
    Scroll at (x, y).
    amount: number of scroll units
    direction: "up" | "down" | "left" | "right"
    """
    try:
        pag = _get_pyautogui()
        pag.moveTo(x, y, duration=0.1)
        clicks = -amount if direction == "down" else amount
        if direction in ("up", "down"):
            pag.scroll(clicks)
        else:
            pag.hscroll(-amount if direction == "right" else amount)
        return ActionResult(success=True, message=f"Scrolled {direction} {amount}x at ({x},{y})")
    except Exception as e:
        return ActionResult(success=False, message=str(e))


# ─────────────────────────────────────────────────────────────
# Keyboard
# ─────────────────────────────────────────────────────────────

def type_text(text: str, interval: float = 0.03) -> ActionResult:
    """Type text at current cursor position"""
    try:
        pag = _get_pyautogui()
        pag.write(text, interval=interval)
        return ActionResult(success=True, message=f"Typed: {text[:40]}{'...' if len(text) > 40 else ''}")
    except Exception as e:
        # Fallback for unicode / special chars
        try:
            import pyperclip
            pyperclip.copy(text)
            hotkey("ctrl", "v") if OS != "Darwin" else hotkey("cmd", "v")
            return ActionResult(success=True, message=f"Typed (clipboard): {text[:40]}")
        except Exception:
            return ActionResult(success=False, message=str(e))


def press_key(key: str) -> ActionResult:
    """Press a single key"""
    try:
        pag = _get_pyautogui()
        # Normalize 'cmd' → 'command' for PyAutoGUI on Mac
        mapped = _map_key(key)
        pag.press(mapped)
        return ActionResult(success=True, message=f"Pressed: {key}")
    except Exception as e:
        return ActionResult(success=False, message=str(e))


def hotkey(*keys: str) -> ActionResult:
    """
    Press key combination.
    e.g. hotkey("cmd", "c")  →  ⌘C on Mac
         hotkey("ctrl", "c") →  Ctrl+C on Win/Linux
    """
    try:
        pag = _get_pyautogui()
        mapped = [_map_key(k) for k in keys]
        pag.hotkey(*mapped)
        return ActionResult(success=True, message=f"Hotkey: {'+'.join(keys)}")
    except Exception as e:
        return ActionResult(success=False, message=str(e))


def _map_key(key: str) -> str:
    """Normalize key names for PyAutoGUI"""
    key = key.lower()
    # 'cmd' works as alias for 'command'
    if key == "cmd":
        return "command" if OS == "Darwin" else "ctrl"
    return key


# ─────────────────────────────────────────────────────────────
# App Launcher
# ─────────────────────────────────────────────────────────────

def open_app(app_name: str) -> ActionResult:
    """
    Open an application by name.
    Cross-platform: macOS / Windows / Linux
    """
    try:
        if OS == "Darwin":
            # Try multiple capitalizations: as-is, Title Case, all variations
            candidates = [
                app_name,
                app_name.title(),           # "apple music" → "Apple Music"
                app_name.capitalize(),       # "spotify" → "Spotify"
                app_name.upper(),
            ]
            # Remove duplicates but keep order
            seen = set()
            candidates = [c for c in candidates if c not in seen and not seen.add(c)]

            result = None
            tried_candidates = []
            for candidate in candidates:
                tried_candidates.append(candidate)
                result = subprocess.run(
                    ["open", "-a", candidate],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    app_name = candidate  # Remember the working name
                    break
            # NOTE: No fallback to "open <name>" — that treats it as a file path

        elif OS == "Windows":
            result = subprocess.run(
                ["start", "", app_name],
                shell=True, capture_output=True, text=True, timeout=10
            )

        else:  # Linux
            result = subprocess.run(
                [app_name.lower().replace(" ", "-")],
                capture_output=True, text=True, timeout=10,
                start_new_session=True
            )

        if result and result.returncode == 0:
            time.sleep(1.5)  # Give app time to open
            return ActionResult(success=True, message=f"Opened: {app_name}")
        else:
            if OS == "Darwin":
                tried = ", ".join(f'"{c}"' for c in tried_candidates)
                return ActionResult(success=False, message=f"App not found. Tried: {tried}")
            return ActionResult(success=False, message=f"Could not open: {app_name}")

    except subprocess.TimeoutExpired:
        return ActionResult(success=False, message=f"Timeout opening {app_name}")
    except Exception as e:
        return ActionResult(success=False, message=str(e))


def open_url(url: str, browser: Optional[str] = None) -> ActionResult:
    """Open a URL in the default or specified browser"""
    try:
        import webbrowser
        if browser:
            b = webbrowser.get(browser)
            b.open(url)
        else:
            webbrowser.open(url)
        time.sleep(1.5)
        return ActionResult(success=True, message=f"Opened URL: {url}")
    except Exception as e:
        return ActionResult(success=False, message=str(e))


def close_app(app_name: str) -> ActionResult:
    """Close an application"""
    try:
        if OS == "Darwin":
            subprocess.run(
                ["osascript", "-e", f'quit app "{app_name}"'],
                capture_output=True, timeout=5
            )
        elif OS == "Windows":
            subprocess.run(
                ["taskkill", "/IM", f"{app_name}.exe", "/F"],
                capture_output=True, timeout=5
            )
        else:  # Linux
            subprocess.run(
                ["pkill", "-f", app_name],
                capture_output=True, timeout=5
            )
        return ActionResult(success=True, message=f"Closed: {app_name}")
    except Exception as e:
        return ActionResult(success=False, message=str(e))


def run_command(cmd: str, shell: bool = True, timeout: int = 30) -> ActionResult:
    """Run a shell command and return output"""
    try:
        from kurt.utils.execution import restricted_run
        result = restricted_run(
            cmd, shell=shell, capture_output=True,
            text=True, timeout=timeout
        )
        output = result.stdout.strip() or result.stderr.strip()
        return ActionResult(
            success=result.returncode == 0,
            message=output[:500] if output else "(no output)",
            data={"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr},
        )
    except subprocess.TimeoutExpired:
        return ActionResult(success=False, message=f"Command timed out ({timeout}s)")
    except Exception as e:
        return ActionResult(success=False, message=str(e))


# ─────────────────────────────────────────────────────────────
# Window Management
# ─────────────────────────────────────────────────────────────

def focus_window(app_name: str) -> ActionResult:
    """Bring an app window to the foreground"""
    try:
        if OS == "Darwin":
            script = f'tell application "{app_name}" to activate'
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)

        elif OS == "Windows":
            # Use pygetwindow if available
            try:
                import pygetwindow as gw
                wins = gw.getWindowsWithTitle(app_name)
                if wins:
                    wins[0].activate()
                else:
                    return ActionResult(success=False, message=f"Window not found: {app_name}")
            except ImportError:
                # Fallback: Alt+Tab approach not reliable, just open
                return open_app(app_name)

        else:  # Linux
            subprocess.run(
                ["wmctrl", "-a", app_name],
                capture_output=True, timeout=5
            )

        time.sleep(0.3)
        return ActionResult(success=True, message=f"Focused: {app_name}")
    except Exception as e:
        return ActionResult(success=False, message=str(e))


def get_active_window() -> ActionResult:
    """Get the name of the currently active window"""
    try:
        if OS == "Darwin":
            script = 'tell application "System Events" to get name of first application process whose frontmost is true'
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5
            )
            return ActionResult(
                success=True,
                message=result.stdout.strip(),
                data={"window": result.stdout.strip()}
            )
        elif OS == "Windows":
            try:
                import pygetwindow as gw
                win = gw.getActiveWindow()
                return ActionResult(success=True, message=win.title if win else "Unknown", data={"window": win.title if win else ""})
            except ImportError:
                return ActionResult(success=False, message="pygetwindow not installed")
        else:  # Linux
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=5
            )
            return ActionResult(success=True, message=result.stdout.strip(), data={"window": result.stdout.strip()})
    except Exception as e:
        return ActionResult(success=False, message=str(e))


# ─────────────────────────────────────────────────────────────
# Clipboard
# ─────────────────────────────────────────────────────────────

def clipboard_copy(text: str) -> ActionResult:
    """Copy text to clipboard"""
    try:
        import pyperclip
        pyperclip.copy(text)
        return ActionResult(success=True, message="Copied to clipboard")
    except ImportError:
        # Fallback
        if OS == "Darwin":
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
        elif OS == "Windows":
            subprocess.run(["clip"], input=text.encode(), check=True)
        else:
            subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), check=True)
        return ActionResult(success=True, message="Copied to clipboard")
    except Exception as e:
        return ActionResult(success=False, message=str(e))


def clipboard_paste() -> ActionResult:
    """Get text from clipboard"""
    try:
        import pyperclip
        text = pyperclip.paste()
        return ActionResult(success=True, message="Got clipboard", data={"text": text})
    except ImportError:
        try:
            if OS == "Darwin":
                result = subprocess.run(["pbpaste"], capture_output=True, text=True)
                return ActionResult(success=True, message="Got clipboard", data={"text": result.stdout})
            elif OS == "Windows":
                import ctypes
                # Read from Windows clipboard
                ctypes.windll.user32.OpenClipboard(0)
                handle = ctypes.windll.user32.GetClipboardData(13)  # CF_UNICODETEXT
                ctypes.windll.user32.CloseClipboard()
                return ActionResult(success=True, message="Got clipboard", data={"text": str(handle)})
        except Exception as e2:
            return ActionResult(success=False, message=str(e2))
    except Exception as e:
        return ActionResult(success=False, message=str(e))


# ─────────────────────────────────────────────────────────────
# High-Level Helpers
# ─────────────────────────────────────────────────────────────

def select_all_and_type(text: str) -> ActionResult:
    """Select all existing text and replace with new text"""
    if OS == "Darwin":
        hotkey("cmd", "a")
    else:
        hotkey("ctrl", "a")
    time.sleep(0.1)
    return type_text(text)


def find_on_page() -> ActionResult:
    """Open browser find bar (Cmd+F / Ctrl+F)"""
    if OS == "Darwin":
        return hotkey("cmd", "f")
    return hotkey("ctrl", "f")


def copy_selection() -> ActionResult:
    """Copy currently selected text"""
    if OS == "Darwin":
        return hotkey("cmd", "c")
    return hotkey("ctrl", "c")


def paste() -> ActionResult:
    """Paste from clipboard"""
    if OS == "Darwin":
        return hotkey("cmd", "v")
    return hotkey("ctrl", "v")


def new_tab() -> ActionResult:
    """Open new browser tab"""
    if OS == "Darwin":
        return hotkey("cmd", "t")
    return hotkey("ctrl", "t")


def close_tab() -> ActionResult:
    """Close current browser tab"""
    if OS == "Darwin":
        return hotkey("cmd", "w")
    return hotkey("ctrl", "w")


def go_back() -> ActionResult:
    """Browser back button"""
    if OS == "Darwin":
        return hotkey("cmd", "left")
    return hotkey("alt", "left")


def scroll_to_top() -> ActionResult:
    """Scroll page to top"""
    return hotkey("command" if OS == "Darwin" else "ctrl", "Home".lower()) if OS == "Windows" else press_key("home")


def scroll_to_bottom() -> ActionResult:
    """Scroll page to bottom"""
    return press_key("end")


# ─────────────────────────────────────────────────────────────
# Wait / Utility
# ─────────────────────────────────────────────────────────────

def wait(seconds: float) -> ActionResult:
    """Wait for N seconds"""
    time.sleep(seconds)
    return ActionResult(success=True, message=f"Waited {seconds}s")


def wait_for_app(app_name: str, timeout: int = 10) -> ActionResult:
    """Wait until an app window appears (up to timeout seconds)"""
    start = time.time()
    while time.time() - start < timeout:
        result = get_active_window()
        if app_name.lower() in result.message.lower():
            return ActionResult(success=True, message=f"{app_name} is ready")
        time.sleep(0.5)
    return ActionResult(success=False, message=f"Timed out waiting for {app_name}")


def get_platform_info() -> dict:
    """Return current platform details"""
    return {
        "os": OS,
        "os_version": platform.version(),
        "machine": platform.machine(),
        "python": platform.python_version(),
    }


# ─────────────────────────────────────────────────────────────
# Install helper
# ─────────────────────────────────────────────────────────────

def check_dependencies() -> dict[str, bool]:
    """Check which optional dependencies are installed"""
    deps = {}
    for pkg in ["pyautogui", "pillow", "pyperclip", "pygetwindow", "pytesseract"]:
        try:
            __import__(pkg.replace("-", "_").replace("pillow", "PIL"))
            deps[pkg] = True
        except ImportError:
            deps[pkg] = False
    return deps


def install_dependencies() -> ActionResult:
    """Install required packages for computer use"""
    packages = ["pyautogui", "pillow", "pyperclip"]
    if OS == "Windows":
        packages.append("pygetwindow")

    result = run_command(
        f"pip install {' '.join(packages)} --break-system-packages -q"
    )
    return result
