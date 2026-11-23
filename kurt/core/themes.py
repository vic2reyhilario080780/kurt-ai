"""
KURT static personalization data — themes, backgrounds, languages, icons,
voice presets and the default persona shape. Split out of persona.py so
that file can stay focused on load/save/getter logic; every name here is
re-exported from kurt.core.persona unchanged, so existing imports
(`from kurt.core.persona import BUILTIN_THEMES`, etc.) keep working.
"""

# ══════════════════════════════════════════════════════════════
# BUILT-IN THEMES
# Each theme = Rich color names for primary, secondary, accent,
# border, dim, success, error, warning
# ══════════════════════════════════════════════════════════════
BUILTIN_THEMES = {
    "cyber": {
        "name": "Cyber (Default)",
        "primary": "bold cyan",
        "secondary": "cyan",
        "accent": "bold magenta",
        "border": "cyan",
        "dim": "dim",
        "success": "bold green",
        "error": "bold red",
        "warning": "bold yellow",
        "info": "dim cyan",
        "banner_color": "bold cyan",
        "box_style": "ROUNDED",
        "emoji_prefix": "🤖",
        "bg_hex": "#061b1e",
        "background": "on #061b1e",
    },
    "violet": {
        "name": "Violet Glow",
        "primary": "bold #c084fc",
        "secondary": "#a78bfa",
        "accent": "bold #67e8f9",
        "border": "#a78bfa",
        "dim": "dim",
        "success": "bold green",
        "error": "bold red",
        "warning": "bold yellow",
        "info": "dim #a78bfa",
        "banner_color": "bold #c084fc",
        "box_style": "ROUNDED",
        "emoji_prefix": "🔮",
        "bg_hex": "#160a2b",
        "background": "on #160a2b",
    },
    "neon": {
        "name": "Neon Pink",
        "primary": "bold magenta",
        "secondary": "magenta",
        "accent": "bold cyan",
        "border": "magenta",
        "dim": "dim",
        "success": "bold green",
        "error": "bold red",
        "warning": "bold yellow",
        "info": "dim magenta",
        "banner_color": "bold magenta",
        "box_style": "DOUBLE",
        "emoji_prefix": "✨",
        "bg_hex": "#1e0726",
        "background": "on #1e0726",
    },
    "matrix": {
        "name": "Matrix Green",
        "primary": "bold green",
        "secondary": "green",
        "accent": "bold yellow",
        "border": "green",
        "dim": "dim",
        "success": "bold bright_green",
        "error": "bold red",
        "warning": "bold yellow",
        "info": "dim green",
        "banner_color": "bold green",
        "box_style": "MINIMAL",
        "emoji_prefix": "🟢",
        "bg_hex": "#061709",
        "background": "on #061709",
    },
    "gold": {
        "name": "Gold / Royal",
        "primary": "bold yellow",
        "secondary": "yellow",
        "accent": "bold white",
        "border": "yellow",
        "dim": "dim",
        "success": "bold green",
        "error": "bold red",
        "warning": "bold orange1",
        "info": "dim yellow",
        "banner_color": "bold yellow",
        "box_style": "HEAVY",
        "emoji_prefix": "👑",
        "bg_hex": "#1e1705",
        "background": "on #1e1705",
    },
    "minimal": {
        "name": "Minimal White",
        "primary": "bold white",
        "secondary": "white",
        "accent": "bold cyan",
        "border": "white",
        "dim": "dim",
        "success": "bold green",
        "error": "bold red",
        "warning": "bold yellow",
        "info": "dim white",
        "banner_color": "bold white",
        "box_style": "SIMPLE",
        "emoji_prefix": "◆",
        "bg_hex": "",
        "background": "",
    },
    "sunset": {
        "name": "Sunset Orange",
        "primary": "bold orange1",
        "secondary": "orange1",
        "accent": "bold red",
        "border": "orange1",
        "dim": "dim",
        "success": "bold green",
        "error": "bold bright_red",
        "warning": "bold yellow",
        "info": "dim orange1",
        "banner_color": "bold orange1",
        "box_style": "ROUNDED",
        "emoji_prefix": "🌅",
        "bg_hex": "#240e06",
        "background": "on #240e06",
    },
    "ocean": {
        "name": "Ocean Blue",
        "primary": "bold blue",
        "secondary": "blue",
        "accent": "bold cyan",
        "border": "blue",
        "dim": "dim",
        "success": "bold green",
        "error": "bold red",
        "warning": "bold yellow",
        "info": "dim blue",
        "banner_color": "bold blue",
        "box_style": "ROUNDED",
        "emoji_prefix": "🌊",
        "bg_hex": "#071426",
        "background": "on #071426",
    },
    "pinoy": {
        "name": "Pinoy — Blue, Red, Yellow",
        "primary": "bold blue",
        "secondary": "bold red",
        "accent": "bold yellow",
        "border": "blue",
        "dim": "dim",
        "success": "bold green",
        "error": "bold red",
        "warning": "bold yellow",
        "info": "dim blue",
        "banner_color": "bold blue",
        "box_style": "ROUNDED",
        "emoji_prefix": "🇵🇭",
        "bg_hex": "#09132b",
        "background": "on #09132b",
    },
}

