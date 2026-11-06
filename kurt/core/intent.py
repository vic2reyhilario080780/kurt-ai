"""
KURT — Smart Intent Detection
Automatically figures out what the user wants without needing /commands.

Just type naturally:
  "buksan mo ang spotify"       → task: open_app(Spotify)
  "ano ang weather ngayon?"     → search: weather
  "kumusta ka?"                 → chat
  "ano yung ginawa natin kahapon?" → memory lookup

Detection layers (fastest to slowest):
  1. Keyword rules     — instant, no model needed
  2. Pattern matching  — regex-based, handles Filipino/Taglish
  3. Local LLM         — Ollama (llama3/mistral) for ambiguous cases
  4. Fallback          — treat as chat if unsure
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Intent types
# ─────────────────────────────────────────────────────────────

INTENT_CHAT    = "chat"      # Tanong, chika, conversation
INTENT_TASK    = "task"      # May gagawin si KURT
INTENT_SEARCH  = "search"    # Hanapin impormasyon
INTENT_MEMORY  = "memory"    # Tungkol sa nakaraan / preferences
INTENT_SYSTEM  = "system"    # KURT settings, status, help


@dataclass
class Intent:
    type: str                        # INTENT_* constant
    confidence: float                # 0.0 – 1.0
    action: str = ""                 # e.g. "open_app", "search_web", "navigate"
    target: str = ""                 # e.g. "Spotify", "youtube.com", "lofi music"
    params: dict = field(default_factory=dict)
    raw_input: str = ""
    detected_by: str = ""            # "keywords" | "patterns" | "llm" | "fallback"

    def __str__(self):
        if self.target:
            return f"[{self.type}] {self.action}({self.target}) — {self.confidence:.0%} via {self.detected_by}"
        return f"[{self.type}] {self.action} — {self.confidence:.0%} via {self.detected_by}"


# ─────────────────────────────────────────────────────────────
# Layer 1 — Keyword rules (instant)
# ─────────────────────────────────────────────────────────────

# Task trigger words (Filipino + English)
TASK_TRIGGERS = [
    # Open / launch
    "buksan", "bukas", "open", "launch", "start", "i-open", "palakasin",
    "i-start", "patakbuhin", "i-launch",
    # Close
    "isara", "close", "quit", "exit", "i-close", "isara mo",
    # Navigate / browse
    "punta", "pumunta", "go to", "navigate", "browse", "buksan ang browser",
    "i-browse", "tingnan", "bisitahin",
    # Play / media
    "i-play", "play", "i-pause", "pause", "stop", "next", "previous",
    "i-next", "i-pause", "volume", "louder", "softer", "mute",
    # Screenshot / screen
    "screenshot", "kunan ng screenshot", "i-screenshot", "i-capture",
    # Type / write
    "i-type", "type", "isulat", "i-paste", "paste", "i-copy", "copy",
    # Click
    "i-click", "click", "pindutin", "press",
    # Scroll
    "i-scroll", "scroll", "pababa", "pataas",
    # Search (as action)
    "hanapin", "i-search", "maghanap",
    # Create / make
    "gumawa", "lumikha", "create", "make", "baguhin", "i-create",
    # Download
    "i-download", "download", "i-save", "save",
    # Send
    "i-send", "send", "ipadala", "magpadala",
    # Set / change
    "baguhin", "palitan", "i-set", "set", "i-change", "change",
    # Volume / brightness
    "volume", "brightness", "liwanag", "lakas",
]

# Search trigger words
SEARCH_TRIGGERS = [
    "ano", "anong", "paano", "bakit", "kailan", "saan", "sino", "ilan",
    "what", "how", "why", "when", "where", "who", "which",
    "what is", "what are", "how to", "tell me", "explain",
    "weather", "panahon", "balita", "news", "presyo", "price",
    "maghanap ng", "search for", "look up", "find info",
    "i-google", "google mo", "i-check",
]

# Memory trigger words
MEMORY_TRIGGERS = [
    "tandaan", "alalahanin", "nakaraan", "dati", "kahapon", "kanina",
    "remember", "recall", "last time", "before", "previously",
    "ano yung ginawa", "ano ang ginawa", "kelan tayo", "noong",
    "i-save", "itago", "huwag kalimutan", "note",
    "preference", "gusto ko", "ayaw ko", "settings",
    "history", "kasaysayan",
]

# System trigger words
SYSTEM_TRIGGERS = [
    "kurt", "help", "tulong", "status", "version", "settings",
    "i-restart", "restart kurt", "stop kurt", "quit kurt",
    "what can you do", "ano kaya mo", "commands", "commands mo",
    "i-update", "update kurt",
]

# Chat indicators (questions/statements that are clearly conversation)
CHAT_INDICATORS = [
    "kumusta", "kamusta", "hello", "hi", "hey", "magandang",
    "good morning", "good evening", "good night", "magandang umaga",
    "salamat", "thank", "thanks", "maraming salamat",
    "ok", "sige", "oo", "hindi", "nope", "yep", "sure",
    "haha", "hehe", "lol", "😂", "😊",
    "palagay mo", "sa tingin mo", "ano menuhin mo",
    "ikaw ba", "pwede ba", "totoo ba",
]


def _keyword_detect(text: str) -> Optional[Intent]:
    """Fast keyword-based intent detection"""
    t = text.lower().strip()
    words = t.split()

    # Check system first (highest priority)
    for trigger in SYSTEM_TRIGGERS:
        if trigger in t and len(words) <= 4:
            return Intent(
                type=INTENT_SYSTEM,
                confidence=0.85,
                action="system",
                raw_input=text,
                detected_by="keywords",
            )

    # Memory check
    for trigger in MEMORY_TRIGGERS:
        if trigger in t:
            return Intent(
                type=INTENT_MEMORY,
                confidence=0.80,
                action="memory_lookup",
                raw_input=text,
                detected_by="keywords",
            )

    # Task check — look for action verbs
    for trigger in TASK_TRIGGERS:
        if trigger in t:
            # Try to extract target
            target = _extract_target_after(t, trigger)
            action = _map_trigger_to_action(trigger)
            return Intent(
                type=INTENT_TASK,
                confidence=0.88,
                action=action,
                target=target,
                raw_input=text,
                detected_by="keywords",
            )

    # Search check — question words
    for trigger in SEARCH_TRIGGERS:
        if t.startswith(trigger) or f" {trigger} " in t:
            return Intent(
                type=INTENT_SEARCH,
                confidence=0.82,
                action="search",
                target=text,
                raw_input=text,
                detected_by="keywords",
            )

    # Chat indicators
    for trigger in CHAT_INDICATORS:
        if trigger in t:
            return Intent(
                type=INTENT_CHAT,
                confidence=0.80,
                action="chat",
                raw_input=text,
                detected_by="keywords",
            )

    return None


# ─────────────────────────────────────────────────────────────
# Layer 2 — Pattern matching (Taglish-aware regex)
# ─────────────────────────────────────────────────────────────

# (pattern, intent_type, action, target_group)
PATTERNS = [
    # Open app: "buksan ang Spotify", "open Spotify", "pa open naman ng apple music"
    # Stops at "sa", "para", "in my", "sa aking", etc. to avoid grabbing extra words
    (r"(?:pa\s+)?(?:buksan|open|launch|i-open|i-launch|start)\s+(?:(?:naman|mo|po|nga)\s+)?(?:(?:ang|ng|si)\s+)?([\w\s]+?)(?:\s+(?:sa|para|in|on|using|via|sa\s+aking|sa\s+iyong|sa\s+browser|sa\s+phone|ngayon|na|please|pls)\b.*)?$",
     INTENT_TASK, "open_app", 1),

    # Navigate: "punta sa youtube.com", "go to netflix.com", "buksan ang google.com"
    (r"(?:punta|pumunta|go to|navigate to|browse to|bisitahin)\s+(?:sa\s+|ang\s+)?(\S+(?:\.\S+)+)",
     INTENT_TASK, "navigate", 1),

    # Play: "i-play ang lofi", "play Spotify", "palarugin ang Netflix"
    (r"(?:i-play|play|palarugin|words)\s+(?:ang\s+|mo\s+)?(.+)",
     INTENT_TASK, "play", 1),

    # Search web: "i-search ang lofi music", "hanapin ang weather sa Manila"
    (r"(?:i-search|hanapin|maghanap|search for|look up)\s+(?:ang\s+|ng\s+)?(.+)",
     INTENT_TASK, "search_web", 1),

    # Screenshot: "kunan ng screenshot", "screenshot ng screen"
    (r"(?:kunan ng screenshot|take screenshot|i-screenshot|screenshot)",
     INTENT_TASK, "screenshot", 0),

    # Volume: "taasan ang volume", "bababin ang volume", "mute"
    (r"(?:taasan|bababin|i-mute|mute|louder|softer|volume up|volume down)\s*(?:ang\s+)?(?:volume)?",
     INTENT_TASK, "volume", 0),

    # Type: "i-type ang 'hello world'"
    (r"(?:i-type|type|isulat)\s+(?:ang\s+|mo\s+)?['\"]?(.+)['\"]?",
     INTENT_TASK, "type_text", 1),

    # Close: "isara ang Chrome", "close Spotify"
    (r"(?:isara|close|quit|exit|i-close)\s+(?:ang\s+|mo\s+)?(.+)",
     INTENT_TASK, "close_app", 1),

    # What is: "ano ang capital ng Pilipinas"
    (r"(?:ano(?:ng)?|what(?:'s| is| are)?)\s+(?:ang\s+|the\s+)?(.+)",
     INTENT_SEARCH, "search", 1),

    # How to: "paano mag-install ng python"
    (r"(?:paano|how to|how do(?:es)?|how can)\s+(.+)",
     INTENT_SEARCH, "search", 1),

    # Remember: "tandaan mo na gusto ko ng dark mode"
    (r"(?:tandaan|remember|i-save|itago|note)\s+(?:mo\s+)?(?:na\s+)?(.+)",
     INTENT_MEMORY, "remember", 1),

    # Weather
    (r"(?:weather|panahon|ulan|init|malamig)\s*(?:ngayon|today|sa\s+\w+)?",
     INTENT_SEARCH, "search_weather", 0),
]

_compiled_patterns = [(re.compile(p, re.IGNORECASE), t, a, g) for p, t, a, g in PATTERNS]


def _pattern_detect(text: str) -> Optional[Intent]:
    """Regex pattern-based intent detection"""
    for pattern, intent_type, action, target_group in _compiled_patterns:
        match = pattern.search(text)
        if match:
            target = ""
            if target_group > 0:
                try:
                    target = match.group(target_group).strip()
                    # Clean up common Filipino particles (prefix)
                    target = re.sub(r'^(ang|ng|sa|mo|ko|niya|natin|naman|po)\s+', '', target, flags=re.IGNORECASE)
                    # Strip trailing particles and phrases
                    target = re.sub(r'\s+(naman|po|nga|daw|raw|pala|na|lang|lamang)$', '', target, flags=re.IGNORECASE)
                    # Strip "sa X", "sa aking X", "sa browser/phone/pc" at the end
                    target = re.sub(r'\s+sa\s+(aking|iyong|browser|phone|pc|laptop|computer|iMac|Mac).*$', '', target, flags=re.IGNORECASE)
                    target = target.strip()
                except IndexError:
                    pass

            return Intent(
                type=intent_type,
                confidence=0.85,
                action=action,
                target=target,
                raw_input=text,
                detected_by="patterns",
            )
    return None


# ─────────────────────────────────────────────────────────────
# Layer 3 — Local LLM (Ollama) for ambiguous cases
# ─────────────────────────────────────────────────────────────

def _llm_detect(text: str) -> Optional[Intent]:
    """
    Use local Ollama LLM for ambiguous intent classification.
    Only called when keywords + patterns both fail.
    """
    import urllib.request
    import json

    prompt = f"""Classify this user message into one of these intents:
