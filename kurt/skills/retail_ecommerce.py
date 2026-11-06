"""
KURT Retail & E-commerce Skills Catalog
Lahat ng 53 Retail & e-commerce skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

RETAIL_ECOMMERCE_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_retail_ecommerce.txt"

RETAIL_ECOMMERCE_DOMAINS = {
    "shopify_ecosystem": [
        "shopify-ai-toolkit", "Shopify DevKit", "Shopify App Builder",
        "storefront-theme-kit", "liquid-skills", "liquid-dev", "Liquid LSP",
        "Replo", "seal-copilot", "Claistore",
    ],
    "marketplace_platforms": [
        "Amazon Selling Partner", "MakeBox for Etsy", "shopee-review",
        "Trendyol Marketplace Integration", "apMZoomAI · Dongdaemun wholesale",
        "Magento 2 / Mage-OS Skills", "Magekwik Magento Toolkit",
        "JoomPulse", "Medusa", "LogiCommerce Backoffice",
    ],
    "product_catalog": [
        "Abracadabrax AI Product Photo Generator", "Simplio3D", "ScaleSKUs",
        "Syndic8", "Inventok", "Product Returns", "Section11",
        "Contezza AI for Merchants", "Sadakio Developer Docs",
    ],
    "customer_engagement": [
        "SmartReply", "Commslayer", "Answering Agent", "Noibu",
        "Privy BFCM Planner", "Seguno", "Pollen",
        "Brendly", "Headset",
    ],
    "analytics_operations": [
        "Decile", "Riskified Beacon Integration", "Realize Plugin",
        "StoreConnect Agent Skills", "Storeadops", "inSitu Sales",
        "NeonPanel", "EasyEsuite", "Dealertide",
        "MerchantFlow", "MarketsEasy",
    ],
    "niche_specialized": [
        "CoCart API", "Awesome Ecom Skills", "Glop Plugin",
        "Karrito", "Kinetic",
    ],
}

DOMAIN_PROMPTS = {
    "shopify_ecosystem": """You are an expert in Shopify development and optimization.
Your expertise covers:
- Shopify theme development with Liquid templating
- Shopify app development and integrations
- Storefront API and headless commerce
- Shopify Plus enterprise features
- Performance optimization for Shopify stores
- App permissions and Shopify partner ecosystem
- Storefront customization and conversion optimization
- Section and block architecture
Build high-performing Shopify experiences.""",

    "marketplace_platforms": """You are an expert in e-commerce marketplace platforms.
Your expertise covers:
- Amazon Seller Central and FBA/FBM operations
- Etsy seller optimization and product listings
- Multi-marketplace inventory synchronization
- Platform-specific SEO and discoverability
- Cross-border and international marketplace selling
- Magento/Adobe Commerce development
- Headless commerce architecture
- API integrations between platforms
Maximize marketplace presence and sales.""",

    "product_catalog": """You are an expert in product catalog management.
Your expertise covers:
- Product data modeling and enrichment
- AI-powered product photo generation and editing
- 3D product visualization and AR commerce
- SKU management and taxonomy design
- Product feed syndication across channels
- Returns management and reverse logistics
- Inventory optimization and forecasting
- Compliance and regulatory product labeling
Create compelling, accurate product experiences.""",

    "customer_engagement": """You are an expert in e-commerce customer engagement.
Your expertise covers:
- Customer service automation and chatbots
- Review management and social proof
- Email marketing and SMS campaigns
- Seasonal and promotional campaign planning (BFCM, etc.)
- Personalization and customer segmentation
- Customer feedback and NPS programs
- Loyalty and retention strategies
- Omnichannel customer communication
Build lasting customer relationships that drive repeat purchases.""",

    "analytics_operations": """You are an expert in e-commerce analytics and operations.
Your expertise covers:
- Revenue analytics and cohort analysis
- Fraud detection and chargeback prevention
- Inventory and supply chain optimization
- Order management and fulfillment operations
- POS and in-store/online integration
- Sales team enablement for e-commerce
- Reporting dashboards for merchants
- Operational efficiency and automation
Drive profitable e-commerce growth through data.""",

    "niche_specialized": """You are a specialist in niche e-commerce tools.
Your expertise covers specialized solutions for:
- Headless cart and checkout experiences
- Regional and vertical-specific commerce platforms
- Niche product category tools
- Emerging commerce technologies
Apply targeted expertise to unique e-commerce challenges.""",
}


def load_all_skills() -> list[str]:
    if RETAIL_ECOMMERCE_SKILLS_FILE.exists():
        return [line.strip() for line in RETAIL_ECOMMERCE_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    all_skills = load_all_skills()
    return [s for s in all_skills if query.lower() in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    skill_lower = skill_name.lower()
    for domain, skills in RETAIL_ECOMMERCE_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"You are an expert in {skill_name}.\n{base_prompt}\nApply the specific knowledge and practices from the '{skill_name}' skill."
    return f"""You are an expert in {skill_name}.
Apply e-commerce best practices:
- Optimize for conversion at every touchpoint
- Leverage data to drive merchandising decisions
- Balance customer experience with operational efficiency
- Implement omnichannel strategies for consistent experiences
- Use automation to scale without proportional headcount
- Monitor and reduce cart abandonment rates
- Build trust through transparent policies and reviews
- Optimize for mobile-first shopping experiences"""


def get_stats() -> dict:
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in RETAIL_ECOMMERCE_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(RETAIL_ECOMMERCE_DOMAINS),
            "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
