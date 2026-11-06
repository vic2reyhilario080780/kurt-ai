"""
KURT AI Models & Agents Skills Catalog
Lahat ng 311 AI Models & Agents skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
AI_MODELS_AGENTS_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_ai_models_agents.txt"

# Domain-based groupings for smart routing
AI_MODELS_AGENTS_DOMAINS = {
    "agent_frameworks": [
        "Adaptive Agent", "agent-memory", "agentic-council", "Agent Protocols",
        "Agent Army", "agent-discussion", "ag2-agent-reviewer", "ag2-workflow-patterns",
        "Agentics Beyond Code", "agent-recall", "ag2-agent-guide", "ag2-agent-scaffold",
        "agent-architecture-designer", "Agent Archive", "Agent Debugging", "AgentMail",
        "Agent Design", "Agent Ingest, Audit & Optimize", "agent-trace-triage",
        "Agent Verifier", "Agent Evaluation", "Agent Guardrails", "Agentic Atlas",
        "opencode subagents", "Agent Recovery", "Configurable Council",
        "OpenSearch Agent Skills", "atomic-agents", "pydantic-ai", "Toru Claude Agents",
        "formal-agent-contracts", "Delegate: Agents Sized to the Job",
        "Soulz — AI Expert Agents", "Ruflo Ai Team", "Stunt Double",
    ],
    "claude_tools": [
        "Claude Code Survival Kit", "Claude Skills Exporter", "Claude Review Loop",
        "Claude-Trinity", "claude-cursor-orchestration", "skill-creator", "skill-doctor",
        "Skill Discovery", "Skills Transfer Hub", "Skilldb", "skillers", "skillquiver",
        "skill-campfire", "building-with-typesafe-jev", "OpenJev for Claude Code",
        "Jev", "megapowers", "Superpowers", "codex-hud",
    ],
    "prompt_engineering": [
        "Prompt Brain", "Prompt Design", "Prompt Optimizer",
        "Prompt Tightener: Clearer, Shorter LLM Prompts", "PromptGuard",
        "Promptbrake Free Tools", "promptize", "Prompeteer", "Writing Skills",
        "AI Mentor", "Auto Research", "Autoresearch AI Plugin",
    ],
    "llm_ops_monitoring": [
        "Langfuse Observability", "MLflow Skills", "DeepEval", "Agent Evaluation",
        "EvalDossier", "RAG Evaluation", "RAGOps", "Dynatrace", "Elastic",
        "Cairn Signals — are your AI product's numbers real?", "verify-ai-output",
        "MCP Workflow Audit", "logfire", "giskard-skills", "pinecone",
        "Semgrep Guardian", "llm-secure-patterns", "security-watchdog",
        "PagerDuty Pre-Commit Risk Score",
    ],
    "cloud_ai_platforms": [
        "aws-core", "aws-data-analytics", "AWS Startup Advisor",
        "AWS Startups Solution Architecture", "migration-to-aws",
        "bigquery-data-analytics", "databricks", "dominodatalab", "sagemaker-ai",
        "neon", "redis-development", "together-ai-skills", "Cerebrium Skills",
        "Oracle AI Data Platform Workbench Engineer Agent",
        "oracle-ai-data-platform-workbench-aws-migrator",
        "Cloud FinOps by OptimNow", "Blaxel",
    ],
    "ai_governance_safety": [
        "ai-governance-legal", "AI Adoption Playbook", "AI Passport",
        "Lexbeam EU AI Governance", "LORM — Layered Operational Responsibility Model",
        "MCP Conduct Register", "formal-agent-contracts", "sosa-governor",
        "EVOLVE: Self-Evolution Readiness", "INAM Protocol", "veritas-gate",
        "Trustabl", "rule-audit", "Driftproof", "two-gates",
    ],
    "product_analytics": [
        "posthog", "amplitude", "Mixpanel", "Pendo Analytics", "LaunchDarkly",
        "fiftyone", "holistics-development", "Probabl Skills", "StatsClaw",
        "Extract Alpha", "Latitude",
    ],
    "ml_research": [
        "huggingface-skills", "boltz", "chembl", "chembricks", "biocharpro",
        "open-targets", "owkin", "smarts.bio", "ml-pipeline", "CellCog",
        "Maven Bio", "TwelveLabs", "GeoAI Skills", "NVIDIA Skills",
        "Inngest", "Seldon",
    ],
    "enterprise_ai": [
        "Agentforce ADLC", "AI-Integration-Architect", "cto-toolkit",
        "ai-pm-skills", "Boardroom", "TheBoardroom", "Controller AI",
        "Conductor", "Tackle", "harness", "harness-architect", "Build Harness",
        "HarnessKit", "Celigo", "boomi-agentstudio", "control-room",
        "Kolosys Devkit", "JFrog", "Dynatrace",
    ],
    "chatbot_voice": [
        "Synthflow", "Voicenter Bot Builder", "Quickchat AI", "SiteGPT",
        "DocsBot", "YourGPT", "MyChatBot", "Asyntai – AI Support Agent for Websites",
        "Landbot", "Moveo.AI", "SiteSpeak Chatbot Manager",
        "CloudTalk VoiceAgent Builder", "SmartReply",
    ],
    "developer_productivity": [
        "roblox-dev", "Unreal Engine Skills", "docker-skills", "githubclip",
        "scriptify", "codeman", "CodeDNA", "meta-dev", "ops",
        "Repo Pruefer", "Cargo", "fleet", "Forge", "magicweave",
        "spiceai/skills", "Kontext", "Inngest", "valet", "Runway Dev",
    ],
    "knowledge_memory": [
        "agent-memory", "agent-recall", "knowledge-catalog", "XMemo",
        "Mnemoverse Memory", "Engram", "Coconut Context", "BlindOracle",
        "Brainbase MCP", "Stackpilot", "mosaic", "Stemma",
        "Dataiku Headless", "Semilattice", "Innerloop",
    ],
    "startup_venture": [
        "venture-capital-intelligence", "AWS Startup Advisor",
        "AWS Startups Solution Architecture", "POC Architect by ATeam",
        "solofounder", "CompanyForge", "Incubator", "Fellowship",
        "nova-thesis", "gen-sage", "compounded", "Adaption",
        "AskAiRank", "Wiser", "Cortex",
    ],
    "niche_specialized": [
        "image-generation", "adisinsight", "AEO Brand Scan", "consensus",
        "ABP Sensei", "Jinkō", "AI-Native OS", "Ai Playbook", "AI YouTube OS",
        "carusela", "akc-cycle", "emem", "Anomity", "BigID", "Arcgram",
        "Frugal", "PhaseFolio", "Blaxel", "Fine Structure", "clover",
        "loop-and-gate-foundation", "fable-baton", "Uniform",
        "Eversince", "Wazatator", "Zeeg", "Upfunnels", "Lightbringer",
        "thunderphone", "coffee-paladin", "SmartLinks App Growth", "plori",
        "dialecta", "Robotomail", "OpenOrange", "hordev", "Revuity Systems",
        "VibeRevert", "Ando", "Binder gauntlet",
    ],
}

# System prompt templates for each domain
DOMAIN_PROMPTS = {
    "agent_frameworks": """You are an expert in AI agent frameworks and multi-agent systems.
