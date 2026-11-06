"""
KURT Pipelines & Jobs Skills Catalog
Lahat ng 368 Pipelines & Jobs skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
PIPELINES_JOBS_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_pipelines_jobs.txt"

# Domain-based groupings for smart routing
PIPELINES_JOBS_DOMAINS = {
    "ci_cd_devops": [
        "gitlab", "github-actions", "CI Optimizer: Faster GitHub Actions and GitLab CI",
        "harness", "harness-init", "Beer and code Harness", "HarnessKit",
        "Checkly", "BugBug", "functionize-mcp", "deploycheck", "claude-release",
        "Cyberine ReleaseGuard", "LaunchNotes", "n360-app-release", "teamcity-cli",
        "Ship A Cloudflare Worker", "Shipwright", "shipwright", "PagerDuty Pre-Commit Risk Score",
        "dod-guard", "gh-guard", "mergify", "Hawkscan Ci", "prepare-delivery",
        "greenfield-delivery", "delivery-skills", "git-weekly-changelog", "Turbocharge",
        "aws-serverless", "aws-core", "Render", "railway", "Runpod", "expo",
        "CloudBees Unify AI plugin", "CloudPloy/Claude-plugin", "cloud-coder",
        "TinMan - Heartbeat for Claude Code", "deploy-checklist",
    ],
    "project_management": [
        "asana", "linear", "Plane", "Plans", "AgileHero", "Agile Sprint Close",
        "Agile Sprint Drain", "Agile Forge Praxis", "sdlc-kit-extended", "Agentic SDLC",
        "Agentic SDLC Kit", "pm", "project-pilot", "lean-pm-skills", "cto-toolkit",
        "Arcade", "Atlassian Teamwork Graph CLI", "Work Unit Roadmap", "Wave Planning",
        "Wave Planner Skill", "Waves Exovian", "roadmapsmith", "Paramify",
        "OpenPlanr", "Pipelinemd", "Three Pillars", "Plantime", "pilots",
        "Varis Plan Tracker", "Gestão Ágil 2.0", "Mission", "dispatch-board",
        "Timesheet", "Auto-log your Claude Code sessions as Odoo timesheets",
    ],
    "monitoring_observability": [
        "Datadog", "New Relic", "Grafana MCP", "Dynatrace", "Mixpanel",
        "posthog", "axiomcore", "logfire", "elmah.io", "Better Stack",
        "Watchgoose Monitoring", "Rootly", "incident.io", "Oncall",
        "Schedule Health Check", "SignalPilot", "Motir", "Notifly",
        "StatsClaw", "Hive", "amplitude", "CSitRep Generator",
        "pushnotifime - human in the loop", "perstat",
    ],
    "data_pipeline": [
        "databricks", "dbt-toolkit", "Data Pipeline Builder: dbt and Airflow Checks",
        "Astronomer", "Prefect", "Temporal", "Conductor", "Celigo",
        "boomi-integration", "boomi-agentstudio", "boomi-data-integration",
        "boomi-marketplace", "Alteryx", "Qlik Agents", "datahub-skills",
        "DataHub Cloud", "Masthead Data", "dataproc", "Dataiku Headless",
        "oryxflow - Trustworthy AI Data Analysis", "csv-quality-gate",
        "Pipeline Reconcile", "EasyEsuite", "Workflows Conductor",
        "drillspark-workflow-toolkit", "outputai", "Genfeed",
    ],
    "cloud_infrastructure": [
        "terraform", "AWS Startups Solution Architecture", "aws-core", "aws-serverless",
        "azure-sql-developer", "arn-infra", "zilliz", "Upstash Redis",
        "MongoDB Atlas (Managed MCP)", "Supaflow", "localstack", "Homelab Docker Ops",
        "docker-skills", "stackql-skills", "NeonPanel", "Carbide", "Blaxel",
        "Zephyr Cloud", "upbound", "Seenode", "RubixKube", "ohmyho.st",
        "spiceai/skills", "superstack",
    ],
    "ai_agents": [
        "agentic-council", "Agent Protocols", "agentic-harness", "agent-handoff",
        "AI Employees", "AI-Integration-Architect", "AgentUI Tools", "Autoresearch",
        "Autoresearch AI Plugin", "Factory", "Codex Dispatch", "Controller AI",
        "Claude-Trinity", "claude-workflow", "claude-forge", "aio watermill-kit",
        "Rig", "Session Orchestration", "Vertical Bar Agent", "Orbit by Noveum",
        "One-Shot — Agentic Feature Generation", "Agentics Beyond Code",
        "huggingface-skills", "Cerebrium Skills", "Brainbase MCP",
        "mister-anderson", "LORM — Layered Operational Responsibility Model",
        "MCP Workflow Audit", "RAGOps", "Eval Conductor",
    ],
    "testing_qa": [
        "Testing", "BugBug", "functionize-mcp", "TestAtlas", "TestDino",
        "qa-quest", "Checkly", "assurance", "Agent Formal Verify",
        "token-efficiency-audit", "dbt-toolkit", "two-gates", "loop-and-gate-build-kit",
        "TrustPin", "Verdict", "Quality Supervisor",
    ],
    "business_automation": [
        "ActiveCampaign", "Customer.io", "AI Context Bridge for HubSpot",
        "Revenue Analytics for HubSpot", "NetSuite SuiteSkills", "Catalyst by Zoho",
        "Supermetrics Ads & Marketing Analytics", "Knock", "Inngest",
        "Flow Studio Power Automate", "Celigo", "hyperflow", "Cohesive",
        "platform-skills", "savvy", "BridgeApp", "wai-suite", "Kowalah",
        "versori-skills", "itential-builder", "Flowglad", "SmartLinks App Growth",
        "WarmySender", "demand-insight", "Upfunnels",
    ],
    "developer_tools": [
        "postman", "apiai.me", "askrubberduck", "lovable", "expo",
        "githubclip", "claude-workflow", "build-companion", "coderocket",
        "superdevflow", "dev-squad", "Claude Code Survival Kit", "beads-superpowers",
        "Accelerate AI Toolkit", "Greenstack Umbraco", "php harmony", "laravel-boost",
        "drupal-boost", "Go Backend Skills", "Headlessmc", "vstack",
        "Coconut Context", "drewcrawford-skills", "ccgrapher", "ergo",
        "streaming-skills-plugin", "cmux-ultimate", "mise-plugin",
    ],
    "security_compliance": [
        "crowdstrike-falcon-foundry", "crowdstrike-falcon-fusion", "genesis-governance-claude",
        "dod-guard", "gh-guard", "assurance", "TrustPin", "PagerDuty Pre-Commit Risk Score",
        "Cyberine ReleaseGuard", "Unleash Feature Flags", "token-efficiency-audit",
        "Agent Formal Verify", "RootCX", "Paramify",
    ],
    "product_analytics": [
        "Pendo Orchestrate", "amplitude", "posthog", "Mixpanel", "Supermetrics Ads & Marketing Analytics",
        "Revenue Analytics for HubSpot", "Socialstats", "StatsClaw", "Decibel Superpowers",
        "adisinsight", "Altertable", "PartnerImpact", "Basedash", "demand-insight",
        "Masthead Data", "Qlik Agents",
    ],
    "sdlc_planning": [
        "Agentic SDLC", "Agentic SDLC Kit", "sdlc-kit-extended", "Sdlc Assist",
        "Think Before You Build", "Three Pillars", "Hypotize", "estimator",
        "devils-advocate", "Agile Forge Praxis", "AgileHero", "story",
        "InsForge", "Project Scaffolder — Synaptic Edition", "join-the-team",
        "hatchable", "Realize Plugin", "optikit", "loopify",
    ],
}

# System prompt templates for each domain
DOMAIN_PROMPTS = {
    "ci_cd_devops": """You are a senior DevOps and CI/CD engineer.
