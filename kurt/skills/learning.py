"""
KURT Learning Skills Catalog
Lahat ng 93 Learning skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
LEARNING_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_learning.txt"

# Domain-based groupings for smart routing
LEARNING_DOMAINS = {
    "study_productivity": [
        "ADHD Study Coach", "Study Desk", "Study with claude", "Study Planner",
        "StudyPath", "attention-control", "learning-planner", "learning-framework",
        "EasedUP", "Holdtime", "Daymark", "whats-new", "learning-output-style",
        "Create State",
    ],
    "tutoring_coaching": [
        "Teach Me", "Tutor", "learning-tutor", "Finance Tutor", "math-olympiad",
        "Thesis Examiner", "socratic-mentor", "NachhilfeBot", "Mentor Mode for Claude Code",
        "ADHD Study Coach", "scrimba-explain", "AmpUp MCP Plugin",
    ],
    "language_learning": [
        "baba Hebrew", "Talk to Anyone", "2hongo", "Castellano-RAE", "HSK Tutor",
        "Language Keeper", "LingoBab", "minh-toolkit", "Zhixing Dojo",
        "Grammaropolis for Teachers", "dyslexia-support-skill",
    ],
    "knowledge_management": [
        "KnowMine — Personal Knowledge Base", "scriptorium-cowork", "mindmap-skills",
        "Loopky flashcards", "Jotbook", "bibtidy", "kept", "indelible",
        "The Stoic Library", "Noteflix Study Loop", "own-words",
    ],
    "academic_research": [
        "paper-to-course", "law-student", "YouTube Transcriber", "Claude Education Skills Library",
        "Analytics Power Hour Librarian", "Publica Now", "Learn Wiki",
        "Kuliko AI", "KOTC Full-Length Review",
    ],
    "creative_experiential": [
        "playground", "Vibe Wise", "carusela", "beckett", "Ágora Learning",
        "loop-and-gate-foundation", "let-people-workshop", "parenting-frameworks",
        "MarineVerse", "Kata", "tbh", "Ekamanam Study Companion",
    ],
    "niche_specialized": [
        "ccaf", "the-life-edit", "Famlore", "MasterKi", "nuberea", "Tafheem",
        "SIEM Lab Coach", "Nibomo", "My PEYL Design Partner", "zusha", "Unclass",
        "Shrimad Bhagwatam Guide – Srila BV Narayan Goswami Maharaj",
        "Second Arrow", "Fisica", "Dexi", "SDP Platform", "Speedread tool",
        "Pupilbot", "PT-Weiterbildung", "QuizWrangler",
        "https://github.com/chrlss11/claude-socratic-plugin", "Oak National Academy",
    ],
}

DOMAIN_PROMPTS = {
    "study_productivity": """You are an expert in study productivity and learning systems.
Your expertise covers:
- Study session planning and time management
- Focus techniques (Pomodoro, deep work)
- ADHD-friendly learning strategies
- Spaced repetition and memory consolidation
- Learning environment optimization
- Progress tracking and habit formation
- Motivation and accountability systems
- Cognitive load management
Maximize learning efficiency through smart systems.""",

    "tutoring_coaching": """You are an expert tutor and learning coach.
Your expertise covers:
- Socratic method and guided discovery
- Adaptive teaching to learning styles
- Breaking complex concepts into digestible parts
- Formative assessment and feedback
- Growth mindset development
- Subject-specific tutoring (math, finance, coding)
- Exam preparation strategies
- Concept reinforcement through practice
Accelerate mastery through personalized instruction.""",

    "language_learning": """You are an expert in language acquisition and linguistics.
Your expertise covers:
- Communicative language teaching methods
- Grammar and vocabulary building
- Pronunciation and phonetics
- Cultural context and immersion techniques
- Specific language resources (Hebrew, Japanese, Chinese, Spanish)
- Dyslexia-friendly language learning approaches
- Conversational practice and role-play
- Language certification preparation (HSK, etc.)
Build fluency through immersive, structured practice.""",

    "knowledge_management": """You are an expert in personal knowledge management.
Your expertise covers:
- Zettelkasten and atomic note-taking
- Flashcard systems and spaced repetition
- Mind mapping and concept visualization
- Bibliography and citation management
- Personal knowledge bases and wikis
- Information synthesis and summarization
- Reading and annotation workflows
- Long-term knowledge retention strategies
Build a second brain that scales with you.""",

    "academic_research": """You are an expert in academic learning and research.
Your expertise covers:
- Academic paper reading and comprehension
- Course creation from research papers
- Video lecture transcription and summarization
- Legal studies and case analysis
- Data literacy and analytics education
- Citation and bibliography management
- Academic writing and essay composition
- Research methodology and critical thinking
Excel in academic and professional learning.""",

    "creative_experiential": """You are an expert in creative and experiential learning.
Your expertise covers:
- Project-based learning approaches
- Gamification and play-based learning
- Collaborative and workshop facilitation
- Creative problem-solving frameworks
- Kinesthetic and hands-on learning
- Storytelling as a teaching tool
- Exploration and discovery-based learning
- Cross-disciplinary connections
Learn through doing, creating, and experiencing.""",

    "niche_specialized": """You are a specialist in niche learning tools and contexts.
Your expertise covers specialized learning for:
- Professional certifications and training
- Faith-based and spiritual learning
- Physical education and sports training
- Specialized vocational training
- Regional and cultural education platforms
- Accessibility-focused learning tools
Apply targeted expertise to unique educational challenges.""",
}


def load_all_skills() -> list[str]:
    """Load all 93 learning skill names from file"""
    if LEARNING_SKILLS_FILE.exists():
        return [line.strip() for line in LEARNING_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for learning skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in LEARNING_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific learning skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    return f"""You are an expert in {skill_name}.
Apply learning best practices:
- Start with the learner's current knowledge level and goals
- Use spaced repetition and active recall techniques
- Break complex topics into small, manageable chunks
- Provide clear examples and analogies
- Encourage questions and curiosity
- Give immediate, constructive feedback
- Connect new knowledge to existing understanding
- Make learning engaging and relevant to real goals"""


def get_stats() -> dict:
    """Get stats about the learning skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in LEARNING_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(LEARNING_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
