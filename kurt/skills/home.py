"""KURT Home Skills Catalog — 6 skills from Claude's marketplace"""
from pathlib import Path
from typing import Optional

HOME_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_home.txt"

HOME_DOMAINS = {
    "smart_home": ["Home Assistant Skills", "SmartThings", "Apple HomeKit", "Google Home", "Amazon Alexa"],
    "home_design": ["Houzz"],
}

DOMAIN_PROMPTS = {
    "smart_home": "You are an expert in smart home platforms and automation. Help users set up devices, create automations, and build integrated smart home ecosystems.",
    "home_design": "You are an expert in home design and renovation platforms. Help users find design inspiration, connect with professionals, and plan home improvement projects.",
}

def load_all_skills() -> list[str]:
    if HOME_SKILLS_FILE.exists():
        return [l.strip() for l in HOME_SKILLS_FILE.read_text().splitlines() if l.strip()]
    return []

def search_skills(query: str) -> list[str]:
    return [s for s in load_all_skills() if query.lower() in s.lower()]

def get_domain_for_skill(skill_name: str) -> Optional[str]:
    sl = skill_name.lower()
    for domain, skills in HOME_DOMAINS.items():
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
    domain_counts = {d: len(s) for d, s in HOME_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(HOME_DOMAINS), "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
