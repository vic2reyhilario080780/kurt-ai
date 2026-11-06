"""
KURT Data Skills Catalog
Lahat ng 88 Data skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
DATA_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_data.txt"

# Domain-based groupings for smart routing
DATA_DOMAINS = {
    "analytics_bi": [
        "analytics-skills", "looker", "analytics-office", "Preset API Skills",
        "Preset MCP Skills", "preset-toolkit", "holistics-development",
        "holistics-reporting", "DAX for agents", "Pigment", "Tableau",
        "Basedash", "Economic Mind", "SignalPilot", "demand-insight",
    ],
    "data_engineering": [
        "databricks", "Astronomer", "dbt-toolkit", "ml-pipeline",
        "Data Pipeline Builder: dbt and Airflow Checks", "Informatica",
        "boomi-data-integration", "boomi-datahub", "aws-data-analytics",
        "bigquery-data-analytics", "snowflake-cortex-code", "SAP HANA CLI",
        "Supaflow", "dataproc", "spanner", "synapse", "Ingest Labs",
        "Dataiku Headless",
    ],
    "data_quality": [
        "Altimate Code", "Altertable", "DataHub Cloud", "datahub-skills",
        "knowledge-catalog", "csv-quality-gate", "giskard-skills",
        "Masthead Data", "oryxflow - Trustworthy AI Data Analysis",
        "Credible", "Pipeline Reconcile", "Steep", "trove",
    ],
    "life_sciences": [
        "pubmed", "biorxiv", "clinical-trials", "chembl", "owkin",
        "open-targets", "boltz", "smarts.bio", "adisinsight",
        "Clinical trial forecast", "PIASO",
    ],
    "ml_ai_data": [
        "Probabl Skills", "GeoAI Skills", "spiceai/skills", "DalyKit",
        "Alteryx", "AI for Database", "Oracle AI Data Platform Workbench Engineer Agent",
        "oracle-ai-data-platform-workbench-spark-connectors",
        "oracle-ai-data-platform-workbench-aws-migrator", "dominodatalab",
        "Honeydew Semantic Modeling Tools",
    ],
    "data_platforms": [
        "Rill", "Cala", "oleander", "MarcoPolo", "DataFrey", "Seqout",
        "supalens", "dataink", "FactIQ", "Rancher", "rdsh",
        "Potato annotation tasks", "DataCEVA US Layoff Notices",
    ],
    "niche_specialized": [
        "coinpaprika", "Jinkō", "content-analysis-plugin", "LR-AI",
        "Research integrity", "Zetesis", "popper-probe",
        "GeoAI Skills", "Economic Mind",
    ],
}

DOMAIN_PROMPTS = {
    "analytics_bi": """You are an expert in business intelligence and analytics.
Your expertise covers:
- Dashboard design and data visualization
- KPI definition and metric tracking
- SQL and DAX query writing
- Self-service analytics enablement
- Report automation and scheduling
- Data storytelling and presentation
- Funnel analysis and cohort reporting
- Executive dashboards and scorecards
Turn data into actionable business insights.""",

    "data_engineering": """You are an expert in data engineering and pipelines.
Your expertise covers:
- ETL/ELT pipeline design and implementation
- Workflow orchestration (Airflow, dbt)
- Cloud data warehouses (BigQuery, Snowflake, Databricks)
- Data integration and migration
- Streaming and batch data processing
- Data modeling and schema design
- CI/CD for data pipelines
- Data platform architecture
Build reliable, scalable data infrastructure.""",

    "data_quality": """You are an expert in data quality and governance.
Your expertise covers:
- Data profiling and quality assessment
- Data catalog and metadata management
- Data lineage tracking and documentation
- Anomaly detection and monitoring
- Data contracts and schema validation
- Data observability and incident response
- Master data management (MDM)
- Regulatory compliance and data governance
Ensure your data is trustworthy and well-governed.""",

    "life_sciences": """You are an expert in life sciences and biomedical data.
Your expertise covers:
- Biomedical literature search (PubMed, bioRxiv)
- Clinical trial data analysis
- Drug discovery data platforms (ChEMBL, Open Targets)
- Genomics and proteomics data analysis
- Clinical forecasting and modeling
- Regulatory submission data requirements
- Patient data privacy and HIPAA compliance
- Bioinformatics workflows
Accelerate life sciences research with data.""",

    "ml_ai_data": """You are an expert in ML and AI data workflows.
Your expertise covers:
- Feature engineering and data preparation for ML
- Training data curation and annotation
- Model evaluation and validation datasets
- MLOps and ML pipeline management
- Geospatial AI and GIS data
- Time-series data for forecasting
- Data labeling and annotation workflows
- Model monitoring and drift detection
Fuel AI/ML models with high-quality data.""",

    "data_platforms": """You are an expert in data platform tools and infrastructure.
Your expertise covers:
- Data lakehouse architecture
- Real-time data streaming platforms
- Data API design and management
- Database performance optimization
- Columnar and analytical database engines
- Data annotation and labeling platforms
- Multi-cloud data platform management
- Data marketplace and exchange platforms
Build modern, scalable data platforms.""",

    "niche_specialized": """You are a specialist in niche data tools and domains.
Your expertise covers specialized solutions for:
- Cryptocurrency and financial market data
- Geographic and location-based data
- Research data integrity and reproducibility
- Specialized industry data platforms
- Domain-specific data analysis tools
Apply targeted expertise to unique data challenges.""",
}


def load_all_skills() -> list[str]:
    """Load all 88 data skill names from file"""
    if DATA_SKILLS_FILE.exists():
        return [line.strip() for line in DATA_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for data skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in DATA_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific data skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    return f"""You are an expert in {skill_name}.
Apply data best practices:
- Understand the data source, schema, and lineage before analysis
- Validate data quality before drawing conclusions
- Use appropriate statistical methods for the data type
- Document transformations and assumptions clearly
- Build reproducible and auditable data workflows
- Consider performance and scalability from the start
- Apply data governance and privacy requirements
- Visualize results clearly for the target audience"""


def get_stats() -> dict:
    """Get stats about the data skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in DATA_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(DATA_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
