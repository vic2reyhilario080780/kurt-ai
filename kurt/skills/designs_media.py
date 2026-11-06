"""
KURT Designs & Media Skills Catalog
Lahat ng 433 Designs & Media skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

# Path to the full skill list
DESIGNS_MEDIA_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_designs_media.txt"

# Domain-based groupings for smart routing
DESIGNS_MEDIA_DOMAINS = {
    "ui_ux_design": [
        "frontend-design", "design-skills", "Superdesign", "21st", "VectorLab UI/UX Skills",
        "design-superpowers", "Figma", "figma-suite", "Figma to Code: Design to React, Vue and HTML",
        "Claude2Figma", "design-is-code", "Design Steward", "Achriom", "design-dev-bridge",
        "Codesign", "Creative Claw", "consistent-ui", "ui-consistency", "Design Council",
        "Rayden UI Design Skill", "Mobile Design System", "Design with Blocks",
        "Mobile App Design (iOS)", "perception-first-design", "Fairmind Design",
        "AI Ready Design System", "design-system-by-blue", "doom-design-system",
        "Stark", "Responsive Check: Mobile Layout Tester", "HIG Compliance Auditor",
        "Web Vitals Auditor", "Mobbin", "Refero", "UX Agent Skills", "UXKIN",
        "euxlab-skills", "penpot-atomic-design", "Intuitive Software Design",
        "Kombai", "vaadin-skills", "Tailwind App", "Ignite UI MCP Tools",
        "DevExpress Blazor Components", "ScreenSpec", "Aictrl.dev",
        "Nickture Skills for interface polish, Russian copy and AI deslop",
    ],
    "video_creation": [
        "Remotion", "AI Video Editor & Timeline by ManyMotions", "animation-studio",
        "watch-video", "Abracadabrax AI Video Generator",
        "AI Video & Image Generator by Clipwave", "Motion Reel", "video-shotcraft",
        "AI UGC Video Ads Maker", "IT Reelsmaker", "AI Video Enhancer Studio",
        "BlitzReels", "Riverside", "CutPro", "Autorender", "Cinematic AI Video Maker with Camera Moves",
        "Short Film Maker: AI Short Films with Story & Dialogue",
        "Anime Story Video Maker: AI Cartoon & Animated Shorts",
        "Comedy Skit Video Maker: AI Funny Shorts & Parodies",
        "Birthday Video Maker: AI Birthday Tribute & Wishes Video",
        "Fitness Video Maker: AI Workout & Training Shorts",
        "Church & Faith Event Video Maker: Event Invitations",
        "Horror Story Video Maker: AI Scary Shorts",
        "Travel Video & Documentary Maker", "CineFlo", "ffmpeg-llm",
        "videodb", "video-to-code-skill", "TwelveLabs", "OpenClips", "OpenClip",
        "letmewatch", "VideoRecompress Studio", "compress-gif",
        "RV and OpenRV Media Review", "FilmEase", "Lumr Studio",
        "My Video Gift", "Unboxing Editor", "Runway Dev", "CellCog",
    ],
    "image_generation": [
        "image-generation", "Abracadabrax AI Image & Video Generator",
        "Abracadabrax AI Product Photo Generator",
        "Abracadabrax Social Media Image & Post Maker",
        "Abracadabrax YouTube Thumbnail Maker", "Abracadabrax Poster & Flyer Maker",
        "Abracadabrax Coloring Page Maker", "Abracadabrax Greeting Card & Invitation Maker",
        "Abracadabrax Album Cover Art Maker", "Generative Art", "Krea",
        "AI Logo Maker & Brand Designer", "AI Avatar Presenter & Explainer Video Maker",
        "Asset Generator", "Icon Creator", "SVG.new", "Supericons", "Streamline Icons",
        "Fluenticons", "Sticklore", "SpriteCook", "Make Poster", "betterposter",
        "Icons8", "Alt Text", "HTML/CSS to Image API", "Car Image API",
        "Abracadabrax Birthday Song Maker", "Morphed", "mcp-image-viewer",
        "imager-x", "A1 Gallery", "Image Deep Research", "Generative Art",
        "anidoodle", "Kling AI", "kling-ai-prompt-generator", "Meshy",
        "Imagelato Image Optimization", "pixinsight-connector-skills", "Lenadweb Image Preview",
    ],
    "social_media": [
        "Social Media Skills", "Posty: Social Media Scheduler", "AdaptlyPost", "Adapty",
        "Ayrshare - Unified Social Media API for AI Agents", "PostEverywhere", "PostDaily",
        "Postiz", "OmniSocials", "Sync Socials", "Postify", "PostSyncer", "PostZen",
        "PostFast", "PostOnce", "PostDashPro", "SocialClaw", "Maeve Social",
        "Socialstats", "SocialFaktory", "Syndic8", "xpost", "x-content-intelligence",
        "InsightPins for Pinterest", "BulkPublish", "Brendly", "DunSocial",
        "Upload-Post", "post bridge", "Postbarrel scripts", "SendIt Social",
        "Virlo", "Buzzfy", "Genviral", "ViralHunt", "Atria", "Banger",
        "BAMF.ai", "Mysocial Intelligence", "Snap Closet",
    ],
    "music_audio": [
        "Abracadabrax AI Background Music Generator", "Abracadabrax AI Song & Music Maker",
        "Abracadabrax Podcast Intro & Jingle Maker", "SoundWeaver", "AudioPod",
        "MuAPI", "Audiorective", "save-to-spotify", "Electra One", "Vocuno",
    ],
    "presentation_slides": [
        "pptx-deck-plugin", "Presenton", "Ploxs Presentations", "htmldeck",
        "FluidDocs Deck Builder", "SlideOps", "slide-revive", "carusela",
        "SuperCool Sites & Decks", "ArcDeck", "DemoDay", "Slidely",
        "Templafy", "keynot", "Tableau",
    ],
    "web_design": [
        "AnimatedWebs", "Website Design", "Chrome Extension Builder", "parallax-threejs",
        "liquid-glass", "liquid-glass-skills", "liquid-dev", "liquid-skills",
        "storefront-theme-kit", "Shopify DevKit", "Replo",
        "Tailwind App", "PlayCanvas", "appstore-screenshots", "app-preview-craft",
        "Responsive Check: Mobile Layout Tester", "Stark", "Bloom",
        "doom-design-system", "Tweenkit", "Pencil Dev Skill", "vaadin-skills",
        "Ignite UI MCP Tools", "DevExpress Blazor Components", "MagicPath",
        "snap-browser", "Screen Browser", "ScreenshotOne", "Screeny",
    ],
    "diagramming_visualization": [
        "Diagrams", "PUML - PlantUML", "excalidraw-plugin", "Whimsical", "IcePanel",
        "tldiagram-create-diagram", "Miro", "archgram", "revit-bim",
        "CADBuildr", "3D CAD Converter", "3DOptix optical design and simulations",
        "Simplio3D", "Avontus Viewer", "SpeakCAD Slicer", "archlens",
        "naksha-studio", "biorender", "IRCODE", "Rapier",
        "Simple Drawing Pad", "Generative Art",
    ],
    "brand_marketing": [
        "brand-studio", "brand-md", "dataink", "render-visual-skill",
        "Adology — Content Intelligence", "AdMakeAI", "Arcads AI",
        "AI Logo Maker & Brand Designer", "Hyper Marketing", "Windsor.ai Ads and Marketing Data",
        "vidIQ", "Mysocial Intelligence", "Marketing for Life Sciences",
        "Bauhaus Digital", "Crayon", "StyleRef", "Achriom", "MakeBox for Etsy",
        "ConvertAPI", "Awesome Ecom Skills", "Brendly", "ClientGen Reach",
        "Ollie: Celebrity Lookalike & Stylist", "Assetlib Audit",
    ],
    "tools_utilities": [
        "YouTube Transcriber", "transcribe-so", "Annotate", "Editorial OS",
        "Online Writing", "FontHound", "DeSlop", "Slop Patterns", "Wiser",
        "conversiontools", "QkConvert", "Contenta Converter", "compress-gif",
        "open-document-skills", "Filestack Claude Plugin", "Pics.io", "BoardRepo",
        "Merch", "Mosaic", "preset-toolkit", "Charmshots", "Elastishot",
        "Stateful", "SnapVisor", "viewprinter", "TrueHue", "static.md",
        "cv-skills", "Waldo fyi", "Dualkit", "Rill", "Morph",
        "Titlize", "Scribe Mail", "Telescope",
    ],
    "game_creative": [
        "Unity", "Kling AI", "playground", "Game Trend Skills", "batocera",
        "Meta VR", "novel-studio", "Fountain", "Generative Art",
        "Anime Story Video Maker: AI Cartoon & Animated Shorts",
        "Horror Story Video Maker: AI Scary Shorts",
        "Comedy Skit Video Maker: AI Funny Shorts & Parodies",
        "SpriteCook", "VerseDB: Comic Book Tracker", "Dreambase",
        "PhaseRunner", "Soggyhotdog", "Thai Memes CC",
    ],
    "analytics_insights": [
        "Adology — Content Intelligence", "Windsor.ai Ads and Marketing Data",
        "vidIQ", "Spytrend MCP Skills", "LurkAPI", "Extract Alpha",
        "Crypto Spot Futures Analyzer", "Sonar ASO", "ViralHunt",
        "Socialstats", "Mysocial Intelligence", "x-content-intelligence",
        "Reader Radius", "BOLD Studios", "hive", "Hive",
        "Telepath", "Postbarrel scripts",
    ],
}

# System prompt templates for each domain
DOMAIN_PROMPTS = {
    "ui_ux_design": """You are a senior UI/UX designer and design engineer.
