"""
KURT Logs & Errors Skills Catalog
Lahat ng 200 Logs & Errors skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
LOGS_ERRORS_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_logs_errors.txt"

# Domain-based groupings for smart routing
LOGS_ERRORS_DOMAINS = {
    "observability_monitoring": [
        "Datadog", "New Relic", "Grafana Assistant", "Grafana MCP", "Better Stack",
        "Dynatrace", "SigNoz", "logfire", "sumologic-mcp", "amplitude", "posthog",
        "Observability Skills", "logrocket", "dash0", "groundcover", "Fullstory",
        "loki", "elastic-sense", "Elastic", "OpenSearch Agent Skills",
        "Langfuse Observability", "MLflow Skills", "Lightrun", "Latitude",
        "Cairn Signals — are your AI product's numbers real?",
    ],
    "incident_management": [
        "incident.io", "PagerDuty Pre-Commit Risk Score", "Oncall", "Rootly",
        "Jam", "Statusline for Claude Code", "TinMan - Heartbeat for Claude Code",
        "Watchgoose Monitoring", "Healthcheckemail", "Uptimely", "Monta",
        "pushnotifime - human in the loop", "terminal-notifier", "Steadwing",
        "Product Support Investigator", "Noibu",
    ],
    "security_compliance": [
        "sentry", "sentry-cli", "Above Security", "Security Audit Loop by ATeam",
        "ARMO Ctrl", "Zscaler MCP Server", "crowdstrike-falcon-fusion", "CrowdSec Skill",
        "BigID", "drata-grc-skills", "SIEM Lab Coach", "Phished", "Sola Security",
        "bash-guardrails", "aws-agents-for-devsecops", "Heimdall", "VPNDetection",
        "gh-guard", "veritas-gate", "Cataam Compliance", "Open Voice Shield",
        "pyvar-operational-risk", "undercover",
    ],
    "debugging_testing": [
        "Agent Debugging", "MCP Debugging", "Agent Evaluation", "DeepEval",
        "Quality Supervisor", "Testing", "Cypress", "Codacy", "Bugsee",
        "RAG Evaluation", "Test Coverage Intelligence: Risk-Ranked Coverage Gaps",
        "Headroom: Large File and Log Reader", "adb-mcp", "Oh My Android",
        "Android Emulator QA Plugin", "claude-code-audit-stack", "claude-lens",
        "Claude Code Cost", "claude-performance", "Eyedbg", "Verdict",
    ],
    "infrastructure_devops": [
        "Kubernetes Mastery", "railway", "Render", "Prefect", "Inngest",
        "localstack", "Serverless Audit", "aws-core", "aws-data-analytics",
        "AWS Cost Guard: Cloud Cost and Kubernetes Debugging", "alloydb-omni",
        "CloudBees Unify AI plugin", "HarnessKit", "teamcity-cli", "Pipelinemd",
        "shipwright", "CI Optimizer: Faster GitHub Actions and GitLab CI",
        "Homelab Docker Ops", "vm-disk-cleanup", "n360-app-release",
        "Hostinger Connector", "arn-infra",
    ],
    "ai_agent_tools": [
        "AI Skills", "Agent Design", "AgentKeeper", "AgentOne Token Compression",
        "Agent Guardrails", "Agent Recovery", "agent-trace-triage",
        "Agentforce ADLC", "RAGOps", "Tool Schemas", "craft-statusline",
        "cto-toolkit", "platform-skills", "Cerebrium Skills", "dominodatalab",
        "Oracle AI Data Platform Workbench Engineer Agent", "Context.dev",
        "backend-performance-review", "Backend Design", "claude-forge",
        "AI-Advisors", "GeoAI Skills",
    ],
    "niche_specialized": [
        "Qdrant", "zilliz", "postman", "elmah.io", "Altertable", "Anomity",
        "quick-gate-python", "idmp-plugin", "wai-suite", "amg-toolkit",
        "arrfleet-toolkit", "Jam", "Rig", "java-backend-skills",
        "Java Backend Skills", "Go Backend Skills", "D365FO X++ Development",
        "Meta VR", "Flow Studio Power Automate", "ergo", "brizz",
        "join-the-team", "Skiffly", "1kmてんき", "search-visibility-kit",
        "ThinWindow", "echosy", "N|Solid Skills", "devrunway", "RAM Sleeper",
        "sosa-governor", "coffee-paladin", "First Pass", "drewcrawford-skills",
        "Launchworthy", "LOCI", "Voitta YOLT", "Normlotse", "simple-workflow",
        "Revelara", "nlsmdn", "freshprobe", "Shipbook", "Subtext",
        "Search o'Clock", "loopify", "SuperBot", "datadops",
        "skillkeel-starter", "perstat", "Firetiger", "Kenwea Notary",
        "ManageLM", "prism", "Titan Receipts", "Relvato", "Eon",
        "Re8ch Tenant", "wawesome", "Vaara", "AppHaven", "guile-skills",
        "Botify", "Styx", "cowork-session-fixer", "SEOcrawl AI Reports",
        "SEO GSC Wizard", "AI Search Visibility & Brand Mentions (GEO/AEO)",
        "github-cli-health-check", "Tuteliq", "drata-grc-skills",
        "RAG Evaluation", "Vinktar", "dash0", "logrocket", "loki",
        "elastic-sense", "shipwright", "wai-suite",
    ],
}

DOMAIN_PROMPTS = {
    "observability_monitoring": """You are an expert in observability and monitoring.
