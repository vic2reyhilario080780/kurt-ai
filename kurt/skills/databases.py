"""
KURT Databases Skills Catalog
Lahat ng 246 Databases skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
DATABASES_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_databases.txt"

# Domain-based groupings for smart routing
DATABASES_DOMAINS = {
    "sql_relational": [
        "supabase", "supabase-expert", "neon", "cloud-sql-postgresql", "cloud-sql-mysql",
        "cloud-sql-sqlserver", "alloydb-omni", "alloydb", "azure-sql-developer",
        "MongoDB (Self-Managed MCP)", "MongoDB Atlas (Managed MCP)", "cockroachdb",
        "oracledb", "Oracle AI Data Platform Workbench Engineer Agent",
        "oracle-ai-data-platform-workbench-spark-connectors",
        "oracle-ai-data-platform-workbench-aws-migrator",
        "Oracle AI Data Platform Workbench Databricks Migrator",
        "SAP HANA CLI", "Couchbase", "spanner", "NeoSQL MCP",
        "RLS Schema Explorer for Supabase", "NeonPanel", "supalens",
        "DB Schema Spy: Database Schema Explorer and ERD", "VillageSQL Skills",
        "Elixir/Phoenix: Ecto", "TypedbEx — TypeDB for Elixir", "whodb",
        "AI for Database", "redis-development", "Upstash Redis",
    ],
    "nosql_vector": [
        "firebase", "firestore-native", "pinecone", "Qdrant", "zilliz",
        "Azure Cosmos DB", "dominodatalab", "Allium", "Xata",
        "DataHub Cloud", "datahub-skills", "BigID", "smarts.bio",
        "knowledge-catalog", "streaming-skills-plugin",
    ],
    "data_warehouse_analytics": [
        "databricks", "snowflake-cortex-code", "bigquery-data-analytics",
        "looker", "Mixpanel", "posthog", "duckdb-skills", "clickhouse-best-practices",
        "Preset API Skills", "Preset MCP Skills", "preset-toolkit", "holistics-development",
        "holistics-reporting", "Alteryx", "Pigment", "Tableau", "Dataiku Headless",
        "Honeydew Semantic Modeling Tools", "Masthead Data", "Rill",
        "Astronomer", "athena-tools", "aws-data-analytics", "Adzviser",
        "Trackian Marketing Analytics", "MARFOR Marketing Mix Modeling",
        "analytics-office", "demand-insight",
    ],
    "orm_migration": [
        "Opinionated Prisma Skills", "dbt-toolkit", "db-migration-guard",
        "Altertable", "Query Inspector", "Basedash", "backend-performance-review",
        "Go Backend Skills", "php harmony", "py-pit", "ml-pipeline",
        "boomi-data-integration", "boomi-datahub", "versori-skills", "synapse",
        "Ingest Labs", "pyvar-arch-data-ingestion", "pyvar-arch-storage",
        "SWIRL", "SpiceGrinder",
    ],
    "erp_enterprise": [
        "NetSuite Finance Analyst", "NetSuite AI Companion", "NetSuite SuiteCloud",
        "Odoo Tools", "ERP Upgrade & Fit-Gap Advisor", "Informatica", "dataverse",
        "Celigo", "SAP HANA CLI", "Lark/Feishu Integration", "InsForge",
        "Standards", "workflow-toolkit", "Civic", "Re8ch Tenant",
        "Merit Aktiva for AI Agents", "QuickBooks Labs",
    ],
    "cloud_data_platforms": [
        "aws-core", "aws-amplify", "aws-transform", "databases-on-aws",
        "sagemaker-ai", "huggingface-skills", "Aiven", "Fine Structure",
        "spiceai/skills", "OpenSearch Agent Skills", "Elastic",
        "Global Database", "Supaflow", "cortellis", "idmp-plugin",
    ],
    "test_seed_data": [
        "Mock Data Hydrator: Seed and Test Data Generator",
        "TDCv2 — Fake & Test Data Generator", "Stackhawk Data Seed",
        "Service Boundary Tests: Containers, Contracts and Mocks",
        "StringSpec", "catdef", "antiagree", "formal-agent-contracts",
        "RiskModels", "TimeDataModel-skill",
    ],
    "niche_specialized": [
        "Claude for Financial Advisors", "Chronograph GP", "fiftyone", "chembl",
        "CellCog", "Jinkō", "ABP Sensei", "agentic-council", "coding-skills",
        "AI Skills", "AgentUI Tools", "GeoAI Skills", "MetaFloor Supply Chain",
        "10x-Team", "TRES Finance Plugin", "Datarails financeos", "Contentstack Agent Skills",
        "Amazon Selling Partner", "Hostinger Connector", "Render", "Cargo",
        "WordPress DevKit", "Catalyst by Zoho", "comp-skills", "AI Context Bridge for HubSpot",
        "Spreadsheet (DWS Build)", "Altimate Code", "oryxflow - Trustworthy AI Data Analysis",
        "PWP-Project Workflow Protocol", "DalyKit", "Anysite GTM", "healthit-copilot",
        "ololand-dd", "ToolJet", "JointJS Code Playground", "revelata",
        "Revenue Analytics for HubSpot", "EasyEsuite", "Vibee", "Dreambase",
        "LORM — Layered Operational Responsibility Model", "Headset", "Dealertide",
        "Magekwik Magento Toolkit", "VerseDB: Comic Book Tracker", "Skiffly",
        "StoreConnect Agent Skills", "mirrord Agent Skills", "RoboSystems", "Powabase",
        "hatchable", "LCA and DEALA agent skills", "Clearskies", "SignalPilot",
        "oleander", "inSitu Sales", "Churn Prevention Kit", "Pipeline Reconcile",
        "OBTO", "TrueGradient Planning Analysis", "Planpack", "Dilaya", "Syndic8",
        "Credible", "Medusa", "Opsera DevSecOps", "Claude Piggy Bank", "Nemi",
        "monl — backend compiler", "TD SYNNEX Plugin", "PIASO", "InternetData",
        "Nogbase", "Croft", "Eqolux", "MarcoPolo", "Numeric MCP Toolkit",
        "ubl-star — facturas electrónicas a Power BI", "Glop Plugin", "PurchasePlus",
        "Karrito", "DataFrey", "followrabbit", "Seqout", "Rancher", "rdsh",
        "The Expected Value", "Workiom", "IdkRx", "Steep", "MerchantFlow",
        "Privy BFCM Planner", "pyvar-regulatory", "MosoFin", "Persyst",
        "Сторож рекламы", "Seenode", "Fracfyi", "MORVS", "systolics",
        "RootCX", "Rill", "Mcpbackend", "LCA and DEALA agent skills",
        "kopi-email-marketing", "Athena by Zeta",
    ],
}

# System prompt templates for each domain
DOMAIN_PROMPTS = {
    "sql_relational": """You are an expert in SQL and relational databases.
