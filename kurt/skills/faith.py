"""KURT Faith Skills Catalog — 7 skills from Claude's marketplace"""
from pathlib import Path
from typing import Optional

FAITH_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_faith.txt"

FAITH_DOMAINS = {
    "bible_study": ["YouVersion Bible", "Logos Bible Software", "Olive Tree", "Blue Letter Bible", "Bible Gateway"],
    "devotional_prayer": ["Daily Audio Bible", "Hallow"],
}

DOMAIN_PROMPTS = {
    "bible_study": "You are an expert in Bible study tools and resources. Help users study scripture, access commentaries, compare translations, and deepen their understanding of the Bible.",
    "devotional_prayer": "You are an expert in devotional and prayer apps. Help users build consistent prayer habits, find guided meditations, and develop daily spiritual disciplines.",
}

def load_all_skills() -> list[str]:
    if FAITH_SKILLS_FILE.exists():
        return [l.strip() for l in FAITH_SKILLS_FILE.read_text().splitlines() if l.strip()]
    return []

def search_skills(query: str) -> list[str]:
    return [s for s in load_all_skills() if query.lower() in s.lower()]

def get_domain_for_skill(skill_name: str) -> Optional[str]:
    sl = skill_name.lower()
    for domain, skills in FAITH_DOMAINS.items():
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
    domain_counts = {d: len(s) for d, s in FAITH_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(FAITH_DOMAINS), "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
