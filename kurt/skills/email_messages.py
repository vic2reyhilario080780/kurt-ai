"""
KURT Email & Messages Skills Catalog
Lahat ng 187 Email & Messages skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
EMAIL_MESSAGES_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_email_messages.txt"

# Domain-based groupings for smart routing
EMAIL_MESSAGES_DOMAINS = {
    "email_marketing": [
        "ActiveCampaign", "kopi-email-marketing", "Loops", "Newsletter Creator Tools",
        "KlickTipp", "Mailercloud", "Seguno", "Emailr", "Nitrosend", "InboxAlly Placement Test",
        "Email Spam Tester", "ClearBounce Email Verification", "WarmySender", "Warmerly",
        "Newsletter Review", "Privy BFCM Planner", "Markaestro", "Orbitwrite",
    ],
    "social_messaging": [
        "instagram", "telegram", "discord", "slack", "Slack", "xpost", "Ayrshare - Unified Social Media API for AI Agents",
        "Posty: Social Media Scheduler", "Postiz", "PostSyncer", "PostEverywhere", "PostFast",
        "PostZen", "Postify", "Post2All", "SocialRobot", "SocialClaw", "SendIt Social",
        "Dash Social", "iHatePosting", "Swoop - X.com listening", "BuzzBit X",
        "ViewsMax", "PostDashPro", "post bridge", "BriefGate",
    ],
    "crm_sales_outreach": [
        "HubSpot Sales", "AI Context Bridge for HubSpot", "Revenue Grid", "Revenue Analytics for HubSpot",
        "Sales Follow-Up", "Follow-Up Writer", "Cold Email, LinkedIn Outreach & Deliverability",
        "B2B Personal Branding", "Ripe Leads Cold Email Writer", "GIA Prospecting Engine",
        "GIA Chief of Staff", "SalesEQ", "PumpGTM", "KiteGTM", "Lead Magnets", "Referent",
    ],
    "messaging_platforms": [
        "imessage", "RingCentral", "DataFlows SMS", "Kudosity SMS", "paging-mcp",
        "mqtt", "claude-telegram-voice", "lark", "Lark/Feishu Integration", "signal-hunter",
        "telegram tools", "Unofficial Telegram MCP", "Chiho.ai Telegram CRM",
        "bluebubbles-gateway", "Trackly SMS", "wechat-audio-toolkit",
    ],
    "productivity_automation": [
        "AgentMail", "AssistantLabs — Personal Assistant for Business", "Email Triage",
        "SmartReply", "Quickchat AI", "Answering Agent", "Telepath", "circleback",
        "dailybot", "meetstream-ai-meeting-bot-api", "Meeting Memory by Grain",
        "Clearskies", "tlgr", "Multi Mail", "SuperMailOS", "pntr",
        "Sent", "Sendly", "Shipmail", "Liftory",
    ],
    "business_communication": [
        "Customer.io", "Landbot", "ChatDaddy", "DialogBrain", "Supovia helpdesk chat",
        "Featurebase", "Brilliant Directories", "SupaBird", "SamDesk Support",
        "DobroDesk Support", "Retenot", "Ultralayer", "Vobiz", "Topo",
        "Client Briefs", "Weekly Client Report", "Deposit Requester",
    ],
    "niche_specialized": [
        "Intuit QuickBooks", "Hostinger Connector", "Pendo Orchestrate",
        "Windsor.ai Ads and Marketing Data", "google-multi-account", "Hyper Marketing",
        "Content Studio", "Career Navigator", "ACA Native MCP Skills",
        "Job Hunt HQ", "Arcade", "Upload-Post", "Zernio", "Higgs Hub", "resend",
        "Sales Skills by Arrows", "Cargo", "DunSocial", "One", "Banger",
        "Anson", "me — write like me", "Airship Agent Tools", "BOLD Studios",
        "Remote.com", "Economico", "Civic", "Reader Radius", "PostSyncer",
        "Ultralayer", "Postproxy", "BridgeApp", "Hive", "Voice Messages",
        "Splashify Pro", "Bigmind", "Ownhand", "Tuteliq", "GetEmployed",
        "PostZen", "luma-mcp", "Loopsii", "Tinylawn", "mail-muncher",
        "Famulor Assistants & History", "Postel", "overloop", "SimplePost",
        "Notifly", "Benaiah", "Trupeo", "slio", "Pay Nudger", "Сторож рекламы",
        "PrefMark", "RiverScript", "Stalwart Mail", "Princi", "enrichley",
        "Slack Dad Joke", "Migma", "Ando", "Mailtea", "Dilaya", "Пост-завод",
        "CallRemind", "Cherami", "Rav Messer", "JuzPost", "SenderKit",
    ],
}

DOMAIN_PROMPTS = {
    "email_marketing": """You are an expert in email marketing and deliverability.
