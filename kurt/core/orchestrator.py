"""
KURT Orchestrator - Ang utak ng lahat
Nag-aanalyze ng task at pinipili ang pinaka-angkop na AI model
"""

import re
from dataclasses import dataclass
from enum import Enum


class TaskType(Enum):
    CHAT = "chat"
    CODE = "code"
    IMAGE = "image"
    MUSIC = "music"
    VIDEO = "video"
    RESEARCH = "research"
    TRANSCRIBE = "transcribe"
    MATH = "math"
    WRITE = "write"
    TRANSLATE = "translate"
    GAME = "game"
    DESIGN = "design"
    ARTIFACT = "artifact"
    SCHEDULE = "schedule"
    UNKNOWN = "unknown"


@dataclass
class TaskAnalysis:
    task_type: TaskType
    model: str
    provider: str
    reason: str
    fallback_model: str
    fallback_provider: str


# Model routing table - libre muna, paid as fallback
ROUTING_TABLE = {
    TaskType.CODE: {
        "model": "deepseek/deepseek-coder",
        "provider": "openrouter",
        "reason": "DeepSeek Coder — pinaka-magaling sa code, libre pa!",
        "fallback_model": "anthropic/claude-3.5-sonnet",
        "fallback_provider": "openrouter",
    },
    TaskType.GAME: {
        "model": "deepseek/deepseek-coder",
        "provider": "openrouter",
        "reason": "DeepSeek Coder — perfect for game development",
        "fallback_model": "anthropic/claude-3.5-sonnet",
        "fallback_provider": "openrouter",
    },
    TaskType.RESEARCH: {
        "model": "google/gemini-flash-1.5",
        "provider": "openrouter",
        "reason": "Gemini Flash — libre, may web access, 1M context!",
        "fallback_model": "perplexity/llama-3.1-sonar-large-128k-online",
        "fallback_provider": "openrouter",
    },
    TaskType.MATH: {
        "model": "deepseek/deepseek-r1",
        "provider": "openrouter",
        "reason": "DeepSeek R1 — pinaka-magaling sa reasoning at math",
        "fallback_model": "openai/o1-mini",
        "fallback_provider": "openrouter",
    },
    TaskType.WRITE: {
        "model": "anthropic/claude-3.5-haiku",
        "provider": "openrouter",
        "reason": "Claude Haiku — pinaka-magaling sa writing",
        "fallback_model": "meta-llama/llama-3.3-70b-instruct",
        "fallback_provider": "openrouter",
    },
    TaskType.TRANSLATE: {
        "model": "google/gemini-flash-1.5",
        "provider": "openrouter",
        "reason": "Gemini Flash — magaling sa multilingual",
        "fallback_model": "meta-llama/llama-3.3-70b-instruct",
        "fallback_provider": "openrouter",
    },
    TaskType.TRANSCRIBE: {
        "model": "whisper-large-v3",
        "provider": "groq",
        "reason": "Whisper via Groq — libre, mabilis, accurate!",
        "fallback_model": "openai/whisper-1",
        "fallback_provider": "openai",
    },
    TaskType.IMAGE: {
        "model": "black-forest-labs/flux-schnell",
        "provider": "fal",
        "reason": "Flux Schnell — mabilis, maganda, mura!",
        "fallback_model": "stability-ai/stable-diffusion-3",
        "fallback_provider": "replicate",
    },
    TaskType.MUSIC: {
        "model": "musicgen-large",
        "provider": "replicate",
        "reason": "MusicGen — open source music generation",
        "fallback_model": "suno",
        "fallback_provider": "suno",
    },
    TaskType.VIDEO: {
        "model": "wan-2.1",
        "provider": "replicate",
        "reason": "Wan 2.1 — open source, libre!",
        "fallback_model": "kling-v1.6",
        "fallback_provider": "kling",
    },
    TaskType.CHAT: {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "provider": "openrouter",
        "reason": "LLaMA 3.3 70B — libre, mabilis via OpenRouter!",
        "fallback_model": "google/gemini-flash-1.5",
        "fallback_provider": "openrouter",
    },
    TaskType.DESIGN: {
        "model": "claude-3-5-sonnet-20241022",
        "provider": "anthropic",
        "reason": "Claude Sonnet — pinaka-creative sa design tasks!",
        "fallback_model": "meta-llama/llama-3.3-70b-instruct:free",
        "fallback_provider": "openrouter",
    },
    TaskType.ARTIFACT: {
        "model": "claude-3-5-sonnet-20241022",
        "provider": "anthropic",
        "reason": "Claude Sonnet — best sa generating structured artifacts!",
        "fallback_model": "deepseek/deepseek-coder",
        "fallback_provider": "openrouter",
    },
    TaskType.SCHEDULE: {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "provider": "openrouter",
        "reason": "LLaMA 3.3 — handling schedule queries",
        "fallback_model": "google/gemini-flash-1.5",
        "fallback_provider": "openrouter",
    },
    TaskType.UNKNOWN: {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "provider": "openrouter",
        "reason": "LLaMA 3.3 — magaling sa general tasks",
        "fallback_model": "google/gemini-flash-1.5",
        "fallback_provider": "openrouter",
    },
}

