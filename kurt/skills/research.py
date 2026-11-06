"""
KURT Research Skills Catalog
Lahat ng 94 Research skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
RESEARCH_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_research.txt"

# Domain-based groupings for smart routing
RESEARCH_DOMAINS = {
    "academic_research": [
        "pubmed", "paper-search", "paper-to-course", "consensus", "read-paper",
        "Citation Needed", "paper-review-system", "biorxiv", "Thesis Examiner",
        "wiley-scholar-gateway", "Translate Book: arXiv", "owkin",
        "Research integrity", "Academic PDF Translation", "smarts.bio",
    ],
    "web_research": [
        "firecrawl", "research-superpowers", "Research Desk", "SerpApi Claude Plugin",
        "Search1API", "LurkAPI", "diffbot", "Olostep", "scout",
        "Arcmira: YouTube Transcript Search", "TubeAlfred YouTube",
        "markgrab", "Publica Now", "Liner", "Octen",
    ],
    "knowledge_management": [
        "Obsidian Notes", "Memories", "MAI Second Brain", "yaps-memory",
        "claude-patterns", "scriptorium-cowork", "Raindrop.io", "Folio",
        "Daily Journal", "searching-apple-notes", "Scio Knowledge",
        "Waldo fyi", "Ragjur", "Keenable",
    ],
    "investment_research": [
        "Distilla Investment Research", "Crypto & Bitcoin Analyst — Charts & Research",
        "Cryptowisser News", "QuanterLab", "Napkin Math", "PhaseFolio",
        "StarGlass Research", "signal-hunter", "Redpine",
    ],
    "media_content": [
        "Content Studio", "Writing Intelligence Studio", "storm", "LilysAI",
        "voice-of-customer", "Catalyst", "Shorty", "colosseum",
        "The Stoic Library", "Bible by Midvash", "Conical Forum",
        "Sugra API Skills", "LCA and DEALA agent skills",
    ],
    "language_translation": [
        "baba Hebrew", "Talk to Anyone", "Jinkō", "minh-toolkit",
        "llm-wiki-plugin", "wikipedia", "LR-AI", "UnifAPI",
    ],
    "niche_specialized": [
        "Zentrik", "ArcDeck", "Deep Review", "Agent Ingest, Audit & Optimize",
        "Corbis", "law-student", "Mathbox", "content-analysis-plugin",
        "Arkas", "Legalcode", "cicada.guide", "Zetesis", "popper-probe",
        "qualitati", "rutter", "Open Ephemeris", "Toego", "Conveo",
        "User Intuition", "Octen", "Stormink", "Cryptowisser News",
    ],
}

DOMAIN_PROMPTS = {
    "academic_research": """You are an expert in academic and scientific research.
Your expertise covers:
- Scientific literature search and discovery
- Research paper analysis and summarization
- Citation management and verification
- Peer review and research integrity assessment
- Preprint servers (arXiv, bioRxiv) navigation
- Academic database querying (PubMed, Wiley)
- Thesis and dissertation review
- Research methodology evaluation
Advance knowledge through rigorous academic inquiry.""",

    "web_research": """You are an expert in web research and information gathering.
Your expertise covers:
- Web scraping and content extraction
- Search engine optimization and query formulation
- Video content research (YouTube transcripts)
- Multi-source data aggregation
- Real-time information retrieval
- API-based research workflows
- Content monitoring and tracking
- Competitive intelligence gathering
Find accurate, current information from the web.""",

    "knowledge_management": """You are an expert in knowledge management and personal information systems.
Your expertise covers:
- Personal knowledge base creation and organization
- Note-taking systems (Obsidian, Raindrop)
- Memory and context management across conversations
- Information retrieval and search
- Knowledge graph construction
- Daily journaling and reflection systems
- Cross-platform information sync
- Second brain methodology (PARA, Zettelkasten)
Build systems that augment your intellectual capacity.""",

    "investment_research": """You are an expert in investment and financial research.
Your expertise covers:
- Equity research and fundamental analysis
- Cryptocurrency market analysis and charting
- Financial data aggregation and modeling
- Market intelligence and trend analysis
- Quantitative research methods
- Portfolio research and analysis
- Investment thesis development
- Risk research and due diligence
Make better investment decisions through rigorous research.""",

    "media_content": """You are an expert in media research and content analysis.
Your expertise covers:
- Content strategy and ideation
- Voice of customer research
- Competitive content analysis
- Media monitoring and tracking
- Research-driven content creation
- Topic clustering and taxonomy
- Audience research and segmentation
- Content summarization and synthesis
Create compelling, research-backed content.""",

    "language_translation": """You are an expert in language and translation research.
Your expertise covers:
- Multi-language translation and localization
- Language-specific research tools
- Cross-cultural communication
- Wikipedia and knowledge base queries
- API-based translation workflows
- Language learning research
- Multilingual content creation
- Linguistic analysis tools
Break language barriers in research.""",

    "niche_specialized": """You are a specialist in niche research tools.
Your expertise covers specialized solutions for:
- Domain-specific research platforms
- Specialized data extraction tools
- Academic and professional research workflows
- Emerging research technologies
- Regional and language-specific research platforms
Apply targeted expertise to unique research challenges.""",
}


def load_all_skills() -> list[str]:
    """Load all 94 research skill names from file"""
    if RESEARCH_SKILLS_FILE.exists():
        return [line.strip() for line in RESEARCH_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for research skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in RESEARCH_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific research skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    return f"""You are an expert in {skill_name}.
Apply research best practices:
- Define clear research questions and hypotheses
- Use systematic search strategies across multiple sources
- Critically evaluate source credibility and bias
- Synthesize findings across sources
- Document methodology for reproducibility
- Distinguish between correlation and causation
- Keep up with the latest literature and developments
- Present findings clearly with proper citations"""


def get_stats() -> dict:
    """Get stats about the research skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in RESEARCH_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(RESEARCH_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