Your expertise covers:
- Email campaign creation and automation
- Newsletter design and content strategy
- Deliverability optimization and spam avoidance
- A/B testing for subject lines and content
- List segmentation and personalization
- Email verification and list hygiene
- Transactional email workflows
- Marketing automation sequences
Drive engagement and conversions through effective email marketing.""",

    "social_messaging": """You are an expert in social media messaging and scheduling.
Your expertise covers:
- Multi-platform social media posting (Instagram, Twitter/X, LinkedIn)
- Content scheduling and automation
- Social listening and brand monitoring
- Cross-platform content distribution
- Engagement optimization strategies
- Social analytics and performance tracking
- Community management workflows
- Platform-specific content formatting
Build consistent social media presence across all channels.""",

    "crm_sales_outreach": """You are an expert in CRM-driven sales outreach.
Your expertise covers:
- HubSpot and CRM integration
- Cold email and LinkedIn outreach sequences
- Sales follow-up automation
- Lead nurturing and scoring
- B2B prospecting and personalization
- Pipeline management and forecasting
- Revenue analytics and reporting
- GTM strategy and execution
Accelerate revenue growth through systematic sales outreach.""",

    "messaging_platforms": """You are an expert in messaging platform integrations.
Your expertise covers:
- Telegram, iMessage, Discord, Slack integrations
- SMS and MMS campaign management
- MQTT and IoT messaging protocols
- Multi-channel messaging orchestration
- Real-time notification systems
- Voice message processing
- WhatsApp Business API
- Cross-platform message routing
Build seamless communication across all messaging channels.""",

    "productivity_automation": """You are an expert in communication productivity and automation.
Your expertise covers:
- Email triage and intelligent sorting
- AI-powered reply generation
- Meeting notes and follow-up automation
- Smart reply suggestions
- Inbox zero workflows
- Communication analytics and insights
- Task extraction from emails
- Calendar and meeting integration
Eliminate communication overhead with intelligent automation.""",

    "business_communication": """You are an expert in business communication tools.
Your expertise covers:
- Customer support chat systems
- Helpdesk ticket management
- Client communication platforms
- Internal team messaging
- Customer feedback collection
- Support ticket routing and triage
- SLA management and reporting
- Knowledge base integration
Deliver exceptional customer and team communication experiences.""",

    "niche_specialized": """You are a specialist in niche email and messaging tools.
Your expertise covers specialized solutions for:
- Industry-specific communication platforms
- Regional and language-specific messaging tools
- Emerging communication technologies
- Niche audience engagement tools
- Experimental messaging workflows
Apply targeted expertise to unique communication challenges.""",
}


def load_all_skills() -> list[str]:
    """Load all 187 email & messages skill names from file"""
    if EMAIL_MESSAGES_SKILLS_FILE.exists():
        return [line.strip() for line in EMAIL_MESSAGES_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for email & messages skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in EMAIL_MESSAGES_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific email & messages skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    return f"""You are an expert in {skill_name}.
Apply email and messaging best practices:
- Write clear, compelling subject lines and CTAs
- Personalize messages for maximum relevance
- Optimize send timing and frequency
- Maintain healthy sender reputation
- Segment audiences for targeted messaging
- Track open rates, clicks, and conversions
- A/B test continuously for improvement
- Comply with email regulations (CAN-SPAM, GDPR)"""


def get_stats() -> dict:
    """Get stats about the email & messages skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in EMAIL_MESSAGES_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(EMAIL_MESSAGES_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
