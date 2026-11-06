"""
KURT v3.0 — Smart Browser Automation
Kurt navigates any browser intelligently — Chrome, Safari, Firefox, Arc, Brave, Edge.
Works via Computer Use (mouse + keyboard) + Vision (see the page).

Features:
- open_browser() / switch_browser() — open any browser
- navigate() — go to URL, wait for page load
- find_and_click() — find element by description, click it
- wait_for_element() — wait until something appears on screen
- fill_form() — fill input fields naturally
- scroll_to() — scroll until element is visible
- get_page_text() — extract visible text from screen
- auto_retry() — retry actions on failure
- page_loaded() — detect if page finished loading
- Browser-aware: knows Chrome vs Safari vs Firefox shortcuts
"""

from __future__ import annotations

import logging
import platform
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

OS = platform.system()  # "Darwin" | "Windows" | "Linux"


# ─────────────────────────────────────────────────────────────
# Result type
# ─────────────────────────────────────────────────────────────

@dataclass
class BrowserResult:
    success: bool
    message: str = ""
    data: dict = field(default_factory=dict)

    def __bool__(self):
        return self.success


# ─────────────────────────────────────────────────────────────
# Browser profiles — shortcuts per browser
# ─────────────────────────────────────────────────────────────

BROWSER_SHORTCUTS = {
    # address bar shortcut
    "chrome":  {"address_bar": ("command", "l") if OS == "Darwin" else ("ctrl", "l"),
                "new_tab": ("command", "t") if OS == "Darwin" else ("ctrl", "t"),
                "close_tab": ("command", "w") if OS == "Darwin" else ("ctrl", "w"),
                "reload": ("command", "r") if OS == "Darwin" else ("ctrl", "r"),
                "find": ("command", "f") if OS == "Darwin" else ("ctrl", "f")},
    "safari":  {"address_bar": ("command", "l"),
                "new_tab": ("command", "t"),
                "close_tab": ("command", "w"),
                "reload": ("command", "r"),
                "find": ("command", "f")},
    "firefox": {"address_bar": ("command", "l") if OS == "Darwin" else ("ctrl", "l"),
                "new_tab": ("command", "t") if OS == "Darwin" else ("ctrl", "t"),
                "close_tab": ("command", "w") if OS == "Darwin" else ("ctrl", "w"),
                "reload": ("command", "r") if OS == "Darwin" else ("ctrl", "r"),
                "find": ("command", "f") if OS == "Darwin" else ("ctrl", "f")},
    "arc":     {"address_bar": ("command", "l"),
                "new_tab": ("command", "t"),
                "close_tab": ("command", "w"),
                "reload": ("command", "r"),
                "find": ("command", "f")},
    "brave":   {"address_bar": ("command", "l") if OS == "Darwin" else ("ctrl", "l"),
                "new_tab": ("command", "t") if OS == "Darwin" else ("ctrl", "t"),
                "close_tab": ("command", "w") if OS == "Darwin" else ("ctrl", "w"),
                "reload": ("command", "r") if OS == "Darwin" else ("ctrl", "r"),
                "find": ("command", "f") if OS == "Darwin" else ("ctrl", "f")},
    "edge":    {"address_bar": ("command", "l") if OS == "Darwin" else ("ctrl", "l"),
                "new_tab": ("command", "t") if OS == "Darwin" else ("ctrl", "t"),
                "close_tab": ("command", "w") if OS == "Darwin" else ("ctrl", "w"),
                "reload": ("command", "r") if OS == "Darwin" else ("ctrl", "r"),
                "find": ("command", "f") if OS == "Darwin" else ("ctrl", "f")},
}

# Default app names per OS
BROWSER_APP_NAMES = {
    "Darwin": {
        "chrome": "Google Chrome",
        "safari": "Safari",
        "firefox": "Firefox",
        "arc": "Arc",
        "brave": "Brave Browser",
        "edge": "Microsoft Edge",
    },
    "Windows": {
        "chrome": "chrome",
        "safari": None,
        "firefox": "firefox",
        "arc": "Arc",
        "brave": "brave",
        "edge": "msedge",
    },
    "Linux": {
        "chrome": "google-chrome",
        "safari": None,
        "firefox": "firefox",
        "arc": None,
        "brave": "brave-browser",
        "edge": "microsoft-edge",
    },
}