Your expertise covers:
- User interface design principles (layout, typography, color, spacing)
- UX research and usability testing
- Design systems and component libraries
- Figma, design tokens, and design-to-code workflows
- Accessibility (WCAG 2.1 AA), mobile-first design
- Responsive layouts and cross-platform consistency
Create designs that are beautiful, accessible, and developer-friendly.""",

    "video_creation": """You are a professional video creator and editor.
Your expertise includes:
- Video production, scripting, and storytelling
- Motion graphics and animation
- AI-assisted video generation workflows
- Short-form content (Reels, TikTok, YouTube Shorts)
- Video editing, effects, and transitions
- Platform-specific optimization
Produce engaging videos that tell compelling stories.""",

    "image_generation": """You are an AI image generation and visual design expert.
Your expertise covers:
- Prompt engineering for image generators (Midjourney, DALL-E, Stable Diffusion)
- Logo design, icons, and brand graphics
- Photo editing and enhancement
- SVG creation and optimization
- Product photography and visual merchandising
Create visuals that are striking, on-brand, and production-ready.""",

    "social_media": """You are a social media content and automation expert.
Your expertise covers:
- Multi-platform content strategy (Instagram, TikTok, LinkedIn, X/Twitter)
- Content scheduling and automation
- Visual content creation for social
- Engagement optimization and analytics
- Community management and growth
Create content that drives engagement and builds audiences.""",

    "music_audio": """You are an audio production and music creation expert.
