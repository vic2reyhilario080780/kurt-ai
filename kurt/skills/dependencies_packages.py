"""
KURT Dependencies & Packages Skills Catalog
Lahat ng 97 Dependencies & packages skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
DEPENDENCIES_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_dependencies_packages.txt"

# Domain-based groupings for smart routing
DEPENDENCIES_DOMAINS = {
    "security_compliance": [
        "Aikido", "SonarQube", "Security Audit Loop by ATeam", "Docker Image Scan",
        "AgentAvow Trust", "Ansvar Compliance Skills", "Pi Security", "Shield",
        "Cyberine ReleaseGuard", "LeakStop", "Dependency Sentinel: Vulnerability and License Scanner",
        "ARMO Ctrl", "Latio Secure Supply Chain Skills", "RegAffairs AI",
        "gh-guard", "public-repo-readiness",
    ],
    "package_management": [
        "NPMScan", "jar-explorer", "Vet Before Install", "dependency-evaluator",
        "Bundle Size Sentinel: JavaScript Bundle Analyzer", "Install Checkpoint",
        "Setup Audit", "Dev Environment Doctor", "Bugsee", "Review Ready",
        "sonatype-guide", "JFrog", "mise-plugin", "NerdyGeek",
    ],
    "cloud_infrastructure": [
        "terraform", "arn-infra", "aws-transform", "Runpod", "arvancloud-api",
        "Hostinger Connector", "Re8ch Tenant", "Rancher",
    ],
    "framework_platform": [
        "expo", "figma-suite", "WordPress Dev Skills", "laravel-best-practices",
        "Laravel AI Starter", "php-lsp — Claude Code Plugin", "Rust CLI Skills",
        "Very Good AI Flutter Plugin", "Java Backend Skills", "koin-migration",
        "huggingface-skills", "Meta VR",
    ],
    "integration_automation": [
        "Celigo", "boomi-marketplace", "streaming-skills-plugin", "sync-my-skills",
        "plugin-pilot", "envrelay", "Plugin Packaging", "cwc-makers",
        "AgentKeeper", "Claude skills updater", "aomi-build", "project-pilot",
        "Acumatica Plugin", "Mollie",
    ],
    "code_quality": [
        "Web Vitals Auditor", "impact-analysis", "arn-code", "Enpitech AI Tools",
        "drewcrawford-skills", "devrunway", "powmcp", "Installed Api",
        "N|Solid Skills", "dx-guard", "turbocharge", "optikit", "prism",
        "Headlessmc", "qrp",
    ],
    "niche_specialized": [
        "legal-builder-hub", "ip-legal", "Awesome Repositories", "MetaFloor Supply Chain",
        "knowledge-catalog", "Anomity", "Repo Pruefer", "CloudBees Unify AI plugin",
        "Mora", "TemplateCentral", "GrapeRoot", "Gateway Tariff Calculator",
        "PurchasePlus", "FreightUtils", "Kenwea Notary", "gortex",
        "Release Notes Index", "skillkeel-starter",
    ],
}

DOMAIN_PROMPTS = {
    "security_compliance": """You are an expert in software security and compliance.
Your expertise covers:
- Vulnerability scanning and remediation (CVEs, OWASP)
- Dependency security auditing and license compliance
- Container and Docker image security
- Supply chain security best practices
- Regulatory compliance (SOC2, GDPR, HIPAA)
- Static analysis and code security review
- Secret and credential leak detection
- Security policy enforcement in CI/CD
Build secure, compliant software from the ground up.""",

    "package_management": """You are an expert in package and dependency management.
Your expertise covers:
- npm, pip, Maven, Gradle, Cargo package ecosystems
- Dependency version pinning and lock files
- Bundle size analysis and optimization
- Package vulnerability assessment
- Dependency graph analysis and visualization
- Update strategies and breaking change management
- Private registry configuration
- Monorepo dependency management
Manage dependencies efficiently and safely.""",

    "cloud_infrastructure": """You are an expert in cloud infrastructure and IaC.
Your expertise covers:
- Terraform infrastructure as code
- AWS, Azure, GCP infrastructure provisioning
- Container orchestration and runtime environments
- Cloud cost optimization
- Infrastructure security hardening
- Multi-cloud deployment strategies
- GitOps and infrastructure automation
- Cloud migration planning
Deploy and manage infrastructure with confidence.""",

    "framework_platform": """You are an expert in development frameworks and platforms.
Your expertise covers:
- React Native / Expo mobile development
- WordPress plugin and theme development
- Laravel PHP framework best practices
- Rust systems programming
- Flutter cross-platform development
- Java backend architecture
- AI/ML framework integration (HuggingFace)
- VR/AR development platforms
Build with modern frameworks effectively.""",

    "integration_automation": """You are an expert in integration and automation platforms.
Your expertise covers:
- iPaaS platforms (Celigo, Boomi)
- API integration patterns and best practices
- Plugin and extension development
- Workflow automation and orchestration
- Data synchronization between systems
- Event-driven integration architectures
- Low-code/no-code integration tools
- Payment and commerce integrations
Connect and automate your tech stack seamlessly.""",

    "code_quality": """You are an expert in code quality and developer tooling.
Your expertise covers:
- Performance profiling and optimization
- Code impact analysis and change management
- Developer environment setup and maintenance
- API schema validation and documentation
- Node.js runtime monitoring and optimization
- Build pipeline optimization
- Developer experience improvement
- Code review automation
Maintain high code quality throughout development.""",

    "niche_specialized": """You are a specialist in niche dependency and package tools.
Your expertise covers specialized solutions for:
- Legal and IP compliance in software
- Supply chain management integrations
- Financial and payment processing integrations
- Specialized registry and repository tools
- Domain-specific package ecosystems
Apply targeted expertise to unique dependency challenges.""",
}


def load_all_skills() -> list[str]:
    """Load all 97 dependencies & packages skill names from file"""
    if DEPENDENCIES_SKILLS_FILE.exists():
        return [line.strip() for line in DEPENDENCIES_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for dependencies skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in DEPENDENCIES_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific dependencies skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    return f"""You are an expert in {skill_name}.
Apply dependency management best practices:
- Audit dependencies for security vulnerabilities regularly
- Pin dependency versions for reproducible builds
- Keep dependencies up to date with minimal breaking changes
- Analyze bundle sizes and remove unused packages
- Use lock files and checksums for supply chain security
- Document why each dependency is needed
- Prefer well-maintained packages with active communities
- Test dependency updates in isolated environments"""


def get_stats() -> dict:
    """Get stats about the dependencies & packages skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in DEPENDENCIES_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(DEPENDENCIES_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
