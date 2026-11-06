"""
KURT Jobs & Career Skills Catalog
Lahat ng 64 Jobs & career skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

JOBS_CAREER_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_jobs_career.txt"

JOBS_CAREER_DOMAINS = {
    "resume_cv": [
        "CV Builder", "ATS Resume Checker & Resume Builder - ResumeNext",
        "Resume Skills & Keywords by Role - ResumeNext",
        "Resume Bullet Point Checker & Action Verbs - ResumeNext",
        "Resume Examples & Templates - ResumeNext", "JD Resume Tailor",
        "Made For You CV", "fix-cv-find-job-skill", "Infinite Resume",
        "Resu Studio", "Resignation Letter Generator - ResumeNext",
        "LinkedIn Profile Review & Resume Converter - ResumeNext",
        "BioFlow",
    ],
    "job_search": [
        "Job Search by Develop21", "Job Hunt Copilot (India)", "Job Hunt HQ",
        "FoundRole Jobs", "GetYourJob", "NeverApply", "ApplyArc",
        "GetEmployed", "Worklittle Jobs", "Joboostr", "Радар вакансий",
        "Job Match & Resume Keyword Scanner - ResumeNext", "oJobinho",
    ],
    "interview_prep": [
        "Job Interview Story Coach", "MagicInterview", "interview-sim",
        "Portfolio Interview", "Product Sense Interview", "MentorCruise",
        "Sarathi", "Career Coaching", "career-brand",
    ],
    "career_development": [
        "Career Compass", "Career Navigator", "Career Desk",
        "LinkedIn Career Intelligence - rankedin", "GapToGrowth",
        "GTD Brain", "RescueTime", "Dev Wrapped", "Lumr Studio",
        "Tenet", "Todo4",
    ],
    "entrepreneurship": [
        "Founder OS", "cofounders", "Incubae", "axiomcore",
        "Consultant Assignments", "strategy-pack",
    ],
    "portfolio_showcase": [
        "GitHub Portfolio Builder", "Artist Portfolio", "Admin Desk",
        "Cover Letter Checker & Builder - ResumeNext", "Publica Now",
        "Mokaru", "Ship Post",
    ],
    "niche_specialized": [
        "Dropthehassle", "PokeBot.ai Career Coach", "Competition Checker",
        "Veteran Companion", "togello", "RescueTime",
    ],
}

DOMAIN_PROMPTS = {
    "resume_cv": """You are an expert in resume and CV writing.
Your expertise covers:
- ATS optimization and keyword strategy
- Achievement-based bullet point writing
- Industry-specific resume formats
- LinkedIn profile optimization
- Cover letter writing
- Resume gap explanation strategies
- Executive and senior-level resume writing
- Career change resume repositioning
Create resumes that get interviews.""",

    "job_search": """You are an expert in job search strategy.
Your expertise covers:
- Job board optimization and search strategies
- Company research and targeting
- Application tracking and follow-up
- Networking and referral strategies
- Job posting analysis and matching
- Salary research and negotiation
- Remote and international job search
- Recruiter outreach strategies
Land the right job faster through smart searching.""",

    "interview_prep": """You are an expert in interview preparation.
Your expertise covers:
- STAR method behavioral interview coaching
- Technical interview preparation
- Product sense and case interview practice
- Interview simulation and feedback
- Salary negotiation tactics
- Thank-you note and follow-up strategy
- Video interview best practices
- Executive presence and communication
Ace every interview with thorough preparation.""",

    "career_development": """You are an expert in career development and growth.
Your expertise covers:
- Career path planning and goal setting
- Skills gap analysis and learning plans
- Personal brand building
- Networking strategy and relationship building
- Performance review preparation
- Promotion case building
- Work-life balance optimization
- Productivity and time management
Build a fulfilling, high-impact career.""",

    "entrepreneurship": """You are an expert in entrepreneurship and founding.
Your expertise covers:
- Startup ideation and validation
- Co-founder matching and dynamics
- Pitch deck and investor communication
- Business model design
- Early-stage hiring and team building
- Consulting and freelance career building
- Side project launch strategy
- Strategic frameworks for founders
Launch and grow successful ventures.""",

    "portfolio_showcase": """You are an expert in portfolio and personal brand building.
Your expertise covers:
- Developer and GitHub portfolio optimization
- Creative portfolio design and curation
- Personal website strategy
- Content creation for career building
- Speaking and thought leadership
- Awards and recognition strategy
- Academic and research portfolio
Showcase your work compellingly.""",

    "niche_specialized": """You are a specialist in niche career tools.
Your expertise covers specialized solutions for:
- Veteran career transition
- Regional job markets
- Specific industry career paths
- Productivity tools for career management
Apply targeted expertise to unique career challenges.""",
}


def load_all_skills() -> list[str]:
    if JOBS_CAREER_SKILLS_FILE.exists():
        return [line.strip() for line in JOBS_CAREER_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    all_skills = load_all_skills()
    return [s for s in all_skills if query.lower() in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    skill_lower = skill_name.lower()
    for domain, skills in JOBS_CAREER_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"You are an expert in {skill_name}.\n{base_prompt}\nApply the specific knowledge and practices from the '{skill_name}' skill."
    return f"""You are an expert in {skill_name}.
Apply career best practices:
- Understand the user's unique background and goals
- Tailor advice to their specific industry and level
- Use data and market insights to guide decisions
- Build on strengths while addressing gaps
- Create actionable, time-bound career plans
- Network strategically, not just broadly
- Negotiate confidently based on market research
- Continuously learn and adapt to market changes"""


def get_stats() -> dict:
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in JOBS_CAREER_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(JOBS_CAREER_DOMAINS),
            "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
