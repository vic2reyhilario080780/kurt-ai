"""
KURT Notes & Memory Skills Catalog
Lahat ng 290 Notes & Memory skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
NOTES_MEMORY_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_notes_memory.txt"

# Domain-based groupings for smart routing
NOTES_MEMORY_DOMAINS = {
    "personal_knowledge_management": [
        "Obsidian Notes", "obsidian-sync", "notion", "Reflect", "Day One Journal",
        "Tana", "Checkvist", "Raindrop.io", "searching-apple-notes", "mac-notes",
        "Jotbook", "Sticky Note", "Memories", "KnowMine — Personal Knowledge Base",
        "Memex — Local AI Memory", "Mnemoverse Memory", "context-vault",
        "GTD Brain", "anchor-memory", "agent-recall", "Agent Archive",
        "Cairn Memory — CLAUDE.md & agent memory that stays true",
        "ai-memory-reader", "memory-agent", "memory-toolkit", "oak-memory",
        "Engram", "engram", "cortex", "Kontext", "Vault Anything",
        "indelible", "MEMANTO", "Continuity", "Context Handoff",
        "context-distill", "context-vault", "Codelux",
    ],
    "ai_memory_systems": [
        "claude-memory", "Adaptive Agent", "Cowork Memory", "MAI Second Brain",
        "ai-memory-reader", "memory-agent", "memory-toolkit", "anchor-memory",
        "agent-recall", "Agent Archive", "token-saver", "AI-Native OS",
        "AI Passport", "Ai Playbook", "MMPM Cognitive OS", "Bigmind",
        "Persyst", "cortex", "apcd", "Cairn Memory — CLAUDE.md & agent memory that stays true",
        "Memex — Local AI Memory", "Mnemoverse Memory", "indelible",
        "yaps-memory", "Vertiso Memory", "Exit Memory Update", "gr0m_mem",
        "Scaffold", "create-smartfolder", "emem", "Holdtime", "Baton",
        "Shorty", "context-distill", "MasterKi", "Char", "Ayda",
        "Terraphim Skills Introduction", "Knowz", "Stash", "Pod",
    ],
    "note_taking_apps": [
        "Obsidian Notes", "obsidian-sync", "notion", "Reflect", "Day One Journal",
        "Tana", "Checkvist", "Jotbook", "Sticky Note", "Dabble Me",
        "searching-apple-notes", "mac-notes", "Noteflix Study Loop",
        "Loopky flashcards", "Raindrop.io", "Nemi", "Notit", "Ando",
        "Snap Closet", "Duda", "Daymark", "Shorthand", "colophon",
        "wiki-wonka", "Mnemoverse Memory",
    ],
    "learning_study": [
        "ADHD Study Coach", "Study Desk", "learning-framework", "learning-tutor",
        "learning-planner", "StudyPath", "Loopky flashcards", "Noteflix Study Loop",
        "Personal Bible Study Companion", "Personalized English Tutor",
        "Finance Tutor", "law-student", "euxlab-skills", "Kuliko AI",
        "LingoBab", "Apodictic", "Mnemoverse Memory", "Tafheem",
        "Research Desk", "research-superpowers", "16minds", "Busymate AI",
    ],
    "writing_content": [
        "Claude ghost writer", "Online Writing", "novel-studio", "YWriter Novel Studio",
        "Content Studio", "me — write like me", "Prompt Coach", "beckett",
        "Planable SMM", "Newsletter Creator Tools", "scriptorium-cowork",
        "beforeword", "own-words", "RiverScript", "RoboWrite", "Postel",
        "colophon", "Renou", "mokata", "Wyatt", "SmartDraftBoard",
        "Tell Index", "Reader Radius", "Marcora: Brand Context & Writing",
        "Пост-завод", "papi",
    ],
    "productivity_context": [
        "AssistantLabs — Personal Assistant for Business", "analytics-office",
        "Admin Desk", "Briefcase", "workflow-toolkit", "GTD Brain",
        "Daymark", "Busymate AI", "token-saver", "Shorty", "apcd",
        "PrefMark", "togello", "Thrice", "standup-logger", "Taskpend",
        "Client Briefs", "GoodSet", "Fellowship", "Standards",
        "let-people-workshop", "minh-toolkit", "fcxo-toolkit",
        "build-companion", "dev-forge", "Innerloop", "LivingMeeting",
        "MeetNotes", "Rapscallion", "whydone", "Knotr", "Mackforge Outside View",
    ],
    "career_professional": [
        "LinkedIn Career Intelligence - rankedin", "Career Compass", "Career Navigator",
        "career-brand", "AI Passport", "Ai Playbook", "Founder OS",
        "strategy-frameworks", "Advisory Council", "Decision Council",
        "product-discovery-flow", "GapToGrowth", "Achriom",
        "PokeBot.ai Career Coach", "EASE OS", "Pragmatic Dev Toolkit",
        "The Pragmatic PM Toolkit", "pm-augmente", "mindpowers",
        "Product Sense Interview", "KOTC Full-Length Review",
        "Sana from Workday", "Second Arrow", "Compartment",
        "PitchHighway", "TickerTrac",
    ],
    "social_community": [
        "Social Media Skills", "Mysocial Intelligence", "Ayrshare - Unified Social Media API for AI Agents",
        "Community & Reddit Marketing", "Planable SMM", "AmplituDE",
        "RingCentral", "AirPrompter", "llm-wiki-plugin", "Arkas",
        "Go-to-Market Planner", "BOLD Studios", "Astro Jyotish",
        "The Astro Diary", "Famlore", "parenting-frameworks",
        "HeroMi Help Me Now: Parenting in Hard Moments",
        "I Do Crew", "SuperMe", "MarineVerse", "Retro Game Gather",
        "Deckaura Tarot", "Raily", "VerseDB: Comic Book Tracker",
        "Loopsii", "Odyssey365", "Whatcha",
    ],
    "research_analysis": [
        "Research Desk", "research-superpowers", "Autoresearch",
        "Glean", "KnowMine — Personal Knowledge Base", "Docbrain",
        "discovery-to-mvp", "ProductPulse", "Coconut Context",
        "reef", "Firmament", "CompanyOS", "Stintwell for Law Firms",
        "ALCBar AI Practice Risk Check", "Litigación Civil España",
        "VA Medicaid Work Rule Guide (unofficial)",
        "Vinoградов", "Тана", "Hypotize", "MCPBinder",
        "Scaffold", "oxagen", "Tenet", "sdlc-kit",
        "Conical Forum", "pmm", "Weekly Client Report",
        "pm-augmente", "GapToGrowth", "Discovery To Mvp",
        "Gestão Ágil 2.0", "Rapier", "Buyer Engagement Sales Engine -- Free",
    ],
    "tools_integrations": [
        "Google Drive → Markdown", "Greenhouse", "amplitude", "Glean",
        "Meeting.ai", "Meeting Memory by Grain", "Grain",
        "planning-skills-for-agents-and-humans", "Anson", "emem",
        "loop-and-gate-foundation", "venture", "Create State",
        "Kuliko AI", "MCPBinder", "colophon", "workflow-toolkit",
        "GoodSet", "minh-toolkit", "Duda", "MeetNotes", "Fellowship",
        "rutter", "FilmEase", "Lightbringer", "Raindrop.io",
        "Nibomo", "ProductPulse", "LilysAI", "ycofficehour",
        "trapic", "Melxis", "Jotbook", "Conveo", "claude-cognis",
        "Ownhand", "Buyer Engagement Sales Engine -- Free",
        "Dabble Me", "reef", "Marcora: Brand Context & Writing",
        "Meeting Memory by Grain", "Shipwright", "Destreamed",
        "Пост-завод", "FilmEase", "wiki-wonka", "Vinoградов",
        "Tafheem", "own-words", "Delimit",
    ],
}

# System prompt templates for each domain
DOMAIN_PROMPTS = {
    "personal_knowledge_management": """You are a personal knowledge management expert.
