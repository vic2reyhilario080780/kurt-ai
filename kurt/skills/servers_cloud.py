"""
KURT Servers & Cloud Skills Catalog
Lahat ng 251 Servers & cloud skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
SERVERS_CLOUD_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_servers_cloud.txt"

# Domain-based groupings for smart routing
SERVERS_CLOUD_DOMAINS = {
    "aws": [
        "aws-core", "aws-serverless", "aws-agents-for-devsecops", "aws-amplify",
        "deploy-on-aws", "AWS Startup Advisor", "AWS Startups Solution Architecture",
        "aws-data-analytics", "aws-transform", "migration-to-aws",
        "AWS Cost Guard: Cloud Cost and Kubernetes Debugging", "aws-cost-audit",
        "dataproc",
    ],
    "gcp_azure": [
        "google-cloud-storage", "GCP DevKit", "cloud-sql-postgresql",
        "cloud-sql-sqlserver", "alloydb-omni", "Azure DevKit", "amg-toolkit",
        "arvancloud-api", "ionoscloud-mcp", "arvancloud-api",
    ],
    "kubernetes_containers": [
        "docker-skills", "Docker Image Scan", "Kubernetes Mastery",
        "Supaflow", "Headlessmc", "localstack", "mirrord Agent Skills",
        "RubixKube", "Worktree Guard", "worktree-workspace",
        "WSL + Windows Workspace Connector",
    ],
    "databases_cache": [
        "supabase", "Upstash Redis", "neon", "duckdb-skills", "cloud-sql-postgresql",
        "cloud-sql-sqlserver", "alloydb-omni", "VillageSQL Skills", "Qdrant",
        "dominodatalab", "Xata", "Tigris", "datadops",
    ],
    "monitoring_observability": [
        "Grafana Assistant", "Grafana MCP", "New Relic", "Dynatrace", "Datadog",
        "sentry", "elmah.io", "Better Stack", "Observability Skills", "logfire",
        "SigNoz", "sumologic-mcp", "groundcover", "Lightrun", "JProfiler",
        "elastic-sense", "N|Solid Skills",
    ],
    "security_devops": [
        "Security Audit Loop by ATeam", "ARMO Ctrl", "Zscaler MCP Server",
        "CrowdSec Skill", "Serverless Audit", "AgentAvow Trust", "TrustPin",
        "Latio Secure Supply Chain Skills", "IaC Reviewer: Terraform Security and Cost Check",
        "nightvision", "Sola Security", "TLS Radar", "Ory Agent Plugin",
        "Varlock Skill", "bash-guardrails", "claude-code-audit-stack",
        "Anomity", "RootCX",
    ],
    "serverless_paas": [
        "Netlify", "railway", "Render", "Runpod", "Blaxel", "Cerebrium Skills",
        "Ship A Cloudflare Worker", "Ship", "ship", "hatchable", "Launchworthy",
        "CloudPloy/Claude-plugin", "AppHaven", "Sprites", "Skiffly",
        "Daytona", "Seenode", "Impreza Host", "Pethost",
    ],
    "networking_cdn": [
        "Cloudflare", "Fastly", "Netlify", "mcp-tunnels", "Ngrok Agent Skills",
        "network-footprint", "Tailproxy", "kong-konnect", "rustunnel",
        "ohmyho.st", "pntr",
    ],
    "iac_automation": [
        "terraform", "terraform-lsp", "Temporal", "itential-builder",
        "stackql-skills", "Checkly", "circle-skills", "Celigo",
        "Opsera DevSecOps", "platform-skills", "arn-infra", "cto-toolkit",
        "project-setup", "system-design-skills", "Clean-Backend",
        "Dev Environment Doctor", "ergo", "envrelay", "mise-plugin",
        "Env Setup Wizard: Project Setup and Onboarding",
    ],
    "cloud_cost_finops": [
        "Cloud FinOps by OptimNow", "aws-cost-audit",
        "AWS Cost Guard: Cloud Cost and Kubernetes Debugging",
        "DoiT Cloud Intelligence", "Costory FinOps Agent",
    ],
    "data_platforms": [
        "databricks", "huggingface-skills", "together-ai-skills", "Elastic",
        "OpenSearch Agent Skills", "oracle-ai-data-platform-workbench-spark-connectors",
        "oracle-ai-data-platform-workbench-aws-migrator", "Preset API Skills",
        "Preset CLI Skills", "spiceai/skills", "Aiven", "Fine Structure",
        "SWIRL", "pyvar-arch-storage",
    ],
    "developer_tools": [
        "expo", "lovable", "appwrite", "adb-mcp", "Cargo", "Go Backend Skills",
        "guile-skills", "Rig", "Ansight", "MapMap", "cmux-ultimate",
        "tmux-status", "logfire", "ergo", "workshop-mode", "batocera",
        "mac-disk-cleaner", "vm-disk-cleanup", "keep-awake",
        "Idasen Desk Control", "sounds", "mqtt", "ilo",
    ],
    "enterprise_integrations": [
        "Catalyst by Zoho", "Celigo", "Intuit Developer", "1Password Developer Tools",
        "InsForge", "amg-toolkit", "TD SYNNEX Plugin", "Indigo claude plugin",
        "Civic", "OneSignal", "Descope", "valet", "Re8ch Tenant",
        "ArcKit Netherlands Public Sector Overlay",
    ],
    "niche_specialized": [
        "Unity", "Unreal Engine Skills", "Meta VR", "NVIDIA Skills", "GeoAI Skills",
        "accelbyte-ai-plugins", "AgentUI Tools", "AgentKeeper", "Agentic SDLC Kit",
        "AI-Integration-Architect", "Backend Design", "KMJ CodeBridge",
        "Greenstack Umbraco", "10x-Team", "MetaFloor Supply Chain",
        "ESP32-AI-Agent-Skill", "Altimate Code", "Mcpbackend",
        "0bull", "Carbide", "Aqteron", "Samebase", "Fracfyi",
        "sethu: command bridge", "LORM — Layered Operational Responsibility Model",
        "Vertical Bar Agent", "drupal-boost", "cwc-makers", "join-the-team",
        "clawback", "deploycheck", "devrunway", "RAM Sleeper",
        "OBTO", "Monta", "Dilaya", "coffee-paladin", "session-sweep",
        "meetstream-ai-meeting-bot-api", "wawesome", "Croft",
        "Eon", "Firetiger", "ManageLM", "followrabbit",
        "Voitta YOLT", "hlx-admin-api-executor-guarded", "Cataam Compliance",
        "Zephyr Cloud", "Exepad", "RateMyCode", "Uptimely", "pilots",
        "ShiftControl", "Shipvela", "ORC8R", "perstat",
        "upbound", "Homelab Docker Ops", "EnergyInCloud",
        "Nimbus Land", "Elaichi", "EnergyFlowX", "idmp-plugin",
        "Testing", "WhatBreaks", "Civic", "arrfleet-toolkit",
        "Plan First", "ToolJet", "deepspace", "CogmemAi",
        "Spring Tools Language Server — Claude Code Plugin", "Samebase",
    ],
}

# System prompt templates for each domain
DOMAIN_PROMPTS = {
    "aws": """You are an AWS cloud expert.
