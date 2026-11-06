"""
KURT APIs Skills Catalog
Lahat ng 346 APIs skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
APIS_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_apis.txt"

# Domain-based groupings for smart routing
APIS_DOMAINS = {
    "payment_billing": [
        "Stripe", "PayPal", "Mercado Pago", "sumup", "airwallex-dev", "Billing Plane",
        "Adapty", "Paymob Integration", "Superwall", "unipaas", "Casapay Connect",
        "YoFacturo", "CryptoETF Flows", "coinpaprika", "CoinLobster", "bitcoin-companies",
        "mastercard-developers", "LNURL Auth", "Deposit Requester", "PaidSync",
        "Xsolla AI Toolkit", "Contezza AI for Merchants",
    ],
    "cloud_infrastructure": [
        "aws-core", "deploy-on-aws", "aws-amplify", "Netlify", "Cloudflare",
        "azure-devkit", "GCP DevKit", "neon", "localstack", "Fastly",
        "arvancloud-api", "Ngrok Agent Skills", "terraform", "stackql-skills",
        "amazon-location-service", "platform-skills", "oracle-ai-data-platform-workbench-spark-connectors",
        "Kampalo", "Porkbun", "Cheapest Domains", "Domain Check Skill", "DomainKits",
        "doDomain", "RedirHub", "URL Shortener by A.af", "TLS Radar",
    ],
    "developer_tools": [
        "github", "postman", "Arcade", "Checkly", "42crunch-api-security-testing",
        "API Contract Forge", "API Doc Generator: OpenAPI from Your Code",
        "API Drift Detector: TypeScript Contract Checker", "API Load Tester: Latency and Throughput Tests",
        "swagger-contract-testing", "Webhook Contract", "Service Boundary Tests: Containers, Contracts and Mocks",
        "mcp-server-dev", "mcp-apps", "mcp2cli", "mcp-client-kit", "mcp-connector",
        "ag2-tool-builder", "AgentUI Tools", "Installed Api", "RepoAccess",
        "postman", "Orbit by Postman API and MCP Server", "Beeceptor",
        "GraphQL Guardian: Breaking Changes and N+1 Check", "localstack",
        "JointJS Code Playground", "CodeQR", "powmcp", "Mcpbackend",
        "querymantic", "protogrid", "Steep", "Fracfyi", "Restless",
        "lite-bb", "pntr", "vda5050", "rdsh",
    ],
    "marketing_ads": [
        "Windsor.ai Ads and Marketing Data", "AdWhispr Ads & Marketing Agent",
        "AdMakeAI", "AdCopilot for Google Ads, Google Analytics, Google Search Console & Google Tag Manager",
        "AdvisorPPC - Google Ads, Analytics, Tag Manager, Search Console and YouTube Connector",
        "Adspirer Advertising Agent", "adplane", "adlane", "Ryze AI Marketing Skills",
        "Supermetrics Ads & Marketing Analytics", "HYPD AI - Paid Ads & Analytics",
        "mcp-gsc", "SE Ranking", "HarborRank SEO", "RankControl", "ASO Atlas",
        "asodev", "apptweak-api", "Socialinsider", "PostSyncer", "Anysite GTM",
        "KiteGTM", "LeadMagic", "lead411", "Letterdrop", "Searcherries",
        "Serpzilla SEO Guest Posting and Link Insertions", "SerpApi Claude Plugin",
    ],
    "security_auth": [
        "workos", "Descope", "crowdstrike-falcon-foundry", "Fingerprint",
        "Proofable", "CrowdSec Skill", "nightvision", "ARMO Ctrl",
        "protect-mcp", "ScanMalware", "VPNDetection", "Ory Agent Plugin",
        "Civic", "network-footprint", "Sola Security", "Open Voice Shield",
        "Confident AI Client", "Duende Agent Skills", "Above Security",
        "Phished", "SignatureAPI", "Signaturit", "GetSign",
    ],
    "data_analytics": [
        "looker", "Allium", "diffbot", "HasData", "Qlik Agents", "Preset API Skills",
        "DataHub Cloud", "dominodatalab", "Bigmind", "Fine Structure",
        "EODHD Financial Data APIs", "Blocksize Market Data", "CarsXE",
        "Car Image API", "FXMacroData", "open-targets", "healthit-copilot",
        "GovTribe", "smarts.bio", "Olostep", "glean-dev-docs", "Hunter",
        "MapMap", "Chicago Cityscape", "LinqAlpha",
    ],
    "communication_messaging": [
        "slack", "RingCentral", "Voicenter MCP", "Voicenter API Skills",
        "SignalWire", "OneSignal", "jambonz-skills", "post bridge",
        "feishu", "SenderKit", "Quickchat AI",
    ],
    "commerce_ecommerce": [
        "shopify-ai-toolkit", "Shopify App Builder", "LogiCommerce Backoffice",
        "wake-storefront", "Trendyol Marketplace Integration", "CoCart API",
        "Printago", "Shippo", "Shipmail", "Rapiboy", "Linkly",
        "DiscoLike", "Toyroom", "Clinch", "ScaleSKUs", "MerchantFlow",
        "Storeadops", "Karrito", "MetaFloor Supply Chain", "MarcoPolo",
        "PlayDrop", "Cala", "Cargo",
    ],
    "ai_ml_tools": [
        "Plugin Management", "claude-code-setup", "ai-governance-legal",
        "AI-Integration-Architect", "agentic-council", "Backend Design",
        "ag2-tool-builder", "AgentUI Tools", "mcp-server-dev",
        "lovable", "Gen-sage", "Vibee", "Realize Plugin", "Pluno WebMCP for Anything",
        "Tool Schemas", "Ultralayer", "Synter", "Monaiq",
        "ThoughtSpot Spottercode", "Styx", "Bigmind", "Instant",
        "Anson", "Snagly", "Hopkin", "Yes2SDK",
    ],
    "monitoring_devops": [
        "incident.io", "Rootly", "Checkly", "soundcheck", "Uptimely",
        "groundcover", "Treblle", "Rapilog", "freshprobe", "monl — backend compiler",
        "Service Boundary Tests: Containers, Contracts and Mocks",
        "hlx-admin-api-executor-guarded", "Fastah NetOps Tools", "mqtt",
        "kong-konnect", "XEDI", "SWIRL", "Runway Dev",
    ],
    "finance_wealth": [
        "Claude for Financial Advisors", "BlackRock Advisor Center",
        "Vanguard Advisor Tools", "Antevo Wealth", "Intuit Developer",
        "NetSuite AI Companion", "Juniper Square", "Wealthbox",
        "TradeOS AI", "Mosaic", "Ripplecom", "Manifold",
        "Golf Intelligence", "IDC Quanta", "Clearskies",
        "SupaBird", "Pollen",
    ],
    "enterprise_integrations": [
        "Celigo", "boomi-agentstudio", "boomi-integration", "Supaflow",
        "Form.io", "Atlassian Forge Skills", "Catalyst by Zoho",
        "dataverse", "Contentstack Agent Skills", "youdotcom-agent-skills",
        "Crossbeam Skills", "accelbyte-ai-plugins", "Acumatica Plugin",
        "AssistantLabs — Personal Assistant for Business", "Sindic8",
        "versori-skills", "Paymob Integration", "SAP", "TD SYNNEX Plugin",
        "Indigo claude plugin", "ScaleSKUs", "concordia-protocol",
        "Croft", "Vaara", "MyChatBot",
    ],
    "healthcare_bio": [
        "Maven Bio", "healthit-copilot", "smarts.bio", "open-targets",
        "Vibee", "Limonene",
    ],
    "legal_compliance": [
        "cocounsel-legal", "ip-legal", "ai-governance-legal",
        "Civic", "Proofable", "InsForge", "Casely",
        "PeerPush", "Saas Rfp",
    ],
}

# System prompt templates for each domain
DOMAIN_PROMPTS = {
    "payment_billing": """You are a payments and billing API expert.
