"""
KURT Files & Documents Skills Catalog
Lahat ng 850 Files & Documents skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
FILES_DOCS_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_files_documents.txt"

# Domain-based groupings for smart routing
FILES_DOCS_DOMAINS = {
    "document_creation": [
        "diataxis", "doc-authoring-skills", "doc-authoring-skills-ja", "Interactive Docs",
        "GitBook", "Mintlify", "OpenDocs", "Docbrain", "sync-docs", "LLM Project Docs",
        "Make Documentation", "pptx-deck-plugin", "htmldeck", "FluidDocs Deck Builder",
        "SlideOps", "Presenton", "Pitch Deck Advisor", "visual-docs", "betterposter",
        "The PDF Maker", "EasyPDF", "PDFBolt", "ADA PDF Compliance", "DevExpress Office & PDF File API",
        "ConvertAPI", "Pdf To Excel", "Pdf Samenvoegen", "PaperPorter", "GetSearchablePDF",
        "Claude Docs", "colophon", "Document Vault", "Vault Anything", "DocsBot",
        "handoff-doc", "repo-docs-system", "RepoAtlas", "repoviewer", "code-map",
        "PUML - PlantUML", "SysML v2 Co-Pilot", "jgs-magic-sysmlv1-read-skills",
        "Whimsical", "excalidraw-plugin", "mindmap-skills", "Miro",
    ],
    "seo_marketing": [
        "Claude SEO and GEO Site Audit", "SEO-AEO-GEO Ultimate", "SEO Audit",
        "AI Search Visibility & Brand Mentions (GEO/AEO)", "AI Search Visibility (AEO/GEO)",
        "rampstack-seo", "SE Ranking", "LovableSEO", "Maquinable GEO",
        "Programmatic SEO Gate", "Site Architecture & Faceted Navigation", "RankControl",
        "Rankability", "Website Copywriting & Positioning", "Ad Copy & Creative Preflight",
        "copy-that-sells", "Marketing Psychology Kit", "Hyper Marketing",
        "B2B Personal Branding", "B2b Sales Enablement", "B2B Events, PR and Launches",
        "B2B Research: Market and Account", "VibeLeads: B2B Lead Finder",
        "Lead Magnets", "analytics-skills", "dataslayer-marketing-skills", "Planable SMM",
        "PostEverywhere", "PostDaily", "AI YouTube OS", "InsightPins for Pinterest",
    ],
    "resume_career": [
        "CV Builder", "LinkedIn Profile Review & Resume Converter - ResumeNext",
        "ATS Resume Checker & Resume Builder - ResumeNext", "Made For You CV",
        "Resume Skills & Keywords by Role - ResumeNext", "Resume Bullet Point Checker & Action Verbs - ResumeNext",
        "Cover Letter Checker & Builder - ResumeNext", "Job Match & Resume Keyword Scanner - ResumeNext",
        "Resume Examples & Templates - ResumeNext", "Resignation Letter Generator - ResumeNext",
        "Infinite Resume", "fix-cv-find-job-skill", "career-brand",
        "Career Compass", "Career Navigator", "Career Desk", "Job Hunt Copilot (India)",
        "Job Hunt HQ", "Job Search by Develop21", "GetEmployed", "Joboostr",
        "Portfolio Interview", "ApplyArc", "JD Resume Tailor", "FoundRole Jobs",
        "Post-Job Summary", "Job Interview and Meeting Preparation",
    ],
    "legal_compliance": [
        "commercial-legal", "litigation-legal", "corporate-legal", "employment-legal",
        "ip-legal", "privacy-legal", "product-legal", "regulatory-legal", "legal-clinic",
        "Litigación Civil España", "Litigación Laboral España",
        "Litigación Contencioso-Administrativa España", "Contratos Civiles y Mercantiles",
        "Contratos Laborales y Asesoría Empresarial", "Compliance ES", "Extranjería España",
        "indian-contracts-drafting", "indian-hc-drafting", "indian-consumer-drafting",
        "indian-company-drafting", "indian-ip-drafting", "indian-family-drafting",
        "indian-property-drafting", "indian-labour-drafting", "indian-mact-drafting",
        "indian-rent-control-drafting", "district-court-drafting", "supreme-court-drafting",
        "Lexbeam EU AI Governance", "GDPRGard Compliance Skills", "Data Protection",
        "Ansvar Compliance Skills", "AAA ClauseBuilder", "Contracko", "PandaDoc",
        "DocuSeal", "GetSign", "legalzoom", "Freelaw Studio", "OpenCase",
        "UAE Healthcare Compliance by ATeam", "Saudi Healthcare Compliance by ATeam",
        "DSAIL: Rules Engine for Written Policy", "genesis-governance-claude",
        "Sammati DPDP Readiness", "EUDR compliance", "regai — Vietnamese Legal Consultant",
        "Reclamos de consumo Perú", "Demand from the File",
    ],
    "memory_context": [
        "claude-memory", "memory-agent", "anchor-memory", "Memory Bank",
        "Cairn Memory — CLAUDE.md & agent memory that stays true", "claude-md-management",
        "Claude MD Optimizer", "bake-claude-md-files", "claude-context-optimizer",
        "claude-context-auto-handoff", "claude-train-prep", "claude-performance",
        "please-optimize-my-claude", "obsidian-sync", "Obsidian Notes",
        "Notion Markdown Sync", "recall", "memory-toolkit", "Continuity",
        "Stemma", "Jotbook", "RepoAtlas",
    ],
    "writing_editing": [
        "writing-quality", "Online Writing", "Copyedit & Proofreading", "Proofread",
        "anti-ai-writing", "unslop", "Slop Stopper", "Claude ghost writer",
        "Everwrite", "Writing Desk", "Writing Intelligence Studio", "Writing With Agents",
        "Writing Process", "ProseShape", "Editorial OS", "Big If True",
        "Annotate", "Markdownby mdedit.ai", "md-linker", "static.md",
        "Dragoman", "DeepL", "translate epub", "Translate Book: arXiv",
        "Academic PDF Translation", "Textpass De", "i18n Sync: Missing Translations Finder",
        "Instructions Cleanup", "ISO 24495 Plain Language",
    ],
    "productivity_tools": [
        "research-superpowers", "Study Desk", "Learn Wiki", "learning-planner",
        "Loopky flashcards", "QuizWrangler", "Tuteliq", "Ekamanam Study Companion",
        "Brief-interview", "Briefcase", "MeetNotes", "Meeting.ai", "handoff-doc",
        "ReadIt", "read-paper", "paper-review-system", "Cite2FN", "bibtidy",
        "plugin-dev", "claude-blog-assistant", "Blog Content Strategy, Content Calendar & Content Audit",
        "BulkPublish", "Fully SEO optimized Article with FAQ's", "Blogr", "Blogizi",
        "PolyBlog Blog Builder",
    ],
    "data_spreadsheet": [
        "Spreadsheet (DWS Build)", "CSV Cleanup", "csv-quality-gate", "duckdb-skills",
        "Alteryx", "holistics-development", "stackql-skills", "Adds Up",
        "Datarails financeos", "Bankstatemently", "Countz Accounting", "stock-portfolio-valuation",
        "Retirement Cash Flow Planner", "TRES Finance Plugin", "Fin3000",
        "Financial Aid Office Workflow", "Juniper Square", "Wealthbox",
        "Datakart", "KontoCSV", "Numeric MCP Toolkit", "ubl-star — facturas electrónicas a Power BI",
        "extractos-ar", "Paušal", "freee",
    ],
    "file_management": [
        "Headroom: Large File and Log Reader", "firecrawl", "Bright Data",
        "Zyte Web Data", "HandwritingOCR", "myocr.app", "File Tools First",
        "create-smartfolder", "Filestack Claude Plugin", "google-cloud-storage",
        "Google Drive → Markdown", "Pics.io", "Assetlib Audit", "BoardRepo",
        "open-document-skills", "hwpx-plugin", "Forge PII Scan", "Env Protector: Secret Scanner",
        "mac-disk-cleaner", "mailmuncher", "iPhone Backup for Linux",
        "biocharpro", "Diamond Painting Converter", "pixinsight-connector-skills",
    ],
    "project_management": [
        "pm", "planning-skills-for-agents-and-humans", "Playbook", "sdlc-kit",
        "sdlc-kit-extended", "Agentic SDLC Kit", "project-setup", "project-boundary",
        "Docket Tracker", "LaunchNotes", "roadmapsmith", "Planpack",
        "OpenPlanr", "okrdev", "Continuity", "Repo Standard Toolkit",
        "Spec Drift Detector", "SpecsGraph", "SpecDD", "SDD Kit", "sdd",
        "SDD Planner", "smdd-toolkit", "groundwork-specflow", "Plugin Packaging",
        "walkthrough", "Env Setup Wizard: Project Setup and Onboarding",
    ],
    "ai_integration": [
        "AI Skills", "AI Employees", "agent-discussion", "research-superpowers",
        "parallel", "Agentics Beyond Code", "AgentUI Tools", "AgentOne Token Compression",
        "render-visual-skill", "dataink", "brand-md", "content-analysis-plugin",
        "analytics-skills", "comp-skills", "Informatica", "Unstructured Foundation",
        "databricks", "dominodatalab", "Oracle AI Data Platform Workbench Engineer Agent",
        "oracle-ai-data-platform-workbench-spark-connectors", "pinecone",
        "RAG Evaluation", "LLM Project Docs", "vellum", "Probabl Skills",
    ],
    "ecommerce_business": [
        "Amazon Selling Partner", "Awesome Ecom Skills", "MakeBox for Etsy",
        "shopee-review", "Replo", "Superwall", "Unbounce Landing Page Builder",
        "LovableSEO", "ConvertAPI", "Contezza AI for Merchants", "StoreConnect Agent Skills",
        "Invoice Generator", "Estimate Builder", "Client Briefs", "ClientGen Reach",
        "Competitive Intel", "Competitive Skills by LMTY", "inSitu Sales",
        "B2b Sales Enablement", "strategy consultant", "management-consulting",
        "Founder OS", "CompanyOS", "Accountable",
    ],
}

# System prompt templates for each domain
DOMAIN_PROMPTS = {
    "document_creation": """You are an expert technical writer and document creator.