# ─────────────────────────────────────────────────────────────
# Core browser functions
# ─────────────────────────────────────────────────────────────

def open_browser(browser: str = "chrome") -> BrowserResult:
    """Open a browser. browser = 'chrome'|'safari'|'firefox'|'arc'|'brave'|'edge'"""
    from kurt.core.computer_use import open_app, wait_for_app

    browser = browser.lower().strip()
    app_names = BROWSER_APP_NAMES.get(OS, {})
    app_name = app_names.get(browser)

    if not app_name:
        return BrowserResult(False, f"Browser '{browser}' not supported on {OS}")

    result = open_app(app_name)
    if result.success:
        wait_for_app(app_name, timeout=5)
    return BrowserResult(result.success, result.message, {"browser": browser})


def navigate(url: str, browser: str = "chrome", wait: float = 2.0) -> BrowserResult:
    """
    Navigate to a URL in the given browser.
    Opens browser if not already open.
    """
    from kurt.core.computer_use import (
        open_app, focus_window, hotkey, type_text,
        press_key, screenshot, wait as _wait
    )

    # Ensure URL has scheme
    if not url.startswith(("http://", "https://", "file://")):
        url = "https://" + url

    browser = browser.lower()
    app_names = BROWSER_APP_NAMES.get(OS, {})
    app_name = app_names.get(browser, browser)

    # Open/focus browser
    focus = focus_window(app_name)
    if not focus.success:
        open_result = open_app(app_name)
        if not open_result.success:
            return BrowserResult(False, f"Could not open {browser}: {open_result.message}")
        _wait(1.5)

    # Open address bar
    shortcuts = BROWSER_SHORTCUTS.get(browser, BROWSER_SHORTCUTS["chrome"])
    addr_shortcut = shortcuts["address_bar"]
    hotkey(*addr_shortcut)
    _wait(0.3)

    # Type URL and go
    type_text(url)
    press_key("enter")
    _wait(wait)  # Wait for page to start loading

    return BrowserResult(True, f"Navigated to {url}", {"url": url, "browser": browser})


def new_tab(browser: str = "chrome") -> BrowserResult:
    """Open a new tab"""
    from kurt.core.computer_use import hotkey, wait

    shortcuts = BROWSER_SHORTCUTS.get(browser.lower(), BROWSER_SHORTCUTS["chrome"])
    hotkey(*shortcuts["new_tab"])
    wait(0.3)
    return BrowserResult(True, "New tab opened")


def close_tab(browser: str = "chrome") -> BrowserResult:
    """Close current tab"""
    from kurt.core.computer_use import hotkey, wait

    shortcuts = BROWSER_SHORTCUTS.get(browser.lower(), BROWSER_SHORTCUTS["chrome"])
    hotkey(*shortcuts["close_tab"])
    wait(0.3)
    return BrowserResult(True, "Tab closed")


def reload_page(browser: str = "chrome") -> BrowserResult:
    """Reload current page"""
    from kurt.core.computer_use import hotkey, wait

    shortcuts = BROWSER_SHORTCUTS.get(browser.lower(), BROWSER_SHORTCUTS["chrome"])
    hotkey(*shortcuts["reload"])
    wait(1.0)
    return BrowserResult(True, "Page reloaded")


def go_back(browser: str = "chrome") -> BrowserResult:
    """Go back in browser history"""
    from kurt.core.computer_use import hotkey, wait

    if OS == "Darwin":
        hotkey("command", "[")
    else:
        hotkey("alt", "left")
    wait(0.5)
    return BrowserResult(True, "Went back")


def go_forward(browser: str = "chrome") -> BrowserResult:
    """Go forward in browser history"""
    from kurt.core.computer_use import hotkey, wait

    if OS == "Darwin":
        hotkey("command", "]")
    else:
        hotkey("alt", "right")
    wait(0.5)
    return BrowserResult(True, "Went forward")