Your expertise covers:
- Log aggregation, analysis, and alerting (Datadog, New Relic, Grafana)
- Application performance monitoring (APM)
- Distributed tracing and span analysis
- Metrics collection and dashboards
- Error tracking and anomaly detection
- SLO/SLI monitoring and alerting
- Real user monitoring (RUM)
- AI/ML model observability
Surface actionable insights from logs and metrics.""",

    "incident_management": """You are an expert in incident management and response.
Your expertise covers:
- On-call scheduling and escalation workflows
- Incident triage and severity classification
- Post-mortem and root cause analysis
- Alerting thresholds and runbooks
- Status page management
- Mean time to resolution (MTTR) optimization
- Uptime monitoring and SLA tracking
- Human-in-the-loop approval workflows
Minimize downtime and improve incident response.""",

    "security_compliance": """You are an expert in security monitoring and compliance.
Your expertise covers:
- SIEM (Security Information and Event Management)
- Vulnerability scanning and penetration testing
- Cloud security posture management (CSPM)
- Compliance frameworks (SOC 2, ISO 27001, GDPR)
- Threat detection and response
- Access control auditing
- Security guardrails and policy enforcement
- Phishing and social engineering defense
Build secure, compliant systems with proactive threat detection.""",

    "debugging_testing": """You are an expert in debugging and test automation.
Your expertise covers:
- Unit, integration, and end-to-end testing
- AI model evaluation and benchmarking
- Code quality analysis and coverage reporting
- Mobile and browser debugging
- RAG pipeline evaluation
- Performance profiling and optimization
- Automated bug reporting and reproduction
- Test-driven development (TDD)
Ship reliable software through comprehensive testing.""",

    "infrastructure_devops": """You are an expert in infrastructure and DevOps.
Your expertise covers:
- Kubernetes orchestration and management
- CI/CD pipeline optimization
- Serverless architecture and deployment
- Cloud cost optimization (AWS, GCP, Azure)
- Container management and Docker
- Infrastructure as code (IaC)
- Local development environment setup
- Database and storage management
Build scalable, cost-efficient infrastructure.""",

    "ai_agent_tools": """You are an expert in AI agent development and operations.
Your expertise covers:
- Agent design patterns and architectures
- Agent evaluation and benchmarking
- RAG operations and optimization
- Token usage optimization
- Agent guardrails and safety controls
- Multi-agent orchestration
- Backend performance for AI workloads
- Claude Code and AI assistant tooling
Build production-ready AI agents with operational excellence.""",

    "niche_specialized": """You are a specialist in niche logging and monitoring tools.
Your expertise covers specialized solutions for:
- Vector database monitoring (Qdrant, Zilliz)
- API testing and management
- Platform-specific debugging tools
- Regional and language-specific monitoring
- Emerging observability technologies
Apply targeted expertise to unique monitoring challenges.""",
}


def load_all_skills() -> list[str]:
    """Load all 200 logs & errors skill names from file"""
    if LOGS_ERRORS_SKILLS_FILE.exists():
        return [line.strip() for line in LOGS_ERRORS_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for logs & errors skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in LOGS_ERRORS_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific logs & errors skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    return f"""You are an expert in {skill_name}.
Apply logging and observability best practices:
- Instrument code for meaningful, structured logs
- Set up alerts for anomalies and errors
- Build dashboards for key metrics
- Automate incident response and triage
- Maintain audit trails for compliance
- Optimize log storage and query performance
- Correlate events across distributed systems"""


def get_stats() -> dict:
    """Get stats about the logs & errors skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in LOGS_ERRORS_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(LOGS_ERRORS_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
