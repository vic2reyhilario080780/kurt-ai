"""
KURT Code Skills Catalog
Lahat ng 1,104 Code skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
CODE_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_code.txt"

# Domain-based groupings for smart routing
CODE_DOMAINS = {
    "agentic_frameworks": [
        "agentic-council", "agentic-harness", "Agent Protocols", "Agent Army",
        "Agent Engineering", "Agent Debugging", "Agent Smith", "Agent Verifier",
        "Agent Formal Verify", "AgentKeeper", "AgentOne Token Compression",
        "agent-handoff", "agent-context-kit", "agent-trace-triage",
        "Agentic SDLC Kit", "Agentic SDLC", "Agentic Beta Testers",
        "Agentics Beyond Code", "atomic-agents", "opencode subagents",
        "Session Orchestration", "virtual-team", "aomi-build", "control-room",
        "coding-agent-skills", "ag2-agent-reviewer", "ag2-agent-scaffold",
        "ag2-workflow-patterns", "ag2-tool-builder",
    ],
    "code_review": [
        "code-review", "Code Review", "codex-review", "claude-code-review-council",
        "Deep Review", "adversarial-review", "finecomb: exhaustive code review and security audit",
        "audit-suite", "audit-project", "Agile Merge Review", "Claude Review Loop",
        "Review Ready", "pr-review-toolkit", "babysit-pr",
        "PR Story Aligner: Pull Request vs Ticket Check", "PRFlow",
        "Repo Pruefer", "Cairn Verify — did the AI really fix it?",
        "Adversarial Review", "code-review-harness", "Kazap Adversarial Review",
        "dishonest-code-audit", "first-principles-review", "Review Mode",
    ],
    "security": [
        "claude-security", "Security Guidance", "securitymaxxing", "security-maxxing",
        "OWASP Security Audit", "Semgrep Guardian", "42crunch-api-security-testing",
        "aws-agents-for-devsecops", "Security Audit Loop by ATeam",
        "finecomb: exhaustive code review and security audit",
        "Pi Security", "Aikido", "Shieldcode", "Verified Security Sweep",
        "Env Protector: Secret Scanner", "Zero Trust Audit Team", "nightvision",
        "Cyberine DevGuard", "Cyberine ReleaseGuard", "clover-security",
        "TrustPin", "bash-guardrails", "llm-secure-patterns", "PromptGuard",
        "LeakStop", "Hawkscan Ci", "Docker Image Scan", "dod-guard",
        "IaC Reviewer: Terraform Security and Cost Check",
        "Latio Secure Supply Chain Skills", "security-watchdog",
        "NiceTryGPT", "Dependency Sentinel: Vulnerability and License Scanner",
        "clover", "vibeguard", "zero-trust-feature-team",
    ],
    "frontend": [
        "design-is-code", "liquid-glass-skills", "shopify-polaris",
        "Skills For Real React/React Native Engineers", "Angular To React",
        "Backbone To React", "Ember To React", "Vanillajs To React",
        "react-native-best-practices", "typescript-native-lsp",
        "TypeScript Patterns Enforcer", "Web Vitals Auditor", "Modern Web Guidance",
        "Perf Profiler: Lighthouse and Core Web Vitals",
        "Bundle Size Sentinel: JavaScript Bundle Analyzer",
        "A11y Enforcer: WCAG Accessibility Checker", "Axe Accessibility",
        "liquid-skills", "liquid-dev", "liquid-glass",
        "parallax-threejs", "scriptify", "PWP-Project Workflow Protocol",
        "appstore-screenshots", "Mobile Release Check: Play and App Store Readiness",
        "Website Design", "Rayden UI Design Skill", "consistent-ui", "ui-consistency",
        "Figma to Code: Design to React, Vue and HTML",
    ],
    "backend": [
        "Backend Design", "Clean-Backend", "clean-architecture",
        "backend-performance-review", "Java Backend Skills", "Go Backend Skills",
        "Fastify Backend Skills", "Laravel AI Starter", "laravel-boost",
        "laravel-best-practices", "php-lsp — Claude Code Plugin", "php harmony",
        "Spring Tools Language Server — Claude Code Plugin", "spring-standards",
        "Elixir/Phoenix: LiveView", "Elixir/Phoenix: Ecto", "ElixirLS LSP",
        "elixir-expert-lsp", "clojure-lsp", "swift-lsp", "kotlin-lsp",
        "delphi-dev", "azure-sql-developer", "clickhouse-best-practices",
        "neon", "cockroachdb", "MongoDB (Self-Managed MCP)", "MongoDB Atlas (Managed MCP)",
        "NeoSQL MCP", "VillageSQL Skills", "db-migration-guard",
        "DB Schema Spy: Database Schema Explorer and ERD",
    ],
    "cloud_devops": [
        "aws-core", "aws-serverless", "aws-amplify", "deploy-on-aws",
        "aws-transform", "migration-to-aws", "databases-on-aws",
        "GCP DevKit", "Azure DevKit", "azure-sql-developer",
        "Kubernetes Mastery", "docker-skills", "Docker Image Scan",
        "terraform", "terraform-lsp", "IaC Reviewer: Terraform Security and Cost Check",
        "Render", "Netlify", "Cloudflare", "CloudPloy/Claude-plugin",
        "cloud-coder", "Runpod", "Daytona", "Blaxel", "Cerebrium Skills",
        "sagemaker-ai", "harness", "harness-architect", "harness-bootstrap",
        "harness-init", "Harness Scope", "Harness Designing Plugin",
        "CI Optimizer: Faster GitHub Actions and GitLab CI", "greenfield-delivery",
        "GCP DevKit", "deploy-on-aws", "arn-code", "arn-infra",
    ],
    "testing": [
        "Testing", "E2E Test Generator: Playwright and Cypress Tests", "Cypress",
        "DeepEval", "QA Bug Hunter", "QA My App", "QAMap", "qa-quest",
        "ado-testcraft", "Testers.ai CARBON Test Harness", "TestAtlas", "TestDino",
        "Test Coverage Intelligence: Risk-Ranked Coverage Gaps", "BugBug",
        "Meticulous", "swagger-contract-testing",
        "Service Boundary Tests: Containers, Contracts and Mocks",
        "Mock Data Hydrator: Seed and Test Data Generator", "playwright",
        "Checkly", "functionize-mcp",
    ],
    "ai_ml": [
        "huggingface-skills", "AI-Integration-Architect", "AI Skills",
        "AI Mentor", "together-ai-skills", "MLflow Skills", "pydantic-ai",
        "Cognee Memory", "graph-indexer", "Langfuse Observability", "logfire",
        "nova-thesis", "NVIDIA Skills", "giskard-skills",
        "LLM Project Docs", "llm-secure-patterns",
    ],
    "mobile": [
        "Dart and Flutter", "Flutter Skills", "flutter-skills",
        "Very Good AI Flutter Plugin", "expo", "adb-mcp",
        "Android Emulator QA Plugin", "SwiftUI guidance for macOS",
        "Swift FocusEngine Pro", "Meta VR", "roblox-dev",
        "Mobile Release Check: Play and App Store Readiness",
        "React Native", "react-native-best-practices",
    ],
    "data": [
        "dataverse", "fiftyone", "athena-tools",
        "DB Schema Spy: Database Schema Explorer and ERD", "db-migration-guard",
        "NeoSQL MCP", "VillageSQL Skills", "Query Inspector",
        "RLS Schema Explorer for Supabase", "supabase", "supabase-expert",
        "neon", "clickhouse-best-practices", "iceberg",
        "Code Metrics: Complexity and Duplication Report", "dbt-toolkit",
        "Data Pipeline Builder: dbt and Airflow Checks", "datahub-skills",
        "Honeydew Semantic Modeling Tools",
    ],
    "workflow_automation": [
        "Make Documentation", "workflow-toolkit", "sdlc-kit", "sdlc-kit-extended",
        "Agentic SDLC Kit", "Agentic SDLC", "itential-builder",
        "Temporal", "Temporal Semantics Guardian", "n8n Knowledge Base",
        "drillspark-workflow-toolkit",
    ],
    "documentation": [
        "doc-authoring-skills", "doc-authoring-skills-ja", "diataxis",
        "LLM Project Docs", "API Doc Generator: OpenAPI from Your Code",
        "Interactive Docs", "GitBook", "Mintlify", "jfrdoc",
        "sync-docs", "OpenDocs",
    ],
    "game_dev": [
        "Unreal Engine Skills", "unity-perf", "Unity", "roblox-dev",
        "PlayCanvas", "Minecraft Modding",
    ],
    "enterprise": [
        "D365FO X++ Development", "NetSuite SuiteCloud", "sap-fiori-mcp-server",
        "Workday Developer Agent for Claude", "boomi-integration", "Celigo",
        "Catalyst by Zoho", "Atlassian Forge Skills", "Atlassian Teamwork Graph CLI",
        "Agentforce ADLC", "Odoo Tools", "Kombai",
    ],
    "shopify": [
        "shopify-ai-toolkit", "shopify-polaris", "Shopify App Builder",
        "Shopify DevKit", "storefront-theme-kit", "liquid-skills",
        "liquid-dev", "liquid-glass-skills",
    ],
}

# System prompt templates for each domain
DOMAIN_PROMPTS = {
    "agentic_frameworks": """You are an expert in agentic AI systems and multi-agent architectures.