# ─────────────────────────────────────────────────────────────
# Smart element finding (Vision-powered)
# ─────────────────────────────────────────────────────────────

def find_and_click(
    element_description: str,
    timeout: float = 10.0,
    retry_interval: float = 1.0,
    screenshot_b64: Optional[str] = None,
) -> BrowserResult:
    """
    Find a UI element by description and click it.
    Uses LLaVA vision to locate the element.

    element_description: e.g. "Search button", "Login link", "Username field"
    """
    from kurt.core.computer_use import screenshot as take_screenshot, click, wait
    from kurt.core.vision import find_element

    start = time.time()
    while time.time() - start < timeout:
        # Take screenshot if not provided
        if not screenshot_b64:
            ss = take_screenshot()
            if not ss.success:
                return BrowserResult(False, "Could not take screenshot")
            img_b64 = ss.data["image_b64"]
        else:
            img_b64 = screenshot_b64
            screenshot_b64 = None  # Reset for next iteration

        # Ask vision to find the element
        result = find_element(img_b64, element_description)
        if result.success and result.elements:
            elem = result.elements[0]
            if elem.get("found"):
                # Try to get coords
                x = elem.get("x")
                y = elem.get("y")
                if x and y:
                    click_result = click(x, y)
                    if click_result.success:
                        return BrowserResult(
                            True,
                            f"Found and clicked '{element_description}'",
                            {"x": x, "y": y},
                        )
                else:
                    # Vision found it but no coords — try smart coordinate estimation
                    coords = _estimate_coords_from_position(result.description)
                    if coords:
                        click(coords[0], coords[1])
                        return BrowserResult(
                            True,
                            f"Clicked '{element_description}' (estimated position)",
                            {"x": coords[0], "y": coords[1]},
                        )

        wait(retry_interval)

    return BrowserResult(False, f"Could not find '{element_description}' within {timeout}s")


def wait_for_element(
    element_description: str,
    timeout: float = 15.0,
    check_interval: float = 1.0,
) -> BrowserResult:
    """
    Wait until an element appears on screen.
    Returns when found or times out.
    """
    from kurt.core.computer_use import screenshot as take_screenshot, wait
    from kurt.core.vision import find_element

    start = time.time()
    while time.time() - start < timeout:
        ss = take_screenshot()
        if ss.success:
            result = find_element(ss.data["image_b64"], element_description)
            if result.success and result.elements and result.elements[0].get("found"):
                elapsed = time.time() - start
                return BrowserResult(
                    True,
                    f"'{element_description}' appeared after {elapsed:.1f}s",
                    {"elapsed": elapsed},
                )
        wait(check_interval)

    return BrowserResult(False, f"'{element_description}' did not appear within {timeout}s")


def wait_for_page_load(timeout: float = 15.0) -> BrowserResult:
    """
    Wait for page to finish loading (spinner gone, content visible).
    Uses vision to detect loading state.
    """
    from kurt.core.computer_use import screenshot as take_screenshot, wait
    from kurt.core.vision import detect_ui_state

    start = time.time()
    prev_hash = None

    while time.time() - start < timeout:
        ss = take_screenshot()
        if not ss.success:
            wait(0.5)
            continue

        img_b64 = ss.data["image_b64"]

        # Check for loading indicators via vision
        state = detect_ui_state(img_b64)
        if state.success and state.elements:
            ui = state.elements[0]
            ready = ui.get("READY", "").lower()
            screen_type = ui.get("SCREEN_TYPE", "").lower()

            if ready == "yes" and screen_type != "loading":
                return BrowserResult(True, "Page loaded", {"elapsed": time.time() - start})

        # Also check if screen stopped changing (hash stabilized)
        import hashlib
        current_hash = hashlib.md5(img_b64[:1000].encode()).hexdigest()
        if current_hash == prev_hash:
            # Screen stable for 1 cycle = likely loaded
            return BrowserResult(True, "Page stable (screen stopped changing)")
        prev_hash = current_hash
        wait(1.0)

    return BrowserResult(True, "Timeout — assuming page loaded")  # Optimistic