BUILTIN_BACKGROUNDS = {
    "theme":         {"name": "Theme Default",     "hex": "",        "desc": "Follow the active theme's background color"},
    "deep_violet":   {"name": "Deep Violet",       "hex": "#160a2b", "desc": "Rich dark violet backdrop"},
    "midnight_cyan": {"name": "Midnight Cyan",     "hex": "#061b1e", "desc": "Dark cyber teal-cyan backdrop"},
    "neon_plum":     {"name": "Neon Plum",         "hex": "#1e0726", "desc": "Dark magenta-plum backdrop"},
    "royal_navy":    {"name": "Royal Navy",        "hex": "#071426", "desc": "Deep ocean navy backdrop"},
    "matrix_dark":   {"name": "Matrix Dark",       "hex": "#061709", "desc": "Deep emerald-black backdrop"},
    "warm_sunset":   {"name": "Warm Sunset",       "hex": "#240e06", "desc": "Warm dark amber-brown backdrop"},
    "obsidian":      {"name": "Obsidian Slate",    "hex": "#11131a", "desc": "Neutral dark charcoal slate"},
    "none":          {"name": "Transparent / None","hex": "none",    "desc": "Use your terminal's own background"},
}

# ══════════════════════════════════════════════════════════════
# SUPPORTED LANGUAGES
# key = language code, value = display info + system instruction
# ══════════════════════════════════════════════════════════════
SUPPORTED_LANGUAGES = {
    "en": {
        "name": "English",
        "flag": "🇺🇸",
        "system_prompt": "Always respond in English.",
        "greeting_templates": [
            "Hello, {name}! How can I help you today?",
            "Hey {name}! What can I do for you?",
            "Good to see you, {name}! What's on your mind?",
        ],
        "kurt_label": "KURT",
    },
    "tl": {
        "name": "Filipino / Tagalog",
        "flag": "🇵🇭",
        "system_prompt": "Sumagot ka palagi sa Filipino/Tagalog. Pwedeng Taglish (mix ng Tagalog at English) para sa natural na pagkakataon.",
        "greeting_templates": [
            "Kumusta, {name}! Ano ang maipaglilingkod ko sa iyo?",
            "Hoy {name}! Ano'ng kailangan mo?",
            "Musta {name}! Anong pinaplano mo ngayon?",
        ],
        "kurt_label": "KURT",
    },
    "taglish": {
        "name": "Taglish (Mix)",
        "flag": "🇵🇭",
        "system_prompt": "Sumagot ka sa Taglish — natural na halo ng Tagalog at English, tulad ng tunay na pakikipag-usap ng mga Pilipino. Huwag i-translate nang literal — gamitin ang natural na Taglish flow.",
        "greeting_templates": [
            "Hoy {name}! Ano'ng kailangan mo ngayon?",
            "Kumusta {name}! What can I do for you?",
            "Hey {name}, musta! Anong task natin today?",
        ],
        "kurt_label": "KURT",
    },
    "ja": {
        "name": "日本語 (Japanese)",
        "flag": "🇯🇵",
        "system_prompt": "常に日本語で返答してください。",
        "greeting_templates": [
            "{name}さん、こんにちは！何かお手伝いできますか？",
            "やあ{name}！今日は何をしましょうか？",
        ],
        "kurt_label": "KURT",
    },
    "zh": {
        "name": "中文 (Chinese)",
        "flag": "🇨🇳",
        "system_prompt": "请始终用中文回答。",
        "greeting_templates": [
            "{name}，你好！有什么我可以帮你的吗？",
            "嗨{name}！今天需要什么帮助？",
        ],
        "kurt_label": "KURT",
    },
    "es": {
        "name": "Español (Spanish)",
        "flag": "🇪🇸",
        "system_prompt": "Responde siempre en español.",
        "greeting_templates": [
            "¡Hola, {name}! ¿En qué puedo ayudarte hoy?",
            "¡Hey {name}! ¿Qué necesitas?",
        ],
        "kurt_label": "KURT",
    },
    "ko": {
        "name": "한국어 (Korean)",
        "flag": "🇰🇷",
        "system_prompt": "항상 한국어로 답해주세요.",
        "greeting_templates": [
            "{name}님, 안녕하세요! 무엇을 도와드릴까요?",
            "안녕 {name}! 오늘 무엇이 필요하세요?",
        ],
        "kurt_label": "KURT",
    },
}

