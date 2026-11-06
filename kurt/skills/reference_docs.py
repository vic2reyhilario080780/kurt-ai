"""
KURT Reference Docs Skills Catalog
Lahat ng 324 Reference Docs skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
REFERENCE_DOCS_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_reference_docs.txt"

# Domain-based groupings for smart routing
REFERENCE_DOCS_DOMAINS = {
    "legal_research": [
        "litigation-legal", "cocounsel-legal", "law-student", "legal-clinic",
        "corporate-legal", "privacy-legal", "regulatory-legal", "ai-governance-legal",
        "employment-legal", "commercial-legal", "ip-legal", "LawDiver",
        "Legalcode", "Codigo Civil Formulacion Juridica", "Litigación Civil España",
        "Litigación Contencioso-Administrativa España", "Litigación Laboral España",
        "Litigación Penal España", "Compliance ES", "Polskie Prawo",
        "regai — Vietnamese Legal Consultant", "Extranjería España",
        "Contratos Civiles y Mercantiles", "OpenCase", "FluidityIQ Patent Intelligence",
        "Data Protection", "GDPRGard Compliance Skills", "Lexbeam EU AI Governance",
        "norma-claude-skill", "EUDR compliance", "realLaw AI", "Ragjur",
        "UCE Evidence Lens", "Nonresident Tax", "ITIN Finance",
        "ACI Risk Indicators", "Ansvar Compliance Skills",
    ],
    "knowledge_documentation": [
        "notion", "GitBook", "microsoft-docs", "wikipedia", "doc-authoring-skills",
        "notion-memory", "context7", "Glean", "glean-dev-docs", "diataxis",
        "system-design-skills", "ag2-agent-guide", "agent-context-kit",
        "loop-and-gate-foundation", "guide", "scriptorium-cowork",
        "Scio Knowledge", "conotate", "Contentstack Vibe Docs",
        "Sadakio Developer Docs", "Release Notes Index", "duckdb-skills",
    ],
    "market_research": [
        "Research Desk", "research-superpowers", "B2B Research: Market and Account",
        "AIResearch — Multi-Lens Stock Deep Dive", "Market Intelligence",
        "Competition Checker", "Competitive Skills by LMTY", "CompanyTrack",
        "Fiscal.ai", "FXMacroData", "StarGlass Research", "Everest Group AI",
        "Dossierfy", "BidSkim - UK Tenders & Contract Renewals",
        "vectorgov", "GovTribe", "GulfPitch", "lotlytics",
        "Economic Mind", "Big If True", "Autoresearch",
    ],
    "medical_health": [
        "pubmed", "clinical-trials", "Marketing for Life Sciences",
        "open-targets", "medidata", "fhir-format", "VA Medicaid Work Rule Guide (unofficial)",
        "ArcKit UK NHS Clinical Safety Overlay", "MMPM Cognitive OS",
        "dyslexia-support-skill", "dyscalculia-support-skill",
        "HealSearch", "biomarkers", "cortellis",
    ],
    "developer_reference": [
        "system-design-skills", "duckdb-skills", "DAX for agents",
        "Ignite UI MCP Tools", "ArcKit Repository Tooling",
        "Kube by Kuberno", "vda5050", "Harness Designing Plugin",
        "SearchAtlas Toolkit", "SerpApi Claude Plugin", "SE Ranking",
        "SEOcrawl AI Reports", "Ubersuggest", "asodev",
        "dev-forge", "AppSkyline", "spec-first", "greenfield-delivery",
        "open-source-launch", "Sadakio Developer Docs",
    ],
    "business_strategy": [
        "strategy consultant", "Advisory Council", "B2b Sales Enablement",
        "Sales Enablement Kit", "Buyer Engagement Sales Engine -- Free",
        "product-discovery-flow", "Agile Product", "The Pragmatic PM Toolkit",
        "Editorial OS", "Agent Ingest, Audit & Optimize",
        "Ad Copy & Creative Preflight", "Brand Context & Writing",
        "Fractional CMO Brain", "cofounders", "StarTap Launch Kit",
        "prepkit-product", "Fiscal.ai", "BuyerCaddy",
    ],
    "government_public_sector": [
        "GovTribe", "vectorgov", "ArcKit USA Federal Civilian Overlay",
        "ArcKit Canadian Federal Overlay", "ArcKit UK Financial Services Payments Overlay",
        "ArcKit French Public Sector Overlay", "ArcKit EU Overlay",
        "ArcKit UAE Federal Overlay", "ArcKit Austrian Overlay",
        "ArcKit Australian Energy Sector Overlay", "ArcKit UK NHS Clinical Safety Overlay",
        "ArcKit Repository Tooling", "IFG", "norma-claude-skill",
        "DataCEVA US Layoff Notices", "ComplyOnSite",
    ],
    "education_learning": [
        "Oak National Academy", "Grammaropolis for Teachers", "baba Hebrew",
        "wiley-scholar-gateway", "Thesis Examiner", "Talk to Anyone",
        "socratic-mentor", "Citation Needed", "wikipedia",
        "bible by Midvash", "The Stoic Library", "patristic",
        "Shrimad Bhagwatam Guide – Srila BV Narayan Goswami Maharaj",
        "Mathbox", "bibtidy", "PT-Weiterbildung",
    ],
    "seo_marketing": [
        "SE Ranking", "SEOcrawl AI Reports", "Ubersuggest", "asodev",
        "SearchAtlas Toolkit", "Maquinable GEO", "AI Search Visibility Tracker",
        "Community & Reddit Marketing", "Marketing for Life Sciences",
        "Blog Content Strategy, Content Calendar & Content Audit",
        "Ad Copy & Creative Preflight", "markgrab", "Botify",
        "Competitive Skills by LMTY", "Competition Checker",
        "holistics-reporting", "Fractional CMO Brain",
        "Flash Veille", "Convertia", "ASO Keyword Sorter",
    ],
    "finance_economics": [
        "Fiscal.ai", "FXMacroData", "AIResearch — Multi-Lens Stock Deep Dive",
        "Crypto & Bitcoin Analyst — Charts & Research", "finsharpe",
        "sp-global", "ITIN Finance", "Nonresident Tax", "LienDeadline",
        "IDC Quanta", "LVAI Pro", "Muffed — verified NFL stats",
        "Oxford Ledge", "Economic Mind", "PhaseFolio",
        "Compabase", "FactIQ", "Dossierfy",
    ],
    "productivity_tools": [
        "parallel", "agent-context-kit", "ag2-agent-guide",
        "SuperMatt", "liquid-glass", "Briefcase",
        "MMPM Cognitive OS", "shazam", "Busymate AI",
        "Commslayer", "In Case Of Crisis", "claude-war-room",
        "Work Unit Roadmap", "Daily Journal", "standup-logger",
        "Monitly", "Keytomic", "toolrouter", "SpecsGraph",
        "Percolate", "Convertia", "BuyerCaddy",
    ],
    "real_estate_property": [
        "IQland Real Estate", "Popety.io", "Tenant Replies",
        "Funraise Taiwan Real Estate", "Market Map by Bali Leads",
        "Silicon Floor", "TenderKart", "Tendrpro Lite",
        "GrafpleMaps", "Northsea", "GulfPitch",
    ],
    "data_analytics": [
        "duckdb-skills", "DAX for agents", "holistics-reporting",
        "lotlytics", "FactIQ", "SpecsGraph", "Monitly",
        "ThoughtSpot Spottercode", "Olostep", "BigID",
        "pi security", "DataCEVA US Layoff Notices",
        "Verisk Underwriting Intelligence", "ACI Risk Indicators",
        "Muffed — verified NFL stats",
    ],
    "niche_specialized": [
        "重調クン (Jucho-kun)", "XiaoHongShu RedNote Local Guide to China",
        "RailJournal India", "GrappleMaps", "Mountaineering",
        "MarineVerse", "Pitwall F1", "Perfume Picks",
        "Pour Picks", "Retro Game Gather", "Muffed — verified NFL stats",
        "Open Ephemeris", "Shrimad Bhagwatam Guide – Srila BV Narayan Goswami Maharaj",
        "Bible by Midvash", "Wireless Choices", "EscapeBot",
        "SDSentry HazCom", "FreightUtils", "Sadakio Developer Docs",
        "RoyaleTools", "NerdyGeek", "SerialHunt",
    ],
}

# System prompt templates for each domain
DOMAIN_PROMPTS = {
    "legal_research": """You are an expert legal researcher and reference specialist.
