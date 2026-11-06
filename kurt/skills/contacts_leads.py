"""
KURT Contacts & Leads Skills Catalog
Lahat ng 246 Contacts & leads skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
CONTACTS_LEADS_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_contacts_leads.txt"

# Domain-based groupings for smart routing
CONTACTS_LEADS_DOMAINS = {
    "crm_sales": [
        "HubSpot Sales", "AI Context Bridge for HubSpot", "Revenue Analytics for HubSpot",
        "Sales Cloud", "Acumatica Plugin", "NetSuite SuiteSkills", "Obriym CRM",
        "Bizopa CRM", "Chiho.ai Telegram CRM", "itinovo CRM", "Wealthbox",
        "CompanyTrack", "Crossbeam Skills", "inSitu Sales", "Featurebase",
        "Sales Skills by Arrows", "Sales Follow-Up", "closedloop-skills",
        "Endgame", "Referent", "Aria", "Standards", "Robin", "Tirion",
        "ChatDaddy", "Lark/Feishu Integration", "RingCentral", "MyChatBot",
        "Unofficial Telegram MCP", "PropertyMe", "Property Management Operator",
        "Juniper Square", "Wealthbox", "Bonusly", "Customer.io", "KlickTipp",
        "Loops", "Kudosity SMS", "Mailercloud",
    ],
    "b2b_prospecting": [
        "Hunter", "apollo", "B2B Research: Market and Account", "VibeLeads: B2B Lead Finder",
        "Lead Magnets", "LeadMagic", "RocketReach", "SalesQL", "diffbot",
        "FullEnrich", "Cargo", "Global Database", "Mysocial Intelligence",
        "Market Intelligence", "B2B Events, PR and Launches", "Anysite GTM",
        "BAMF.ai", "fcxo-toolkit", "PartnerImpact", "fiber-ai-plugin",
        "Cold Email, LinkedIn Outreach & Deliverability", "Ripe Leads Cold Email Writer",
        "WarmySender", "Warmerly", "ClientGen Reach", "GIA Prospecting Engine",
        "PumpGTM", "Datakart", "overloop", "lead411", "Letterdrop",
        "KiteGTM", "Reo.Dev Your Developer GTM Copilot", "enrichley",
        "Sales Retriever", "Nitrosend", "Zillasales", "BuyerCaddy",
        "Upfunnels", "Swoop - X.com listening", "Preyreach", "Folkso",
        "opentriangle", "MORVS",
    ],
    "job_search_career": [
        "Career Coaching", "Career Compass", "Career Desk", "Career Navigator",
        "Job Search by Develop21", "Job Hunt Copilot (India)", "GetYourJob",
        "GetEmployed", "MagicInterview", "PokeBot.ai Career Coach", "NeverApply",
        "fix-cv-find-job-skill", "JD Resume Tailor", "ApplyArc", "MentorCruise",
        "Worklittle Jobs", "FoundRole Jobs", "RolePark", "oJobinho",
        "Радар вакансий", "Raily", "EULER for Partner Managers",
        "Consultant Assignments", "cofounders",
    ],
    "marketing_outreach": [
        "ActiveCampaign", "Windsor.ai Ads and Marketing Data", "Adology — Content Intelligence",
        "Agency MCP", "Hyper Marketing", "Mysocial Intelligence", "Dash Social",
        "Arcade", "Splashify Pro", "Banger", "BuzzBit X", "PodPitch",
        "Letterdrop", "Gratefully", "Anysite GTM", "Sales Follow-Up",
        "AssistantLabs — Personal Assistant for Business", "Sent", "Sendly",
        "Mailercloud", "black-label-presence", "SPACEXPLORATION", "Incubae",
        "JoomPulse", "turtini", "RedReplier", "Gurusup Brain",
    ],
    "financial_advisors": [
        "Claude for Financial Advisors", "Zocks Advisor Intelligence",
        "MySSAgent for Financial Advisors", "Wealthbox", "Fin3000",
        "TRES Finance Plugin", "PrivCo Data", "Juniper Square",
        "Wingspan", "Economico", "YoFacturo", "freee", "Compabase",
        "Apollo Invoicing", "Checkout Page", "Clinch",
    ],
    "hr_recruiting": [
        "Greenhouse", "Windmill HR", "UKG Bryte", "Lusha Talent Sourcing",
        "comp-skills", "Intelligo", "CoverCount Staff", "Worklittle Jobs",
        "FoundRole Jobs", "Worklittle Jobs", "Remote.com", "Bonusly",
        "Bigmind", "Brouky", "MagicInterview", "GetEmployed",
        "DiscoLike", "Zeeg",
    ],
    "real_estate_property": [
        "PropertyMe", "Property Management Operator", "cicada.guide",
        "Juniper Square", "Funraise Taiwan Real Estate", "RenooLab — Rénovation et artisans",
        "LegalizaObra", "Renou", "Nowistay",
    ],
    "customer_success": [
        "Customer Research Kit", "Customer Success: Churn and QBRs",
        "Asyntai – AI Support Agent for Websites", "SiteGPT", "FrontDesk Chat",
        "VibeCS support chat", "User Intuition", "Featurebase",
        "Brilliant Directories", "Clientmate", "MyChatBot", "Glean",
        "DialogBrain", "Resurface", "Syft AI", "CallRemind",
    ],
    "data_enrichment": [
        "HasData", "diffbot", "Global Database", "FullEnrich", "PrivCo Data",
        "Middesk", "Intuizi", "Decile", "Intelligo", "ClearBounce Email Verification",
        "Postproxy", "anVendor", "Trupeo", "Datakart", "Carbide",
        "TD SYNNEX Plugin", "Slice Global", "Athena by Zeta",
    ],
    "niche_specialized": [
        "Leadfeeder", "Revenue Grid", "instagram", "Voicenter API Skills",
        "ACA Native MCP Skills", "UnifAPI", "Manifold", "Lark/Feishu Integration",
        "BOLD Studios", "Document Vault", "Sent", "award-travel-finder",
        "The Hard Half", "YnotOne", "BidSkim - UK Tenders & Contract Renewals",
        "Cala", "Aqtos", "zime-skills", "tlgr", "saleshandy-plugin",
        "Vivid", "Upfunnels", "Freelaw Studio", "apMZoomAI · Dongdaemun wholesale",
        "Rav Messer", "FactoryFox", "Topo", "Karrito", "Genaya", "Dopia",
        "Unreasonable Eco", "Oktio.app", "Xestando", "LiteTMS",
        "Minz.ai", "Formify Core", "ShiftControl", "iMario",
        "Lovelio", "Itha", "Tweener", "Warmerly", "Stalwart Mail",
        "Vruum", "EZ Flow Pro", "Eryx", "VCupid", "I Do Crew",
        "i118 Phone Assistant", "SysIgreja", "SuperMe", "Small Business Operator",
        "AncestralFire", "Mokaru", "Kube by Kuberno", "Airship Agent Tools",
        "cicada.guide", "Airship Agent Tools",
    ],
}

# System prompt templates for each domain
DOMAIN_PROMPTS = {
    "crm_sales": """You are an expert in CRM systems and sales operations.