You can design, build, and debug complex agent workflows.
Apply best practices from agent engineering: proper handoffs, context management,
tool use, error recovery, and agent evaluation.
Consider: agent memory, context limits, task decomposition, and orchestration patterns.""",

    "code_review": """You are a world-class code reviewer with deep expertise in software engineering.
When reviewing code:
1. Check for bugs, edge cases, and logic errors
2. Assess security vulnerabilities (OWASP Top 10)
3. Evaluate performance and scalability concerns
4. Review code style, readability, and maintainability
5. Suggest specific improvements with examples
6. Prioritize findings by severity (Critical/High/Medium/Low)
Be constructive and explain the 'why' behind each suggestion.""",

    "security": """You are a cybersecurity expert specializing in application security.
Your expertise covers:
- OWASP Top 10 and beyond
- Secure coding practices for all major languages
- Authentication and authorization patterns
- Cryptography and secrets management
- Dependency vulnerability scanning
- Infrastructure security (IaC, containers, cloud)
Always think like an attacker to find vulnerabilities before they do.""",

    "frontend": """You are a senior frontend engineer with expertise in modern web development.
Your knowledge covers:
- React, Vue, Angular, and vanilla JS
- TypeScript best practices
- Performance optimization (Core Web Vitals, bundle size)
- Accessibility (WCAG 2.1 AA)
- CSS/styling systems and design tokens
- State management patterns
Write clean, accessible, performant code.""",

    "backend": """You are a backend engineering expert.
