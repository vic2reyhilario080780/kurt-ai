"""
KURT v3.0 — Local Vision Engine
Kurt "sees" the screen using local vision models via Ollama.
No internet required. No Claude API needed for basic vision tasks.

Supported models (auto-detected):
  - llava:7b          (best balance — recommended)
  - llava:13b         (more accurate, needs more RAM)
  - moondream         (fastest, lightest — good for simple UI tasks)
  - llava-llama3      (best accuracy if available)
"""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Default vision model — can be overridden
DEFAULT_VISION_MODEL = "llava"
OLLAMA_BASE_URL = "http://localhost:11434"


# ─────────────────────────────────────────────────────────────
# Result types
# ─────────────────────────────────────────────────────────────

@dataclass
class VisionResult:
    success: bool
    description: str = ""
    elements: list[dict] = field(default_factory=list)
    raw: str = ""
    model_used: str = ""
    error: str = ""

    def __bool__(self):
        return self.success


# ─────────────────────────────────────────────────────────────
# Ollama client (local, no API key)
# ─────────────────────────────────────────────────────────────

def _ollama_vision(
    image_b64: str,
    prompt: str,
    model: str = DEFAULT_VISION_MODEL,
    timeout: int = 60,
) -> str:
    """Send image + prompt to local Ollama vision model"""
    import urllib.request
    import urllib.error

    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return data.get("response", "")
    except urllib.error.URLError as e:
        raise ConnectionError(
            f"Ollama not running. Start it with: ollama serve\nError: {e}"
        )


def _ollama_available() -> bool:
    """Check if Ollama is running locally"""
    import urllib.request
    try:
        urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        return True
    except Exception:
        return False


def _get_available_vision_models() -> list[str]:
    """List vision models installed in Ollama"""
    import urllib.request
    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=5) as resp:
            data = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
            vision_keywords = ["llava", "moondream", "vision", "bakllava"]
            return [m for m in models if any(k in m.lower() for k in vision_keywords)]
    except Exception:
        return []


def _best_vision_model() -> str:
    """Return best available vision model, falling back to default"""
    available = _get_available_vision_models()
    priority = ["llava-llama3", "llava:13b", "llava:7b", "llava", "moondream"]
    for preferred in priority:
        for installed in available:
            if preferred in installed:
                return installed
    return available[0] if available else DEFAULT_VISION_MODEL


# ─────────────────────────────────────────────────────────────
# Core vision functions
# ─────────────────────────────────────────────────────────────

def describe_screen(image_b64: str, model: Optional[str] = None) -> VisionResult:
    """
    Get a general description of what's on screen.
    Good for: understanding current context before acting.
    """
    model = model or _best_vision_model()
    prompt = (
        "Describe what you see on this computer screen. "
        "Include: what application is open, what content is visible, "
        "any buttons or interactive elements, and what the user might be doing. "
        "Be specific and concise."
    )
    try:
        response = _ollama_vision(image_b64, prompt, model)
        return VisionResult(
            success=True,
            description=response,
            raw=response,
            model_used=model,
        )
    except Exception as e:
        return VisionResult(success=False, error=str(e))


def find_element(image_b64: str, element_description: str, model: Optional[str] = None) -> VisionResult:
    """
    Find a UI element on screen and get its approximate coordinates.
    element_description: e.g. "New Playlist button", "search bar", "close button"
    """
    model = model or _best_vision_model()
    prompt = (
        f"I need to find: '{element_description}' on this screen.\n"
        "If you can see it, tell me:\n"
        "1. Whether it exists (yes/no)\n"
        "2. Its approximate position described as: top-left, top-center, top-right, "
        "middle-left, center, middle-right, bottom-left, bottom-center, bottom-right\n"
        "3. Any nearby landmarks to help locate it\n"
        "4. If you can estimate pixel coordinates (x, y) based on screen size, do so.\n"
        "Format: FOUND: yes/no | POSITION: <position> | COORDS: x,y (if estimable) | NOTES: <details>"
    )
    try:
        response = _ollama_vision(image_b64, prompt, model)

        # Parse structured response
        elements = []
        found = "yes" in response.lower()[:100]
        if found:
            elements.append({
                "description": element_description,
                "found": True,
                "raw_location": response,
            })
            # Try to extract coords if model provided them
            coords = _extract_coords(response)
            if coords:
                elements[0]["x"] = coords[0]
                elements[0]["y"] = coords[1]

        return VisionResult(
            success=True,
            description=response,
            elements=elements,
            raw=response,
            model_used=model,
        )
    except Exception as e:
        return VisionResult(success=False, error=str(e))