Your expertise covers:
- Case law research and legal precedent analysis
- Regulatory compliance across multiple jurisdictions
- Contract review and legal document drafting
- International law and cross-border compliance
- Specialized practice areas (IP, employment, corporate, privacy)
- Spanish, French, Polish, and other jurisdiction-specific law
Navigate complex legal landscapes with precision and thoroughness.""",

    "knowledge_documentation": """You are a knowledge management and documentation expert.
Your expertise includes:
- Technical documentation systems (Notion, GitBook, Confluence)
- Developer documentation and API reference guides
- Knowledge base architecture and information organization
- Documentation-as-code workflows
- Context management for AI agents
- Writing for different audiences (technical vs. non-technical)
Build documentation that teams actually use.""",

    "market_research": """You are a market research and competitive intelligence expert.
Your expertise covers:
- Primary and secondary market research methodologies
- Competitive landscape analysis and benchmarking
- Industry trend analysis and forecasting
- Financial data research and company profiling
- Government procurement and contracting intelligence
- B2B market sizing and segmentation
Turn market data into actionable strategic insights.""",

    "medical_health": """You are a medical and health sciences research expert.
Your expertise includes:
- Clinical trial design and regulatory requirements
- Medical literature search and synthesis (PubMed, clinical databases)
- Healthcare data standards (FHIR, HL7)
- Drug discovery and life sciences research
- Health technology assessment
- Medical compliance and NHS/FDA requirements
Support evidence-based healthcare decisions.""",

    "developer_reference": """You are a technical reference and developer documentation expert.
