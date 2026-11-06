"""
KURT Websites Skills Catalog
Lahat ng 285 Websites skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
WEBSITES_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_websites.txt"

# Domain-based groupings for smart routing
WEBSITES_DOMAINS = {
    "seo_tools": [
        "Claude SEO and GEO Site Audit", "SEO-AEO-GEO Ultimate", "SEO Audit",
        "AEO Brand Scan", "AEOTester: AI SEO Audit and Fix", "SEO Writers",
        "SearchFit SEO", "seo-geo-consultant", "AI Search Visibility & Brand Mentions (GEO/AEO)",
        "AI Search Visibility (AEO/GEO)", "rampstack-seo", "SE Ranking",
        "AI Search Visibility Tracker", "aeo", "HarborRank SEO",
        "SEO GSC Wizard", "Fully SEO optimized Article with FAQ's", "seo-check",
        "LovableSEO", "SerpApi Claude Plugin", "SearchAtlas Toolkit",
        "Website Check-up by SEO Records", "Ubersuggest", "Programmatic SEO Gate",
        "SEOcrawl AI Reports", "Maquinable GEO", "Serpzilla SEO Guest Posting and Link Insertions",
        "search-visibility-kit", "RankControl", "Rankability", "BacklinksWinkel",
        "Spytrend MCP Skills", "mcp-gsc", "authorityprompt-installer",
        "Botify", "JSON SEO", "Searcherries",
    ],
    "website_builders": [
        "8B AI Website Builder", "Hostinger Connector", "Superdesign",
        "AnimatedWebs", "Website Design", "Lindo AI", "VibeMeASite",
        "Ullbek — AI website builder", "Replo", "Unbounce Landing Page Builder",
        "Brendly", "Duda", "Brilliant Directories", "AppSkyline",
        "Shopify App Builder", "Shopify DevKit", "Awesome Ecom Skills",
        "storefront-theme-kit", "wake-storefront", "Magento 2 / Mage-OS Skills",
        "StoreConnect Agent Skills", "LogiCommerce Backoffice", "rampstack-starter",
        "wordpress-mcp", "JoomPulse", "d0ma1n", "Kleap", "Rolino",
        "Zephyr Cloud", "Pluno WebMCP for Anything", "Simple Host",
        "Newlogic Online", "Pixelesq", "Shipvela",
    ],
    "testing_qa": [
        "playwright", "BugBug", "Checkly", "E2E Test Generator: Playwright and Cypress Tests",
        "QA My App", "Waldo fyi", "Meticulous", "Testers.ai CARBON Test Harness",
        "Agentic Beta Testers", "qa-quest", "TesterArmy", "website-quality-checker",
        "Responsive Check: Mobile Layout Tester", "Perf Profiler: Lighthouse and Core Web Vitals",
        "Web Vitals Auditor", "CRO Audit and Test Kit", "hormozi-offer-audit",
        "ux-ui-audit", "Axe Accessibility", "Stark", "eaa-audit",
        "CheckSite", "ScanMalware",
    ],
    "analytics_tracking": [
        "Leadfeeder", "Windsor.ai Ads and Marketing Data", "HYPD AI - Paid Ads & Analytics",
        "Supermetrics Ads & Marketing Analytics", "Trackian Marketing Analytics",
        "Fullstory", "logrocket", "Clicktrail", "Socialstats",
        "AppFollow AI Toolkit", "Sonar ASO", "ViewsMax", "vidIQ",
        "Adology — Content Intelligence", "Market Intelligence", "Manifold",
        "Spyglasses", "Datafluxor", "Attri",
    ],
    "ecommerce": [
        "Shopify DevKit", "Shopify App Builder", "Awesome Ecom Skills",
        "storefront-theme-kit", "wake-storefront", "Magento 2 / Mage-OS Skills",
        "StoreConnect Agent Skills", "LogiCommerce Backoffice", "Replo",
        "shopee-review", "Riskified Beacon Integration", "Review Replier",
        "WEM Price Compare", "Applixir",
    ],
    "content_marketing": [
        "Website Copywriting & Positioning", "Blogr", "Blogizi",
        "PolyBlog Blog Builder", "Marky", "Copycat", "Planable SMM",
        "SocialRobot", "Socialstats", "BAMF.ai", "viral-launch-pipeline",
        "ViralHunt", "x-content-intelligence", "Adology — Content Intelligence",
        "Genviral", "Virlo", "SuperCool Sites & Decks",
        "StarTap Launch Kit", "Hyper Marketing",
    ],
    "ads_paid_media": [
        "AdvisorPPC - Google Ads Analytics Tag Manager Search Console and YouTube Connector",
        "Adspirer Advertising Agent", "Windsor.ai Ads and Marketing Data",
        "HYPD AI - Paid Ads & Analytics", "Supermetrics Ads & Marketing Analytics",
        "Adzviser", "Admaxxer", "Agency MCP", "Accelerate AI Toolkit",
    ],
    "web_scraping_data": [
        "Apify", "firecrawl", "Bright Data", "diffbot", "Zyte Web Data",
        "HasData", "LurkAPI", "Search1API", "Olostep", "scout",
        "clawpage", "Internet Tools", "HTML/CSS to Image API", "ScreenshotOne",
        "youdotcom-agent-skills", "UnifAPI", "Unfetch",
    ],
    "infrastructure_hosting": [
        "Cloudflare", "Netlify", "Fastly", "arvancloud-api",
        "Simple Host", "Seenode", "Zephyr Cloud",
        "liquid-dev", "liquid-skills", "Postproxy",
        "amazon-location-service", "Porkbun", "DomainKits",
        "RedirHub", "Tabfleet Browser",
    ],
    "chatbot_support": [
        "SiteGPT", "DocsBot", "Quickchat AI", "Landbot",
        "SiteSpeak Chatbot Manager", "Asyntai – AI Support Agent for Websites",
        "FrontDesk Chat", "VibeCS support chat", "DialogBrain",
        "Answe", "ChatBot",
    ],
    "design_ux": [
        "Superdesign", "Mobbin", "Design Steward", "UXKIN",
        "inhabited design", "jp-web-design-guardrails", "Intuitive Software Design",
        "BOLD Studios", "Artist Portfolio", "Portfolio Interview",
        "A1 Gallery", "Image Deep Research", "Critic Layer",
        "ThemeSniffer - WordPress Theme and Plugin Detector", "Flowsery",
    ],
    "portfolio_showcase": [
        "Artist Portfolio", "Portfolio Interview", "A1 Gallery",
        "SuperCool Sites & Decks", "StarTap Launch Kit", "Brilliant Directories",
        "Markaestro", "black-label-presence", "Liftaven",
    ],
    "niche_specialized": [
        "Noibu", "seal-copilot", "TubeAlfred YouTube", "parallel",
        "Arcmira: YouTube Transcript Search", "Swoop - X.com listening",
        "claude-mac-chrome", "flowy", "Talk to Anyone", "Snagly",
        "Uniform", "Flint", "Context.dev", "Cargo", "AI-Advisors",
        "AskAiRank", "Wiser", "Big If True", "citable",
        "Actuent", "Hive", "MAI Second Brain", "hubcap",
        "Liquid LSP", "Cast", "BioFlow", "Magpie",
        "Kolosys Devkit", "Sitelemetry", "Pollen", "Liner",
        "drewcrawford-skills", "Octen", "Stunt Double", "Mailtea",
        "socialync", "Upfunnels", "SocialFaktory", "Dropthehassle",
        "ship", "SmartLinks App Growth", "Share Artifacts",
        "WeInc", "Mora", "JuzPost", "Keenable", "Tako",
        "Keytomic", "toolrouter", "Falatu.ai", "Applyra",
        "Difficat", "Dopia", "Machine Relations Index",
        "Аграновский", "Relvato", "Just.", "Subtext",
        "Loomaly", "stacktree", "Mountaineering", "Gyoza Recipes",
        "mida-so", "Showly", "SDP Platform", "Botscope",
        "Vruum", "spun.ink", "country-flag-picker",
        "OPEN - what is open right now", "Shipstar",
        "Zyte Web Data", "JSON Schema App MCP", "Docket Tracker",
        "colosseum", "VariFlight", "lux", "powmcp",
        "Kluwer", "Colosseum",
    ],
}

# System prompt templates for each domain
DOMAIN_PROMPTS = {
    "seo_tools": """You are an expert in SEO, AEO (Answer Engine Optimization), and GEO (Generative Engine Optimization).