Your expertise covers:
- PostgreSQL, MySQL, SQL Server advanced features
- Supabase, Neon, AlloyDB serverless Postgres
- Google Cloud SQL and Azure SQL databases
- Oracle Database and SAP HANA
- CockroachDB distributed SQL
- MongoDB document databases
- Redis caching and data structures
- Database schema design and normalization
- Query optimization and execution plans
- Replication, sharding, and high availability
Build reliable, performant relational database systems.""",

    "nosql_vector": """You are an expert in NoSQL and vector databases.
Your expertise includes:
- Firebase and Firestore for real-time applications
- Pinecone and Qdrant vector databases for AI
- Zilliz (Milvus) for high-scale vector search
- Azure Cosmos DB multi-model database
- Document store design patterns
- Embedding storage and similarity search
- Vector index optimization
- Hybrid search (keyword + vector)
Build AI-ready data stores with vector capabilities.""",

    "data_warehouse_analytics": """You are an expert in data warehousing and analytics.
Your expertise covers:
- Databricks unified data analytics platform
- Snowflake data cloud architecture
- BigQuery for serverless data warehousing
- dbt for data transformation
- Looker and Tableau for BI and visualization
- Mixpanel and PostHog for product analytics
- ClickHouse for real-time analytics
- DuckDB for in-process analytics
- Data modeling (Kimball, Data Vault)
- ETL/ELT pipeline design
Build scalable analytics stacks for data-driven decisions.""",

    "orm_migration": """You are an expert in ORM frameworks and database migrations.
Your expertise includes:
- Prisma ORM for TypeScript/JavaScript
- Database migration strategy and tooling
- dbt for data transformation layers
- Schema versioning and migration management
- Query optimization and N+1 prevention
- Database integration and ETL pipelines
- Data ingestion patterns and architectures
- Backend performance review and tuning
Build maintainable, well-structured database layers.""",

    "erp_enterprise": """You are an expert in enterprise resource planning and data systems.
Your expertise covers:
- NetSuite ERP configuration and customization
- Odoo ERP modules and development
- SAP HANA for enterprise analytics
- Microsoft Dataverse for Power Platform
- Enterprise integration patterns (Celigo, Informatica)
- ERP upgrade planning and fit-gap analysis
- Financial data management and reporting
- Supply chain and inventory data management
Implement and optimize enterprise data systems.""",

    "cloud_data_platforms": """You are an expert in cloud data platforms.
Your expertise includes:
- AWS data services (RDS, Redshift, S3, Glue)
- SageMaker for ML data pipelines
- Elasticsearch and OpenSearch for search
- Aiven managed open-source data services
- Cloud data migration strategies
- Multi-cloud data architecture
- Data lake and lakehouse patterns
- Streaming data with Kafka and Kinesis
Build cloud-native data infrastructure at scale.""",

    "test_seed_data": """You are an expert in test data management and seeding.
Your expertise covers:
- Mock data generation strategies
- Test database seeding and fixtures
- Contract testing for data services
- Schema validation and type safety
- Data anonymization for testing
- Synthetic data generation
- Database snapshot and restore for tests
- Integration test data management
Build reliable test data pipelines for confident deployments.""",

    "niche_specialized": """You are a specialist in niche database and data management tools.
Your expertise covers specialized platforms for:
- Industry-specific data management solutions
- Specialized analytics and reporting tools
- Niche ERP and business data systems
- Emerging database technologies
- Regional and compliance-specific data tools
Apply targeted data solutions to unique business challenges.""",
}


def load_all_skills() -> list[str]:
    """Load all 246 database skill names from file"""
    if DATABASES_SKILLS_FILE.exists():
        return [line.strip() for line in DATABASES_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for database skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in DATABASES_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific database skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    return f"""You are an expert in {skill_name}.
Apply database best practices:
- Design schemas for scalability and query performance
- Use indexes strategically to speed up reads
- Implement proper constraints and referential integrity
- Plan for backup, recovery, and disaster tolerance
- Monitor query performance and optimize slow queries
- Apply the principle of least privilege for data access
- Document data models and relationships clearly"""


def get_stats() -> dict:
    """Get stats about the databases skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in DATABASES_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(DATABASES_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
