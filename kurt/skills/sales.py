"""
KURT Sales Skills Catalog
Lahat ng 84 Sales skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
SALES_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_sales.txt"

# Domain-based groupings for smart routing
SALES_DOMAINS = {
    "crm_pipeline": [
        "HubSpot Sales", "AI Context Bridge for HubSpot", "Revenue Analytics for HubSpot",
        "Sales Cloud", "Obriym CRM", "Wealthbox", "Revenue Grid", "Cargo",
        "CompanyTrack", "Crossbeam Skills", "Endgame", "Sales Follow-Up", "Follow-Up Writer",
        "SalesEQ", "Clearskies",
    ],
    "prospecting_leads": [
        "Leadfeeder", "apollo", "Hunter", "VibeLeads: B2B Lead Finder", "FullEnrich",
        "SalesQL", "LeadMagic", "fiber-ai-plugin", "GIA Prospecting Engine",
        "B2B Research: Market and Account", "Global Database", "Ripe Leads Cold Email Writer",
        "Cold Email, LinkedIn Outreach & Deliverability", "zime-skills",
    ],
    "financial_advisory": [
        "Claude for Financial Advisors", "BlackRock Advisor Center", "Vanguard Advisor Tools",
        "Zocks Advisor Intelligence", "Juniper Square", "MySSAgent for Financial Advisors",
        "finsharpe", "venture-capital-intelligence",
    ],
    "sales_enablement": [
        "B2b Sales Enablement", "Sales Enablement Kit", "Sales Skills by Arrows",
        "Pitch Deck Advisor", "hormozi-offer-audit", "Competitive Intel",
        "EULER for Partner Managers", "PartnerImpact", "Buyer Engagement Sales Engine -- Free",
        "The Hard Half", "toughtongue",
    ],
    "deals_proposals": [
        "PandaDoc", "Invoice Generator", "Templify by Irvito", "Apollo Invoicing",
        "Client Briefs", "Weekly Client Report", "AgentPricing Connector",
        "Brendly", "BidSkim - UK Tenders & Contract Renewals", "GovTribe",
    ],
    "recruiting_careers": [
        "Greenhouse", "Career Compass", "Career Navigator", "ACA Native MCP Skills",
        "MagicInterview", "Job Interview and Meeting Preparation", "NeverApply",
        "Worklittle Jobs", "cofounders", "AssistantLabs — Personal Assistant for Business",
    ],
    "niche_specialized": [
        "Amazon Selling Partner", "MakeBox for Etsy", "AmpUp MCP Plugin",
        "MyChatBot", "Consultant Assignments", "Anysite GTM", "fcxo-toolkit",
        "YnotOne", "Decile", "Tirion", "anVendor", "ChatDaddy",
        "Bigmind", "Brouky", "Headset", "Intelligo",
    ],
}

DOMAIN_PROMPTS = {
    "crm_pipeline": """You are an expert in CRM and sales pipeline management.
Your expertise covers:
- HubSpot, Salesforce, and CRM data management
- Pipeline stage tracking and velocity optimization
- Deal scoring and prioritization
- Sales activity logging and follow-up automation
- Revenue forecasting and analytics
- Cross-sell and upsell identification
- Account health monitoring
- CRM data hygiene and deduplication
Drive revenue growth through systematic pipeline management.""",

    "prospecting_leads": """You are an expert in B2B prospecting and lead generation.
Your expertise covers:
- ICP (Ideal Customer Profile) definition and targeting
- Contact and account data enrichment
- Cold outreach email and LinkedIn sequences
- Lead scoring and qualification frameworks
- Intent data analysis
- Multi-channel prospecting workflows
- Deliverability optimization
- Appointment setting and SDR workflows
Build a predictable pipeline through systematic prospecting.""",

    "financial_advisory": """You are an expert in financial advisory and wealth management.
Your expertise covers:
- Investment portfolio analysis and reporting
- Client relationship management for advisors
- Regulatory compliance (FINRA, SEC, fiduciary)
- Financial planning workflows
- Advisor productivity tools
- Venture capital and private equity intelligence
- Market data and analytics integration
- Client communication and reporting
Deliver exceptional financial advisory services.""",

    "sales_enablement": """You are an expert in sales enablement and performance.
Your expertise covers:
- Sales playbook creation and enforcement
- Competitive battlecards and positioning
- Pitch coaching and objection handling
- Sales training and onboarding content
- Win/loss analysis
- Partner and channel enablement
- Sales methodology frameworks (MEDDIC, SPIN, Challenger)
- Performance analytics and coaching
Equip sales teams to win more deals.""",

    "deals_proposals": """You are an expert in deal execution and proposal management.
Your expertise covers:
- Proposal and quote generation
- Contract and document management
- Pricing strategy and configuration
- E-signature and approval workflows
- Government and public sector tendering
- Invoicing and billing automation
- Deal room management
- Contract lifecycle management
Close deals faster with professional proposals.""",

    "recruiting_careers": """You are an expert in recruiting and career development.
Your expertise covers:
- ATS (Applicant Tracking System) management
- Interview preparation and coaching
- Job description writing and optimization
- Candidate sourcing and outreach
- Career path planning and navigation
- Offer negotiation support
- Onboarding workflow automation
- Talent acquisition analytics
Build great teams and advance careers.""",

    "niche_specialized": """You are a specialist in niche sales and commerce tools.
Your expertise covers specialized solutions for:
- E-commerce and marketplace selling (Amazon, Etsy)
- Industry-specific CRM solutions
- Emerging sales technology
- Regional sales platforms
- Niche market development
Apply targeted expertise to unique sales challenges.""",
}


def load_all_skills() -> list[str]:
    """Load all 84 sales skill names from file"""
    if SALES_SKILLS_FILE.exists():
        return [line.strip() for line in SALES_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for sales skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in SALES_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific sales skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    return f"""You are an expert in {skill_name}.
Apply sales best practices:
- Understand the buyer's journey and decision process
- Qualify opportunities with proven frameworks
- Personalize outreach for maximum relevance
- Track and optimize pipeline metrics
- Build relationships that drive long-term revenue
- Use data to prioritize the highest-value activities
- Automate repetitive tasks to focus on selling
- Continuously improve based on win/loss analysis"""


def get_stats() -> dict:
    """Get stats about the sales skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in SALES_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(SALES_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
