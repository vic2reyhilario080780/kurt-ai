"""KURT Government Skills Catalog — 15 skills from Claude's marketplace"""
from pathlib import Path
from typing import Optional

GOVERNMENT_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_government.txt"

GOVERNMENT_DOMAINS = {
    "federal_services": ["USA.gov Skills", "Benefits.gov", "SSA.gov", "IRS.gov Skills", "USPS Skills"],
    "state_local": ["DMV Skills"],
    "jobs_procurement": ["USAJobs", "SAM.gov", "Grants.gov"],
    "data_transparency": ["Data.gov", "Census Bureau", "OpenFEC"],
    "legislation": ["Congress.gov", "GovTrack", "VoteSmart"],
}

DOMAIN_PROMPTS = {
    "federal_services": "You are an expert in US federal government services. Help citizens navigate benefits, taxes, Social Security, and postal services efficiently.",
    "state_local": "You are an expert in state and local government services. Help with DMV transactions, licenses, registrations, and local permits.",
    "jobs_procurement": "You are an expert in government employment and procurement. Help with federal job applications, contract opportunities, and grant applications.",
    "data_transparency": "You are an expert in government open data. Help researchers and citizens find, access, and analyze public government datasets.",
    "legislation": "You are an expert in legislative tracking and civic engagement. Help citizens track bills, understand voting records, and engage with the legislative process.",
}

def load_all_skills() -> list[str]:
    if GOVERNMENT_SKILLS_FILE.exists():
        return [l.strip() for l in GOVERNMENT_SKILLS_FILE.read_text().splitlines() if l.strip()]
    return []

def search_skills(query: str) -> list[str]:
    return [s for s in load_all_skills() if query.lower() in s.lower()]

def get_domain_for_skill(skill_name: str) -> Optional[str]:
    sl = skill_name.lower()
    for domain, skills in GOVERNMENT_DOMAINS.items():
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
    domain_counts = {d: len(s) for d, s in GOVERNMENT_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(GOVERNMENT_DOMAINS), "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
