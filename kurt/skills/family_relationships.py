"""KURT Family & Relationships Skills Catalog — 12 skills from Claude's marketplace"""
from pathlib import Path
from typing import Optional

FAMILY_RELATIONSHIPS_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_family_relationships.txt"

FAMILY_RELATIONSHIPS_DOMAINS = {
    "family_organization": ["Cozi Family Organizer", "OurFamilyWizard", "FamilyWall", "Life360"],
    "parental_controls": ["Bark", "Circle Parental Controls", "Qustodio", "Google Family Link", "Apple Screen Time"],
    "relationship_tools": ["Gottman Card Decks", "Lasting", "Paired"],
}

DOMAIN_PROMPTS = {
    "family_organization": "You are an expert in family organization tools. Help families coordinate schedules, share calendars, track chores, and communicate across households.",
    "parental_controls": "You are an expert in parental control and digital safety tools. Help parents monitor screen time, filter content, and keep children safe online.",
    "relationship_tools": "You are an expert in relationship-strengthening apps. Help couples improve communication, deepen connection, and build healthier relationship habits.",
}

def load_all_skills() -> list[str]:
    if FAMILY_RELATIONSHIPS_SKILLS_FILE.exists():
        return [l.strip() for l in FAMILY_RELATIONSHIPS_SKILLS_FILE.read_text().splitlines() if l.strip()]
    return []

def search_skills(query: str) -> list[str]:
    return [s for s in load_all_skills() if query.lower() in s.lower()]

def get_domain_for_skill(skill_name: str) -> Optional[str]:
    sl = skill_name.lower()
    for domain, skills in FAMILY_RELATIONSHIPS_DOMAINS.items():
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
    domain_counts = {d: len(s) for d, s in FAMILY_RELATIONSHIPS_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(FAMILY_RELATIONSHIPS_DOMAINS), "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
