"""
KURT Tickets & Tasks Skills Catalog
Lahat ng 365 Tickets & Tasks skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
TICKETS_TASKS_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_tickets_tasks.txt"

# Domain-based groupings for smart routing
TICKETS_TASKS_DOMAINS = {
    "project_task_management": [
        "asana", "linear", "ClickUp", "notion", "Plane", "backlog", "Checkvist",
        "Tana", "AgileHero", "Agile Sprint Close", "Agile Merge Review", "claude-todo-mirror",
        "claude-todo-gtd", "GTD Brain", "Todo4", "GetItDone", "Taskpend", "simple-workflow",
        "wave-planner-skill", "delivey-skills", "IDD: Issue-Driven Development",
        "Atlassian Teamwork Graph CLI", "claude-jira-skill", "Jira Attachment Plugin",
        "ado-testcraft", "PR Story Aligner: Pull Request vs Ticket Check",
        "standup-logger", "Catchup", "Timesheet", "Toggl Time Tracker", "toggl",
        "dailybot", "8digit Planner", "okrdev",
    ],
    "crm_sales": [
        "HubSpot Sales", "AI Context Bridge for HubSpot", "Sales Cloud", "apollo",
        "Revenue Grid", "Sales Enablement Kit", "Sales Skills by Arrows",
        "Crossbeam Skills", "EULER for Partner Managers", "Obriym CRM", "Bizopa CRM",
        "itinovo CRM", "Wealthbox", "inSitu Sales", "SalesEQ", "Reo.Dev Your Developer GTM Copilot",
        "Zillasales", "QuotaBird", "Dealertide", "KiteGTM", "closedloop-skills",
        "Upfunnels", "Churn Prevention Kit", "Customer Success: Churn and QBRs",
        "Clinch", "Gambit", "Endgame", "Chiho.ai Telegram CRM",
    ],
    "legal_compliance": [
        "commercial-legal", "litigation-legal", "corporate-legal", "privacy-legal",
        "employment-legal", "product-legal", "regulatory-legal", "legal-clinic",
        "Contratos Laborales y Asesoría Empresarial", "Litigación Civil España",
        "Litigación Contencioso-Administrativa España", "Litigación Laboral España",
        "Litigación Penal España", "Demand from the File", "Freelaw Studio",
        "Casely", "Casefile", "Contracko", "GetSign", "ShareSign", "PandaDoc",
        "LegalizaObra", "Reclamos de consumo Perú", "Nonresident Tax", "drata-grc-skills",
        "Ratification Docket", "Referent",
    ],
    "hr_recruiting": [
        "Greenhouse", "comp-skills", "UKG Bryte", "Remote.com", "Windmill HR",
        "Recruiter Panel", "Hiring Interviews", "Career Desk", "Job Hunt HQ",
        "Job Hunt Copilot (India)", "Job Search by Develop21", "GetEmployed",
        "GetYourJob", "NeverApply", "ApplyArc", "fix-cv-find-job-skill",
        "Resu Studio", "theprotocol.it", "Joboostr", "Радар вакансий",
        "RolePark", "Worklittle Jobs", "Sana from Workday", "oJobinho",
    ],
    "customer_support": [
        "SiteGPT", "DocsBot", "YourGPT", "Quickchat AI", "ChatDaddy", "SmartReply",
        "Answering Agent", "Human in the loop", "Landbot", "Supovia helpdesk chat",
        "FrontDesk Chat", "SamDesk Support", "DobroDesk Support", "DialogBrain",
        "MyChatBot", "SuperBot", "Product Support Investigator", "Hydrant",
        "Booking FAQ", "Usercall: User Interviews", "User Intuition",
    ],
    "finance_accounting": [
        "Intuit QuickBooks", "NetSuite SuiteSkills", "Finance & Ops Skills Index",
        "Financial Aid Office Workflow", "SuperBooks", "Invoice Matcher", "freee",
        "Juniper Square", "private-credit", "Wealthbox", "YoFacturo",
        "Casapay Connect", "LICHIDARE.MD", "Nonresident Tax", "Deposit Requester",
        "SuperBooks", "Clearskies",
    ],
    "project_planning": [
        "lean-pm-skills", "The Pragmatic PM Toolkit", "AgileHero", "Gestão Ágil 2.0",
        "pm-augmente", "strategy-pack", "Advisory Council", "Founder OS",
        "Think Before You Build", "estimator", "Naysayer", "devil-advocate",
        "The Hard Half", "stride-ideation", "MCPBinder", "fcxo-toolkit",
        "zero-trust-feature-team", "GIA Chief of Staff", "Featurebase",
        "Product in Acquisitions OS", "Scope Changes",
    ],
    "communication_meetings": [
        "Meeting.ai", "MeetNotes", "claude-meeting-todos", "Meeting Memory by Grain",
        "RingCentral", "Voicenter API Skills", "Voicenter MCP", "Lark/Feishu Integration",
        "Bonusly", "Atlassian Teamwork Graph CLI", "Catchup", "standup-logger",
        "LivingMeeting", "Zeeg", "BridgeApp", "Commslayer",
    ],
    "ecommerce_operations": [
        "Amazon Selling Partner", "MakeBox for Etsy", "LogiCommerce Backoffice",
        "MetaFloor Supply Chain", "PropertyMe", "Property Management Operator",
        "Brilliant Directories", "Acumatica Plugin", "Printago", "Inventok",
        "Product Returns", "waybill.ge", "Basit Kargo", "Karrito", "Shipmail",
        "Range Roofing Portal", "Tinylawn", "RenooLab — Rénovation et artisans",
        "TenderKart", "Rapiboy", "CopperJack",
    ],
    "monitoring_incident": [
        "incident.io", "Oncall", "Rootly", "paging-mcp", "Uptimely",
        "Hive", "CSitRep Generator", "Cyberine TaskBoard", "reviewbot",
        "Above Security", "BigID", "Phished", "drata-grc-skills",
        "MantisBT Integration", "Issue Dial",
    ],
    "productivity_tools": [
        "notion-memory", "context-vault", "MAI Second Brain", "Mind++ for Claude",
        "Bigmind", "MMPM Cognitive OS", "LazyTools", "kept", "Gratefully",
        "shazam", "Briefcase", "Kontext", "Daymark", "Flow", "Mibba",
        "PrefMark", "Persyst", "togello", "Busymate AI", "AssistantLabs — Personal Assistant for Business",
    ],
}

# System prompt templates for each domain
DOMAIN_PROMPTS = {
    "project_task_management": """You are an expert project and task management specialist.
