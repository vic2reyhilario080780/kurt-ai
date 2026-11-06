"""
KURT Finance Skills Catalog
Lahat ng 230 Finance skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
FINANCE_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_finance.txt"

# Domain-based groupings for smart routing
FINANCE_DOMAINS = {
    "investment_wealth": [
        "BlackRock Advisor Center", "Zocks Advisor Intelligence", "Vanguard Advisor Tools",
        "Distilla Investment Research", "AIResearch — Multi-Lens Stock Deep Dive",
        "StockPortfolio.pro — Verified Financial Data", "stock-portfolio-valuation",
        "Morningstar", "Chronograph LP", "Chronograph GP", "PrivCo Data",
        "Juniper Square", "Antevo Wealth", "WealthStoryLine", "Fin3000",
        "MySSAgent for Financial Advisors", "Retirement Estimator",
        "Retirement Cash Flow Planner", "pyvar-portfolio-analytics",
        "PhaseFolio", "FundFacts", "sp-global", "lseg", "Insider Trades",
        "AlphaYou", "LinqAlpha", "QuanterLab", "Distilla Investment Research",
        "venture-capital", "private-credit", "Briefcase",
    ],
    "accounting_erp": [
        "NetSuite Finance Analyst", "NetSuite SuiteSkills", "Intuit QuickBooks",
        "QuickBooks Labs", "freee", "Datarails financeos", "Accountable",
        "Finance & Ops Skills Index", "Acumatica Plugin", "Statutory Reporting Plugin",
        "SuperBooks", "Invoice Generator", "Invoice Matcher", "InsForge",
        "Granatum Financeiro", "YoFacturo", "facturillo", "myocr.app",
        "Bankstatemently", "DokladBot", "KontoCSV", "Receiptor AI",
        "Paušal", "extractos-ar", "ubl-star — facturas electrónicas a Power BI",
        "REST API for Perfex CRM", "Inventok",
    ],
    "payments_fintech": [
        "Stripe", "PayPal", "Mollie", "Payagentic", "Paymob Integration",
        "unipaas", "BlindPay", "Casapay Connect", "StreamPay", "Checkout Page",
        "koko-credit-cards", "Apollo Invoicing", "LogiCommerce Backoffice",
        "ArcKit UK Financial Services Payments Overlay", "Wingsp an",
        "Amazon Selling Partner", "MerchantFlow", "Setttle", "PandaDoc",
    ],
    "trading_crypto": [
        "TradingCalc", "TradeOS AI", "bitcoin-companies", "CryptoETF Flows",
        "CoinLobster", "Galleon DeFi Strategy", "Galleon DeFi Portfolio",
        "Blocksize Market Data", "EODHD Financial Data APIs", "TickerLayer",
        "TickerTrac", "Boersi", "FXMacroData", "snowball", "BlindOracle",
        "ACI Risk Indicators", "Squawkflow",
    ],
    "risk_insurance": [
        "RiskModels", "pyvar-credit-risk", "pyvar-market-risk", "pyvar-operational-risk",
        "pyvar-derivatives", "pyvar-liquidity-risk", "pyvar-alm", "pyvar-regulatory",
        "pyvar-mcp", "Swallow Insurance Rating Engine", "Pencil Underwriting",
        "IAseguro", "seal-copilot", "Nonresident Tax", "ITIN Finance",
        "pyvar-credit-risk", "Sprout: AI Finance & Cash Flow",
    ],
    "marketing_analytics": [
        "Windsor.ai Ads and Marketing Data", "AdCopilot for Google Ads, Google Analytics, Google Search Console & Google Tag Manager",
        "AdWhispr Ads & Marketing Agent", "Adspirer Advertising Agent",
        "Supermetrics Ads & Marketing Analytics", "dataslayer-marketing-skills",
        "Ryze AI Marketing Skills", "Admaxxer", "MARFOR Marketing Mix Modeling",
        "Trackian Marketing Analytics", "Adzviser", "fcxo-toolkit",
        "PartnerImpact", "Agency MCP", "RevOps Metrics Kit", "amg-toolkit",
        "JSON SEO",
    ],
    "cloud_cost_ops": [
        "Cloud FinOps by OptimNow", "aws-cost-audit", "DoiT Cloud Intelligence",
        "Costory FinOps Agent", "circle-skills", "management-consulting",
        "AssistantLabs — Personal Assistant for Business", "Masthead Data",
        "Timesheet", "CoverCount Staff", "CompanyTrack", "revelata",
        "FactIQ", "Decile", "Slice Global", "toolrouter", "Storeadops",
        "Found", "Zeno", "Remote.com", "Sana from Workday",
    ],
    "niche_specialized": [
        "Wingspan", "cashflow", "Small Business Operator", "cofounders",
        "Fiscal.ai", "CineFlo", "Worker K", "MakeBox for Etsy",
        "Economic Mind", "Claistore", "Music Catalog Diligence",
        "Production Engine", "TomeScout Toolkit", "One", "TRES Finance Plugin",
        "Obriym CRM", "Economico", "ViewsMax", "award-travel-finder",
        "octopus-ai", "finsharpe", "ololand-dd", "Brouky", "Headset",
        "Dealertide", "kap", "RoboSystems", "LinkJolt", "Silicon Floor",
        "Vivid", "Hammer Worlds", "TD SYNNEX Plugin", "Stackin",
        "Synter", "Tako", "Nogbase", "Eqolux", "Numeric MCP Toolkit",
        "Gateway Tariff Calculator", "Oxford Ledge", "Genaya", "Effective",
        "App Growth Calculator", "Xestando", "Minz.ai", "Kabuken",
        "Compabase", "Mattemena Nerve", "Nowistay", "SKU Margin",
        "Range Roofing Portal", "ShiftControl", "MosoFin", "EscapeBot",
        "waybill.ge", "Vino Alert", "Pay Nudger", "QRS", "Seenode",
        "DealFlowPro", "Essentio", "CopperJack", "EZ Flow Pro",
        "BetterOff", "Ultralayer", "Aqtos", "LegalizaObra", "NeonPanel",
        "CoinLobster", "Retenot", "Churn Prevention Kit", "inSitu Sales",
        "Referent", "pyvar-mcp", "RenooLab — Rénovation et artisans",
        "OnArrival Travel", "Sugra API Skills", "Interim", "LogiCommerce Backoffice",
        "Verus by Markst", "unipaas", "Genaya", "Effective",
    ],
}

# System prompt templates for each domain
DOMAIN_PROMPTS = {
    "investment_wealth": """You are an expert in investment and wealth management.