Your expertise covers:
- HubSpot Sales Hub configuration and automation
- Salesforce Sales Cloud workflows and integrations
- CRM data management and pipeline optimization
- Sales activity tracking and reporting
- Customer relationship management best practices
- Multi-channel communication (Telegram, Lark, RingCentral)
- Revenue analytics and forecasting
- Deal stage management and automation
Build scalable CRM processes that drive revenue growth.""",

    "b2b_prospecting": """You are an expert in B2B lead generation and prospecting.
Your expertise includes:
- LinkedIn outreach and Sales Navigator automation
- Email prospecting and cold outreach sequences
- Account-based marketing (ABM) strategies
- Lead enrichment and data quality management
- Intent data and buying signals
- Multi-channel prospecting (email, LinkedIn, phone)
- B2B database management and list building
- Sales development representative (SDR) workflows
Generate high-quality B2B pipeline at scale.""",

    "job_search_career": """You are an expert in career development and job searching.
Your expertise covers:
- Resume writing and optimization (ATS-friendly)
- LinkedIn profile optimization
- Job application strategy and tracking
- Interview preparation and coaching
- Career transition planning
- Salary negotiation tactics
- Networking and personal branding
- Job market research by industry and location
Accelerate career growth with strategic job search tactics.""",

    "marketing_outreach": """You are an expert in marketing outreach and demand generation.