Your expertise includes:
- AI music generation and composition
- Podcast production and editing
- Sound design and audio engineering
- Music licensing and distribution
- Jingle and brand audio creation
Produce professional-quality audio content.""",

    "presentation_slides": """You are a presentation design expert.
Your expertise covers:
- PowerPoint, Keynote, and web-based slide design
- Data visualization in presentations
- Storytelling and narrative structure
- Brand-consistent templates
- Pitch decks and investor presentations
Create presentations that persuade and inform.""",

    "web_design": """You are a web design and frontend development expert.
Your expertise includes:
- Modern CSS, animations, and interactions
- Responsive and mobile-first design
- Component libraries and design systems
- Performance optimization
- E-commerce and landing page design
Build web experiences that convert and delight.""",

    "diagramming_visualization": """You are a diagramming and technical visualization expert.
Your expertise covers:
- Architecture diagrams (UML, C4, sequence)
- Flowcharts and process diagrams
- 3D modeling and CAD visualization
- Scientific and technical illustrations
- Interactive diagrams and prototypes
Create visuals that communicate complex ideas clearly.""",

    "brand_marketing": """You are a brand design and marketing creative expert.
Your expertise includes:
- Brand identity and visual language
- Marketing asset creation
- Ad creative and campaign design
- Content marketing and copywriting
- Competitive analysis and positioning
Build brands that stand out and convert.""",

    "tools_utilities": """You are a creative tools and media utilities expert.
Your expertise covers:
- File format conversion and optimization
- Asset management and organization
- Creative workflow automation
- Media processing and transformation
- Typography and font management
Streamline creative workflows efficiently.""",

    "game_creative": """You are a game development and creative media expert.
Your expertise includes:
- Game design and mechanics
- 3D assets and game art
- Interactive storytelling
- VR/AR experiences
- Creative AI applications
Build immersive, engaging interactive experiences.""",

    "analytics_insights": """You are a media analytics and insights expert.
Your expertise covers:
- Social media analytics and reporting
- Content performance optimization
- Competitive intelligence
- Audience research and segmentation
- ROI measurement for creative campaigns
Turn data into actionable creative decisions.""",
}


def load_all_skills() -> list[str]:
    """Load all 433 designs & media skill names from file"""
    if DESIGNS_MEDIA_SKILLS_FILE.exists():
        return [line.strip() for line in DESIGNS_MEDIA_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    """Search for designs & media skills by name (case-insensitive)"""
    all_skills = load_all_skills()
    query_lower = query.lower()
    return [s for s in all_skills if query_lower in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Find which domain a skill belongs to"""
    skill_lower = skill_name.lower()
    for domain, skills in DESIGNS_MEDIA_DOMAINS.items():
        for s in skills:
            if s.lower() == skill_lower or skill_lower in s.lower():
                return domain
    return None


def get_domain_prompt(domain: str) -> Optional[str]:
    """Get the system prompt for a domain"""
    return DOMAIN_PROMPTS.get(domain)


def get_skill_context(skill_name: str) -> str:
    """Get context/prompt for a specific designs & media skill"""
    domain = get_domain_for_skill(skill_name)
    if domain:
        base_prompt = DOMAIN_PROMPTS.get(domain, "")
        return f"""You are an expert in {skill_name}.
{base_prompt}
Apply the specific knowledge and practices from the '{skill_name}' skill."""

    # Generic prompt for skills not in a specific domain
    return f"""You are an expert in {skill_name}.
Apply design and media best practices:
- Create visually compelling, audience-appropriate content
- Follow platform and format conventions
- Prioritize clarity, aesthetics, and engagement
- Optimize for the intended medium and audience
- Deliver production-ready, polished results"""


def get_stats() -> dict:
    """Get stats about the designs & media skills catalog"""
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in DESIGNS_MEDIA_DOMAINS.items()}

    return {
        "total_skills": len(all_skills),
        "domains": len(DESIGNS_MEDIA_DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }
