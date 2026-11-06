"""KURT Customer Support Skills Catalog — 30 skills from Claude's marketplace"""
from pathlib import Path
from typing import Optional

CUSTOMER_SUPPORT_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_customer_support.txt"

CUSTOMER_SUPPORT_DOMAINS = {
    "help_desk": ["Zendesk Skills", "Freshdesk", "Help Scout", "Zoho Desk", "Kayako", "Groove", "HappyFox", "Kustomer"],
    "messaging": ["Intercom Skills", "Front", "Hiver", "Missive", "Helpwise", "Reamaze", "Gorgias", "Re:amaze"],
    "live_chat": ["Tidio", "LiveChat", "Olark", "Drift", "Crisp", "Chatra", "Smartsupp", "Tawk.to"],
    "feedback": ["UserVoice", "Canny", "Productboard Support", "Pendo Support", "Mixpanel Support", "Amplitude Support"],
}

DOMAIN_PROMPTS = {
    "help_desk": "You are an expert in help desk and ticketing systems. Help configure ticket routing, SLA policies, canned responses, and agent workflows for efficient customer support.",
    "messaging": "You are an expert in shared inbox and messaging tools for support teams. Help set up team inboxes, assignments, and collaborative support workflows.",
    "live_chat": "You are an expert in live chat and chatbot configuration. Help design chat flows, set up proactive messaging, and train chatbots for common support scenarios.",
    "feedback": "You are an expert in customer feedback and product analytics tools. Help collect, categorize, and act on customer feedback to improve products and services.",
}

def load_all_skills() -> list[str]:
    if CUSTOMER_SUPPORT_SKILLS_FILE.exists():
        return [l.strip() for l in CUSTOMER_SUPPORT_SKILLS_FILE.read_text().splitlines() if l.strip()]
    return []

def search_skills(query: str) -> list[str]:
    return [s for s in load_all_skills() if query.lower() in s.lower()]

def get_domain_for_skill(skill_name: str) -> Optional[str]:
    sl = skill_name.lower()
    for domain, skills in CUSTOMER_SUPPORT_DOMAINS.items():
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
    domain_counts = {d: len(s) for d, s in CUSTOMER_SUPPORT_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(CUSTOMER_SUPPORT_DOMAINS), "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