Your expertise covers:
- Portfolio construction and asset allocation
- Equity and fixed income analysis
- Alternative investments (PE, VC, credit)
- Wealth management and financial planning
- Retirement planning and income strategies
- Investment research and due diligence
- Performance attribution and reporting
- Risk-adjusted return analysis
Build comprehensive investment strategies for wealth creation.""",

    "accounting_erp": """You are an expert in accounting and ERP systems.
Your expertise covers:
- NetSuite, QuickBooks, and accounting software
- Financial statement preparation and analysis
- Invoicing, accounts payable/receivable
- General ledger management
- Tax compliance and reporting
- Month-end and year-end close processes
- Multi-currency and international accounting
- ERP configuration and customization
Streamline financial operations with efficient accounting workflows.""",

    "payments_fintech": """You are an expert in payments and fintech solutions.
Your expertise covers:
- Payment gateway integration (Stripe, PayPal, Mollie)
- Digital wallets and mobile payments
- Cross-border payment processing
- Payment reconciliation and settlement
- Subscription billing and recurring payments
- Fraud detection and prevention
- PCI compliance and security
- Open banking and API integrations
Build secure, scalable payment solutions.""",

    "trading_crypto": """You are an expert in trading and cryptocurrency markets.
Your expertise covers:
- Algorithmic trading strategies
- Cryptocurrency portfolio management
- DeFi protocols and yield optimization
- Technical analysis and charting
- Market data APIs and feeds
- Options and derivatives pricing
- Crypto tax and regulatory compliance
- Trading bot development
Navigate financial markets with data-driven trading strategies.""",

    "risk_insurance": """You are an expert in financial risk management and insurance.
Your expertise covers:
- Credit risk modeling and scoring
- Market risk (VaR, stress testing)
- Operational risk frameworks
- Derivatives valuation and hedging
- Insurance underwriting and pricing
- Regulatory compliance (Basel, Solvency II)
- Liquidity risk management
- Asset-liability management (ALM)
Build robust risk frameworks for financial stability.""",

    "marketing_analytics": """You are an expert in marketing analytics and advertising.
Your expertise covers:
- Multi-channel attribution modeling
- Google Ads and Meta Ads optimization
- Marketing mix modeling (MMM)
- Customer acquisition cost (CAC) analysis
- Return on ad spend (ROAS) optimization
- Marketing data integration and reporting
- SEO and content performance analytics
- Growth marketing strategies
Drive revenue with data-driven marketing analytics.""",

    "cloud_cost_ops": """You are an expert in cloud cost management and financial operations.
Your expertise covers:
- Cloud FinOps and cost optimization
- AWS, GCP, Azure cost analysis
- SaaS spend management
- Financial operations automation
- Revenue operations (RevOps) metrics
- Business intelligence and reporting
- Workforce management and timesheets
- Vendor management and procurement
Optimize cloud and operational costs for maximum efficiency.""",

    "niche_specialized": """You are a specialist in niche financial tools and solutions.
Your expertise covers specialized platforms for:
- Industry-specific financial workflows
- Regional and international financial tools
- Small business financial management
- Emerging fintech solutions
- Compliance and regulatory tools
Apply targeted financial tools to unique business challenges.""",
}


def load_all_skills() -> list[str]:
    """Load all 230 finance skill names from file"""
    if FINANCE_SKILLS_FILE.exists():
        return [line.strip() for line in FINANCE_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for finance skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in FINANCE_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific finance skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    return f"""You are an expert in {skill_name}.
Apply finance best practices:
- Ensure accuracy and compliance in all financial calculations
- Use data-driven approaches for financial analysis
- Maintain audit trails and documentation
- Apply relevant regulatory and accounting standards
- Optimize for efficiency and cost reduction
- Communicate financial insights clearly to stakeholders
- Manage risk with appropriate controls and safeguards"""


def get_stats() -> dict:
    """Get stats about the finance skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in FINANCE_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(FINANCE_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