Your expertise covers:
- Building and maintaining a second brain
- Note-taking systems (Zettelkasten, PARA, GTD)
- Knowledge graphs and linking ideas
- Obsidian, Notion, Tana, and similar PKM tools
- Information capture and retrieval workflows
- Long-term knowledge retention strategies
Help users build systems that make their knowledge accessible and actionable.""",

    "ai_memory_systems": """You are an AI memory and agent context specialist.
Your expertise includes:
- Persistent memory for AI agents and Claude
- Context management across conversations
- CLAUDE.md and agent memory patterns
- Memory architecture and retrieval
- Context handoff between sessions
- AI-native knowledge systems
Build AI systems that remember and learn effectively.""",

    "note_taking_apps": """You are a note-taking tools and apps expert.
Your expertise covers:
- Note-taking app selection and setup (Obsidian, Notion, Reflect, Tana)
- Organizing and structuring notes
- Templates and workflows for capture
- Syncing and backup strategies
- Integrations with other productivity tools
- Migration between note-taking systems
Help users capture and organize their thoughts efficiently.""",

    "learning_study": """You are a learning science and study methods expert.
Your expertise includes:
- Spaced repetition and flashcard systems
- Active recall and retrieval practice
- Feynman technique and elaborative interrogation
- Learning frameworks and mental models
- Language acquisition and skill building
- Academic and professional study workflows
Make learning faster, deeper, and more durable.""",

    "writing_content": """You are a writing productivity and content creation expert.