Your expertise covers:
- API documentation and integration guides
- System design patterns and architecture references
- Database query languages (SQL, DAX, DuckDB)
- DevOps and infrastructure documentation
- SEO and web technology references
- Code standards and best practices documentation
Give developers the precise reference they need.""",

    "business_strategy": """You are a business strategy and go-to-market expert.
Your expertise includes:
- Strategic frameworks and business model analysis
- Go-to-market strategy and sales enablement
- Product discovery and market validation
- Agile product management practices
- Brand strategy and positioning
- Startup and founder playbooks
Build strategies that create competitive advantage.""",

    "government_public_sector": """You are a government and public sector intelligence expert.
Your expertise covers:
- Government procurement and contracting (US, UK, EU, Canada, UAE)
- Public sector compliance frameworks
- Regulatory and policy analysis
- Healthcare system regulations (NHS, Medicare/Medicaid)
- Cross-jurisdiction public sector requirements
- Government data sources and databases
Navigate public sector complexity with confidence.""",

    "education_learning": """You are an educational resources and learning specialist.
Your expertise includes:
- Curriculum development and educational standards
- Language learning and multilingual education
- Academic research and citation management
- Religious and philosophical texts analysis
- Special education and accessibility (dyslexia, dyscalculia)
- Tutoring methodologies and Socratic learning
Make knowledge accessible and engaging for every learner.""",

    "seo_marketing": """You are an SEO and digital marketing reference expert.
Your expertise covers:
- Technical SEO auditing and optimization
- Keyword research and content strategy
- App Store Optimization (ASO)
- Marketing analytics and attribution
- Content marketing and editorial planning
- Competitive SEO analysis
Drive organic growth through data-driven marketing.""",

    "finance_economics": """You are a financial research and economic analysis expert.
Your expertise includes:
- Equity research and investment analysis
- Cryptocurrency and digital asset research
- Financial modeling and valuation
- Tax compliance and international taxation
- Real estate and property finance
- Economic indicators and macro analysis
Make informed financial decisions with rigorous research.""",

    "productivity_tools": """You are a productivity and workflow optimization expert.
Your expertise covers:
- AI agent tooling and orchestration
- Task management and project coordination
- Crisis management and incident response
- Communication and status reporting
- Workflow automation and integration
- Personal and team productivity systems
Get more done with less friction.""",

    "real_estate_property": """You are a real estate and property intelligence expert.
Your expertise includes:
- Property research and valuation
- Real estate market analysis
- Tenant management and landlord resources
- Real estate technology and PropTech
- Geographic and location intelligence
- Property compliance and regulations
Navigate property markets with confidence.""",

    "data_analytics": """You are a data analytics and business intelligence expert.
Your expertise covers:
- SQL and analytical query languages (DAX, DuckDB)
- Business intelligence platforms and reporting
- Data visualization and dashboarding
- Security and compliance data analysis
- Market data feeds and financial analytics
- Operational analytics and KPI tracking
Turn raw data into business intelligence.""",

    "niche_specialized": """You are a specialist in niche and specialized reference domains.
Your expertise includes deep knowledge of specialized topics:
- Regional and cultural guides (Japanese, Chinese, Indian)
- Sports and recreation references (F1, motorsport, climbing, sailing)
- Religious and philosophical texts
- Consumer product guides and recommendations
- Hardware and technical specifications
- Industry-specific compliance and standards
Provide authoritative guidance in your specialized domain.""",
}


def load_all_skills() -> list[str]:
    """Load all 324 reference docs skill names from file"""
    if REFERENCE_DOCS_SKILLS_FILE.exists():
        return [line.strip() for line in REFERENCE_DOCS_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for reference docs skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in REFERENCE_DOCS_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific reference docs skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    # Generic prompt for skills not in a specific domain
    return f"""You are an expert in {skill_name}.
Apply reference documentation best practices:
- Provide accurate, well-sourced information
- Cite authoritative sources and official documentation
- Structure information for easy retrieval and use
- Keep content current and flag when things may have changed
- Make complex reference material accessible"""


def get_stats() -> dict:
    """Get stats about the reference docs skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in REFERENCE_DOCS_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(REFERENCE_DOCS_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