Your expertise covers:
- Technical SEO auditing and on-page optimization
- Keyword research, clustering, and content strategy
- AI search visibility and brand mention tracking
- Google Search Console analysis and optimization
- Link building, guest posting, and backlink strategy
- Local SEO and international SEO
- Schema markup and structured data
Drive organic growth through comprehensive search optimization.""",

    "website_builders": """You are an expert in website and web application development platforms.
Your expertise includes:
- No-code and low-code website builders
- E-commerce platform development (Shopify, Magento, WooCommerce)
- CMS platforms (WordPress, Joomla) and headless CMS
- Landing page builders and conversion optimization
- Domain registration and DNS management
- Web hosting configuration and deployment
Build websites that convert and scale.""",

    "testing_qa": """You are an expert in web application testing and quality assurance.
Your expertise covers:
- End-to-end test automation (Playwright, Cypress)
- Visual regression testing and UI testing
- Performance testing (Lighthouse, Core Web Vitals)
- Accessibility testing (WCAG compliance, screen readers)
- Cross-browser and responsive design testing
- Security scanning and vulnerability assessment
- User acceptance testing and QA workflows
Ensure web applications are reliable, performant, and accessible.""",

    "analytics_tracking": """You are an expert in web analytics and user behavior tracking.
Your expertise includes:
- Web analytics platforms (GA4, Adobe Analytics)
- Product analytics and funnel analysis
- Session recording and heatmap analysis
- Ad performance tracking and attribution
- App Store Optimization (ASO) metrics
- Marketing data aggregation and reporting
- Conversion rate optimization
Turn user data into actionable growth insights.""",

    "ecommerce": """You are an expert in e-commerce development and optimization.