Your expertise covers:
- CI/CD pipeline design (GitHub Actions, GitLab CI, Harness, Jenkins)
- Container orchestration (Docker, Kubernetes, Helm)
- Cloud deployment strategies (blue/green, canary, rolling)
- Infrastructure as code (Terraform, Pulumi)
- Release management and version control
- Build optimization and test parallelization
Build reliable, fast deployment pipelines.""",

    "project_management": """You are an expert project manager and delivery lead.
Your expertise includes:
- Agile methodologies (Scrum, Kanban, SAFe)
- Sprint planning, velocity tracking, and retrospectives
- Roadmap creation and stakeholder communication
- Risk management and dependency tracking
- Tools like Asana, Linear, Jira, Plane
- OKR frameworks and delivery metrics
Drive projects to successful, on-time delivery.""",

    "monitoring_observability": """You are a site reliability and observability expert.
Your expertise covers:
- Observability pillars: metrics, logs, traces
- Alerting strategy and incident management
- Tools: Datadog, New Relic, Grafana, Dynatrace
- SLOs, SLAs, and error budgets
- Runbooks and post-mortem processes
- Performance profiling and anomaly detection
Keep systems reliable and observable.""",

    "data_pipeline": """You are a data engineering and pipeline expert.
Your expertise includes:
- ETL/ELT pipeline design and orchestration
- Tools: dbt, Airflow, Prefect, Temporal, Databricks
- Data quality, lineage, and governance
- Real-time streaming vs batch processing
- Data warehouse and lakehouse architectures
- Integration platforms (Boomi, Celigo, Alteryx)
Build scalable, reliable data pipelines.""",

    "cloud_infrastructure": """You are a cloud infrastructure and platform engineer.
