"""
KURT v3.0 Core — Computer Control, Vision, Screen Watching, Voice, Memory

Modules:
  computer_use   — Cross-platform mouse/keyboard/app control
  vision         — Local vision engine (Ollama LLaVA + Claude fallback)
  screen_watcher — Always-on screen change detection
  wake_word      — "Hey Kurt" voice trigger + TTS
  habit_memory   — Persistent memory + habit learning
"""

# Lazy imports — only load what's needed
def get_computer():
    from kurt.core.computer_use import (
        screenshot, click, double_click, right_click, move_to,
        drag, scroll, type_text, press_key, hotkey,
        open_app, open_url, close_app, focus_window,
        get_active_window, clipboard_copy, clipboard_paste,
        wait, wait_for_app, run_command, check_dependencies,
        install_dependencies, ActionResult, Key,
    )
    return locals()


def get_vision():
    from kurt.core.vision import (
        describe_screen, find_element, read_text_on_screen,
        understand_context, verify_action_done, detect_ui_state,
        smart_vision, get_vision_status, install_vision_model,
        VisionResult,
    )
    return locals()


def get_screen_watcher():
    from kurt.core.screen_watcher import (
        get_watcher, get_proactive, start_watching, stop_watching,
        ScreenWatcher, KURTProactive, ScreenEvent,
    )
    return locals()


def get_voice():
    from kurt.core.wake_word import (
        speak, transcribe_audio, record_audio,
        start_listening, stop_listening, get_listener,
        check_dependencies, install_dependencies,
        WakeWordListener, VoiceEvent,
    )
    return locals()


def get_memory():
    from kurt.core.habit_memory import (
        remember, recall, forget, remember_now, recall_now,
        log_interaction, get_suggestions, save_preference,
        get_preference, get_context, get_stats, get_habit_summary,
        KURTMemory,
    )
    return locals()


# v3.0 capability flags
V3_CAPABILITIES = {
    "computer_control": True,     # Phase 1
    "local_vision": True,         # Phase 2
    "screen_watcher": True,       # Phase 3
    "wake_word": True,            # Phase 4
    "habit_memory": True,         # Phase 5
}
