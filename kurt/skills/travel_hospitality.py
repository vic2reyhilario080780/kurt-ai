"""KURT Travel Hospitality Skills Catalog — 6 skills from Claude's marketplace"""
from pathlib import Path
from typing import Optional

TRAVEL_HOSPITALITY_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_travel_hospitality.txt"

TRAVEL_HOSPITALITY_DOMAINS = {
    "pms_enterprise": ["Cloudbeds", "Mews"],
    "independent_hotels": ["Little Hotelier", "Lodgify"],
    "vacation_rentals": ["Hostaway", "Guesty"],
}

DOMAIN_PROMPTS = {
    "pms_enterprise": "You are an expert in enterprise property management systems. Help hoteliers manage reservations, front desk operations, channel distribution, and revenue management.",
    "independent_hotels": "You are an expert in independent hotel management software. Help small and boutique hotels manage bookings, OTA connections, and guest communications.",
    "vacation_rentals": "You are an expert in vacation rental management platforms. Help property managers automate listings, sync calendars, manage cleanings, and optimize pricing.",
}

def load_all_skills() -> list[str]:
    if TRAVEL_HOSPITALITY_SKILLS_FILE.exists():
        return [l.strip() for l in TRAVEL_HOSPITALITY_SKILLS_FILE.read_text().splitlines() if l.strip()]
    return []

def search_skills(query: str) -> list[str]:
    return [s for s in load_all_skills() if query.lower() in s.lower()]

def get_domain_for_skill(skill_name: str) -> Optional[str]:
    sl = skill_name.lower()
    for domain, skills in TRAVEL_HOSPITALITY_DOMAINS.items():
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
    domain_counts = {d: len(s) for d, s in TRAVEL_HOSPITALITY_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(TRAVEL_HOSPITALITY_DOMAINS), "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
