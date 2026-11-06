"""KURT Travel Skills Catalog — 25 skills from Claude's marketplace"""
from pathlib import Path
from typing import Optional

TRAVEL_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_travel.txt"

TRAVEL_DOMAINS = {
    "booking": ["TripIt", "Google Travel", "Expedia Skills", "Booking.com Skills", "Airbnb Skills", "VRBO Skills", "Kayak", "Skyscanner", "Hopper"],
    "planning": ["Rome2rio", "Wanderlog", "Roadtrippers", "Tripadvisor Skills", "Yelp Travel", "Atlas Obscura", "Culture Trip"],
    "guides": ["Lonely Planet", "Fodor's Travel"],
    "experiences": ["Viator", "GetYourGuide", "Klook"],
    "insurance_esim": ["Airalo", "Nomad Insurance", "SafetyWing", "World Nomads"],
}

DOMAIN_PROMPTS = {
    "booking": "You are an expert in travel booking platforms. Help find the best flights, hotels, and rentals, compare prices across platforms, and optimize booking strategies.",
    "planning": "You are an expert in trip planning tools. Help build detailed itineraries, discover hidden gems, and organize multi-destination travel efficiently.",
    "guides": "You are an expert in travel guides and destination research. Provide in-depth destination information, cultural tips, and travel recommendations.",
    "experiences": "You are an expert in tours and experiences. Help find and book the best local activities, tours, and experiences at destinations worldwide.",
    "insurance_esim": "You are an expert in travel insurance and connectivity. Help travelers choose appropriate insurance coverage and eSIM data plans for international travel.",
}

def load_all_skills() -> list[str]:
    if TRAVEL_SKILLS_FILE.exists():
        return [l.strip() for l in TRAVEL_SKILLS_FILE.read_text().splitlines() if l.strip()]
    return []

def search_skills(query: str) -> list[str]:
    return [s for s in load_all_skills() if query.lower() in s.lower()]

def get_domain_for_skill(skill_name: str) -> Optional[str]:
    sl = skill_name.lower()
    for domain, skills in TRAVEL_DOMAINS.items():
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
    domain_counts = {d: len(s) for d, s in TRAVEL_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(TRAVEL_DOMAINS), "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