def read_text_on_screen(image_b64: str, region_hint: str = "", model: Optional[str] = None) -> VisionResult:
    """
    Read and extract text visible on screen.
    region_hint: optional hint like "top bar", "notification area", "dialog box"
    """
    model = model or _best_vision_model()
    region_part = f" Focus on the {region_hint}." if region_hint else ""
    prompt = (
        f"Read and extract all visible text from this screen.{region_part} "
        "List the text exactly as it appears, maintaining structure where possible."
    )
    try:
        response = _ollama_vision(image_b64, prompt, model)
        return VisionResult(
            success=True,
            description=response,
            raw=response,
            model_used=model,
        )
    except Exception as e:
        return VisionResult(success=False, error=str(e))


def understand_context(image_b64: str, task: str, model: Optional[str] = None) -> VisionResult:
    """
    Understand screen context relative to a task Kurt is trying to perform.
    task: what Kurt is trying to do, e.g. "create a Spotify playlist"
    """
    model = model or _best_vision_model()
    prompt = (
        f"I'm trying to: {task}\n\n"
        "Looking at this screen:\n"
        "1. What is currently open/visible?\n"
        "2. What is the current state? (e.g., app is on home screen, search bar is focused, etc.)\n"
        "3. What is the NEXT action I should take to accomplish my task?\n"
        "4. Is there anything blocking progress? (error, loading, wrong screen?)\n"
        "Be direct and actionable. Format: STATE: <state> | NEXT_ACTION: <action> | BLOCKING: yes/no | DETAILS: <details>"
    )
    try:
        response = _ollama_vision(image_b64, prompt, model)
        return VisionResult(
            success=True,
            description=response,
            raw=response,
            model_used=model,
        )
    except Exception as e:
        return VisionResult(success=False, error=str(e))


def verify_action_done(image_b64: str, expected_result: str, model: Optional[str] = None) -> VisionResult:
    """
    After performing an action, verify it worked by looking at the screen.
    expected_result: e.g. "Spotify playlist was created", "browser navigated to google.com"
    """
    model = model or _best_vision_model()
    prompt = (
        f"I just performed an action. The expected result was: '{expected_result}'\n"
        "Looking at this screen:\n"
        "1. Did the action succeed? (yes/no/partial)\n"
        "2. What evidence do you see?\n"
        "3. If it failed or is incomplete, what do you see instead?\n"
        "Format: SUCCESS: yes/no/partial | EVIDENCE: <what you see> | ISSUE: <if any>"
    )
    try:
        response = _ollama_vision(image_b64, prompt, model)
        success_indicators = ["success: yes", "succeeded", "completed", "created", "done"]
        verified = any(ind in response.lower() for ind in success_indicators)
        return VisionResult(
            success=True,
            description=response,
            raw=response,
            model_used=model,
            elements=[{"verified": verified}],
        )
    except Exception as e:
        return VisionResult(success=False, error=str(e))


def detect_ui_state(image_b64: str, model: Optional[str] = None) -> VisionResult:
    """
    Detect the current UI state — useful for decision making in loops.
    Returns structured state info.
    """
    model = model or _best_vision_model()
    prompt = (
        "Analyze this screen and return a structured state report:\n"
        "APP: <name of main application visible>\n"
        "SCREEN_TYPE: <home/settings/dialog/loading/error/content/login/other>\n"
        "INTERACTIVE_ELEMENTS: <list key buttons/inputs visible>\n"
        "ALERTS: <any popups, errors, notifications visible>\n"
        "READY: <yes if screen is stable and ready for input, no if loading>\n"
        "Be brief. Each field on its own line."
    )
    try:
        response = _ollama_vision(image_b64, prompt, model)

        # Parse key fields
        state = {}
        for line in response.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                state[key.strip().upper()] = val.strip()

        return VisionResult(
            success=True,
            description=response,
            elements=[state],
            raw=response,
            model_used=model,
        )
    except Exception as e:
        return VisionResult(success=False, error=str(e))