Your expertise includes:
- API design (REST, GraphQL, gRPC)
- Database design and optimization
- Microservices and distributed systems
- Message queues and event-driven architecture
- Authentication and authorization
- Performance and scalability patterns
- Multiple languages: Python, Go, Java, PHP, Ruby, Elixir, Rust
Write robust, maintainable, well-tested server-side code.""",

    "cloud_devops": """You are a DevOps and cloud engineering expert.
Your skills include:
- AWS, GCP, Azure architectures
- Kubernetes and container orchestration
- Infrastructure as Code (Terraform, CDK, Pulumi)
- CI/CD pipeline design
- Deployment strategies (blue-green, canary, rolling)
- Cost optimization
- SRE practices and reliability engineering
Build scalable, resilient, cost-effective cloud infrastructure.""",

    "testing": """You are a quality assurance and testing expert.
Your expertise covers:
- Test strategy and pyramid (unit/integration/e2e)
- Test-driven development (TDD/BDD)
- End-to-end testing (Playwright, Cypress)
- Performance testing
- Security testing
- Mock and test data strategies
Write tests that are reliable, fast, and meaningful.""",

    "ai_ml": """You are an AI/ML engineering expert.
Your knowledge covers:
- LLM integration and prompt engineering
- RAG (Retrieval Augmented Generation) systems
- Vector databases and embeddings
- Model evaluation and observability
- Fine-tuning and RLHF
- MLOps and model deployment
Build AI systems that are reliable, observable, and scalable.""",

    "mobile": """You are a mobile development expert.
Your expertise includes:
- React Native and Expo
- Flutter and Dart
- iOS (Swift, SwiftUI)
- Android (Kotlin, Jetpack Compose)
- Cross-platform strategies
- App store optimization and release management
Build beautiful, performant mobile apps.""",

    "data": """You are a data engineering expert.
Your skills include:
- Database design and optimization
- SQL query optimization
- Data modeling and schema design
- ETL/ELT pipelines
- Data lake and warehouse architectures
- Streaming data processing
Build reliable, scalable data systems.""",

    "workflow_automation": """You are a workflow automation expert.
Your skills include:
- n8n, Make (Integromat), Zapier workflows
- Business process automation
- Event-driven architectures
- Temporal and durable workflow patterns
- SDLC automation
Automate repetitive processes reliably and efficiently.""",

    "documentation": """You are a technical documentation expert.
Your expertise covers:
- API documentation (OpenAPI, AsyncAPI)
- Developer guides and tutorials
- Architecture decision records (ADRs)
- Diataxis framework (tutorials, how-tos, references, explanations)
- Doc-as-code workflows
Write clear, accurate, maintainable technical documentation.""",

    "game_dev": """You are an expert game developer.
You can build games with Unity, Unreal Engine, Roblox, and HTML5.
Always include: game loop structure, collision detection, score system, game over/restart.
Make games playable and fun!""",

    "enterprise": """You are an enterprise software integration expert.
Your expertise includes:
- SAP, Salesforce, Oracle integrations
- Workday and HR systems
- iPaaS platforms (Boomi, MuleSoft, Celigo)
- Enterprise API patterns
- Data governance and compliance
Build reliable enterprise integrations with proper error handling.""",

    "shopify": """You are a Shopify development expert.
Your expertise covers:
- Shopify Liquid templating
- Shopify app development (Polaris, App Bridge)
- Theme customization and storefront
- Shopify APIs and webhooks
- Conversion optimization
Build high-converting Shopify stores and apps.""",
}


def load_all_skills() -> list[str]:
    """Load all 1,104 code skill names from file"""
    if CODE_SKILLS_FILE.exists():
        return [line.strip() for line in CODE_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for code skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in CODE_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific code skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    # Generic coding prompt for skills not in a specific domain
    return f"""You are an expert in {skill_name}.
Apply coding best practices:
- Write clean, maintainable code
- Follow established patterns for this technology
- Consider performance, security, and scalability
- Document your work clearly
- Test your implementations thoroughly"""


def get_stats() -> dict:
    """Get stats about the code skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in CODE_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(CODE_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