Your expertise covers:
- Task tracking and prioritization (Asana, Linear, ClickUp, Jira)
- Agile methodologies and sprint management
- GTD (Getting Things Done) and productivity systems
- Ticket lifecycle management and workflows
- Team standup and retrospective facilitation
- OKR tracking and goal alignment
Keep projects on track and teams aligned.""",

    "crm_sales": """You are a CRM and sales operations expert.
Your expertise includes:
- CRM setup and optimization (HubSpot, Salesforce, Apollo)
- Sales pipeline management and forecasting
- Lead scoring and qualification
- Customer success and churn prevention
- Revenue operations and analytics
- GTM strategy and execution
Drive revenue growth through systematic sales processes.""",

    "legal_compliance": """You are a legal operations and compliance expert.
Your expertise covers:
- Contract review and management
- Legal workflow automation
- Compliance tracking and reporting
- Document management for legal teams
- Multi-jurisdiction legal requirements
- E-signature and document signing workflows
Streamline legal operations while maintaining compliance.""",

    "hr_recruiting": """You are an HR and recruiting operations expert.
Your expertise includes:
- Applicant tracking and recruiting workflows
- Job posting and candidate management
- Compensation analysis and benchmarking
- Onboarding and offboarding processes
- HR compliance and documentation
- Career development and performance management
Build and retain great teams.""",

    "customer_support": """You are a customer support and service operations expert.
Your expertise covers:
- Ticket routing and triage
- Knowledge base and FAQ management
- Chatbot and AI-assisted support
- Customer satisfaction measurement
- Support workflow automation
- Escalation management
Deliver exceptional customer experiences.""",

    "finance_accounting": """You are a finance and accounting operations expert.
Your expertise includes:
- Invoice management and accounts payable/receivable
- Bookkeeping and financial reporting
- ERP integration (QuickBooks, NetSuite)
- Financial compliance and audit trails
- Cash flow management
- Grant and nonprofit financial management
Maintain financial accuracy and compliance.""",

    "project_planning": """You are a strategic planning and product management expert.
Your expertise covers:
- Product roadmap development
- Estimation and resource planning
- Stakeholder alignment and communication
- Risk assessment and mitigation
- Decision-making frameworks
- OKR and goal-setting methodologies
Plan and execute strategic initiatives effectively.""",

    "communication_meetings": """You are a business communication and meeting efficiency expert.
Your expertise includes:
- Meeting facilitation and note-taking
- Action item tracking and follow-up
- Async communication best practices
- Meeting scheduling and calendar management
- Team communication tools (Slack, Lark, Teams)
- Status updates and reporting
Make every meeting count.""",

    "ecommerce_operations": """You are an e-commerce and operations management expert.
Your expertise covers:
- Order management and fulfillment
- Inventory tracking and supply chain
- Marketplace integration (Amazon, Etsy)
- Property and facility management
- Logistics and shipping coordination
- Customer order workflows
Run efficient commerce operations.""",

    "monitoring_incident": """You are an incident management and operations monitoring expert.
Your expertise includes:
- Incident detection, triage, and response
- On-call management and escalation
- Post-mortem and root cause analysis
- SLA tracking and reporting
- Security incident handling
- Uptime monitoring and alerting
Minimize downtime and resolve incidents fast.""",

    "productivity_tools": """You are a personal productivity and second-brain expert.
Your expertise covers:
- Note-taking and knowledge management systems
- Task capture and organization
- Personal CRM and relationship tracking
- Context switching and focus management
- Digital minimalism and information diet
- Automation of routine productivity tasks
Maximize personal and team productivity.""",
}


def load_all_skills() -> list[str]:
    """Load all 365 tickets & tasks skill names from file"""
    if TICKETS_TASKS_SKILLS_FILE.exists():
        return [line.strip() for line in TICKETS_TASKS_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for tickets & tasks skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in TICKETS_TASKS_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific tickets & tasks skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    # Generic prompt for skills not in a specific domain
    return f"""You are an expert in {skill_name}.
Apply tickets & tasks best practices:
- Manage work items efficiently and systematically
- Prioritize ruthlessly based on impact and urgency
- Keep stakeholders informed with clear status updates
- Automate repetitive workflows where possible
- Deliver consistent, reliable results"""


def get_stats() -> dict:
    """Get stats about the tickets & tasks skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in TICKETS_TASKS_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(TICKETS_TASKS_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