Your skills include:
- Creating clear, structured documents (APIs, guides, runbooks, wikis)
- Presentation design and slide deck creation
- PDF generation and document conversion
- Diagram and flowchart creation (PlantUML, Mermaid, SysML)
- Document management and version control
Write documents that are clear, maintainable, and audience-appropriate.""",

    "seo_marketing": """You are an SEO and digital marketing expert.
Your expertise covers:
- Technical SEO, on-page optimization, AEO/GEO strategies
- Content strategy and keyword clustering
- Ad copy and conversion optimization
- B2B marketing, lead generation, and pipeline building
- Social media content and brand positioning
- Analytics and marketing performance tracking
Drive organic growth and maximize marketing ROI.""",

    "resume_career": """You are a career development and resume expert.
Your expertise includes:
- Resume writing, ATS optimization, and keyword placement
- LinkedIn profile optimization
- Cover letter and job application writing
- Interview preparation and coaching
- Career planning and job search strategy
Help candidates land their dream jobs with compelling materials.""",

    "legal_compliance": """You are a legal document and compliance expert.
Your expertise covers:
- Contract drafting and review (commercial, employment, IP)
- Legal compliance frameworks (GDPR, EUDR, DPDP)
- Court document drafting (pleadings, motions, petitions)
- Multi-jurisdiction knowledge (Spain, India, UAE, Saudi Arabia)
- Document signing and workflow automation
Always note that this is AI assistance, not legal advice.""",

    "memory_context": """You are an expert in AI context management and memory systems.
