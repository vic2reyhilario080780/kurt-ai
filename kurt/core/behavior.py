"""
KURT v3.0 — Behavior & Diskarte Engine
Defines Kurt's personality, decision-making rules, and survival strategies.

Hindi lang ito system prompt — ito ang "utak" ni Kurt.
Kung paano siya mag-isip, mag-decide, at mag-act.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import platform
import subprocess
import json
import os

OS = platform.system()

# ─────────────────────────────────────────────────────────────
# Kurt's Core Identity
# ─────────────────────────────────────────────────────────────

KURT_NAME = "K.U.R.T."
KURT_FULL_NAME = "Kinetic Unified Response Terminal"
KURT_VERSION = "3.0"
KURT_OWNER = "Daddy Tito"

KURT_PERSONALITY = """
Ikaw si KURT — personal AI assistant ni Daddy Tito sa kanyang iMac.

UGALI MO:
- Matulungin at tapat — kung hindi mo kaya, sabihin mo agad kung bakit at ano ang solusyon
- Marunong mag-Taglish — natural na nakikipag-usap sa Filipino/English mix
- Hindi ka nagse-give up agad — susubukan mo muna lahat ng paraan bago mag-fail
- Mabilis ka kumilos — walang matagal na paliwanag kung kaya mong gawin na agad
- Confident pero humble — alam mo ang limitasyon mo

DISKARTE MO (priority order):
1. Direct command muna — kung may shortcut, gamitin (open -a, AppleScript, shell)
2. Kung hindi gumagana, subukan ang variations (capitalization, full path, process check)
3. Screen vision — kung kailangan talaga ng visual na pag-check
4. Kung lahat failed — sabihin honestly, mag-suggest ng solusyon

BAWAL:
- Mag-fail nang walang explanation
- Mag-ask ng maraming clarification bago kumilos
- Mag-pretend na may nagawa kung wala naman
- Maging makulit sa user kung simpleng tanong lang

