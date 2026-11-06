"""
KURT Marketing Skills Catalog
Lahat ng 221 Marketing skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
MARKETING_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_marketing.txt"

# Domain-based groupings for smart routing
MARKETING_DOMAINS = {
    "seo_search": [
        "Claude SEO and GEO Site Audit", "SEO-AEO-GEO Ultimate", "SEO Audit",
        "SEO GSC Wizard", "SearchFit SEO", "SE Ranking", "HarborRank SEO",
        "AI Search Visibility (AEO/GEO)", "AI Search Visibility Tracker",
        "rampstack-seo", "aeo", "AEO Brand Scan", "AEOTester: AI SEO Audit and Fix",
        "Website Check-up by SEO Records", "Ubersuggest", "SEOcrawl AI Reports",
        "Maquinable GEO", "Botify", "SearchAtlas Toolkit", "Programmatic SEO Gate",
        "mcp-gsc", "search-visibility-kit", "RankControl", "Searcherries",
        "Rankability", "Serpzilla SEO Guest Posting and Link Insertions",
        "BacklinksWinkel", "JSON SEO", "Keytomic", "apptweak-api",
        "ASO Specialist", "Sonar ASO", "ASO Keyword Sorter", "AppSkyline",
        "SmartLinks App Growth", "ThemeSniffer - WordPress Theme and Plugin Detector",
        "website-quality-checker", "AskAiRank",
    ],
    "paid_ads": [
        "AdWhispr Ads & Marketing Agent", "AdCopilot for Google Ads, Google Analytics, Google Search Console & Google Tag Manager",
        "Adspirer Advertising Agent", "AdvisorPPC - Google Ads, Analytics, Tag Manager, Search Console and YouTube Connector",
        "Windsor.ai Ads and Marketing Data", "Supermetrics Ads & Marketing Analytics",
        "HYPD AI - Paid Ads & Analytics", "PaidSync", "AdMakeAI",
        "Ad Copy & Creative Preflight", "AdsAgent", "adplane", "adlane",
        "Adzviser", "Admaxxer", "MARFOR Marketing Mix Modeling",
        "Trackian Marketing Analytics", "Spytrend MCP Skills",
        "Clicktrail", "Attri", "Datafluxor", "Privy BFCM Planner",
    ],
    "social_media": [
        "Social Media Skills", "Ayrshare - Unified Social Media API for AI Agents",
        "Socialinsider", "Socialstats", "Social Post Flow", "PostSyncer",
        "Planable SMM", "PostEverywhere", "PostDaily", "PostZen", "Postraid",
        "Postproxy", "Postify", "SocialRobot", "SocialFaktory", "Dash Social",
        "Maeve Social", "Aria", "BAMF.ai", "vidIQ", "InsightPins for Pinterest",
        "Airship Agent Tools", "Customer.io", "Recharm", "BuzzBit X",
        "Spyglasses", "eonik", "Machine Relations Index", "Songstats",
    ],
    "content_seo": [
        "Website Copywriting & Positioning", "Product Marketing",
        "Marketing Psychology Kit", "Marketing Ideas & Growth Experiments",
        "Adology — Content Intelligence", "Editorial OS", "Content Studio",
        "Blog Content", "Blogr", "PolyBlog Blog Builder", "Fully SEO optimized Article with FAQ's",
        "Writing With Agents", "claude-blog-assistant", "B2B Personal Branding",
        "Positioning and GTM Strategy", "Manifold", "Marcora: Brand Context & Writing",
        "brand-md", "DeSlop", "Zero Slop Hosted", "RoboWrite", "Fountain",
        "citable", "Genfeed", "Templafy", "Morphed",
    ],
    "email_marketing": [
        "ActiveCampaign", "kopi-email-marketing", "Newsletter Creator Tools",
        "Loops", "KlickTipp", "DataFlows SMS", "ClearBounce Email Verification",
        "Email Spam Tester", "Newsletter Review", "Emailr", "Kudosity SMS",
        "Mailercloud", "Scribe Mail", "Nitrosend", "InboxAlly Placement Test",
        "Seguno", "Sendly", "Shipstar", "Sent", "Lindo AI",
    ],
    "growth_analytics": [
        "Pendo Orchestrate", "Ryze AI Marketing Skills", "AI-Advisors",
        "Accelerate AI Toolkit", "Hyper Marketing", "Community & Reddit Marketing",
        "voice-of-customer", "cialdini-influence-audit", "Fractional CMO Brain",
        "Kampalo", "TrendsAGI", "Tareno", "Oktio.app", "querymantic",
        "Intuizi", "Realize Plugin", "Liftaven", "PodPitch", "Linkly",
        "Hopkin", "Mora",
    ],
    "creative_assets": [
        "Abracadabrax AI Product Photo Generator", "Creative Claw",
        "AI UGC Video Ads Maker", "Krea", "OpenClips", "Arcads AI",
        "app-preview-craft", "Facade Ui", "Splashify Pro", "CodeQR",
        "Atria", "Banger", "Marky", "Lead Magnets",
        "StarTap Launch Kit", "DemoDay", "Merch", "Pixelesq",
    ],
    "niche_specialized": [
        "Agency MCP", "seal-copilot", "pptx-deck-plugin", "8digit Planner",
        "SEO Writers", "Big If True", "Zernio", "ViralHunt",
        "claude-train-prep", "UnifAPI", "career-brand", "Claistore",
        "Waldo fyi", "Reader Radius", "JSON Schema App MCP",
        "Brandvane", "shopee-review", "Klaket", "Demovela",
        "Magpie", "Pollen", "Orcool", "Synter", "Storeadops",
        "Unfetch", "Rav Messer", "Аграновский", "daitsch", "Servanta",
        "Flowsery", "Markaestro", "Matematic Reviewer", "Mattemena Nerve",
        "Сторож рекламы", "Ship Post", "viral-launch-pipeline",
        "ClientGen Reach", "Unbounce Landing Page Builder", "PostSyncer",
        "Programmatic SEO Gate", "BAMF.ai", "Waldo fyi",
    ],
}

# System prompt templates for each domain
DOMAIN_PROMPTS = {
    "seo_search": """You are an expert in SEO and search visibility.