def scroll_to(
    element_description: str,
    max_scrolls: int = 10,
    scroll_amount: int = 3,
) -> BrowserResult:
    """
    Scroll down until element is visible on screen.
    """
    from kurt.core.computer_use import screenshot as take_screenshot, scroll, wait
    from kurt.core.vision import find_element

    screen_w, screen_h = _get_screen_size()
    cx, cy = screen_w // 2, screen_h // 2

    for i in range(max_scrolls):
        ss = take_screenshot()
        if ss.success:
            result = find_element(ss.data["image_b64"], element_description)
            if result.success and result.elements and result.elements[0].get("found"):
                return BrowserResult(True, f"'{element_description}' is now visible")

        scroll(cx, cy, amount=scroll_amount, direction="down")
        wait(0.5)

    return BrowserResult(False, f"Could not scroll to '{element_description}'")


def fill_form(fields: dict[str, str], tab_between: bool = True) -> BrowserResult:
    """
    Fill form fields by clicking each and typing.
    fields = {"field description": "value to type"}
    Example: {"username field": "myuser", "password field": "mypass"}
    """
    from kurt.core.computer_use import type_text, press_key, wait

    filled = []
    for field_desc, value in fields.items():
        result = find_and_click(field_desc, timeout=5.0)
        if result.success:
            wait(0.2)
            type_text(value)
            filled.append(field_desc)
            if tab_between:
                press_key("tab")
                wait(0.1)
        else:
            logger.warning(f"Could not find field: {field_desc}")

    if filled:
        return BrowserResult(True, f"Filled {len(filled)} fields: {filled}", {"filled": filled})
    return BrowserResult(False, "Could not fill any fields")


def type_in_search(query: str, browser: str = "chrome") -> BrowserResult:
    """
    Click the browser's address bar and search for a query (adds 'search' intent).
    """
    from kurt.core.computer_use import hotkey, type_text, press_key, wait

    shortcuts = BROWSER_SHORTCUTS.get(browser.lower(), BROWSER_SHORTCUTS["chrome"])
    hotkey(*shortcuts["address_bar"])
    wait(0.3)
    type_text(query)
    press_key("enter")
    wait(1.5)
    return BrowserResult(True, f"Searched for: {query}")


def get_page_text(region: str = "") -> BrowserResult:
    """
    Get visible text from the current page using vision OCR.
    region: optional hint like "main content", "navigation", "article"
    """
    from kurt.core.computer_use import screenshot as take_screenshot
    from kurt.core.vision import read_text_on_screen

    ss = take_screenshot()
    if not ss.success:
        return BrowserResult(False, "Screenshot failed")

    result = read_text_on_screen(ss.data["image_b64"], region_hint=region)
    if result.success:
        return BrowserResult(True, result.description, {"text": result.description})
    return BrowserResult(False, result.error)


def take_page_screenshot(save_path: Optional[str] = None) -> BrowserResult:
    """Take a screenshot of the current browser page"""
    from kurt.core.computer_use import screenshot as take_screenshot

    result = take_screenshot(save_path=save_path)
    if result.success:
        return BrowserResult(True, "Screenshot taken", result.data)
    return BrowserResult(False, result.message)


# ─────────────────────────────────────────────────────────────
# High-level browser tasks
# ─────────────────────────────────────────────────────────────

def browse_to(url: str, browser: str = "chrome", wait_load: bool = True) -> BrowserResult:
    """
    Full navigate: open browser → go to URL → wait for load.
    One-liner for common usage.
    """
    result = navigate(url, browser=browser)
    if not result.success:
        return result
    if wait_load:
        wait_for_page_load(timeout=10.0)
    return result


