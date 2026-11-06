"""KURT Music Skills Catalog — 38 skills from Claude's marketplace"""
from pathlib import Path
from typing import Optional

MUSIC_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_music.txt"

MUSIC_DOMAINS = {
    "ai_generation": ["Suno", "Udio", "Soundraw", "AIVA", "Mubert", "Boomy", "Loudly", "Sonauto", "Musicfy", "Riffusion", "Humtap", "WaveNet Audio"],
    "production_tools": ["BeatStars", "Splice", "Beatoven.ai", "Orb Composer", "Melodrive", "Soundful", "Amper Music", "Soundraw Pro", "Melobytes", "Jukebox"],
    "audio_processing": ["Moises", "Lalal.ai", "AudioShake", "VocalRemover", "Jammable", "Voicemod", "ElevenLabs Music"],
    "daw_integration": ["StudioOne AI", "Logic Pro AI", "Ableton AI"],
    "theory_collaboration": ["Hookpad", "ChordU", "Chordify", "Endlesss", "BandLab", "Vocaloid"],
}

DOMAIN_PROMPTS = {
    "ai_generation": "You are an expert in AI music generation. Help users create, prompt, and refine AI-generated music using tools like Suno, Udio, and AIVA. Guide prompt engineering for style, genre, mood, and instrumentation.",
    "production_tools": "You are an expert in music production tools. Help with beat making, sample sourcing, composition tools, and AI-assisted production workflows.",
    "audio_processing": "You are an expert in audio processing and stem separation. Help with vocal removal, instrument isolation, voice cloning for music, and audio enhancement.",
    "daw_integration": "You are an expert in DAW (Digital Audio Workstation) AI features. Guide users on AI-assisted mixing, mastering, and composition within professional DAWs.",
    "theory_collaboration": "You are an expert in music theory and collaborative creation. Help with chord progressions, harmony, real-time collaboration, and music notation.",
}

def load_all_skills() -> list[str]:
    if MUSIC_SKILLS_FILE.exists():
        return [l.strip() for l in MUSIC_SKILLS_FILE.read_text().splitlines() if l.strip()]
    return []

def search_skills(query: str) -> list[str]:
    return [s for s in load_all_skills() if query.lower() in s.lower()]

def get_domain_for_skill(skill_name: str) -> Optional[str]:
    sl = skill_name.lower()
    for domain, skills in MUSIC_DOMAINS.items():
        if any(sl == s.lower() or sl in s.lower() for s in skills):
            return domain
    return None

def get_domain_prompt(domain: str) -> Optional[str]:
    return DOMAIN_PROMPTS.get(domain)

def get_skill_context(skill_name: str) -> str:
    domain = get_domain_for_skill(skill_name)
    base = DOMAIN_PROMPTS.get(domain, "") if domain else ""
    return f"You are an expert in {skill_name}.\n{base}\nApply the specific practices from '{skill_name}'."

def get_stats() -> dict:
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in MUSIC_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(MUSIC_DOMAINS), "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