Your expertise includes:
- Email marketing campaigns and automation
- Social media marketing and analytics
- Content marketing and lead magnets
- Marketing attribution and ROI tracking
- Multi-channel campaign orchestration
- Brand awareness and thought leadership
- Influencer and partner marketing
- Marketing analytics and performance reporting
Drive leads and pipeline through strategic marketing.""",

    "financial_advisors": """You are an expert in tools for financial advisors and wealth management.
Your expertise covers:
- Financial advisor CRM and client management
- Investment proposal and presentation tools
- Client onboarding and compliance workflows
- Portfolio reporting and performance tracking
- Advisor productivity and practice management
- Regulatory compliance (FINRA, SEC) tools
- Client communication and meeting prep
- Fee billing and invoicing for advisory firms
Build exceptional financial advisory practices with technology.""",

    "hr_recruiting": """You are an expert in HR technology and recruiting.
Your expertise includes:
- Applicant tracking systems (ATS) and recruiting workflows
- Candidate sourcing and talent acquisition
- Employee onboarding and offboarding
- HR analytics and workforce planning
- Compensation benchmarking and analysis
- Performance management systems
- HR compliance and policy management
- Diversity and inclusion recruiting strategies
Build scalable, data-driven talent acquisition processes.""",

    "real_estate_property": """You are an expert in real estate and property management technology.
Your expertise covers:
- Property management software and automation
- Real estate CRM and lead management
- Tenant communication and lease management
- Property listing and marketing tools
- Construction and renovation project management
- Real estate compliance and legal documentation
- Investment property analysis
- Short-term rental management
Optimize real estate operations with the right technology stack.""",

    "customer_success": """You are an expert in customer success and support technology.
Your expertise includes:
- Customer health scoring and churn prediction
- QBR (Quarterly Business Review) preparation
- Customer onboarding and adoption workflows
- Support ticket management and automation
- Customer feedback and NPS collection
- Self-service portal and knowledge base management
- Customer communication automation
- Expansion revenue and upsell identification
Maximize customer lifetime value and reduce churn.""",

    "data_enrichment": """You are an expert in contact and company data enrichment.
Your expertise covers:
- Contact data verification and email validation
- Company firmographic data enrichment
- Intent data and technographic profiling
- Data hygiene and deduplication
- CRM data quality management
- Third-party data integration and API management
- Identity resolution and contact matching
- Compliance (GDPR, CCPA) for data management
Build clean, accurate, and actionable prospect databases.""",

    "niche_specialized": """You are a specialist in niche sales and marketing tools.
Your expertise covers specialized platforms for:
- Specific industry verticals and use cases
- International and regional market tools
- Emerging sales and marketing technologies
- Niche workflow automation solutions
- Specialized compliance and regulatory tools
Apply targeted tools to solve unique go-to-market challenges.""",
}


def load_all_skills() -> list[str]:
    """Load all 246 contacts & leads skill names from file"""
    if CONTACTS_LEADS_SKILLS_FILE.exists():
        return [line.strip() for line in CONTACTS_LEADS_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for contacts & leads skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in CONTACTS_LEADS_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific contacts & leads skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    # Generic prompt for skills not in a specific domain
    return f"""You are an expert in {skill_name}.
Apply contacts and leads best practices:
- Build and maintain high-quality prospect databases
- Create personalized, relevant outreach at scale
- Track and optimize conversion rates at every funnel stage
- Use data to prioritize the highest-value opportunities
- Automate repetitive tasks to focus on relationship building
- Comply with data privacy regulations (GDPR, CAN-SPAM, CCPA)
- Measure and report on pipeline and revenue impact"""


def get_stats() -> dict:
    """Get stats about the contacts & leads skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in CONTACTS_LEADS_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(CONTACTS_LEADS_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
