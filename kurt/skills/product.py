"""
KURT Product Skills Catalog
Lahat ng 95 Product skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
PRODUCT_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_product.txt"

# Domain-based groupings for smart routing
PRODUCT_DOMAINS = {
    "product_management": [
        "lean-pm-skills", "ai-pm-skills", "The Pragmatic PM Toolkit", "AgileHero",
        "Agile Product", "plan-review-skill", "PRP Manager", "build-companion",
        "product-discovery-flow", "pm-augmente", "planning-skills-for-agents-and-humans",
        "Portfolio Interview", "prepkit-product", "Advisory Council",
    ],
    "analytics_metrics": [
        "Pendo Analytics", "Pendo Guides", "posthog", "amplitude", "Mixpanel",
        "Fullstory", "Adapty", "AppFollow AI Toolkit", "app-review",
        "App Review Companion", "Product Tracking", "Stateful",
        "Cairn Signals — are your AI product's numbers real?",
        "CRO Audit and Test Kit", "asodev", "ASO Atlas",
    ],
    "strategy_research": [
        "strategy-frameworks", "strategy consultant", "strategy-pack",
        "Market Intelligence", "Competitive Skills by LMTY",
        "Go-to-Market Planner", "venture", "AI Adoption Playbook",
        "paper-review-system", "TheBoardroom", "ycofficehour",
        "Verisk Underwriting Intelligence", "medidata",
    ],
    "ux_design": [
        "ux-superpowers", "Customer Research Kit", "Agentic user research at scale",
        "User Intuition", "Conveo", "brief-interview", "qualitati",
        "Screen Browser", "let-people-workshop", "antiagree",
        "devil-advocate", "devils-advocate", "Naysayer",
    ],
    "ideation_innovation": [
        "Incubator", "idea-launch", "Hypotize", "Discovery To Mvp",
        "POC Architect by ATeam", "Think Before You Build equivalent - product",
        "Prompt Coach", "AI-Native OS", "Game Trend Skills",
        "mindpowers", "Make My Product Clear", "Greenflash",
    ],
    "content_publishing": [
        "notion", "/workflow-audit", "LaunchNotes", "Writers' Room",
        "Copycat", "FluidDocs Deck Builder", "ThemeReviewKit",
        "Site Architecture & Faceted Navigation", "Replo",
    ],
    "niche_specialized": [
        "Noibu", "Maven Bio", "Zentrik", "carusela", "arn-spark",
        "Gambit", "cairo", "signal-hunter", "Simplio3D", "maddog",
        "Usero", "Cladeon", "closedloop-skills", "hive",
        "PlausibleBA — Business Architecture Skills", "Stunt Double",
        "Toego", "Syndic8", "saas-corpus",
    ],
}

DOMAIN_PROMPTS = {
    "product_management": """You are an expert in product management.
Your expertise covers:
- Product roadmap development and prioritization
- Agile/Scrum methodologies and sprint planning
- Requirements gathering and specification writing
- Stakeholder alignment and communication
- Product metrics definition and tracking
- Backlog grooming and story writing
- Release planning and go-to-market coordination
- PM interview preparation and portfolio building
Build products that users love and drive business growth.""",

    "analytics_metrics": """You are an expert in product analytics and metrics.
Your expertise covers:
- Event tracking and funnel analysis
- Retention and cohort analysis
- A/B testing and experimentation
- App store optimization (ASO)
- User behavior analytics (heatmaps, session replays)
- KPI dashboards and reporting
- Growth metrics and North Star framework
- Mobile app analytics
Make data-driven product decisions.""",

    "strategy_research": """You are an expert in product strategy and market research.
Your expertise covers:
- Market sizing and opportunity analysis
- Competitive landscape mapping
- Go-to-market strategy development
- Business model design and validation
- Strategic frameworks (Jobs-to-be-Done, Blue Ocean)
- Venture and startup strategy
- Industry research and trend analysis
- Executive stakeholder communication
Define winning product strategies.""",

    "ux_design": """You are an expert in UX research and design.
Your expertise covers:
- User interview design and facilitation
- Usability testing methodologies
- Persona and journey map creation
- Information architecture and navigation design
- Prototyping and design critique
- Accessibility standards and best practices
- Design sprint facilitation
- Voice of customer programs
Create products people genuinely want to use.""",

    "ideation_innovation": """You are an expert in product ideation and innovation.
Your expertise covers:
- Brainstorming facilitation and ideation techniques
- Hypothesis formation and validation
- MVP scoping and definition
- POC architecture and feasibility assessment
- AI-powered product development
- Innovation frameworks and methodologies
- Opportunity identification and prioritization
- Concept testing and feedback collection
Launch innovative products faster.""",

    "content_publishing": """You are an expert in product content and documentation.
Your expertise covers:
- Product documentation and knowledge bases
- Release notes and changelog management
- Content strategy and information architecture
- Technical writing for product teams
- Landing page optimization
- SEO and content distribution
- Workflow documentation
- Publication and CMS management
Communicate product value clearly.""",

    "niche_specialized": """You are a specialist in niche product tools.
Your expertise covers specialized solutions for:
- Vertical-specific product platforms
- Emerging product methodologies
- Domain-specific analytics and tracking
- Niche market product development
Apply targeted expertise to unique product challenges.""",
}


def load_all_skills() -> list[str]:
    """Load all 95 product skill names from file"""
    if PRODUCT_SKILLS_FILE.exists():
        return [line.strip() for line in PRODUCT_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for product skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in PRODUCT_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific product skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    return f"""You are an expert in {skill_name}.
Apply product management best practices:
- Start with deep user understanding and empathy
- Define clear success metrics before building
- Prioritize ruthlessly based on impact and effort
- Build, measure, learn in short cycles
- Communicate product vision compellingly
- Balance user needs with business objectives
- Make decisions based on data and evidence
- Ship incrementally and iterate based on feedback"""


def get_stats() -> dict:
    """Get stats about the product skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in PRODUCT_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(PRODUCT_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
