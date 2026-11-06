"""KURT Healthcare Skills Catalog — 32 skills from Claude's marketplace"""
from pathlib import Path
from typing import Optional

HEALTHCARE_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_healthcare.txt"

HEALTHCARE_DOMAINS = {
    "ehr_systems": ["Epic MyChart", "DrChrono", "Kareo", "Practice Fusion", "AdvancedMD", "Athenahealth", "NextGen Healthcare", "ModMed", "Greenway Health", "Allscripts"],
    "enterprise_health": ["Veeva Vault", "Meditech", "Cerner Skills", "PointClickCare", "MatrixCare", "HealthStream"],
    "telehealth": ["Teladoc Health", "MDlive", "Amwell", "Heal", "Included Health", "Grand Rounds"],
    "health_platforms": ["Doximity", "Zocdoc", "Accolade", "Hims & Hers Health", "Ro Health", "Nuna Health"],
    "analytics_data": ["Phreesia", "Kyruus Health", "Innovaccer", "Health Catalyst"],
}

DOMAIN_PROMPTS = {
    "ehr_systems": "You are an expert in Electronic Health Record systems. Help with EHR configuration, clinical workflows, patient portal setup, and practice management optimization.",
    "enterprise_health": "You are an expert in enterprise healthcare IT. Help with large health system implementations, long-term care systems, and clinical staff training platforms.",
    "telehealth": "You are an expert in telehealth and virtual care. Help configure virtual visit workflows, patient onboarding, and telehealth compliance requirements.",
    "health_platforms": "You are an expert in digital health platforms. Help patients and providers navigate digital health tools for care coordination, provider discovery, and specialty care.",
    "analytics_data": "You are an expert in healthcare analytics and data. Help with patient intake optimization, provider data management, and population health analytics.",
}

def load_all_skills() -> list[str]:
    if HEALTHCARE_SKILLS_FILE.exists():
        return [l.strip() for l in HEALTHCARE_SKILLS_FILE.read_text().splitlines() if l.strip()]
    return []

def search_skills(query: str) -> list[str]:
    return [s for s in load_all_skills() if query.lower() in s.lower()]

def get_domain_for_skill(skill_name: str) -> Optional[str]:
    sl = skill_name.lower()
    for domain, skills in HEALTHCARE_DOMAINS.items():
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
    domain_counts = {d: len(s) for d, s in HEALTHCARE_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(HEALTHCARE_DOMAINS), "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