Your skills include:
- CLAUDE.md creation and optimization
- Context window management and compression
- Agent memory architectures (anchor, episodic, semantic)
- Cross-session continuity and state management
- Knowledge base synchronization
Build AI systems that remember what matters.""",

    "writing_editing": """You are a professional writing and editing expert.
Your expertise covers:
- Copyediting, proofreading, and style guides
- AI writing detection and humanization
- Technical and creative writing
- Multi-language translation and localization
- Content quality scoring and improvement
- Academic and professional writing standards
Produce polished, human-quality writing.""",

    "productivity_tools": """You are a productivity and knowledge management expert.
Your skills include:
- Research synthesis and summarization
- Note-taking and knowledge organization
- Meeting facilitation and documentation
- Citation management and academic research
- Learning and study optimization
- Content calendars and publishing workflows
Maximize output and minimize friction.""",

    "data_spreadsheet": """You are a data and spreadsheet expert.
Your expertise includes:
- Spreadsheet design, formulas, and automation
- Financial modeling and accounting
- Data cleaning and transformation
- Business intelligence and analytics
- CSV processing and ETL workflows
- Compliance reporting and financial statements
Turn raw data into actionable insights.""",

    "file_management": """You are a file and document management expert.
Your skills include:
- File organization, archiving, and retrieval
- OCR and document digitization
- Cloud storage integration (Google Drive, etc.)
- Asset management and digital libraries
- File format conversion
- Security scanning and PII detection
Keep files organized, secure, and accessible.""",

    "project_management": """You are a project and product management expert.
Your expertise covers:
- Project planning, roadmapping, and OKR setting
- SDLC workflows and agile methodologies
- Specification writing and design docs
- Release management and launch tracking
- Dependency tracking and risk management
- Team coordination and status reporting
Deliver projects on time and on scope.""",

    "ai_integration": """You are an AI integration and data pipeline expert.
Your skills include:
- LLM integration and RAG systems
- Vector databases and semantic search
- Data pipeline design and orchestration
- AI workflow automation
- Model evaluation and observability
- Enterprise AI platform integration
Build reliable, scalable AI-powered systems.""",

    "ecommerce_business": """You are an e-commerce and business operations expert.
Your expertise covers:
- Online store optimization and conversion
- Product listing and catalog management
- Invoice and estimate generation
- Sales pipeline and CRM workflows
- Competitive intelligence and market research
- Business strategy and consulting frameworks
Grow revenue and streamline operations.""",
}


def load_all_skills() -> list[str]:
    """Load all 850 files & documents skill names from file"""
    if FILES_DOCS_SKILLS_FILE.exists():
        return [line.strip() for line in FILES_DOCS_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for files & documents skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in FILES_DOCS_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific files & documents skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    # Generic prompt for skills not in a specific domain
    return f"""You are an expert in {skill_name}.
Apply document and file management best practices:
- Create clear, well-structured documents
- Optimize for the intended audience
- Follow industry standards and conventions
- Ensure accuracy and completeness
- Make content discoverable and maintainable"""


def get_stats() -> dict:
    """Get stats about the files & documents skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in FILES_DOCS_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(FILES_DOCS_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
