"""KURT Shopping Skills Catalog — 13 skills from Claude's marketplace"""
from pathlib import Path
from typing import Optional

SHOPPING_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_shopping.txt"

SHOPPING_DOMAINS = {
    "coupons_cashback": ["Honey Skills", "Capital One Shopping", "Rakuten", "RetailMeNot", "Coupon Cabin"],
    "price_tracking": ["ShopSavvy", "Price Spy", "CamelCamelCamel", "Keepa"],
    "deals": ["Slickdeals", "Brad's Deals", "DealNews", "The Penny Hoarder"],
}

DOMAIN_PROMPTS = {
    "coupons_cashback": "You are an expert in coupon and cashback strategies. Help shoppers maximize savings through promo codes, browser extensions, and cashback portals.",
    "price_tracking": "You are an expert in price tracking tools. Help shoppers monitor price history, set alerts, and time purchases for maximum savings.",
    "deals": "You are an expert in deal discovery. Help shoppers find the best deals, flash sales, and limited-time offers across categories.",
}

def load_all_skills() -> list[str]:
    if SHOPPING_SKILLS_FILE.exists():
        return [l.strip() for l in SHOPPING_SKILLS_FILE.read_text().splitlines() if l.strip()]
    return []

def search_skills(query: str) -> list[str]:
    return [s for s in load_all_skills() if query.lower() in s.lower()]

def get_domain_for_skill(skill_name: str) -> Optional[str]:
    sl = skill_name.lower()
    for domain, skills in SHOPPING_DOMAINS.items():
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
    domain_counts = {d: len(s) for d, s in SHOPPING_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(SHOPPING_DOMAINS), "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