Your expertise covers:
- AWS core services (EC2, S3, Lambda, RDS, DynamoDB, VPC)
- AWS serverless architecture and Lambda functions
- AWS DevSecOps pipelines and security automation
- AWS Amplify for full-stack development
- AWS data analytics (Kinesis, Glue, Athena, Redshift)
- Cloud cost optimization and AWS Cost Explorer
- Migration strategies to AWS
- AWS startup architecture and scaling
Build secure, scalable, cost-effective AWS infrastructure.""",

    "gcp_azure": """You are a Google Cloud Platform and Azure cloud expert.
Your expertise includes:
- GCP core services (Compute Engine, GKE, Cloud Run, BigQuery)
- Google Cloud Storage and Cloud SQL (PostgreSQL, SQL Server)
- AlloyDB for PostgreSQL workloads
- Azure services and DevKit tooling
- Multi-cloud and hybrid cloud architectures
- ArvanCloud and Ionos cloud platforms
- Cloud-native application development
Build scalable cloud solutions on GCP and Azure.""",

    "kubernetes_containers": """You are an expert in Kubernetes and container orchestration.
Your expertise covers:
- Kubernetes cluster management and deployment strategies
- Docker containerization and image scanning
- Helm charts and Kubernetes operators
- Local development with LocalStack and Mirrord
- Container security and image hardening
- WSL and Windows/Linux interoperability
- Microservices architecture patterns
Orchestrate containers at scale reliably.""",

    "databases_cache": """You are an expert in cloud databases and caching systems.
Your expertise includes:
- Supabase and Neon (serverless Postgres)
- Upstash Redis for serverless caching
- DuckDB for analytics workloads
- Cloud SQL (PostgreSQL, SQL Server) on GCP
- AlloyDB for high-performance Postgres
- Qdrant vector database for AI workloads
- Xata and Tigris managed databases
Design and optimize database architectures for cloud applications.""",

    "monitoring_observability": """You are an expert in cloud monitoring and observability.
Your expertise covers:
- Grafana dashboards and alerting
- Datadog APM and infrastructure monitoring
- New Relic and Dynatrace observability
- Sentry error tracking and performance monitoring
- ELK Stack (Elasticsearch, Logstash, Kibana)
- SigNoz open-source observability
- SumoLogic log management
- Distributed tracing and OpenTelemetry
Build comprehensive observability stacks.""",

    "security_devops": """You are an expert in cloud security and DevSecOps.
