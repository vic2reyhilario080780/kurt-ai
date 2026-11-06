"""
KURT Pull Requests Skills Catalog
Lahat ng 162 Pull Requests skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
PULL_REQUESTS_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_pull_requests.txt"

# Domain-based groupings for smart routing
PULL_REQUESTS_DOMAINS = {
    "code_review": [
        "code-review", "Qodo", "CodeRabbit", "finecomb: exhaustive code review and security audit",
        "claude-code-review-council", "pr-review-toolkit", "Deep Refactor", "Codacy",
        "dishonest-code-audit", "greptile", "Meticulous", "Pragmatic Dev Toolkit",
        "PR Story Aligner: Pull Request vs Ticket Check", "PRFlow",
        "Cairn Verify — did the AI really fix it?", "Quality Supervisor", "Three Pillars",
    ],
    "security_audit": [
        "Security Guidance", "claude-security", "securitymaxxing", "Pi Security",
        "aws-agents-for-devsecops", "governance skill", "heyGRC", "GraphQL Guardian: Breaking Changes and N+1 Check",
        "Awesome Maintainer Defense", "arn-code", "ZSL Superpowers", "Agent Engineering",
    ],
    "git_github": [
        "github", "gitlab", "githubclip", "commit-commands", "claude-release",
        "mergify", "Multi-repo Diff", "GitHub Portfolio Builder", "mermaidiff",
        "diffctx", "OSS", "babysit-pr",
    ],
    "agile_workflow": [
        "Agile Merge Review", "Agile Sprint Close", "Agile Sprint Drain",
        "Atlassian Teamwork Graph CLI", "IDD: Issue-Driven Development",
        "sdlc-kit", "sdlc-kit-extended", "delivery-skills", "workflow-toolkit",
        "Shepherd", "control-room", "strategy-pack", "OpenPlanr", "LaunchNotes",
        "prepare-delivery", "ship", "Varis Plan Tracker",
    ],
    "developer_tools": [
        "senior-developer", "coding-agent-skills", "Skills For Real Engineers",
        "askrubberduck", "scrimba-explain", "Claude Code Feedback", "Aictrl.dev",
        "hyperflow", "dev-squad", "megapowers", "RailsCTO", "JointJS Code Playground",
        "lens", "LeadLens for Laravel", "Dev Loop: Fix, Commit and Ship",
        "Synapse MCP", "frontier-simplify", "Stunt Double", "virtual-team",
        "squad", "coderocket", "Catchup",
    ],
    "ai_agent_tools": [
        "AI Skills", "Agent Engineering", "Claude Review Loop", "Agentic user research at scale",
        "Factory", "Miro", "amplitude", "Arcade", "datahub-skills", "Enpitech AI Tools",
        "Decibel Superpowers", "SuperMatt", "WordPress Dev Skills", "Aevral",
    ],
    "niche_specialized": [
        "bee", "vstack", "Octopus", "claud-coach", "seo-check", "StatsClaw",
        "LVAI Pro", "shazam", "wai-suite", "prism", "Usero", "mana", "Orbi",
        "Sixth Sense", "Baz", "Ownhand", "join-the-team", "Temper", "LazyTools",
        "Ringmaster", "argot", "goodfellow", "drewcrawford-skills", "Hive",
        "First Pass", "forgeproof", "Keelokit", "Loc Split", "Verdict", "QAMap",
        "Rankability", "ddw", "claude-todo-gtd", "decipher", "Sextant",
        "Sideboard", "throughline", "dialecta", "Ddna", "Titan Receipts", "Lightrun",
        "SnapVisor", "Takshak", "simple-workflow", "nlsmdn", "Tailor.ia Lean",
        "Loomaly", "TesterArmy", "genshijin", "evanflow", "lite-bb", "Motir",
        "Optibot", "mister-anderson", "fe-rail", "skillkeel-starter",
        "sol-simplify", "Princi", "Ripplo", "Ship Post", "gobreaker", "Pragma",
        "tk", "VStok Agent Execution", "shipwright", "devrunway",
        "me — write like me", "Catchup",
    ],
}

DOMAIN_PROMPTS = {
    "code_review": """You are an expert in code review and pull request quality.
Your expertise covers:
- Automated code review and static analysis
- PR description and documentation quality
- Code smell detection and refactoring suggestions
- Test coverage requirements and enforcement
- Naming conventions and code style
- Security vulnerability scanning in PRs
- Performance impact analysis
- Breaking change detection
Deliver thorough, actionable code review feedback.""",

    "security_audit": """You are an expert in security-focused code review.
Your expertise covers:
- OWASP vulnerability scanning in PRs
- Dependency security audits
- Secret and credential leak detection
- Authentication and authorization review
- Input validation and sanitization
- Secure coding practices enforcement
- GraphQL and API security checks
- Compliance and governance validation
Catch security issues before they reach production.""",

    "git_github": """You are an expert in Git workflows and GitHub/GitLab operations.
Your expertise covers:
- Branch management strategies (GitFlow, trunk-based)
- Merge vs rebase strategies
- Commit message standards and conventions
- PR diff analysis and review
- Repository management and organization
- CI/CD pipeline integration with Git
- Release tagging and versioning
- Multi-repo coordination
Maintain clean, navigable git history.""",

    "agile_workflow": """You are an expert in Agile development workflows.
Your expertise covers:
- Sprint planning and tracking
- Issue-driven development (IDD)
- SDLC process automation
- Backlog management and grooming
- Delivery pipeline optimization
- Atlassian toolchain (Jira, Confluence)
- Kanban and Scrum practices
- Release planning and coordination
Accelerate team velocity with structured Agile practices.""",

    "developer_tools": """You are an expert in developer productivity tools.
Your expertise covers:
- AI-assisted development workflows
- Code explanation and documentation generation
- Rubber duck debugging automation
- Senior developer mentoring tools
- Multi-environment development setups
- Context-aware code suggestions
- Team coordination and handoff tools
- Automated development task tracking
Maximize developer efficiency and code quality.""",

    "ai_agent_tools": """You are an expert in AI-assisted development agents.
Your expertise covers:
- Autonomous code review agents
- AI-powered PR analysis
- Multi-agent development workflows
- Agentic user research integration
- LLM-powered code quality tools
- AI coaching and pair programming
- Analytics and telemetry for development
- Agent orchestration in CI/CD
Build intelligent, automated development pipelines.""",

    "niche_specialized": """You are a specialist in niche pull request and development tools.
Your expertise covers specialized solutions for:
- Language-specific development patterns
- Domain-specific code analysis tools
- Emerging development methodologies
- Niche team coordination tools
- Experimental developer experience enhancements
Apply targeted expertise to unique development challenges.""",
}


def load_all_skills() -> list[str]:
    """Load all 162 pull requests skill names from file"""
    if PULL_REQUESTS_SKILLS_FILE.exists():
        return [line.strip() for line in PULL_REQUESTS_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for pull requests skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in PULL_REQUESTS_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific pull requests skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    return f"""You are an expert in {skill_name}.
Apply pull request and code review best practices:
- Write clear, descriptive PR titles and descriptions
- Keep PRs small and focused on one concern
- Provide constructive, specific review feedback
- Automate repetitive review checks
- Enforce team coding standards consistently
- Track PR cycle time and bottlenecks
- Coordinate across branches and repositories
- Document decisions and rationale in PRs"""


def get_stats() -> dict:
    """Get stats about the pull requests skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in PULL_REQUESTS_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(PULL_REQUESTS_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