Your expertise covers:
- Writing workflows and tools (Obsidian, Ulysses, Scrivener)
- Ghostwriting and voice matching
- Newsletter and content creation systems
- Manuscript and long-form writing management
- Prompt engineering for creative output
- Editing and revision workflows
Help writers produce consistent, high-quality content.""",

    "productivity_context": """You are a personal productivity and workflow optimization expert.
Your expertise includes:
- Getting Things Done (GTD) methodology
- Task and project management systems
- Standup and meeting facilitation
- Context switching and deep work
- Automation of routine tasks
- Personal operating systems
Build workflows that keep you focused and productive.""",

    "career_professional": """You are a career development and professional growth expert.
Your expertise covers:
- Personal branding and LinkedIn optimization
- Career planning and goal setting
- Job search and application strategy
- Professional skill development
- Networking and relationship building
- Product management and business strategy
Drive intentional career growth and professional impact.""",

    "social_community": """You are a social media and community management expert.
Your expertise includes:
- Social media strategy and content planning
- Community building and engagement
- API integrations for social platforms
- Family and parenting organization
- Personal interest tracking and journaling
- Creative hobby management
Build authentic connections and engaged communities.""",

    "research_analysis": """You are a research and analytical thinking expert.
Your expertise covers:
- Systematic research methodologies
- Literature review and synthesis
- Competitive and market analysis
- Legal and regulatory research
- Product discovery and validation
- Data-driven decision making
Turn raw information into actionable insights.""",

    "tools_integrations": """You are a productivity tools and integrations expert.
Your expertise includes:
- Connecting and syncing tools across platforms
- API and webhook integrations
- Workflow automation between apps
- Data migration and import/export
- Building custom integrations
- Tool evaluation and selection
Make your tools work together seamlessly.""",
}


def load_all_skills() -> list[str]:
    """Load all 290 notes & memory skill names from file"""
    if NOTES_MEMORY_SKILLS_FILE.exists():
        return [line.strip() for line in NOTES_MEMORY_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for notes & memory skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in NOTES_MEMORY_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific notes & memory skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    # Generic prompt for skills not in a specific domain
    return f"""You are an expert in {skill_name}.
Apply notes & memory best practices:
- Help users capture, organize, and retrieve knowledge effectively
- Build systems that work with how the human mind learns and remembers
- Balance structure with flexibility in note organization
- Make information actionable, not just archived
- Prioritize recall and retrieval over mere collection"""


def get_stats() -> dict:
    """Get stats about the notes & memory skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in NOTES_MEMORY_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(NOTES_MEMORY_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