Your expertise covers:
- Payment gateway integration (Stripe, PayPal, Mercado Pago)
- Subscription and billing management
- Cryptocurrency and blockchain payments
- PCI compliance and security
- Invoice generation and accounting integrations
- Multi-currency and international payments
Build reliable payment systems that scale.""",

    "cloud_infrastructure": """You are a cloud infrastructure and DevOps expert.
Your expertise includes:
- Cloud platform APIs (AWS, Azure, GCP, Cloudflare)
- Infrastructure as code (Terraform, CDK)
- Edge computing and CDN configuration
- Domain management and DNS
- Serverless functions and API gateways
- Container orchestration and deployment
Deploy and scale cloud infrastructure with confidence.""",

    "developer_tools": """You are a developer tools and API engineering expert.
Your expertise covers:
- API design, testing, and documentation (OpenAPI, Postman)
- Webhook architecture and testing
- MCP server development and integration
- Contract testing and API versioning
- GraphQL and REST best practices
- Local development environments
Build APIs that developers love to work with.""",

    "marketing_ads": """You are a marketing technology and advertising API expert.
Your expertise includes:
- Google Ads, Meta Ads, and programmatic advertising APIs
- Analytics integration (GA4, Tag Manager)
- SEO tooling and rank tracking APIs
- Social media management and scheduling
- Ad performance measurement and attribution
- Marketing automation workflows
Maximize ROI through data-driven marketing integrations.""",

    "security_auth": """You are a security and authentication API expert.
