"""KURT Education Skills Catalog — 10 skills from Claude's marketplace"""
from pathlib import Path
from typing import Optional

EDUCATION_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_education.txt"

EDUCATION_DOMAINS = {
    "online_learning": ["Khan Academy", "Coursera Skills", "edX Skills", "Udemy Skills"],
    "language_learning": ["Duolingo"],
    "flashcards_quizzing": ["Anki", "Quizlet"],
    "classroom_tools": ["Kahoot", "Socrative", "Nearpod"],
}

DOMAIN_PROMPTS = {
    "online_learning": "You are an expert in online learning platforms. Help learners find courses, structure learning paths, and get the most from MOOCs and video-based education.",
    "language_learning": "You are an expert in language learning apps. Help users build consistent practice habits, maximize streak benefits, and master vocabulary and grammar.",
    "flashcards_quizzing": "You are an expert in spaced repetition and flashcard study. Help students create effective decks, optimize review schedules, and retain information long-term.",
    "classroom_tools": "You are an expert in interactive classroom engagement tools. Help educators create quizzes, polls, and interactive lessons for student participation.",
}

def load_all_skills() -> list[str]:
    if EDUCATION_SKILLS_FILE.exists():
        return [l.strip() for l in EDUCATION_SKILLS_FILE.read_text().splitlines() if l.strip()]
    return []

def search_skills(query: str) -> list[str]:
    return [s for s in load_all_skills() if query.lower() in s.lower()]

def get_domain_for_skill(skill_name: str) -> Optional[str]:
    sl = skill_name.lower()
    for domain, skills in EDUCATION_DOMAINS.items():
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
    domain_counts = {d: len(s) for d, s in EDUCATION_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(EDUCATION_DOMAINS), "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
