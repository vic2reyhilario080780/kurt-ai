"""KURT Health & Fitness Skills Catalog — 21 skills from Claude's marketplace"""
from pathlib import Path
from typing import Optional

HEALTH_FITNESS_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_health_fitness.txt"

HEALTH_FITNESS_DOMAINS = {
    "nutrition": ["MyFitnessPal", "Cronometer", "Lose It", "Noom", "WW (Weight Watchers)"],
    "fitness_tracking": ["Fitbit Skills", "Apple Health", "Garmin Connect", "Strava", "Nike Training Club", "Peloton Skills"],
    "biometrics": ["Whoop", "Oura Ring", "Eight Sleep", "Rise Sleep"],
    "mindfulness": ["Calm", "Headspace", "Insight Timer", "Waking Up", "Ten Percent Happier", "Nightly"],
}

DOMAIN_PROMPTS = {
    "nutrition": "You are an expert in nutrition tracking and healthy eating. Help users log food, understand macros, set calorie goals, and build sustainable eating habits.",
    "fitness_tracking": "You are an expert in fitness tracking and workout planning. Help users track activities, interpret fitness metrics, and optimize training plans.",
    "biometrics": "You are an expert in biometric monitoring and recovery. Help users understand HRV, sleep stages, recovery scores, and optimize performance through data.",
    "mindfulness": "You are an expert in mindfulness and meditation apps. Help users build meditation habits, manage stress, improve sleep quality, and develop mental resilience.",
}

def load_all_skills() -> list[str]:
    if HEALTH_FITNESS_SKILLS_FILE.exists():
        return [l.strip() for l in HEALTH_FITNESS_SKILLS_FILE.read_text().splitlines() if l.strip()]
    return []

def search_skills(query: str) -> list[str]:
    return [s for s in load_all_skills() if query.lower() in s.lower()]

def get_domain_for_skill(skill_name: str) -> Optional[str]:
    sl = skill_name.lower()
    for domain, skills in HEALTH_FITNESS_DOMAINS.items():
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
    domain_counts = {d: len(s) for d, s in HEALTH_FITNESS_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(HEALTH_FITNESS_DOMAINS), "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