Your expertise covers:
- Identity and access management (WorkOS, Auth0, Descope)
- Zero-trust security architectures
- Fraud detection and device fingerprinting
- API security scanning and vulnerability management
- Digital signatures and document verification
- Threat intelligence and security monitoring
Build secure-by-design applications and APIs.""",

    "data_analytics": """You are a data and analytics API expert.
Your expertise includes:
- Business intelligence API integrations (Looker, Qlik)
- Data enrichment and web scraping APIs
- Financial data feeds and market data
- Geospatial and mapping data
- Health and life sciences data APIs
- Real-time data streaming
Turn raw data into actionable business intelligence.""",

    "communication_messaging": """You are a communications and messaging API expert.
Your expertise covers:
- Messaging platform APIs (Slack, Teams, WhatsApp)
- VoIP and telephony integrations
- Push notification services
- Video and conferencing APIs
- SMS and email delivery
- Real-time communication architectures
Connect people and systems through reliable communication APIs.""",

    "commerce_ecommerce": """You are an e-commerce and commerce API expert.
Your expertise includes:
- Shopping platform integrations (Shopify, WooCommerce)
- Inventory and fulfillment APIs
- Shipping and logistics APIs
- Product catalog management
- Order management systems
- Marketplace integrations
Build seamless commerce experiences across channels.""",

    "ai_ml_tools": """You are an AI and machine learning tools expert.
Your expertise covers:
- LLM API integration and orchestration
- AI agent frameworks and tools
- MCP (Model Context Protocol) development
- AI governance and compliance
- Model deployment and serving
- Prompt engineering and fine-tuning
Integrate AI capabilities into production systems.""",

    "monitoring_devops": """You are a monitoring, observability, and DevOps API expert.
Your expertise includes:
- Incident management and alerting APIs
- Application performance monitoring
- Log aggregation and analysis
- API gateway and proxy management
- IoT and MQTT protocols
- CI/CD pipeline integrations
Keep systems reliable and observable at scale.""",

    "finance_wealth": """You are a financial services and wealth management API expert.
Your expertise covers:
- Wealth management platform APIs
- Financial advisor tools and integrations
- Trading and market data APIs
- ERP and accounting system integrations
- Investment portfolio management
- Financial reporting and analytics
Build sophisticated financial applications with confidence.""",

    "enterprise_integrations": """You are an enterprise integration and middleware expert.
Your expertise includes:
- iPaaS platforms (Celigo, Boomi, Zapier)
- ERP system integrations (NetSuite, SAP, Acumatica)
- CRM and business process automation
- Enterprise service bus patterns
- Data transformation and mapping
- Multi-system workflow orchestration
Connect enterprise systems for seamless operations.""",

    "healthcare_bio": """You are a healthcare and biotech API expert.
Your expertise covers:
- Health data standards (FHIR, HL7)
- Clinical data management APIs
- Bioinformatics and genomics tools
- Drug discovery and research APIs
- Healthcare interoperability
- Medical device integrations
Accelerate healthcare innovation with compliant integrations.""",

    "legal_compliance": """You are a legal technology and compliance API expert.
Your expertise includes:
- E-signature and document signing APIs
- Legal research and case management
- Compliance monitoring and reporting
- Contract lifecycle management
- Identity verification for KYC/AML
- Intellectual property management
Streamline legal workflows with modern API integrations.""",
}


def load_all_skills() -> list[str]:
    """Load all 346 APIs skill names from file"""
    if APIS_SKILLS_FILE.exists():
        return [line.strip() for line in APIS_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for APIs skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in APIS_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific APIs skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    # Generic prompt for skills not in a specific domain
    return f"""You are an expert in {skill_name}.
Apply APIs and integration best practices:
- Design clean, versioned API interfaces
- Handle authentication, rate limiting, and errors gracefully
- Write comprehensive API documentation
- Build robust retry and fallback mechanisms
- Monitor API health and performance
- Follow security best practices for all integrations"""


def get_stats() -> dict:
    """Get stats about the APIs skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in APIS_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(APIS_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
