"""KURT Media & Entertainment Skills Catalog — 12 skills from Claude's marketplace"""
from pathlib import Path
from typing import Optional

MEDIA_ENTERTAINMENT_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_media_entertainment.txt"

MEDIA_ENTERTAINMENT_DOMAINS = {
    "movie_tracking": ["Letterboxd", "JustWatch", "Reelgood"],
    "tv_tracking": ["TV Time", "Trakt", "Serializd"],
    "media_servers": ["Plex Skills", "Jellyfin", "Infuse"],
    "book_tracking": ["Goodreads", "StoryGraph", "Bookly"],
}

DOMAIN_PROMPTS = {
    "movie_tracking": "You are an expert in movie discovery and tracking apps. Help users log watched films, find streaming availability, and discover new movies.",
    "tv_tracking": "You are an expert in TV show tracking apps. Help users track episodes, manage watchlists, and discover new series across streaming platforms.",
    "media_servers": "You are an expert in personal media server software. Help users set up, configure, and optimize Plex, Jellyfin, and Infuse for home media libraries.",
    "book_tracking": "You are an expert in reading tracking and book discovery apps. Help users log books, find recommendations, and build reading habits.",
}

def load_all_skills() -> list[str]:
    if MEDIA_ENTERTAINMENT_SKILLS_FILE.exists():
        return [l.strip() for l in MEDIA_ENTERTAINMENT_SKILLS_FILE.read_text().splitlines() if l.strip()]
    return []

def search_skills(query: str) -> list[str]:
    return [s for s in load_all_skills() if query.lower() in s.lower()]

def get_domain_for_skill(skill_name: str) -> Optional[str]:
    sl = skill_name.lower()
    for domain, skills in MEDIA_ENTERTAINMENT_DOMAINS.items():
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
    domain_counts = {d: len(s) for d, s in MEDIA_ENTERTAINMENT_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(MEDIA_ENTERTAINMENT_DOMAINS), "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