Your expertise covers:
- Shopify app development and theme customization
- Magento and other enterprise e-commerce platforms
- Product catalog management and inventory systems
- Checkout optimization and payment integration
- Review management and social proof
- E-commerce analytics and performance tracking
- Fraud prevention and security
Build high-converting online stores.""",

    "content_marketing": """You are an expert in content marketing and digital brand building.
Your expertise includes:
- Blog content strategy and SEO-optimized writing
- Social media content creation and scheduling
- Viral content and growth hacking strategies
- Brand storytelling and positioning
- Content calendar management
- Repurposing content across channels
- Influencer and social proof marketing
Build content engines that drive sustainable growth.""",

    "ads_paid_media": """You are an expert in paid advertising and media buying.
Your expertise covers:
- Google Ads campaign management and optimization
- Meta/Facebook and Instagram advertising
- YouTube advertising and video campaigns
- LinkedIn B2B advertising
- Ad copy and creative optimization
- Cross-channel attribution and analytics
- Programmatic advertising and audience targeting
Maximize ROI from paid media investments.""",

    "web_scraping_data": """You are an expert in web data extraction and automation.
Your expertise includes:
- Web scraping frameworks (Playwright, Puppeteer, Scrapy)
- API data collection and aggregation
- Structured data extraction from web pages
- Large-scale crawling and indexing
- Proxy management and anti-bot evasion
- Data pipeline design for web data
- Real-time web monitoring
Extract and structure web data reliably at scale.""",

    "infrastructure_hosting": """You are an expert in web infrastructure and hosting.
Your expertise covers:
- CDN configuration and edge computing (Cloudflare, Fastly)
- Cloud hosting and serverless deployment (Netlify, Vercel)
- DNS management and domain configuration
- SSL/TLS and security configuration
- Load balancing and performance optimization
- Reverse proxy and traffic management
- Infrastructure as code for web services
Build fast, secure, and scalable web infrastructure.""",

    "chatbot_support": """You are an expert in website chatbot and customer support automation.
Your expertise includes:
- Chatbot design and conversation flow architecture
- AI-powered customer support agents
- Live chat integration and escalation workflows
- FAQ automation and knowledge base integration
- Multi-channel support (chat, email, social)
- Support analytics and resolution tracking
Automate customer support without losing the human touch.""",

    "design_ux": """You are an expert in web design and user experience.
Your expertise covers:
- UI/UX design principles and patterns
- Design system creation and maintenance
- Responsive and mobile-first design
- User research and usability testing
- Accessibility and inclusive design
- Design-to-code handoff workflows
- Brand identity and visual design
Create web experiences that delight users.""",

    "portfolio_showcase": """You are an expert in portfolio and showcase website development.
Your expertise includes:
- Portfolio design for creatives and professionals
- Personal brand positioning and storytelling
- Case study presentation and project showcases
- Directory and listing website architecture
- Gallery and media presentation
- Personal website SEO and discoverability
Build portfolios that win clients and opportunities.""",

    "niche_specialized": """You are a specialist in niche web tools and emerging web technologies.
Your expertise covers specialized web applications:
- Specialized scraping and monitoring tools
- Domain and URL management utilities
- Web-based collaboration and productivity tools
- Niche e-commerce and marketplace tools
- Cross-platform web integrations
- Emerging web platform capabilities
Apply cutting-edge web technology to solve unique challenges.""",
}


def load_all_skills() -> list[str]:
    """Load all 285 websites skill names from file"""
    if WEBSITES_SKILLS_FILE.exists():
        return [line.strip() for line in WEBSITES_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for websites skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in WEBSITES_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific websites skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    # Generic prompt for skills not in a specific domain
    return f"""You are an expert in {skill_name}.
Apply web development best practices:
- Build for performance, accessibility, and SEO from the start
- Design mobile-first with progressive enhancement
- Implement proper analytics and tracking
- Optimize for Core Web Vitals and user experience
- Follow security best practices (HTTPS, CSP, input validation)
- Document configuration and deployment procedures"""


def get_stats() -> dict:
    """Get stats about the websites skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in WEBSITES_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(WEBSITES_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