Your expertise includes:
- Security audit automation and scanning
- Zero-trust security architectures
- Supply chain security and SBOM management
- TLS/SSL certificate management
- Identity and access management (IAM/RBAC)
- Container and infrastructure security scanning
- Runtime security monitoring
- Compliance automation (SOC2, ISO27001, PCI-DSS)
Build security into every layer of the stack.""",

    "serverless_paas": """You are an expert in serverless and PaaS platforms.
Your expertise covers:
- Netlify and Vercel serverless deployments
- Railway and Render PaaS platforms
- Cloudflare Workers edge computing
- RunPod and Cerebrium GPU serverless
- Blaxel agent deployment platform
- App deployment automation and CI/CD
- Serverless function optimization
- Edge computing patterns
Deploy applications without managing infrastructure.""",

    "networking_cdn": """You are an expert in cloud networking and CDN.
Your expertise includes:
- Cloudflare CDN and DDoS protection
- Fastly edge computing and caching
- API gateway configuration (Kong)
- Tunnel management (Ngrok, Tailproxy)
- Network security and footprint analysis
- DNS and traffic routing
- Zero-trust networking
Optimize network performance and security.""",

    "iac_automation": """You are an expert in Infrastructure as Code and automation.
Your expertise covers:
- Terraform for multi-cloud infrastructure
- CI/CD pipeline automation (CircleCI)
- Workflow orchestration with Temporal
- Environment management and provisioning
- Dev environment setup automation
- Backend design patterns and clean architecture
- System design and architecture review
- Project scaffolding and boilerplate
Automate infrastructure with code and best practices.""",

    "cloud_cost_finops": """You are an expert in cloud cost optimization and FinOps.
Your expertise includes:
- Cloud cost visibility and attribution
- Reserved instance and savings plan optimization
- Kubernetes cost management
- Multi-cloud cost comparison and optimization
- Automated cost anomaly detection
- FinOps culture and practices
- Cost allocation and chargeback
Reduce cloud spend while maintaining performance.""",

    "data_platforms": """You are an expert in cloud data platforms and analytics.
Your expertise covers:
- Databricks unified data analytics platform
- Hugging Face model deployment and hosting
- Together AI for distributed AI inference
- Elasticsearch and OpenSearch
- Oracle data platform and cloud services
- Preset for data visualization (Apache Superset)
- SpiceAI for time-series data
- Aiven managed open-source data services
Build scalable data infrastructure for AI and analytics.""",

    "developer_tools": """You are an expert in cloud developer tools and utilities.
Your expertise includes:
- Expo for cross-platform mobile development
- Lovable for AI-assisted app building
- Appwrite backend-as-a-service
- Android Debug Bridge (ADB) automation
- Terminal and tmux workspace management
- IoT and embedded systems (ESP32, MQTT)
- Build tooling and language servers
- Developer productivity and workflow automation
Accelerate development with the right tools.""",

    "enterprise_integrations": """You are an expert in enterprise cloud integrations.
Your expertise covers:
- Zoho Catalyst enterprise platform
- Celigo iPaaS integration platform
- Intuit Developer APIs
- Identity and authentication services (Descope, Ory)
- Enterprise notification services (OneSignal)
- Multi-tenant architecture patterns
- Enterprise security and compliance
- API management and governance
Connect enterprise systems reliably and securely.""",

    "niche_specialized": """You are a specialist in niche cloud and infrastructure tools.
Your expertise covers specialized platforms:
- Game engine cloud deployments (Unity, Unreal Engine)
- GPU and ML infrastructure (NVIDIA, RunPod)
- IoT and edge computing platforms
- Supply chain and operations tools
- Specialized compliance and governance platforms
- Emerging cloud-native technologies
Apply cutting-edge infrastructure to solve unique challenges.""",
}


def load_all_skills() -> list[str]:
    """Load all 251 servers & cloud skill names from file"""
    if SERVERS_CLOUD_SKILLS_FILE.exists():
        return [line.strip() for line in SERVERS_CLOUD_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for servers & cloud skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in SERVERS_CLOUD_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific servers & cloud skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    # Generic prompt for skills not in a specific domain
    return f"""You are an expert in {skill_name}.
Apply cloud and infrastructure best practices:
- Design for high availability and fault tolerance
- Implement security at every layer
- Optimize for cost and performance
- Use infrastructure as code for reproducibility
- Monitor, log, and alert on critical metrics
- Follow the principle of least privilege
- Document architecture and runbooks"""


def get_stats() -> dict:
    """Get stats about the servers & cloud skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in SERVERS_CLOUD_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(SERVERS_CLOUD_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