DAPAT:
- Kumilos muna, mag-report pagkatapos
- Mag-recover mula sa errors nang mag-isa
- Tandaan ang mga bagay tungkol sa iMac ni Daddy Tito
- Mag-learn mula sa mga failures para hindi na maulit
"""

# ─────────────────────────────────────────────────────────────
# iMac Knowledge Base — Natatandaan ni Kurt ang iMac
# ─────────────────────────────────────────────────────────────

IMAC_KNOWLEDGE_FILE = os.path.expanduser("~/.kurt/imac_knowledge.json")

DEFAULT_IMAC_KNOWLEDGE = {
    "apps_verified": {},        # app_name -> {"path": str, "last_opened": str}
    "apps_failed": {},          # app_name -> {"tried": [...], "reason": str}
    "user_preferences": {},     # key -> value
    "shortcuts_learned": {},    # command -> {"action": str, "success_rate": float}
    "screen_layout": {},        # app_name -> {"common_elements": [...]}
}


def load_imac_knowledge() -> dict:
    """Load Kurt's knowledge about this iMac"""
    try:
        if os.path.exists(IMAC_KNOWLEDGE_FILE):
            with open(IMAC_KNOWLEDGE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return DEFAULT_IMAC_KNOWLEDGE.copy()


def save_imac_knowledge(knowledge: dict) -> None:
    """Save updated iMac knowledge"""
    try:
        os.makedirs(os.path.dirname(IMAC_KNOWLEDGE_FILE), exist_ok=True)
        with open(IMAC_KNOWLEDGE_FILE, "w") as f:
            json.dump(knowledge, f, indent=2)
    except Exception:
        pass


def remember_app_success(app_name: str, working_name: str) -> None:
    """Remember that this app name worked"""
    knowledge = load_imac_knowledge()
    knowledge["apps_verified"][app_name.lower()] = {
        "working_name": working_name,
        "path": f"/Applications/{working_name}.app",
    }
    # Remove from failed if it was there
    knowledge["apps_failed"].pop(app_name.lower(), None)
    save_imac_knowledge(knowledge)


def remember_app_failure(app_name: str, tried_names: list, reason: str) -> None:
    """Remember that this app couldn't be opened and why"""
    knowledge = load_imac_knowledge()
    knowledge["apps_failed"][app_name.lower()] = {
        "tried": tried_names,
        "reason": reason,
    }
    save_imac_knowledge(knowledge)


def get_known_app_name(app_name: str) -> Optional[str]:
    """Check if we already know the working name for this app"""
    knowledge = load_imac_knowledge()
    result = knowledge["apps_verified"].get(app_name.lower())
    if result:
        return result.get("working_name")
    return None


# ─────────────────────────────────────────────────────────────
# App Discovery — Kurt discovers all installed apps
# ─────────────────────────────────────────────────────────────

def discover_installed_apps() -> list[str]:
    """Get list of all installed apps on this Mac"""
    apps = []
    app_dirs = [
        "/Applications",
        "/Applications/Utilities",
        os.path.expanduser("~/Applications"),
        "/System/Applications",
    ]
    for directory in app_dirs:
        try:
            result = subprocess.run(
                ["find", directory, "-maxdepth", "2", "-name", "*.app"],
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.splitlines():
                name = os.path.basename(line).replace(".app", "")
                if name:
                    apps.append(name)
        except Exception:
            pass
    return sorted(set(apps))


def find_app_fuzzy(query: str) -> Optional[str]:
    """Find best matching app name for a fuzzy query"""
    apps = discover_installed_apps()
    query_lower = query.lower()

    # Exact match first
    for app in apps:
        if app.lower() == query_lower:
            return app

    # Starts with
    for app in apps:
        if app.lower().startswith(query_lower):
            return app

    # Contains
    for app in apps:
        if query_lower in app.lower():
            return app

    # Word match (e.g. "music" matches "Apple Music")
    for app in apps:
        words = app.lower().split()
        if any(query_lower in word for word in words):
            return app

    return None


# ─────────────────────────────────────────────────────────────
# Smart App Opener — Kurt's multi-layer strategy
# ─────────────────────────────────────────────────────────────

@dataclass
class OpenAppResult:
    success: bool
    message: str
    method_used: str = ""
    app_name_used: str = ""


def smart_open_app(app_name: str) -> OpenAppResult:
    """
    Kurt's diskarte para magbukas ng app.
    Multi-layer approach — hindi agad nagfe-fail.
    """
    # Layer 0: Check if we already know the working name
    known_name = get_known_app_name(app_name)
    if known_name:
        result = subprocess.run(
            ["open", "-a", known_name],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return OpenAppResult(True, f"Binuksan: {known_name}", "cached", known_name)

    # Layer 1: Try direct open -a with variations
    candidates = _build_app_candidates(app_name)
    tried = []
    for candidate in candidates:
        tried.append(candidate)
        result = subprocess.run(
            ["open", "-a", candidate],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            remember_app_success(app_name, candidate)
            return OpenAppResult(True, f"Binuksan: {candidate}", "open -a", candidate)

    # Layer 2: Check if already running (maybe just hidden)
    running = _check_if_running(app_name)
    if running:
        # Bring to front using AppleScript
        for candidate in candidates:
            script = f'tell application "{candidate}" to activate'
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return OpenAppResult(True, f"Na-activate: {candidate} (nasa background pala)", "applescript", candidate)

    # Layer 3: Fuzzy find from installed apps
    fuzzy_match = find_app_fuzzy(app_name)
    if fuzzy_match:
        result = subprocess.run(
            ["open", "-a", fuzzy_match],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            remember_app_success(app_name, fuzzy_match)
            return OpenAppResult(True, f"Binuksan: {fuzzy_match} (similar sa '{app_name}')", "fuzzy match", fuzzy_match)

    # Layer 4: Try using Spotlight (mdfind)
    spotlight_result = _spotlight_find_app(app_name)
    if spotlight_result:
        result = subprocess.run(
            ["open", spotlight_result],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            app_display = os.path.basename(spotlight_result).replace(".app", "")
            remember_app_success(app_name, app_display)
            return OpenAppResult(True, f"Binuksan: {app_display} (via Spotlight)", "spotlight", app_display)

    # All layers failed
    remember_app_failure(app_name, tried, "Not found after all attempts")

    # Suggest similar apps
    suggestion = fuzzy_match or _suggest_similar(app_name)
    msg = f"Hindi ko mahanap ang '{app_name}'."
    if suggestion:
        msg += f" Ibig mo bang buksan ang '{suggestion}'?"
    else:
        msg += " Naka-install ba ito? I-check mo sa /Applications folder."

    return OpenAppResult(False, msg, "none", "")


def _build_app_candidates(app_name: str) -> list[str]:
    """Build list of name variations to try"""
    candidates = []
    seen = set()

    def add(name):
        if name and name not in seen:
            seen.add(name)
            candidates.append(name)

    add(app_name)
    add(app_name.title())
    add(app_name.capitalize())
    add(app_name.upper())
    # Handle common compound names
    add(" ".join(w.capitalize() for w in app_name.split()))

    return candidates


def _check_if_running(app_name: str) -> bool:
    """Check if app process is running"""
    try:
        result = subprocess.run(
            ["pgrep", "-if", app_name],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def _spotlight_find_app(app_name: str) -> Optional[str]:
    """Use Spotlight (mdfind) to find app by name"""
    try:
        result = subprocess.run(
            ["mdfind", f"kMDItemContentType == 'com.apple.application-bundle' && kMDItemDisplayName == '{app_name}*'"],
            capture_output=True, text=True, timeout=5
        )
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip().endswith(".app")]
        if lines:
            return lines[0]
    except Exception:
        pass
    return None


def _suggest_similar(app_name: str) -> Optional[str]:
    """Suggest a similar app that is installed"""
    apps = discover_installed_apps()
    # Simple Levenshtein-ish: check if most chars match
    query = set(app_name.lower())
    best_match = None
    best_score = 0
    for app in apps:
        app_chars = set(app.lower())
        overlap = len(query & app_chars) / max(len(query), 1)
        if overlap > 0.7 and overlap > best_score:
            best_score = overlap
            best_match = app
    return best_match


# ─────────────────────────────────────────────────────────────
# System Prompt Builder — ang complete na instructions para kay Kurt
# ─────────────────────────────────────────────────────────────

def build_system_prompt(context: Optional[dict] = None) -> str:
    """Build Kurt's full system prompt with personality + current context"""
    knowledge = load_imac_knowledge()

    known_apps = list(knowledge.get("apps_verified", {}).keys())
    known_apps_str = ", ".join(known_apps[:20]) if known_apps else "wala pa"

    context_str = ""
    if context:
        for key, val in context.items():
            context_str += f"\n- {key}: {val}"

    prompt = f"""Ikaw si {KURT_NAME} ({KURT_FULL_NAME}) v{KURT_VERSION}.
Personal AI assistant ni {KURT_OWNER} sa kanyang iMac M4.

{KURT_PERSONALITY}

CURRENT IMAC KNOWLEDGE:
- Known apps (working): {known_apps_str}
- OS: macOS (Darwin)
- Tools available: open -a, osascript, pgrep, mdfind, pyautogui, screenshot

TOOLS MO (gamitin sa tool calls):
- open_app(name) — buksan ang app
- screenshot() — kunan ng screenshot
- click(x, y) — mag-click sa coordinates
- type_text(text) — mag-type
- run_command(cmd) — mag-run ng shell command
- focus_window(app) — i-bring sa front ang app
- search_web(query) — mag-search sa web
- read_file(path) — basahin ang file
- write_file(path, content) — magsulat ng file

CURRENT CONTEXT:{context_str if context_str else " normal conversation"}

RULE #1: Kumilos agad. Huwag magtatanong ng marami kung kaya mong gawin na.
RULE #2: I-report ang ginawa mo pagkatapos, hindi bago.
RULE #3: Kung may error, i-fix mo mismo bago mag-report kay user.
RULE #4: Magsalita ka ng natural na Taglish kasama si Daddy Tito.
"""
    return prompt


# ─────────────────────────────────────────────────────────────
# Decision Engine — kung paano mag-decide si Kurt
# ─────────────────────────────────────────────────────────────

@dataclass
class Decision:
    action: str
    method: str
    confidence: float
    fallback: Optional[str] = None
    reason: str = ""


def decide_how_to_open_app(app_name: str) -> Decision:
    """Kurt decides the best way to open an app"""
    known = get_known_app_name(app_name)

    if known:
        return Decision(
            action="open_app",
            method="open -a (cached)",
            confidence=0.95,
            reason=f"Kilala na natin ito: {known}"
        )

    # Check if it looks like a web app
    web_indicators = ["chrome", "firefox", "safari", "brave", "edge", "browser"]
    if any(w in app_name.lower() for w in web_indicators):
        return Decision(
            action="open_browser",
            method="open -a (browser)",
            confidence=0.9,
            reason="Browser ito"
        )

    return Decision(
        action="open_app",
        method="smart_open_app (multi-layer)",
        confidence=0.75,
        fallback="ask_user_if_installed",
        reason="Di pa natin alam ang exact name nito"
    )