# Keywords para sa task detection
TASK_KEYWORDS = {
    TaskType.CODE: [
        "code", "program", "script", "function", "class", "bug", "fix",
        "debug", "develop", "implement", "python", "javascript",
        "typescript", "java", "php", "html", "css", "api", "database",
        "i-code", "i-fix", "i-debug", "i-build"
    ],
    TaskType.GAME: [
        "game", "laro", "snake", "tetris", "flappy", "mario", "pygame",
        "unity", "godot", "platformer", "shooter", "puzzle", "2d", "3d"
    ],
    TaskType.IMAGE: [
        "image", "picture", "photo", "draw", "generate image", "create image",
        "larawan", "gumawa ng picture", "iguhit", "dall-e", "midjourney",
        "flux", "stable diffusion", "artwork", "logo", "banner", "poster"
    ],
    TaskType.MUSIC: [
        "music", "song", "compose", "melody", "beat", "kanta",
        "musika", "gumawa ng kanta", "mag-compose", "lyrics", "tune"
    ],
    TaskType.VIDEO: [
        "video", "clip", "animation", "movie", "film", "generate video",
        "gumawa ng video", "animate", "motion"
    ],
    TaskType.RESEARCH: [
        "research", "search", "find", "look up", "what is", "who is",
        "latest", "news", "current", "today", "2026", "maghanap",
        "ano ang", "sino ang", "balita", "i-research", "i-check"
    ],
    TaskType.MATH: [
        "calculate", "compute", "math", "equation", "solve", "formula",
        "kalkulahin", "arithmetic", "algebra", "statistics", "percent",
        "derivative", "integral", "proof"
    ],
    TaskType.WRITE: [
        "write", "essay", "article", "blog", "post", "caption", "copy",
        "content", "letter", "email", "sumulat", "i-write", "mag-draft",
        "paraphrase", "summarize", "i-summarize", "synopsis"
    ],
    TaskType.TRANSLATE: [
        "translate", "i-translate", "pagsalin", "english to", "tagalog to",
        "in english", "in tagalog", "i-translate sa"
    ],
    TaskType.TRANSCRIBE: [
        "transcribe", "audio to text", "speech to text", "i-transcribe",
        "gawin text", "mp3", "wav", "voice to text"
    ],
    TaskType.DESIGN: [
        "design", "ui", "ux", "layout", "wireframe", "mockup", "prototype",
        "color scheme", "typography", "figma", "logo design", "brand",
        "i-design", "gumawa ng design", "interface", "frontend design",
        "app design", "web design", "visual", "aesthetic"
    ],
    TaskType.ARTIFACT: [
        "artifact", "save code", "export", "save output", "generate file",
        "i-save", "i-export", "output file", "create artifact",
    ],
    TaskType.SCHEDULE: [
        "schedule", "every day", "every hour", "cron", "recurring",
        "daily", "weekly", "i-schedule", "mag-schedule", "automation",
        "auto run", "regular task", "set reminder"
    ],
}


def classify_task(prompt: str) -> TaskType:
    """Nag-aanalyze ng prompt at nagre-return ng TaskType"""
    prompt_lower = prompt.lower()

    scores = {task_type: 0 for task_type in TaskType}

    for task_type, keywords in TASK_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in prompt_lower:
                scores[task_type] += 1

    # Remove UNKNOWN from scoring
    scores.pop(TaskType.UNKNOWN)

    best_task = max(scores, key=scores.get)

    # Kung walang match, default sa CHAT
    if scores[best_task] == 0:
        return TaskType.CHAT

    return best_task


def analyze_task(prompt: str) -> TaskAnalysis:
    """Full task analysis - returns model recommendation"""
    task_type = classify_task(prompt)
    routing = ROUTING_TABLE[task_type]

    return TaskAnalysis(
        task_type=task_type,
        model=routing["model"],
        provider=routing["provider"],
        reason=routing["reason"],
        fallback_model=routing["fallback_model"],
        fallback_provider=routing["fallback_provider"],
    )
