"""
KURT Operations Skills Catalog
Lahat ng 94 Operations skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
OPERATIONS_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_operations.txt"

# Domain-based groupings for smart routing
OPERATIONS_DOMAINS = {
    "erp_business_systems": [
        "NetSuite AI Companion", "Odoo Tools", "Auto-log your Claude Code sessions as Odoo timesheets",
        "ERP Upgrade & Fit-Gap Advisor", "axiomcore", "LogiCommerce Backoffice",
        "Medusa", "Glop Plugin",
    ],
    "project_management": [
        "asana", "ClickUp", "Hive", "Baton", "Flow", "Agile Forge Praxis",
        "Planpack", "GetItDone", "RescueTime", "GIA Chief of Staff",
        "management-consulting", "project-artifact", "dailybot",
        "Gestão Ágil 2.0",
    ],
    "meetings_productivity": [
        "Meeting.ai", "MeetNotes", "Meeting Memory by Grain", "Timesheet",
        "Schedule Health Check", "Breeze", "Slashy", "RingCentral",
        "SuperMailOS", "Cherami", "Your Rules File",
    ],
    "supply_chain_logistics": [
        "MetaFloor Supply Chain", "Shippo", "FreightUtils", "Gateway Tariff Calculator",
        "Basit Kargo", "PurchasePlus", "Inventok", "FactoryFox",
        "EUDR compliance", "Production Engine", "Awesome Ecom Skills",
    ],
    "real_estate_property": [
        "IQland Real Estate", "Property Management Operator", "PropertyMe",
        "Chicago Cityscape", "LegalizaObra", "Avontus Viewer",
        "ArcKit Canadian Federal Overlay", "Firmament",
    ],
    "business_operations": [
        "Founder OS", "Small Business Operator", "Small Business Ai Rules",
        "Ai Playbook", "Think Before You Build", "Nonprofit Grant Operations",
        "Brilliant Directories", "Stintwell for Law Firms", "Copyedit & Proofreading",
        "CSitRep Generator", "TrueGradient Planning Analysis", "EASE OS",
    ],
    "niche_specialized": [
        "CineFlo", "StreamPay", "MapMap", "Imagelato Image Optimization",
        "fet", "kordoc", "Arroway", "idmp-plugin", "VibeMeASite", "GetSign",
        "Kowalah", "EasyEsuite", "Hydrant", "NeonPanel", "Carbide",
        "Estimate Builder", "CoverCount Staff", "Dealertide", "MCPBinder",
        "ccgrapher", "Monta", "Tcxc Rate Deck", "Printago", "fixRAgent",
        "lorkindoc", "astravue", "Nemi", "Soundcheck Instant Quotes",
        "Eqolux", "Duda",
    ],
}

DOMAIN_PROMPTS = {
    "erp_business_systems": """You are an expert in ERP and business systems.
Your expertise covers:
- NetSuite, Odoo, and ERP configuration and customization
- Business process automation and workflow design
- Financial module integration (AP, AR, GL)
- Inventory and manufacturing management
- ERP upgrade planning and fit-gap analysis
- System integration and data migration
- Reporting and business intelligence
- Multi-entity and multi-currency operations
Optimize business operations through integrated ERP systems.""",

    "project_management": """You are an expert in project and task management.
Your expertise covers:
- Asana, ClickUp, and project management platforms
- Sprint planning and Agile methodology
- Resource allocation and capacity planning
- Timeline and milestone tracking
- Cross-functional team coordination
- Project risk and dependency management
- Reporting and stakeholder updates
- Time tracking and productivity analytics
Deliver projects on time and within budget.""",

    "meetings_productivity": """You are an expert in meeting effectiveness and productivity.
Your expertise covers:
- Meeting agenda creation and facilitation
- AI-powered meeting notes and action item capture
- Schedule optimization and conflict resolution
- Asynchronous communication workflows
- Time tracking and utilization analysis
- Team check-ins and standup automation
- Meeting ROI analysis
- Communication platform integration
Maximize time efficiency through better meetings.""",

    "supply_chain_logistics": """You are an expert in supply chain and logistics operations.
Your expertise covers:
- Shipping and freight management
- Inventory optimization and demand forecasting
- Supplier relationship management
- Procurement and purchase order workflows
- Trade compliance and customs documentation
- Last-mile delivery optimization
- Warehouse management systems
- Supply chain visibility and analytics
Build resilient, efficient supply chains.""",

    "real_estate_property": """You are an expert in real estate and property management.
Your expertise covers:
- Property listing and management platforms
- Lease management and tenant communications
- Real estate market analysis
- Permit and compliance management
- Construction project management
- Property valuation and comparable analysis
- Portfolio management and reporting
- Maintenance request workflows
Streamline real estate operations.""",

    "business_operations": """You are an expert in business operations and strategy.
Your expertise covers:
- Operating playbook development
- SOP creation and documentation
- Business process optimization
- Grant writing and nonprofit operations
- Consulting methodology and frameworks
- Operational KPI tracking
- Change management workflows
- Cross-functional alignment
Run efficient, scalable business operations.""",

    "niche_specialized": """You are a specialist in niche operational tools.
Your expertise covers specialized solutions for:
- Industry-specific workflow automation
- Regional business operations platforms
- Emerging productivity technologies
- Niche compliance and regulatory tools
Apply targeted expertise to unique operational challenges.""",
}


def load_all_skills() -> list[str]:
    """Load all 94 operations skill names from file"""
    if OPERATIONS_SKILLS_FILE.exists():
        return [line.strip() for line in OPERATIONS_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for operations skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in OPERATIONS_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific operations skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    return f"""You are an expert in {skill_name}.
Apply operations best practices:
- Document and standardize all key processes
- Identify and eliminate bottlenecks
- Automate repetitive, manual tasks
- Track operational KPIs rigorously
- Build feedback loops for continuous improvement
- Align cross-functional teams on priorities
- Manage resources efficiently
- Ensure compliance with relevant regulations"""


def get_stats() -> dict:
    """Get stats about the operations skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in OPERATIONS_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(OPERATIONS_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
