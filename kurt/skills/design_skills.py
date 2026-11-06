"""
KURT Design Skills Catalog
Lahat ng 83 Design skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
DESIGN_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_design.txt"

# Domain-based groupings for smart routing
DESIGN_DOMAINS = {
    "ui_ux_design": [
        "frontend-design", "design-skills", "design-superpowers", "VectorLab UI/UX Skills",
        "ux-ui-audit", "UX Agent Skills", "UXKIN", "Rayden UI Design Skill",
        "perception-first-design", "Fairmind Design", "euxlab-skills",
        "Intuitive Software Design", "consistent-ui", "ui-consistency",
        "inhabited design", "Mobile App Design (iOS)", "Mobile Design System",
    ],
    "figma_tools": [
        "Figma", "Claude2Figma", "figma-suite", "Figma to Code: Design to React, Vue and HTML",
        "design-dev-bridge", "Codesign", "Superdesign", "penpot-atomic-design",
        "Pencil Dev Skill", "naksha-studio", "Kombai",
    ],
    "icons_assets": [
        "image-generation", "Asset Generator", "Icon Creator", "Icons8",
        "Supericons", "Fluenticons", "Streamline Icons", "A1 Gallery",
        "Image Deep Research", "Extract Alpha",
    ],
    "design_systems": [
        "AI Ready Design System", "brand-studio", "Design Steward", "Design Council",
        "doom-design-system", "Ignite UI MCP Tools", "StyleRef", "Canon Check",
        "liquid-glass", "Bauhaus Digital", "lux",
    ],
    "design_review": [
        "designs-drift", "Critic Layer", "HIG Compliance Auditor", "Annotate",
        "ScreenSpec", "Responsive Check: Mobile Layout Tester", "render-visual-skill",
        "Nickture Skills for interface polish, Russian copy and AI deslop",
        "Slop Patterns", "Intent", "hone",
    ],
    "prototyping_tools": [
        "MagicPath", "flowy", "tesserai", "Refero", "Appllama", "Flint",
        "vellum", "Mobbin", "21st", "storefront-theme-kit", "Dualkit",
        "Power BI Accessibility (PBIP/PBIR)",
    ],
    "niche_specialized": [
        "Eversince", "SoundWeaver", "RV and OpenRV Media Review", "Pics.io",
        "jp-web-design-guardrails", "Playbook", "TellTale", "WeInc",
        "Skyelight", "Vulca", "Мильчин",
    ],
}

DOMAIN_PROMPTS = {
    "ui_ux_design": """You are an expert in UI/UX design.
Your expertise covers:
- User interface design principles and patterns
- UX research and usability testing
- Interaction design and microanimations
- Mobile-first and responsive design
- Accessibility standards (WCAG 2.1)
- Design critique and improvement
- Component-based design thinking
- User journey mapping and flow design
Create interfaces that delight users and achieve business goals.""",

    "figma_tools": """You are an expert in Figma and design tooling.
Your expertise covers:
- Figma design system creation and maintenance
- Component libraries and auto-layout
- Figma-to-code workflows (React, Vue, HTML)
- Design handoff and developer collaboration
- Prototyping and interactive flows
- Figma plugins and automation
- Design token management
- Cross-platform design consistency
Maximize design-to-development workflow efficiency.""",

    "icons_assets": """You are an expert in visual assets and icon design.
Your expertise covers:
- Icon design principles and consistency
- SVG optimization and generation
- AI image generation for design assets
- Icon library management and customization
- Brand asset creation and management
- Visual style guide development
- Asset organization and naming conventions
- Cross-platform icon sizing and formats
Create compelling visual assets at scale.""",

    "design_systems": """You are an expert in design systems.
Your expertise covers:
- Design token architecture (colors, typography, spacing)
- Component library design and documentation
- Design system governance and versioning
- Brand guideline implementation
- Cross-platform design consistency
- Design system adoption and onboarding
- Accessibility in design systems
- Design-code synchronization
Build scalable design systems that teams love.""",

    "design_review": """You are an expert in design review and quality assurance.
Your expertise covers:
- Design critique frameworks and methodologies
- Platform compliance auditing (Apple HIG, Material Design)
- Responsive layout testing and verification
- Design consistency checking
- Accessibility auditing
- Design annotation and specification
- Anti-pattern identification
- Design-to-spec verification
Ensure design quality through systematic review.""",

    "prototyping_tools": """You are an expert in prototyping and design exploration.
Your expertise covers:
- Rapid prototyping techniques
- Interactive flow creation
- Motion design and animation
- Design pattern libraries and references
- Low-fidelity to high-fidelity progression
- User testing prototype preparation
- E-commerce and storefront design
- Dashboard and data visualization design
Bring ideas to life through powerful prototypes.""",

    "niche_specialized": """You are a specialist in niche design tools.
Your expertise covers specialized solutions for:
- Media asset management and review
- Audio and multimedia design tools
- Regional and language-specific design guidelines
- Specialized industry design platforms
- Emerging design methodologies
Apply targeted expertise to unique design challenges.""",
}


def load_all_skills() -> list[str]:
    """Load all 83 design skill names from file"""
    if DESIGN_SKILLS_FILE.exists():
        return [line.strip() for line in DESIGN_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for design skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in DESIGN_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific design skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    return f"""You are an expert in {skill_name}.
Apply design best practices:
- Start with user needs and business objectives
- Apply visual hierarchy and information architecture
- Ensure accessibility and inclusive design
- Maintain consistency with design systems and brand guidelines
- Design for all screen sizes and contexts
- Collaborate closely with developers for feasibility
- Test designs with real users early and often
- Iterate based on feedback and data"""


def get_stats() -> dict:
    """Get stats about the design skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in DESIGN_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(DESIGN_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
