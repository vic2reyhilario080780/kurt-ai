"""KURT Events Skills Catalog — 31 skills from Claude's marketplace"""
from pathlib import Path
from typing import Optional

EVENTS_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_events.txt"

EVENTS_DOMAINS = {
    "enterprise_events": ["Eventbrite", "Cvent", "Bizzabo", "Splash", "Swoogo", "Attendease"],
    "virtual_hybrid": ["Hopin", "Hubilo", "Airmeet", "Brella", "Swapcard", "Grip", "Accelevents"],
    "ticketing": ["RegFox", "Luma", "Partiful", "RSVPify", "Ticket Tailor", "TicketSpice", "Universe", "Oveit", "Konfeo", "Eventzilla", "EventCreate"],
    "conference_cfp": ["Whova", "Sched", "Sessionize", "Papercall", "Pretalx"],
    "community": ["Meetup Skills", "AllEvents"],
}

DOMAIN_PROMPTS = {
    "enterprise_events": "You are an expert in enterprise event management. Help plan, promote, and execute large-scale corporate events, conferences, and trade shows.",
    "virtual_hybrid": "You are an expert in virtual and hybrid event platforms. Help maximize engagement, networking, and production quality for online and hybrid events.",
    "ticketing": "You are an expert in event ticketing and registration. Help set up ticket tiers, promo codes, check-in workflows, and registration forms.",
    "conference_cfp": "You are an expert in conference scheduling and call-for-proposals. Help manage speaker submissions, session scheduling, and attendee agendas.",
    "community": "You are an expert in community event organization. Help build recurring meetup cadences, grow community attendance, and foster member engagement.",
}

def load_all_skills() -> list[str]:
    if EVENTS_SKILLS_FILE.exists():
        return [l.strip() for l in EVENTS_SKILLS_FILE.read_text().splitlines() if l.strip()]
    return []

def search_skills(query: str) -> list[str]:
    return [s for s in load_all_skills() if query.lower() in s.lower()]

def get_domain_for_skill(skill_name: str) -> Optional[str]:
    sl = skill_name.lower()
    for domain, skills in EVENTS_DOMAINS.items():
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
    domain_counts = {d: len(s) for d, s in EVENTS_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(EVENTS_DOMAINS), "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