def search_web(query: str, engine: str = "google", browser: str = "chrome") -> BrowserResult:
    """
    Search the web for a query.
    engine: 'google'|'bing'|'duckduckgo'|'youtube'
    """
    engines = {
        "google": f"https://www.google.com/search?q={query.replace(' ', '+')}",
        "bing": f"https://www.bing.com/search?q={query.replace(' ', '+')}",
        "duckduckgo": f"https://duckduckgo.com/?q={query.replace(' ', '+')}",
        "youtube": f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}",
    }
    url = engines.get(engine.lower(), engines["google"])
    return browse_to(url, browser=browser)


def watch_video(url: str, browser: str = "chrome") -> BrowserResult:
    """
    Open a video URL and auto-play.
    Works with YouTube, Netflix, Vimeo, etc.
    """
    result = browse_to(url, browser=browser, wait_load=True)
    if not result.success:
        return result

    # Try to click play if not auto-playing
    from kurt.core.computer_use import wait
    wait(2.0)

    # Check if there's a play button
    play_result = find_and_click("play button", timeout=3.0)
    if play_result.success:
        return BrowserResult(True, "Video playing", {"url": url})

    return BrowserResult(True, "Video page opened (may be auto-playing)", {"url": url})


def login_to(
    site_url: str,
    username: str,
    password: str,
    browser: str = "chrome",
    username_field: str = "username or email field",
    password_field: str = "password field",
    submit_button: str = "login or sign in button",
) -> BrowserResult:
    """
    Log in to a website.
    Navigates to URL, fills credentials, submits form.
    """
    # Navigate
    result = browse_to(site_url, browser=browser)
    if not result.success:
        return result

    # Fill credentials
    fill_result = fill_form({
        username_field: username,
        password_field: password,
    }, tab_between=True)

    if not fill_result.success:
        return BrowserResult(False, f"Could not fill login form: {fill_result.message}")

    # Submit
    click_result = find_and_click(submit_button, timeout=5.0)
    if not click_result.success:
        # Try pressing Enter instead
        from kurt.core.computer_use import press_key
        press_key("enter")

    from kurt.core.computer_use import wait
    wait(2.0)
    return BrowserResult(True, f"Login submitted to {site_url}")


# ─────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────

def _get_screen_size() -> tuple[int, int]:
    """Get screen dimensions"""
    try:
        import pyautogui
        return pyautogui.size()
    except Exception:
        return 1920, 1080  # Fallback


def _estimate_coords_from_position(description: str) -> Optional[tuple[int, int]]:
    """
    Map position descriptions to approximate screen coordinates.
    e.g. "top-center" → (960, 50), "center" → (960, 540)
    """
    w, h = _get_screen_size()
    desc = description.lower()

    positions = {
        "top-left": (w * 0.1, h * 0.1),
        "top-center": (w * 0.5, h * 0.1),
        "top-right": (w * 0.9, h * 0.1),
        "middle-left": (w * 0.1, h * 0.5),
        "center": (w * 0.5, h * 0.5),
        "middle-right": (w * 0.9, h * 0.5),
        "bottom-left": (w * 0.1, h * 0.9),
        "bottom-center": (w * 0.5, h * 0.9),
        "bottom-right": (w * 0.9, h * 0.9),
    }

    for pos_name, coords in positions.items():
        if pos_name in desc:
            return int(coords[0]), int(coords[1])
    return None


def auto_retry(func, max_retries: int = 3, delay: float = 1.0):
    """
    Decorator/wrapper: retry a browser action on failure.
    Usage: result = auto_retry(lambda: find_and_click("Submit"), max_retries=3)
    """
    for attempt in range(max_retries):
        try:
            result = func()
            if result and result.success:
                return result
            if attempt < max_retries - 1:
                time.sleep(delay)
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
    return BrowserResult(False, f"Failed after {max_retries} attempts")


def get_active_browser() -> str:
    """Try to detect which browser is currently active/focused"""
    from kurt.core.computer_use import get_active_window
    result = get_active_window()
    if result.success:
        win = result.data.get("window", "").lower()
        for browser in ["chrome", "safari", "firefox", "arc", "brave", "edge"]:
            if browser in win:
                return browser
    return "chrome"  # Default assumption