Your expertise covers:
- Multi-cloud architecture (AWS, Azure, GCP)
- Infrastructure as code (Terraform, CDK)
- Kubernetes and container platforms
- Database management (Postgres, MongoDB, Redis)
- Cost optimization and resource management
- Security and compliance at scale
Design robust, cost-effective cloud infrastructure.""",

    "ai_agents": """You are an AI agent systems architect.
Your expertise includes:
- Multi-agent orchestration and coordination
- LLM integration patterns and tool use
- Agent memory, planning, and reasoning
- Workflow automation with AI
- MCP server design and integration
- Evaluation frameworks for AI agents
Build reliable, effective AI agent systems.""",

    "testing_qa": """You are a quality assurance and testing expert.
Your expertise covers:
- Test strategy: unit, integration, E2E, performance
- Test automation frameworks and best practices
- Quality gates and acceptance criteria
- Formal verification and property testing
- Load testing and chaos engineering
- Continuous testing in CI/CD pipelines
Ensure software quality at every stage.""",

    "business_automation": """You are a business process automation expert.
Your expertise includes:
- CRM integration (HubSpot, Salesforce, Zoho)
- Marketing automation and customer journeys
- ERP integration (NetSuite, Odoo)
- iPaaS platforms (Celigo, Boomi, Zapier)
- Workflow automation and event-driven architecture
- API orchestration and data synchronization
Automate business processes for efficiency.""",

    "developer_tools": """You are a developer productivity and tooling expert.
Your expertise covers:
- Developer experience (DX) improvement
- API design and testing (Postman, OpenAPI)
- Code generation and scaffolding tools
- IDE integrations and extensions
- Documentation automation
- Developer onboarding and workflow optimization
Make developers more productive.""",

    "security_compliance": """You are a DevSecOps and compliance expert.
Your expertise includes:
- Shift-left security practices
- SAST, DAST, and dependency scanning
- Compliance frameworks (SOC 2, GDPR, HIPAA)
- Secret management and access control
- Security in CI/CD pipelines
- Incident response and forensics
Embed security throughout the SDLC.""",

    "product_analytics": """You are a product analytics and growth expert.
Your expertise covers:
- Product metrics and KPI frameworks
- Analytics tools (Mixpanel, Amplitude, PostHog)
- A/B testing and experimentation
- Funnel analysis and user journey mapping
- Data-driven product decisions
- Growth loops and retention strategies
Turn product data into actionable insights.""",

    "sdlc_planning": """You are a software development lifecycle planning expert.
Your expertise includes:
- Technical scoping and estimation
- Architecture decision records (ADRs)
- Technical debt management
- Feature flagging and gradual rollouts
- Risk assessment and mitigation
- Engineering team structure and processes
Plan and execute software projects effectively.""",
}


def load_all_skills() -> list[str]:
    """Load all 368 pipelines & jobs skill names from file"""
    if PIPELINES_JOBS_SKILLS_FILE.exists():
        return [line.strip() for line in PIPELINES_JOBS_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for pipelines & jobs skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in PIPELINES_JOBS_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific pipelines & jobs skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    # Generic prompt for skills not in a specific domain
    return f"""You are an expert in {skill_name}.
Apply pipelines & jobs best practices:
- Design reliable, automated workflows and pipelines
- Follow DevOps and agile principles
- Prioritize observability, reliability, and scalability
- Optimize for developer productivity and delivery speed
- Deliver production-ready, maintainable solutions"""


def get_stats() -> dict:
    """Get stats about the pipelines & jobs skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in PIPELINES_JOBS_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(PIPELINES_JOBS_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