def load_image_b64(path: str) -> str:
    """Read an arbitrary image file from disk and return it base64-encoded."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def answer_about_image(image_b64: str, question: str, model: Optional[str] = None) -> VisionResult:
    """
    Answer an arbitrary free-form question about an existing image (not a live
    screen capture) — e.g. a saved screenshot, a photo, a downloaded picture.
    """
    model = model or _best_vision_model()
    prompt = question.strip() or "Describe what you see in this image."
    try:
        response = _ollama_vision(image_b64, prompt, model)
        return VisionResult(success=True, description=response, raw=response, model_used=model)
    except Exception as e:
        return VisionResult(success=False, error=str(e))


# ─────────────────────────────────────────────────────────────
# Claude Vision fallback (when Ollama not available)
# ─────────────────────────────────────────────────────────────

def describe_screen_claude(image_b64: str, prompt: str = "") -> VisionResult:
    """
    Fallback: use Claude API for vision when Ollama is not available.
    Requires ANTHROPIC_API_KEY in environment.
    """
    import os
    if os.environ.get("KURT_ALLOW_CLOUD_VISION") != "1":
        return VisionResult(success=False, error="Cloud vision is disabled. Use local Ollama, or explicitly enable KURT_ALLOW_CLOUD_VISION=1.")
    try:
        import anthropic
        client = anthropic.Anthropic()

        default_prompt = (
            "Describe what you see on this computer screen. "
            "Include what app is open, visible content, and interactive elements."
        )

        message = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": prompt or default_prompt},
                ],
            }],
        )
        response = message.content[0].text
        return VisionResult(
            success=True,
            description=response,
            raw=response,
            model_used="claude-3-5-haiku",
        )
    except Exception as e:
        return VisionResult(success=False, error=str(e))


# ─────────────────────────────────────────────────────────────
# Smart vision router — tries local first, falls back to Claude
# ─────────────────────────────────────────────────────────────

def smart_vision(image_b64: str, prompt: str, prefer_local: bool = True, allow_cloud: bool = True) -> VisionResult:
    """
    Smart vision: use local Ollama if available, else Claude API.
    prefer_local=True: always try Ollama first
    prefer_local=False: use Claude directly
    """
    if prefer_local and _ollama_available():
        model = _best_vision_model()
        try:
            response = _ollama_vision(image_b64, prompt, model)
            return VisionResult(
                success=True,
                description=response,
                raw=response,
                model_used=model,
            )
        except Exception as e:
            logger.warning(f"Local vision failed, falling back to Claude: {e}")

    if not allow_cloud:
        return VisionResult(success=False, error="Local vision unavailable; cloud fallback is disabled for this request.")
    # Fallback to Claude (requires explicit environment opt-in as well).
    return describe_screen_claude(image_b64, prompt)


# ─────────────────────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────────────────────

def _extract_coords(text: str) -> Optional[tuple[int, int]]:
    """Try to extract x,y coordinates from model response"""
    import re
    # Look for patterns like "COORDS: 450, 230" or "(450, 230)" or "x=450 y=230"
    patterns = [
        r"COORDS:\s*(\d+)[,\s]+(\d+)",
        r"\((\d+)[,\s]+(\d+)\)",
        r"x[=:]\s*(\d+)[,\s]+y[=:]\s*(\d+)",
        r"(\d{3,4})[,\s]+(\d{3,4})",  # 3-4 digit numbers = likely pixel coords
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(2))
    return None


def get_vision_status() -> dict:
    """Return status of vision capabilities"""
    ollama_up = _ollama_available()
    models = _get_available_vision_models() if ollama_up else []

    has_anthropic = False
    try:
        import anthropic  # noqa
        import os
        has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    except ImportError:
        pass

    return {
        "ollama_running": ollama_up,
        "vision_models": models,
        "best_local_model": _best_vision_model() if models else None,
        "claude_api_available": has_anthropic,
        "can_see": ollama_up or has_anthropic,
    }


def install_vision_model(model: str = "llava") -> dict:
    """Pull a vision model via Ollama"""
    import subprocess
    result = subprocess.run(
        ["ollama", "pull", model],
        capture_output=True, text=True
    )
    return {
        "success": result.returncode == 0,
        "output": result.stdout or result.stderr,
        "model": model,
    }
