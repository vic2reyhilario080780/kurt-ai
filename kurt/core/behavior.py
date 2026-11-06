"""
KURT v3.0 — Behavior & Diskarte Engine
Defines Kurt's personality, decision-making rules, and survival strategies.

Hindi lang ito system prompt — ito ang "utak" ni Kurt.
Kung paano siya mag-isip, mag-decide, at mag-act.

Cross-platform: macOS (Darwin), Windows, Linux
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import platform
import subprocess
import json
import os
import shutil

OS = platform.system()   # "Darwin" | "Windows" | "Linux"
IS_MAC     = OS == "Darwin"
IS_WINDOWS = OS == "Windows"
IS_LINUX   = OS == "Linux"

# ─────────────────────────────────────────────────────────────
# Kurt's Core Identity
# ─────────────────────────────────────────────────────────────

KURT_NAME = "K.U.R.T."
KURT_FULL_NAME = "Kinetic Unified Response Terminal"
KURT_VERSION = "3.0"
KURT_OWNER = "Daddy Tito"

KURT_PERSONALITY = """
Ikaw si KURT — personal AI assistant ni Daddy Tito.

UGALI MO:
- Matulungin at tapat — kung hindi mo kaya, sabihin mo agad kung bakit at ano ang solusyon
- Marunong mag-Taglish — natural na nakikipag-usap sa Filipino/English mix
- Hindi ka nagse-give up agad — susubukan mo muna lahat ng paraan bago mag-fail
- Mabilis ka kumilos — walang matagal na paliwanag kung kaya mong gawin na agad
- Confident pero humble — alam mo ang limitasyon mo
- Cross-platform — works sa Mac, Windows, at Linux

DISKARTE MO (priority order):
1. Direct command muna — kung may shortcut, gamitin (open -a sa Mac, start sa Windows, xdg-open sa Linux)
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
- Tandaan ang mga bagay tungkol sa computer ni Daddy Tito
- Mag-learn mula sa mga failures para hindi na maulit
"""

# ─────────────────────────────────────────────────────────────
# iMac Knowledge Base — Natatandaan ni Kurt ang iMac
# ─────────────────────────────────────────────────────────────

KURT_KNOWLEDGE_FILE = os.path.expanduser("~/.kurt/machine_knowledge.json")
IMAC_KNOWLEDGE_FILE = KURT_KNOWLEDGE_FILE  # backward-compat alias

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
    if IS_MAC:
        path_hint = f"/Applications/{working_name}.app"
    elif IS_WINDOWS:
        path_hint = working_name  # Could be exe path or display name
    else:
        path_hint = working_name  # Executable name or .desktop id
    knowledge["apps_verified"][app_name.lower()] = {
        "working_name": working_name,
        "path": path_hint,
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
    """Get list of all installed apps — cross-platform"""
    apps = []

    if IS_MAC:
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

    elif IS_WINDOWS:
        # Read installed apps from common Program Files directories
        prog_dirs = [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            os.path.expanduser(r"~\AppData\Local\Programs"),
            os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs"),
        ]
        for directory in prog_dirs:
            if not directory or not os.path.exists(directory):
                continue
            try:
                for entry in os.scandir(directory):
                    if entry.is_dir():
                        apps.append(entry.name)
                    elif entry.name.lower().endswith(".exe"):
                        apps.append(entry.name[:-4])
            except Exception:
                pass
        # Also check Windows Registry for installed apps
        try:
            import winreg
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
                try:
                    key = winreg.OpenKey(hive, key_path)
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            sub = winreg.OpenKey(key, winreg.EnumKey(key, i))
                            name, _ = winreg.QueryValueEx(sub, "DisplayName")
                            if name:
                                apps.append(str(name))
                        except Exception:
                            pass
                except Exception:
                    pass
        except ImportError:
            pass  # winreg only available on Windows

    else:  # Linux
        # Check common app directories
        linux_dirs = [
            "/usr/share/applications",
            "/usr/local/share/applications",
            os.path.expanduser("~/.local/share/applications"),
            "/var/lib/flatpak/exports/share/applications",
            os.path.expanduser("~/.local/share/flatpak/exports/share/applications"),
        ]
        for directory in linux_dirs:
            if not os.path.exists(directory):
                continue
            try:
                for f in os.listdir(directory):
                    if f.endswith(".desktop"):
                        # Read Name= from .desktop file
                        try:
                            with open(os.path.join(directory, f)) as fh:
                                for line in fh:
                                    if line.startswith("Name="):
                                        name = line.strip().split("=", 1)[1]
                                        if name:
                                            apps.append(name)
                                        break
                        except Exception:
                            # Fallback: use filename without .desktop
                            apps.append(f[:-8])
            except Exception:
                pass

    return sorted(set(a for a in apps if a))


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
    Cross-platform: Mac / Windows / Linux
    """
    if IS_MAC:
        return _smart_open_mac(app_name)
    elif IS_WINDOWS:
        return _smart_open_windows(app_name)
    else:
        return _smart_open_linux(app_name)