- task: user wants KURT to DO something (open app, click, type, play music, navigate browser)
- search: user wants information (questions, facts, weather, news)
- chat: casual conversation, greeting, opinion, feelings
- memory: user refers to past interactions or wants to save/recall something
- system: about KURT itself (settings, help, status)

User message: "{text}"

Reply with ONLY a JSON object like:
{{"intent": "task", "confidence": 0.9, "action": "open_app", "target": "Spotify"}}

For chat/search with no specific action, use "" for action and target."""

    try:
        payload = json.dumps({
            "model": "llama3",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 100},
        }).encode()

        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            response_text = data.get("response", "").strip()

            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return Intent(
                    type=result.get("intent", INTENT_CHAT),
                    confidence=float(result.get("confidence", 0.75)),
                    action=result.get("action", ""),
                    target=result.get("target", ""),
                    raw_input=text,
                    detected_by="llm",
                )
    except Exception as e:
        logger.debug(f"LLM intent detection failed: {e}")

    # Try mistral as fallback model
    try:
        payload = json.dumps({
            "model": "mistral",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 100},
        }).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            response_text = data.get("response", "").strip()
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return Intent(
                    type=result.get("intent", INTENT_CHAT),
                    confidence=float(result.get("confidence", 0.70)),
                    action=result.get("action", ""),
                    target=result.get("target", ""),
                    raw_input=text,
                    detected_by="llm",
                )
    except Exception:
        pass

    return None


# ─────────────────────────────────────────────────────────────
# Main detector — combines all layers
# ─────────────────────────────────────────────────────────────

def detect_intent(
    text: str,
    use_llm: bool = True,
    min_confidence: float = 0.60,
) -> Intent:
    """
    Detect user intent from natural language input.
    Tries keyword rules → patterns → LLM → fallback to chat.

    Args:
        text: User's raw input
        use_llm: Whether to use local Ollama LLM for ambiguous cases
        min_confidence: Minimum confidence threshold

    Returns:
        Intent object with type, action, target, confidence
    """
    if not text or not text.strip():
        return Intent(INTENT_CHAT, 1.0, "chat", raw_input=text, detected_by="empty")

    text = text.strip()

    # Layer 1: Keywords (fastest)
    intent = _keyword_detect(text)
    if intent and intent.confidence >= min_confidence:
        logger.debug(f"Intent (keywords): {intent}")
        return intent

    # Layer 2: Patterns
    intent = _pattern_detect(text)
    if intent and intent.confidence >= min_confidence:
        logger.debug(f"Intent (patterns): {intent}")
        return intent

    # Layer 3: Local LLM (only for ambiguous)
    if use_llm:
        intent = _llm_detect(text)
        if intent and intent.confidence >= min_confidence:
            logger.debug(f"Intent (LLM): {intent}")
            return intent

    # Fallback: treat as chat
    logger.debug(f"Intent (fallback→chat): '{text}'")
    return Intent(
        type=INTENT_CHAT,
        confidence=0.60,
        action="chat",
        raw_input=text,
        detected_by="fallback",
    )


# ─────────────────────────────────────────────────────────────
# Intent Router — connects intent to KURT actions
# ─────────────────────────────────────────────────────────────

def route_intent(intent: Intent) -> dict:
    """
    Given a detected intent, return what KURT should do.
    Returns a dict with 'handler' and 'kwargs'.
    """
    if intent.type == INTENT_TASK:
        return _route_task(intent)
    elif intent.type == INTENT_SEARCH:
        return {"handler": "search", "kwargs": {"query": intent.target or intent.raw_input}}
    elif intent.type == INTENT_MEMORY:
        return {"handler": "memory", "kwargs": {"query": intent.target or intent.raw_input, "action": intent.action}}
    elif intent.type == INTENT_SYSTEM:
        return {"handler": "system", "kwargs": {"action": intent.action}}
    else:  # INTENT_CHAT
        return {"handler": "chat", "kwargs": {"message": intent.raw_input}}


def _route_task(intent: Intent) -> dict:
    """Route task intents to specific handlers"""
    action = intent.action
    target = intent.target

    routing = {
        "open_app":    {"handler": "computer.open_app",    "kwargs": {"app_name": target}},
        "close_app":   {"handler": "computer.close_app",   "kwargs": {"app_name": target}},
        "navigate":    {"handler": "browser.navigate",     "kwargs": {"url": target}},
        "search_web":  {"handler": "browser.search_web",   "kwargs": {"query": target}},
        "play":        {"handler": "computer.open_app",    "kwargs": {"app_name": target}},
        "screenshot":  {"handler": "computer.screenshot",  "kwargs": {}},
        "type_text":   {"handler": "computer.type_text",   "kwargs": {"text": target}},
        "volume":      {"handler": "computer.volume",      "kwargs": {"direction": target}},
        "search_weather": {"handler": "search",            "kwargs": {"query": f"weather {target}"}},
    }

    return routing.get(action, {
        "handler": "chat",
        "kwargs": {"message": intent.raw_input},
    })


# ─────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────

def _extract_target_after(text: str, trigger: str) -> str:
    """Extract target word(s) after a trigger word"""
    idx = text.lower().find(trigger.lower())
    if idx == -1:
        return ""
    after = text[idx + len(trigger):].strip()
    # Remove Filipino particles
    after = re.sub(r'^(ang|ng|sa|mo|ko|niya|natin|yung|yong|si)\s+', '', after, flags=re.IGNORECASE)
    # Take first meaningful chunk (up to comma or period)
    after = re.split(r'[,.]', after)[0].strip()
    return after


def _map_trigger_to_action(trigger: str) -> str:
    """Map trigger word to KURT action name"""
    open_words = ["buksan", "bukas", "open", "launch", "start", "i-open", "i-launch", "i-start", "patakbuhin"]
    close_words = ["isara", "close", "quit", "exit", "i-close"]
    play_words = ["i-play", "play", "palarugin"]
    search_words = ["hanapin", "i-search", "maghanap"]
    nav_words = ["punta", "pumunta", "go to", "navigate", "browse", "bisitahin"]
    screenshot_words = ["screenshot", "i-screenshot", "kunan ng screenshot", "i-capture"]
    type_words = ["i-type", "type", "isulat"]
    scroll_words = ["i-scroll", "scroll", "pababa", "pataas"]
    click_words = ["i-click", "click", "pindutin", "press"]

    t = trigger.lower()
    if any(w in t for w in open_words):   return "open_app"
    if any(w in t for w in close_words):  return "close_app"
    if any(w in t for w in play_words):   return "play"
    if any(w in t for w in search_words): return "search_web"
    if any(w in t for w in nav_words):    return "navigate"
    if any(w in t for w in screenshot_words): return "screenshot"
    if any(w in t for w in type_words):   return "type_text"
    if any(w in t for w in scroll_words): return "scroll"
    if any(w in t for w in click_words):  return "click"
    return "generic_task"


def explain_intent(intent: Intent) -> str:
    """Human-readable explanation of detected intent (for debugging)"""
    lines = [
        f"Input   : \"{intent.raw_input}\"",
        f"Type    : {intent.type}",
        f"Action  : {intent.action or '(none)'}",
        f"Target  : {intent.target or '(none)'}",
        f"Confidence: {intent.confidence:.0%}",
        f"Detected by: {intent.detected_by}",
    ]
    return "\n".join(lines)