# ══════════════════════════════════════════════════════════════
# BUILT-IN ICONS
# ══════════════════════════════════════════════════════════════
BUILTIN_ICONS = {
    "robot":    "🤖",
    "brain":    "🧠",
    "lightning":"⚡",
    "fire":     "🔥",
    "star":     "⭐",
    "diamond":  "💎",
    "crown":    "👑",
    "sword":    "⚔️",
    "shield":   "🛡️",
    "rocket":   "🚀",
    "alien":    "👽",
    "ghost":    "👻",
    "flag_ph":  "🇵🇭",
    "kurt_k":   "K",
    "dot":      "◆",
    "arrow":    "▶",
    "wave":     "🌊",
    "sun":      "☀️",
    "moon":     "🌙",
    "custom":   None,  # user provides their own emoji/char
}

# ══════════════════════════════════════════════════════════════
# VOICE PRESETS (TTS) — used by kurt.core.wake_word.speak()
# ══════════════════════════════════════════════════════════════
VOICE_PRESETS = {
    "young_boy": {
        "label": "Batang Lalaki (Young Boy)",
        # Filipino neural voice (not a US English one) so Tagalog/Taglish
        # words come out with natural pronunciation instead of an
        # American "slang" accent. Pitched up + sped up for a boyish sound.
        "edge_voice": "fil-PH-AngeloNeural",
        "edge_rate": "+18%",
        "edge_pitch": "+40Hz",
        "mac_say_voice": "Junior",   # macOS built-in kid-sounding voice (English fallback only)
        "pyttsx3_rate": 200,
    },
    "default": {
        "label": "Default (Aria)",
        "edge_voice": "en-US-AriaNeural",
        "edge_rate": "+0%",
        "edge_pitch": "+0Hz",
        "mac_say_voice": None,
        "pyttsx3_rate": 175,
    },
}

# ══════════════════════════════════════════════════════════════
# DEFAULT PERSONA
# ══════════════════════════════════════════════════════════════
DEFAULT_PERSONA = {
    "version": "2.2",
    # Identity
    "user_name": "Boss",          # Paano tawaging ang user
    "kurt_name": "KURT",          # Pwedeng palitan ang pangalan ni KURT
    # Theme
    "theme": "cyber",             # Key from BUILTIN_THEMES
    "custom_background": "theme", # Key from BUILTIN_BACKGROUNDS or #rrggbb
    "icon": "robot",              # Key from BUILTIN_ICONS
    "custom_icon": None,          # Kung "custom" ang icon, dito ilagay
    # Voice (TTS persona for wake_word.speak())
    "voice": "young_boy",         # Key from VOICE_PRESETS
    # Language
    "language": "taglish",        # Key from SUPPORTED_LANGUAGES
    # Greeting style
    "greeting_style": "casual",   # casual | professional | hype
    "custom_greeting": None,      # Kung gusto ng sariling greeting template
    # AI Mode (hybrid KURT + Claude)
    "default_model": "auto",
    "default_cli": "auto",
    "default_image_model": "auto",
    "default_video_model": "auto",
    "speech_provider": "auto",
    "speech_language": "auto",
    "speech_model": "whisper-large-v3",
    "speech_vocabulary": [],
    "speech_pause_seconds": 2.0,
    "ai_mode": "hybrid",          # hybrid | kurt_only | claude_only
    # Projects context (na-dedisplay sa banner)
    "active_projects": [],        # List of active projects for context
    # Misc
    "show_routing_info": False,   # Show model routing by default
    "compact_mode": False,        # Compact output
}