def _smart_open_mac(app_name: str) -> OpenAppResult:
    """Mac-specific multi-layer app opener"""
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
            return OpenAppResult(True, f"Binuksan: {fuzzy_match} (similar sa '{app_name}')", "fuzzy", fuzzy_match)

    # Layer 4: Spotlight (mdfind)
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

    remember_app_failure(app_name, tried, "Not found after all attempts")
    suggestion = fuzzy_match or _suggest_similar(app_name)
    msg = f"Hindi ko mahanap ang '{app_name}'."
    if suggestion:
        msg += f" Ibig mo bang buksan ang '{suggestion}'?"
    else:
        msg += " Naka-install ba ito? I-check mo sa /Applications folder."
    return OpenAppResult(False, msg, "none", "")


def _smart_open_windows(app_name: str) -> OpenAppResult:
    """Windows-specific multi-layer app opener"""
    # Layer 0: Check known working name
    known_name = get_known_app_name(app_name)
    if known_name:
        result = subprocess.run(
            f'start "" "{known_name}"',
            shell=True, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return OpenAppResult(True, f"Binuksan: {known_name}", "cached", known_name)

    # Layer 1: Try start command with name variations
    candidates = _build_app_candidates(app_name)
    tried = []
    for candidate in candidates:
        tried.append(candidate)
        # Try as bare name (Windows Start menu search)
        result = subprocess.run(
            f'start "" "{candidate}"',
            shell=True, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            remember_app_success(app_name, candidate)
            return OpenAppResult(True, f"Binuksan: {candidate}", "start", candidate)

    # Layer 2: Check if already running (tasklist)
    running = _check_if_running(app_name)
    if running:
        # Bring to front via VBScript
        vbs = f'AppActivate "{app_name}"'
        result = subprocess.run(
            ["cscript", "//nologo", "//e:vbscript", f"//{vbs}"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return OpenAppResult(True, f"Na-activate: {app_name} (nasa background pala)", "tasklist", app_name)

    # Layer 3: Search for .exe in common paths
    exe_path = _find_exe_windows(app_name)
    if exe_path:
        result = subprocess.run(
            [exe_path],
            capture_output=True, text=True, timeout=10,
            creationflags=0x00000008  # DETACHED_PROCESS
        )
        if result.returncode == 0:
            remember_app_success(app_name, exe_path)
            return OpenAppResult(True, f"Binuksan: {exe_path}", "exe direct", exe_path)

    # Layer 4: Try fuzzy match from installed apps
    fuzzy_match = find_app_fuzzy(app_name)
    if fuzzy_match:
        result = subprocess.run(
            f'start "" "{fuzzy_match}"',
            shell=True, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            remember_app_success(app_name, fuzzy_match)
            return OpenAppResult(True, f"Binuksan: {fuzzy_match} (similar sa '{app_name}')", "fuzzy", fuzzy_match)

    remember_app_failure(app_name, tried, "Not found after all attempts")
    suggestion = fuzzy_match or _suggest_similar(app_name)
    msg = f"Hindi ko mahanap ang '{app_name}'."
    if suggestion:
        msg += f" Ibig mo bang buksan ang '{suggestion}'?"
    else:
        msg += " Naka-install ba ito? I-check mo sa Start menu."
    return OpenAppResult(False, msg, "none", "")


def _smart_open_linux(app_name: str) -> OpenAppResult:
    """Linux-specific multi-layer app opener"""
    # Layer 0: Check known working name
    known_name = get_known_app_name(app_name)
    if known_name:
        try:
            subprocess.Popen(
                [known_name.lower().replace(" ", "-")],
                start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return OpenAppResult(True, f"Binuksan: {known_name}", "cached", known_name)
        except Exception:
            pass

    candidates = _build_app_candidates(app_name)
    tried = []

    # Layer 1: Try executable name directly (command-based apps)
    for candidate in candidates:
        tried.append(candidate)
        cmd = candidate.lower().replace(" ", "-")
        if shutil.which(cmd):
            try:
                subprocess.Popen(
                    [cmd],
                    start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                remember_app_success(app_name, cmd)
                return OpenAppResult(True, f"Binuksan: {cmd}", "exec", cmd)
            except Exception:
                pass

    # Layer 2: gtk-launch (uses .desktop files)
    desktop_id = app_name.lower().replace(" ", "-")
    result = subprocess.run(
        ["gtk-launch", desktop_id],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode == 0:
        remember_app_success(app_name, desktop_id)
        return OpenAppResult(True, f"Binuksan: {desktop_id}", "gtk-launch", desktop_id)

    # Layer 3: Check if already running (pgrep)
    running = _check_if_running(app_name)
    if running:
        # Try wmctrl to bring to front
        result = subprocess.run(
            ["wmctrl", "-a", app_name],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return OpenAppResult(True, f"Na-activate: {app_name} (nasa background pala)", "wmctrl", app_name)

    # Layer 4: Fuzzy match + xdg-open via .desktop
    fuzzy_match = find_app_fuzzy(app_name)
    if fuzzy_match:
        cmd = fuzzy_match.lower().replace(" ", "-")
        if shutil.which(cmd):
            try:
                subprocess.Popen(
                    [cmd],
                    start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                remember_app_success(app_name, cmd)
                return OpenAppResult(True, f"Binuksan: {fuzzy_match} (similar sa '{app_name}')", "fuzzy", fuzzy_match)
            except Exception:
                pass

    remember_app_failure(app_name, tried, "Not found after all attempts")
    suggestion = fuzzy_match or _suggest_similar(app_name)
    msg = f"Hindi ko mahanap ang '{app_name}'."
    if suggestion:
        msg += f" Ibig mo bang buksan ang '{suggestion}'?"
    else:
        msg += " Naka-install ba ito? Try: which <appname> or apt/snap/flatpak search."
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
    """Check if app process is running — cross-platform"""
    try:
        if IS_WINDOWS:
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {app_name}.exe", "/NH"],
                capture_output=True, text=True, timeout=5
            )
            return app_name.lower() in result.stdout.lower()
        else:
            # pgrep works on both Mac and Linux
            result = subprocess.run(
                ["pgrep", "-if", app_name],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
    except Exception:
        return False


def _spotlight_find_app(app_name: str) -> Optional[str]:
    """Use Spotlight (mdfind) to find app by name — Mac only"""
    if not IS_MAC:
        return None
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


def _find_exe_windows(app_name: str) -> Optional[str]:
    """Search for .exe in common Windows install paths"""
    if not IS_WINDOWS:
        return None
    search_dirs = [
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        os.path.expanduser(r"~\AppData\Local\Programs"),
        os.path.expanduser(r"~\AppData\Local"),
    ]
    name_lower = app_name.lower()
    for base_dir in search_dirs:
        if not base_dir or not os.path.exists(base_dir):
            continue
        try:
            for root, dirs, files in os.walk(base_dir):
                for f in files:
                    if f.lower().endswith(".exe") and name_lower in f.lower():
                        return os.path.join(root, f)
                # Limit depth to avoid scanning too deep
                if root.count(os.sep) - base_dir.count(os.sep) >= 3:
                    dirs.clear()
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

def _get_os_tools_info() -> str:
    """Return OS-specific tool info for the system prompt"""
    if IS_MAC:
        return (
            "- OS: macOS (Darwin)\n"
            "- App launch: open -a <name>, osascript\n"
            "- Process check: pgrep\n"
            "- App search: mdfind (Spotlight)\n"
            "- Other: pyautogui, screenshot"
        )
    elif IS_WINDOWS:
        return (
            "- OS: Windows\n"
            "- App launch: start \"\" \"<name>\", direct .exe path\n"
            "- Process check: tasklist\n"
            "- App search: Registry, Program Files scan\n"
            "- Other: pyautogui, screenshot, PowerShell"
        )
    else:
        return (
            "- OS: Linux\n"
            "- App launch: exec by name, gtk-launch, xdg-open\n"
            "- Process check: pgrep\n"
            "- App search: .desktop files, which\n"
            "- Other: pyautogui, screenshot, wmctrl"
        )


def build_system_prompt(context: Optional[dict] = None) -> str:
    """Build Kurt's full system prompt with personality + current context"""
    knowledge = load_imac_knowledge()

    known_apps = list(knowledge.get("apps_verified", {}).keys())
    known_apps_str = ", ".join(known_apps[:20]) if known_apps else "wala pa"

    context_str = ""
    if context:
        for key, val in context.items():
            context_str += f"\n- {key}: {val}"

    os_label = {
        "Darwin": "macOS (iMac M4)",
        "Windows": "Windows",
        "Linux": "Linux",
    }.get(OS, OS)

    prompt = f"""Ikaw si {KURT_NAME} ({KURT_FULL_NAME}) v{KURT_VERSION}.
Personal AI assistant ni {KURT_OWNER} sa kanyang {os_label}.

{KURT_PERSONALITY}

CURRENT MACHINE KNOWLEDGE:
- Known apps (working): {known_apps_str}
{_get_os_tools_info()}

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
