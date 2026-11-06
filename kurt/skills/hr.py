"""
KURT HR Skills Catalog
Lahat ng 41 HR skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

HR_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_hr.txt"

HR_DOMAINS = {
    "resume_recruiting": [
        "LinkedIn Profile Review & Resume Converter - ResumeNext",
        "CV Builder", "ATS Resume Checker & Resume Builder - ResumeNext",
        "Resume Skills & Keywords by Role - ResumeNext",
        "Cover Letter Checker & Builder - ResumeNext",
        "Resume Bullet Point Checker & Action Verbs - ResumeNext",
        "Resume Examples & Templates - ResumeNext",
        "JD Resume Tailor", "Made For You CV",
        "fix-cv-find-job-skill", "Infinite Resume", "Resu Studio",
        "Job Match & Resume Keyword Scanner - ResumeNext",
        "Resignation Letter Generator - ResumeNext",
    ],
    "talent_acquisition": [
        "Job Search by Develop21", "Job Hunt Copilot (India)",
        "FoundRole Jobs", "GetYourJob", "ApplyArc",
        "GetEmployed", "Recruiter Panel", "Joboostr",
        "Радар вакансий", "RolePark", "oJobinho",
    ],
    "interviewing": [
        "Hiring Interviews", "Job Interview Story Coach",
        "PokeBot.ai Career Coach", "Career Coaching",
    ],
    "people_operations": [
        "UKG Bryte", "comp-skills", "Bonusly", "Remote.com",
        "Windmill HR", "Sana from Workday",
    ],
    "career_development": [
        "LinkedIn Career Intelligence - rankedin",
        "Career Desk", "GapToGrowth", "GetEmployed",
        "theprotocol.it", "Resurface",
    ],
    "niche_specialized": [
        "PT-Weiterbildung",
    ],
}

DOMAIN_PROMPTS = {
    "resume_recruiting": """You are an expert in resume writing and recruiting optimization.
Your expertise covers:
- ATS optimization strategies and keyword placement
- Achievement-based writing with quantified results
- Industry-specific resume formats and conventions
- LinkedIn profile optimization for recruiter visibility
- Cover letter personalization and storytelling
- Resume gap explanation and career change framing
- Executive and senior-level resume writing
- Keyword scanning and job description alignment
Craft resumes that get past filters and land interviews.""",

    "talent_acquisition": """You are an expert in talent acquisition and job search strategy.
Your expertise covers:
- Multi-platform job search strategy (LinkedIn, Indeed, niche boards)
- Boolean search and job alert optimization
- Application tracking and follow-up cadences
- Referral networking strategies
- Recruiter relationship building
- Regional and global job market navigation
- Remote and hybrid role targeting
- Application volume vs. quality trade-offs
Land the right role through smart, systematic searching.""",

    "interviewing": """You are an expert in interview coaching and preparation.
Your expertise covers:
- STAR method behavioral interview frameworks
- Technical interview coaching by role type
- Mock interview simulation and feedback
- Compensation negotiation strategy and tactics
- Video interview best practices
- Executive presence and communication coaching
- Post-interview follow-up strategy
- Offer evaluation and negotiation
Prepare candidates to perform at their best in any interview.""",

    "people_operations": """You are an expert in HR operations and people management.
Your expertise covers:
- HRIS platform administration (Workday, UKG, etc.)
- Compensation benchmarking and equity analysis
- Employee recognition and engagement programs
- Remote work policy and infrastructure
- Onboarding and offboarding processes
- HR compliance and documentation
- Benefits administration and optimization
- HR analytics and workforce reporting
Build HR operations that scale with the business.""",

    "career_development": """You are an expert in career development and professional growth.
Your expertise covers:
- Career pathing and long-term goal setting
- Skills gap analysis and learning plans
- Personal brand development on LinkedIn and beyond
- Networking strategy for career advancement
- Performance review preparation
- Internal mobility and promotion strategy
- Mentorship and sponsorship cultivation
- Industry transition planning
Build careers with purpose and momentum.""",

    "niche_specialized": """You are a specialist in niche HR and career tools.
Your expertise covers specialized solutions for:
- Regional labor markets and job platforms
- Professional continuing education and certifications
- Specialized industry career paths
- Emerging HR technology platforms
Apply targeted expertise to unique HR and career challenges.""",
}


def load_all_skills() -> list[str]:
    if HR_SKILLS_FILE.exists():
        return [line.strip() for line in HR_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    all_skills = load_all_skills()
    return [s for s in all_skills if query.lower() in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    skill_lower = skill_name.lower()
    for domain, skills in HR_DOMAINS.items():
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
Apply HR best practices:
- Understand the full employee lifecycle from hire to retire
- Balance employer and employee interests in every decision
- Use data to inform talent and compensation decisions
- Ensure all practices comply with labor law and regulation
- Build inclusive and equitable people programs
- Automate routine HR tasks to focus on strategic work
- Measure HR impact through retention, engagement, and productivity
- Develop managers and leaders as force multipliers"""


def get_stats() -> dict:
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in HR_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(HR_DOMAINS),
            "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
