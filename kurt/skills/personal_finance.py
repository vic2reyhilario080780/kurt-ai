"""KURT Personal Finance Skills Catalog — 35 skills from Claude's marketplace"""
from pathlib import Path
from typing import Optional

PERSONAL_FINANCE_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_personal_finance.txt"

PERSONAL_FINANCE_DOMAINS = {
    "budgeting": ["Copilot Money", "YNAB", "Monarch Money", "Simplifi by Quicken", "Rocket Money", "PocketGuard", "Goodbudget", "Spendee", "Budgetbakers", "Mvelopes", "Honeydue", "Zeta"],
    "investing": ["Personal Capital", "Empower", "Acorns", "Betterment", "Wealthfront", "Stash", "Fidelity AI", "Schwab Intelligent Portfolios", "Robinhood Skills"],
    "credit_debt": ["Credit Karma", "NerdWallet", "Bankrate", "Experian Boost", "Credit Sesame", "Debt Payoff Planner", "Undebt.it", "Payoff", "Snowball Debt"],
    "tools_apps": ["Tiller Money", "MagnifyMoney", "LendingTree", "Albert", "Cleo"],
}

DOMAIN_PROMPTS = {
    "budgeting": "You are an expert in personal budgeting. Help users track spending, create budgets, and develop healthy financial habits using zero-based budgeting, envelope methods, and automated tracking.",
    "investing": "You are an expert in personal investing. Guide users on portfolio allocation, robo-advisors, retirement accounts, and building long-term wealth through diversified investments.",
    "credit_debt": "You are an expert in credit and debt management. Help improve credit scores, create debt payoff strategies (avalanche/snowball), and navigate credit monitoring tools.",
    "tools_apps": "You are an expert in personal finance apps. Help users choose and maximize personal finance tools for their specific financial situation and goals.",
}

def load_all_skills() -> list[str]:
    if PERSONAL_FINANCE_SKILLS_FILE.exists():
        return [l.strip() for l in PERSONAL_FINANCE_SKILLS_FILE.read_text().splitlines() if l.strip()]
    return []

def search_skills(query: str) -> list[str]:
    return [s for s in load_all_skills() if query.lower() in s.lower()]

def get_domain_for_skill(skill_name: str) -> Optional[str]:
    sl = skill_name.lower()
    for domain, skills in PERSONAL_FINANCE_DOMAINS.items():
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
    domain_counts = {d: len(s) for d, s in PERSONAL_FINANCE_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(PERSONAL_FINANCE_DOMAINS), "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
