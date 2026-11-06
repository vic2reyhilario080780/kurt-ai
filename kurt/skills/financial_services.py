"""
KURT Financial Services Skills Catalog
Lahat ng 82 Financial services skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
FINANCIAL_SERVICES_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_financial_services.txt"

# Domain-based groupings for smart routing
FINANCIAL_SERVICES_DOMAINS = {
    "wealth_advisory": [
        "Claude for Financial Advisors", "BlackRock Advisor Center", "Vanguard Advisor Tools",
        "Zocks Advisor Intelligence", "Antevo Wealth", "Wealthbox",
        "MySSAgent for Financial Advisors", "ClientGen Reach", "Briefcase",
    ],
    "investment_research": [
        "Distilla Investment Research", "Blocksize Market Data", "venture-capital-intelligence",
        "coinpaprika", "PhaseFolio", "revelata", "Insider Trades", "sp-global",
        "finsharpe", "lseg", "PrivCo Data", "GulfPitch", "TickerTrac",
        "Fiscal.ai", "bitcoin-companies",
    ],
    "risk_compliance": [
        "Ansvar Compliance Skills", "ACI Risk Indicators", "RiskModels",
        "pyvar-credit-risk", "pyvar-market-risk", "pyvar-operational-risk",
        "pyvar-derivatives", "pyvar-liquidity-risk", "pyvar-regulatory",
        "pyvar-alm", "pyvar-mcp", "Intelligo", "Sammati DPDP Readiness",
        "RegAffairs AI", "Normlotse",
    ],
    "accounting_reporting": [
        "NetSuite Finance Analyst", "Chronograph LP", "Chronograph GP",
        "Statutory Reporting Plugin", "TRES Finance Plugin", "Numeric MCP Toolkit",
        "ubl-star — facturas electrónicas a Power BI", "Merit Aktiva for AI Agents",
        "KontoCSV", "extractos-ar", "YoFacturo", "Xestando", "Paušal", "DokladBot",
    ],
    "payments_fintech": [
        "Mercado Pago", "Paymob Integration", "BlindPay", "mastercard-developers",
        "airwallex-dev", "unipaas", "ArcKit UK Financial Services Payments Overlay",
        "Intuit Developer", "myocr.app", "waybill.ge",
    ],
    "fund_private_markets": [
        "Juniper Square", "Chronograph LP", "Chronograph GP", "private-credit",
        "Briefcase", "kap", "Silicon Floor", "IFG", "Stackin",
    ],
    "niche_specialized": [
        "Allium", "Corbis", "Worker K", "Brouky", "Ultralayer",
        "Fin3000", "FXMacroData", "Nonresident Tax", "Vivid",
        "Compabase", "Kabuken", "cortellis",
    ],
}

DOMAIN_PROMPTS = {
    "wealth_advisory": """You are an expert in wealth management and financial advisory.
Your expertise covers:
- Portfolio construction and asset allocation
- Client relationship management (CRM)
- Financial planning and goal setting
- Investment proposal generation
- Retirement planning and income strategies
- Risk tolerance assessment
- Regulatory compliance (fiduciary duty)
- Client communication and reporting
Deliver exceptional client outcomes through personalized advice.""",

    "investment_research": """You are an expert in investment research and analysis.
Your expertise covers:
- Equity and credit research
- Cryptocurrency and blockchain analytics
- Market data analysis and interpretation
- Venture capital and private company research
- Technical and fundamental analysis
- Investment thesis development
- Comparable company analysis
- Due diligence workflows
Make better investment decisions through rigorous research.""",

    "risk_compliance": """You are an expert in financial risk management and compliance.
Your expertise covers:
- Market, credit, operational, and liquidity risk modeling
- Regulatory compliance (Basel III, IFRS, GDPR, DPDP)
- Value-at-Risk (VaR) and stress testing
- Derivatives risk and valuation
- Asset-liability management (ALM)
- KYC/AML compliance workflows
- Regulatory reporting and submission
- Risk framework design and governance
Protect financial institutions through robust risk management.""",

    "accounting_reporting": """You are an expert in financial accounting and reporting.
Your expertise covers:
- ERP and accounting system integration (NetSuite)
- Statutory and regulatory reporting
- Electronic invoicing and billing (UBL, e-factura)
- Financial statement preparation and analysis
- Fund accounting and LP/GP reporting
- Tax compliance and reporting
- Chart of accounts design
- Automated reconciliation workflows
Ensure accurate, compliant financial reporting.""",

    "payments_fintech": """You are an expert in payments and fintech development.
Your expertise covers:
- Payment gateway integration (Mercado Pago, Paymob, Mastercard)
- Payment orchestration and routing
- Open banking and API integration
- Embedded finance and BaaS
- Fraud detection and prevention
- Payment compliance (PCI-DSS, PSD2)
- Mobile and digital wallet integration
- Cross-border payment solutions
Build seamless, secure payment experiences.""",

    "fund_private_markets": """You are an expert in fund operations and private markets.
Your expertise covers:
- LP/GP fund administration and reporting
- Portfolio company monitoring and reporting
- Capital call and distribution management
- Private credit and debt fund operations
- Fund performance analytics (IRR, TVPI, DPI)
- Investor relations and communication
- Fund compliance and regulatory reporting
- Alternative investment data management
Optimize fund operations for GPs and LPs.""",

    "niche_specialized": """You are a specialist in niche financial services tools.
Your expertise covers specialized solutions for:
- Blockchain and on-chain data analytics
- Regional financial market platforms
- Tax residency and non-resident compliance
- Specialized financial data providers
- Emerging market fintech platforms
Apply targeted expertise to unique financial challenges.""",
}


def load_all_skills() -> list[str]:
    """Load all 82 financial services skill names from file"""
    if FINANCIAL_SERVICES_SKILLS_FILE.exists():
        return [line.strip() for line in FINANCIAL_SERVICES_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for financial services skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in FINANCIAL_SERVICES_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific financial services skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    return f"""You are an expert in {skill_name}.
Apply financial services best practices:
- Maintain strict compliance with financial regulations
- Prioritize data accuracy and integrity
- Apply appropriate risk management frameworks
- Document all analysis and assumptions clearly
- Consider fiduciary responsibilities and client interests
- Use industry-standard financial models and methodologies
- Ensure auditability of all financial calculations
- Apply data privacy and security standards (GDPR, PCI-DSS)"""


def get_stats() -> dict:
    """Get stats about the financial services skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in FINANCIAL_SERVICES_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(FINANCIAL_SERVICES_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