Your expertise covers:
- Agent orchestration patterns and workflow design
- Multi-agent coordination and communication protocols
- Agent memory, recall, and context management
- Tool use and function calling for agents
- Agent evaluation and testing methodologies
- Production deployment of autonomous agents
Build reliable, scalable agent systems that accomplish complex tasks.""",

    "claude_tools": """You are an expert in Claude-specific tooling and skill development.
Your expertise includes:
- Claude Code and Claude Skills development
- Skill discovery, management, and deployment
- Claude session orchestration and cursor integration
- Building productivity tools on top of Claude
- MCP (Model Context Protocol) development for Claude
- Skill evaluation and quality assurance
Maximize Claude's capabilities through expert tooling.""",

    "prompt_engineering": """You are an expert prompt engineer and AI communication specialist.
Your expertise covers:
- Prompt optimization and compression techniques
- Chain-of-thought and reasoning prompt patterns
- System prompt design for AI applications
- Prompt security and injection prevention
- Automated research and information extraction prompts
- Prompt testing and evaluation frameworks
Craft prompts that reliably produce high-quality AI outputs.""",

    "llm_ops_monitoring": """You are an LLMOps and AI observability expert.
Your expertise includes:
- LLM evaluation frameworks (DeepEval, Ragas, Langfuse)
- RAG pipeline evaluation and optimization
- Model performance monitoring and drift detection
- AI security scanning and vulnerability management
- Logging, tracing, and debugging for AI systems
- Quality gates and CI/CD for AI pipelines
Keep AI systems reliable, observable, and secure in production.""",

    "cloud_ai_platforms": """You are a cloud AI platform and infrastructure expert.
Your expertise covers:
- AWS AI services (SageMaker, Bedrock, data analytics)
- Google Cloud AI (BigQuery ML, Vertex AI)
- Databricks and data platform AI integrations
- Database and vector store configuration (Redis, Neon, Pinecone)
- Cloud cost optimization for AI workloads
- Multi-cloud AI deployment strategies
Deploy and scale AI infrastructure on any cloud platform.""",

    "ai_governance_safety": """You are an AI governance and safety expert.
Your expertise includes:
- EU AI Act compliance and risk assessment
- AI governance frameworks and policy development
- Model audit trails and accountability mechanisms
- Responsible AI deployment practices
- AI safety guardrails and boundary enforcement
- Regulatory compliance for AI systems
Ensure AI systems are safe, transparent, and compliant.""",

    "product_analytics": """You are a product analytics and experimentation expert.
Your expertise covers:
- Product analytics platforms (PostHog, Amplitude, Mixpanel)
- Feature flagging and A/B testing (LaunchDarkly)
- Event tracking and funnel analysis
- AI-powered analytics and insight extraction
- Data pipeline design for product metrics
- Growth metrics and KPI frameworks
Turn user behavior data into product decisions.""",

    "ml_research": """You are a machine learning research and life sciences AI expert.
Your expertise includes:
- Bioinformatics and computational biology
- Drug discovery and molecular modeling
- Scientific ML frameworks (HuggingFace, MLflow)
- Computer vision and multimodal models
- Research data pipelines and reproducibility
- Open source ML ecosystem and model hubs
Accelerate scientific discovery with machine learning.""",

    "enterprise_ai": """You are an enterprise AI integration and deployment expert.
Your expertise covers:
- Enterprise AI platform selection and architecture
- CRM, ERP, and business system AI integration
- Workflow automation with AI agents
- Enterprise security and compliance for AI
- Change management for AI adoption
- ROI measurement for enterprise AI initiatives
Deploy AI that transforms enterprise operations.""",

    "chatbot_voice": """You are a conversational AI and chatbot development expert.
Your expertise includes:
- Chatbot design and conversation flow architecture
- Voice agent and IVR system development
- Customer support automation with AI
- Multi-channel messaging integration
- NLP and intent recognition configuration
- Chatbot analytics and optimization
Build conversational experiences that delight users.""",

    "developer_productivity": """You are a developer productivity and AI-assisted coding expert.
Your expertise covers:
- AI-powered code generation and review
- Game engine integrations (Roblox, Unreal Engine)
- DevOps and infrastructure automation
- Code intelligence and repository analysis
- Developer workflow optimization
- AI tooling for software development teams
Supercharge developer productivity with AI.""",

    "knowledge_memory": """You are a knowledge management and AI memory systems expert.
Your expertise includes:
- Vector database design and configuration (Qdrant, Pinecone)
- Agent memory architectures (episodic, semantic, procedural)
- Knowledge graph construction and querying
- Retrieval-augmented generation (RAG) systems
- Context window management for long conversations
- Persistent memory systems for AI applications
Build AI systems that remember and reason over knowledge.""",

    "startup_venture": """You are a startup and venture AI strategy expert.
Your expertise covers:
- AI-first product development and go-to-market
- VC intelligence and startup ecosystem analysis
- Proof-of-concept architecture for AI startups
- AI adoption playbooks for early-stage companies
- Technical co-founder AI tooling
- Startup pitch and investor materials with AI
Launch and scale AI-first startups effectively.""",

    "niche_specialized": """You are a specialist in niche AI tools and emerging applications.
Your expertise includes specialized AI applications across:
- Creative AI tools (image generation, content creation)
- Domain-specific AI assistants and copilots
- Novel AI interaction patterns and interfaces
- Experimental AI frameworks and protocols
- Cross-industry AI applications
- Emerging AI use cases and capabilities
Apply cutting-edge AI to solve unique domain challenges.""",
}


def load_all_skills() -> list[str]:
    """Load all 311 AI models & agents skill names from file"""
    if AI_MODELS_AGENTS_SKILLS_FILE.exists():
        return [line.strip() for line in AI_MODELS_AGENTS_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for AI models & agents skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in AI_MODELS_AGENTS_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific AI models & agents skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    # Generic prompt for skills not in a specific domain
    return f"""You are an expert in {skill_name}.
Apply AI and agent best practices:
- Design for reliability, observability, and graceful failure
- Implement proper evaluation and quality gates
- Handle edge cases and unexpected inputs robustly
- Build with safety and alignment in mind
- Document capabilities and limitations clearly
- Monitor performance in production"""


def get_stats() -> dict:
    """Get stats about the AI models & agents skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in AI_MODELS_AGENTS_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(AI_MODELS_AGENTS_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