Your expertise covers:
- Technical SEO audits and site optimization
- On-page and off-page SEO strategies
- AEO (Answer Engine Optimization) and GEO (Generative Engine Optimization)
- Keyword research and cluster planning
- Google Search Console analysis
- App Store Optimization (ASO)
- Link building and authority development
- Core Web Vitals and performance optimization
- Local SEO and structured data
- AI search visibility and citation optimization
Drive organic growth with data-driven search strategies.""",

    "paid_ads": """You are an expert in paid advertising and performance marketing.
Your expertise covers:
- Google Ads (Search, Display, YouTube, Shopping)
- Meta Ads (Facebook, Instagram) campaign management
- Multi-channel attribution modeling
- Ad creative testing and optimization
- Marketing mix modeling (MMM)
- Return on ad spend (ROAS) optimization
- Audience segmentation and targeting
- Conversion tracking and analytics
- Budget allocation and bidding strategies
- Competitive ad intelligence
Maximize ROI through data-driven paid media strategies.""",

    "social_media": """You are an expert in social media marketing.
Your expertise covers:
- Multi-platform social media strategy
- Content scheduling and automation
- Social media analytics and reporting
- Community building and engagement
- Influencer marketing and UGC
- Short-form video content (TikTok, Reels)
- Pinterest and visual platform marketing
- LinkedIn B2B social strategy
- Social listening and brand monitoring
- Viral content creation frameworks
Build engaged communities and amplify brand presence.""",

    "content_seo": """You are an expert in content marketing and brand positioning.
Your expertise covers:
- Content strategy and editorial planning
- SEO-optimized blog and article writing
- Brand voice and messaging frameworks
- Product marketing and go-to-market strategy
- Copywriting for conversions
- Content briefs and topical authority
- Thought leadership and B2B content
- AI-assisted content creation
- Content repurposing and syndication
- Competitive positioning and differentiation
Drive growth with compelling content that ranks and converts.""",

    "email_marketing": """You are an expert in email marketing and CRM.
Your expertise covers:
- Email campaign strategy and automation
- Newsletter creation and optimization
- Email deliverability and inbox placement
- Segmentation and personalization
- SMS marketing and mobile messaging
- List hygiene and email verification
- A/B testing for subject lines and content
- Lifecycle email campaigns
- Transactional email optimization
- Email analytics and attribution
Build customer relationships through targeted email programs.""",

    "growth_analytics": """You are an expert in growth marketing and analytics.
Your expertise covers:
- Product-led growth strategies
- Customer acquisition funnel optimization
- Growth experiment design and analysis
- Voice of customer research
- Conversion rate optimization (CRO)
- Marketing psychology and persuasion
- Community-led growth tactics
- Referral and viral loop mechanics
- Marketing analytics and attribution
- Fractional CMO-level strategic guidance
Drive sustainable growth through experimentation and data.""",

    "creative_assets": """You are an expert in marketing creative and visual assets.
Your expertise covers:
- AI-generated product photography
- Video ad creation and UGC
- Social media graphics and templates
- Landing page design optimization
- QR code and digital asset creation
- Brand asset management
- Ad creative testing frameworks
- Motion graphics and animations
- Launch kit and campaign materials
- Visual content for e-commerce
Create compelling visual content that drives engagement.""",

    "niche_specialized": """You are a specialist in niche marketing tools and platforms.
Your expertise covers specialized solutions for:
- Agency and client management workflows
- Niche platform-specific marketing
- Regional and international marketing tools
- Emerging marketing technologies
- Industry-specific campaign management
Apply targeted marketing expertise to unique business challenges.""",
}


def load_all_skills() -> list[str]:
    """Load all 221 marketing skill names from file"""
    if MARKETING_SKILLS_FILE.exists():
        return [line.strip() for line in MARKETING_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for marketing skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in MARKETING_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific marketing skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    return f"""You are an expert in {skill_name}.
Apply marketing best practices:
- Focus on measurable outcomes and ROI
- Use data to inform creative and strategic decisions
- Build campaigns that resonate with target audiences
- Test, iterate, and optimize continuously
- Align marketing efforts with business objectives
- Track attribution across the full customer journey
- Create compelling narratives that drive action"""


def get_stats() -> dict:
    """Get stats about the marketing skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in MARKETING_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(MARKETING_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
