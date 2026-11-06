"""KURT Books Skills Catalog — 5 skills from Claude's marketplace"""
from pathlib import Path
from typing import Optional

BOOKS_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_books.txt"

BOOKS_DOMAINS = {
    "social_reading": ["Goodreads Skills", "StoryGraph"],
    "library_ebooks": ["Libby"],
    "digital_reading": ["Kindle Skills", "Audible Skills"],
}

DOMAIN_PROMPTS = {
    "social_reading": "You are an expert in social reading and book discovery platforms. Help readers track books, find recommendations based on taste, and engage with reading communities.",
    "library_ebooks": "You are an expert in library ebook and audiobook borrowing. Help patrons find titles, manage holds, and borrow digital content from their local library.",
    "digital_reading": "You are an expert in digital reading and audiobook platforms. Help users manage their Kindle library, find Audible titles, and optimize their reading experience.",
}

def load_all_skills() -> list[str]:
    if BOOKS_SKILLS_FILE.exists():
        return [l.strip() for l in BOOKS_SKILLS_FILE.read_text().splitlines() if l.strip()]
    return []

def search_skills(query: str) -> list[str]:
    return [s for s in load_all_skills() if query.lower() in s.lower()]

def get_domain_for_skill(skill_name: str) -> Optional[str]:
    sl = skill_name.lower()
    for domain, skills in BOOKS_DOMAINS.items():
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
    domain_counts = {d: len(s) for d, s in BOOKS_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(BOOKS_DOMAINS), "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
