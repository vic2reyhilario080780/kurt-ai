"""
KURT Skills Manager - Install, list, remove skills
Skills = domain knowledge na nag-ggguide sa AI behavior

Includes 1,203 Engineering skills, 1,104 Code skills, 850 Files & Documents,
433 Designs & Media skills, 368 Pipelines & Jobs skills, 365 Tickets & Tasks,
290 Notes & Memory skills, 346 APIs skills, 324 Reference Docs skills,
311 AI Models & Agents skills, 285 Websites skills, 251 Servers & Cloud skills,
246 Contacts & Leads skills, 246 Databases skills, and 230 Finance skills from Claude's marketplace.
"""

import os
import json
import shutil
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import box

# Engineering skills catalog
from kurt.skills.engineering import (
    load_all_skills as load_engineering_skills,
    search_skills as search_engineering_skills,
    get_skill_context as get_engineering_skill_context,
    get_domain_prompt as get_engineering_domain_prompt,
    get_stats as get_engineering_stats,
    ENGINEERING_DOMAINS,
)

# Code skills catalog
from kurt.skills.code_skills import (
    load_all_skills as load_code_skills,
    search_skills as search_code_skills,
    get_skill_context as get_code_skill_context,
    get_domain_prompt as get_code_domain_prompt,
    get_stats as get_code_stats,
    CODE_DOMAINS,
)

# Files & Documents skills catalog
from kurt.skills.files_docs import (
    load_all_skills as load_files_docs_skills,
    search_skills as search_files_docs_skills,
    get_skill_context as get_files_docs_skill_context,
    get_domain_prompt as get_files_docs_domain_prompt,
    get_stats as get_files_docs_stats,
    FILES_DOCS_DOMAINS,
)

# Designs & Media skills catalog
from kurt.skills.designs_media import (
    load_all_skills as load_designs_media_skills,
    search_skills as search_designs_media_skills,
    get_skill_context as get_designs_media_skill_context,
    get_domain_prompt as get_designs_media_domain_prompt,
    get_stats as get_designs_media_stats,
    DESIGNS_MEDIA_DOMAINS,
)

# Pipelines & Jobs skills catalog
from kurt.skills.pipelines_jobs import (
    load_all_skills as load_pipelines_jobs_skills,
    search_skills as search_pipelines_jobs_skills,
    get_skill_context as get_pipelines_jobs_skill_context,
    get_domain_prompt as get_pipelines_jobs_domain_prompt,
    get_stats as get_pipelines_jobs_stats,
    PIPELINES_JOBS_DOMAINS,
)

# Tickets & Tasks skills catalog
from kurt.skills.tickets_tasks import (
    load_all_skills as load_tickets_tasks_skills,
    search_skills as search_tickets_tasks_skills,
    get_skill_context as get_tickets_tasks_skill_context,
    get_domain_prompt as get_tickets_tasks_domain_prompt,
    get_stats as get_tickets_tasks_stats,
    TICKETS_TASKS_DOMAINS,
)

# Notes & Memory skills catalog
from kurt.skills.notes_memory import (
    load_all_skills as load_notes_memory_skills,
    search_skills as search_notes_memory_skills,
    get_skill_context as get_notes_memory_skill_context,
    get_domain_prompt as get_notes_memory_domain_prompt,
    get_stats as get_notes_memory_stats,
    NOTES_MEMORY_DOMAINS,
)

# APIs skills catalog
from kurt.skills.apis import (
    load_all_skills as load_apis_skills,
    search_skills as search_apis_skills,
    get_skill_context as get_apis_skill_context,
    get_domain_prompt as get_apis_domain_prompt,
    get_stats as get_apis_stats,
    APIS_DOMAINS,
)

# Reference Docs skills catalog
from kurt.skills.reference_docs import (
    load_all_skills as load_reference_docs_skills,
    search_skills as search_reference_docs_skills,
    get_skill_context as get_reference_docs_skill_context,
    get_domain_prompt as get_reference_docs_domain_prompt,
    get_stats as get_reference_docs_stats,
    REFERENCE_DOCS_DOMAINS,
)

# AI Models & Agents skills catalog
from kurt.skills.ai_models_agents import (
    load_all_skills as load_ai_models_agents_skills,
    search_skills as search_ai_models_agents_skills,
    get_skill_context as get_ai_models_agents_skill_context,
    get_domain_prompt as get_ai_models_agents_domain_prompt,
    get_stats as get_ai_models_agents_stats,
    AI_MODELS_AGENTS_DOMAINS,
)

# Websites skills catalog
from kurt.skills.websites import (
    load_all_skills as load_websites_skills,
    search_skills as search_websites_skills,
    get_skill_context as get_websites_skill_context,
    get_domain_prompt as get_websites_domain_prompt,
    get_stats as get_websites_stats,
    WEBSITES_DOMAINS,
)

# Servers & Cloud skills catalog
from kurt.skills.servers_cloud import (
    load_all_skills as load_servers_cloud_skills,
    search_skills as search_servers_cloud_skills,
    get_skill_context as get_servers_cloud_skill_context,
    get_domain_prompt as get_servers_cloud_domain_prompt,
    get_stats as get_servers_cloud_stats,
    SERVERS_CLOUD_DOMAINS,
)

# Contacts & Leads skills catalog
from kurt.skills.contacts_leads import (
    load_all_skills as load_contacts_leads_skills,
    search_skills as search_contacts_leads_skills,
    get_skill_context as get_contacts_leads_skill_context,
    get_domain_prompt as get_contacts_leads_domain_prompt,
    get_stats as get_contacts_leads_stats,
    CONTACTS_LEADS_DOMAINS,
)

# Finance skills catalog
from kurt.skills.finance import (
    load_all_skills as load_finance_skills,
    search_skills as search_finance_skills,
    get_skill_context as get_finance_skill_context,
    get_domain_prompt as get_finance_domain_prompt,
    get_stats as get_finance_stats,
    FINANCE_DOMAINS,
)

# Databases skills catalog
from kurt.skills.databases import (
    load_all_skills as load_databases_skills,
    search_skills as search_databases_skills,
    get_skill_context as get_databases_skill_context,
    get_domain_prompt as get_databases_domain_prompt,
    get_stats as get_databases_stats,
    DATABASES_DOMAINS,
)

console = Console()

KURT_DIR = Path.home() / ".kurt"
SKILLS_DIR = KURT_DIR / "skills"


# Built-in skills na kasama na sa KURT
BUILTIN_SKILLS = {
    "tiktok": {
        "name": "TikTok Viral Formula",
        "description": "Alam na ang pinaka-viral na TikTok format, hooks, at captions",
        "version": "1.0.0",
        "author": "KURT",
        "system_prompt": """You are a TikTok viral content expert.
        When creating TikTok content, always:
        1. Start with a strong hook in the first 3 seconds
        2. Use trending sounds and effects recommendations
        3. Keep videos 15-60 seconds for maximum reach
        4. Add 3-5 relevant hashtags (mix of niche and popular)
        5. End with a clear call-to-action
        6. Use pattern interrupts every 5-7 seconds
        Format: Hook → Problem → Solution → CTA"""
    },
    "copywriting": {
        "name": "Copywriting Expert",
        "description": "Sales copy, persuasive writing, conversion optimization",
        "version": "1.0.0",
        "author": "KURT",
        "system_prompt": """You are a world-class copywriter.
        Apply these frameworks:
        - AIDA: Attention, Interest, Desire, Action
        - PAS: Problem, Agitate, Solution
        - 4Ps: Promise, Picture, Proof, Push
        Always focus on benefits over features.
        Write in the voice of the target audience."""
    },
    "seo": {
        "name": "SEO Expert",
        "description": "On-page SEO, keyword research, content optimization",
        "version": "1.0.0",
        "author": "KURT",
        "system_prompt": """You are an SEO expert with deep knowledge of:
        - Keyword research and clustering
        - On-page optimization (title, meta, headers)
        - Content structure for E-E-A-T
        - Technical SEO best practices
        - Link building strategies
        Always provide actionable, specific recommendations."""
    },
    "trading": {
        "name": "Crypto Trading Analyst",
        "description": "Technical analysis, trading strategies, risk management",
        "version": "1.0.0",
        "author": "KURT",
        "system_prompt": """You are a crypto trading expert.
        Provide:
        - Technical analysis (RSI, MACD, Bollinger Bands)
        - Support/Resistance levels
        - Risk/Reward ratios
        - Position sizing recommendations
        - Market sentiment analysis
        Always emphasize risk management. Never give financial advice."""
    },
    "filipino": {
        "name": "Filipino Language Expert",
        "description": "Nag-rereplies sa Filipino/Tagalog, may cultural context",
        "version": "1.0.0",
        "author": "KURT",
        "system_prompt": """Ikaw ay isang Filipino AI assistant.
        Sumasagot ka sa Taglish (mix ng Tagalog at English).
        May malalim kang kaalaman sa:
        - Filipino culture at traditions
        - Local expressions at idioms
        - Philippine business practices
        - Pinoy humor at communication style
        Maging casual at friendly, tulad ng kausap mo ang kaibigan."""
    },
    "game-dev": {
        "name": "Game Developer",
        "description": "Game design, pygame, HTML5 games, game mechanics",
        "version": "1.0.0",
        "author": "KURT",
        "system_prompt": """You are an expert game developer.
        You can build:
        - Python games with pygame
        - HTML5/JavaScript browser games
        - Terminal/ASCII games
        Always include:
        - Game loop structure
        - Collision detection
        - Score system
        - Game over/restart functionality
        Make games playable and fun!"""
    },
    "ecommerce": {
        "name": "E-Commerce Expert",
        "description": "Shopee, Lazada, product listings, pricing strategies",
        "version": "1.0.0",
        "author": "KURT",
        "system_prompt": """You are a Philippine e-commerce expert.
        Specialized in Shopee PH and Lazada PH:
        - Product title optimization
        - Keyword-rich descriptions
        - Competitive pricing strategies
        - Flash sale tactics
        - Customer service best practices
        - Shipping optimization
        Focus on Philippine market dynamics."""
    },
}


def init_skills():
    """Initialize skills directory"""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    # Save built-in skills
    for skill_id, skill_data in BUILTIN_SKILLS.items():
        skill_file = SKILLS_DIR / f"{skill_id}.json"
        if not skill_file.exists():
            with open(skill_file, "w") as f:
                json.dump({**skill_data, "id": skill_id, "builtin": True}, f, indent=2)


def list_skills():
    """List all installed skills"""
    init_skills()

    table = Table(
        title="🧠 KURT Skills",
        box=box.ROUNDED,
        border_style="cyan",
        show_header=True,
    )
    table.add_column("ID", style="cyan", width=15)
    table.add_column("Name", style="white", width=25)
    table.add_column("Description", style="dim", width=40)
    table.add_column("Type", style="yellow", width=10)

    for skill_file in sorted(SKILLS_DIR.glob("*.json")):
        with open(skill_file) as f:
            skill = json.load(f)

        skill_type = "[green]Built-in[/green]" if skill.get("builtin") else "[blue]Custom[/blue]"
        table.add_row(
            skill["id"],
            skill["name"],
            skill["description"],
            skill_type,
        )

    console.print(table)
    console.print(f"\n[dim]Skills dir: {SKILLS_DIR}[/dim]")
    console.print("[dim]Install custom skill: kurt skill install <path>[/dim]")


def get_skill(skill_id: str) -> dict | None:
    """Get a skill's data"""
    init_skills()
    skill_file = SKILLS_DIR / f"{skill_id}.json"
    if skill_file.exists():
        with open(skill_file) as f:
            return json.load(f)
    return None


def get_skill_prompt(skill_id: str) -> str | None:
    """Get a skill's system prompt"""
    skill = get_skill(skill_id)
    if skill:
        return skill.get("system_prompt", "")
    return None


def install_skill(source: str):
    """Install a skill from a JSON file"""
    init_skills()

    if not source or not source.strip():
        console.print("[red]❌ No source specified. Provide a path or URL.[/red]")
        return

    # Handle URL sources gracefully
    if source.startswith("http://") or source.startswith("https://"):
        console.print(f"[yellow]⚠️  URL install not yet supported: {source}[/yellow]")
        console.print("[dim]Download the skill JSON manually then run: kurt skill install <path>[/dim]")
        return

    source_path = Path(source)

    if not source_path.exists() or source_path.is_dir():
        console.print(f"[red]❌ File not found: {source}[/red]")
        return

    try:
        with open(source_path) as f:
            skill_data = json.load(f)

        # Validate required fields
        required = ["id", "name", "description", "system_prompt"]
        for field in required:
            if field not in skill_data:
                console.print(f"[red]❌ Missing field: {field}[/red]")
                return

        skill_data["builtin"] = False
        dest = SKILLS_DIR / f"{skill_data['id']}.json"

        with open(dest, "w") as f:
            json.dump(skill_data, f, indent=2)

        console.print(f"[green]✅ Skill installed: {skill_data['name']}[/green]")
        console.print(f"[dim]Use with: kurt --skill {skill_data['id']} \"your task\"[/dim]")

    except json.JSONDecodeError:
        console.print("[red]❌ Invalid JSON file[/red]")


def list_engineering_skills(domain: str = None, search: str = None):
    """List or search engineering skills from Claude's marketplace"""
    if search:
        results = search_engineering_skills(search)
        console.print(f"\n[cyan]🔍 Engineering skills matching '{search}':[/cyan]")
        for s in results[:20]:
            console.print(f"  [white]• {s}[/white]")
        if len(results) > 20:
            console.print(f"  [dim]... and {len(results) - 20} more[/dim]")
        console.print(f"\n[dim]Total matches: {len(results)}[/dim]")
        return

    if domain:
        skills = ENGINEERING_DOMAINS.get(domain, [])
        console.print(f"\n[cyan]⚙️  Engineering domain: {domain}[/cyan]")
        for s in skills:
            console.print(f"  [white]• {s}[/white]")
        console.print(f"\n[dim]Total in domain: {len(skills)}[/dim]")
        return

    # Show overview
    stats = get_engineering_stats()
    console.print(f"\n[bold cyan]⚙️  KURT Engineering Skills Catalog[/bold cyan]")
    console.print(f"[dim]Sourced from Claude's marketplace — {stats['total_skills']:,} unique skills[/dim]\n")

    table = Table(box=box.ROUNDED, border_style="cyan")
    table.add_column("Domain", style="cyan", width=20)
    table.add_column("Skills Count", style="white", justify="right", width=15)
    table.add_column("Sample Skills", style="dim", width=50)

    sample_map = {
        "agentic": "agentic-council, Agent Engineering, Session Orchestration",
        "code_review": "code-review, Deep Review, finecomb, PR Story Aligner",
        "security": "OWASP Security Audit, Semgrep Guardian, Shieldcode",
        "frontend": "liquid-glass-skills, Web Vitals Auditor, A11y Enforcer",
        "backend": "Go Backend Skills, laravel-boost, spring-standards",
        "cloud_devops": "aws-core, Kubernetes Mastery, terraform",
        "testing": "E2E Test Generator, Cypress, Test Coverage Intelligence",
        "ai_ml": "huggingface-skills, RAGOps, Langfuse Observability",
        "mobile": "Flutter Skills, expo, SwiftUI guidance for macOS",
        "data": "supabase, clickhouse-best-practices, DB Schema Spy",
        "observability": "New Relic, Dynatrace, Grafana Assistant",
        "enterprise": "D365FO X++ Development, boomi-integration, Celigo",
        "workflow_automation": "n8n Knowledge Base, Make Documentation, Temporal",
        "documentation": "diataxis, API Doc Generator, Mintlify",
        "game_dev": "Unity, Unreal Engine Skills, unity-perf",
    }

    for domain_name, count in sorted(stats["domain_breakdown"].items(), key=lambda x: -x[1]):
        table.add_row(domain_name, str(count), sample_map.get(domain_name, ""))

    console.print(table)
    console.print(f"\n[dim]Use: kurt skill eng --search <query>  or  kurt skill eng --domain <name>[/dim]")
    console.print(f"[dim]Remaining {stats['total_skills'] - stats['domain_coverage']} skills are cross-domain/specialized[/dim]")


def list_code_skills(domain: str = None, search: str = None):
    """List or search code skills from Claude's marketplace"""
    if search:
        results = search_code_skills(search)
        console.print(f"\n[cyan]🔍 Code skills matching '{search}':[/cyan]")
        for s in results[:20]:
            console.print(f"  [white]• {s}[/white]")
        if len(results) > 20:
            console.print(f"  [dim]... and {len(results) - 20} more[/dim]")
        console.print(f"\n[dim]Total matches: {len(results)}[/dim]")
        return

    if domain:
        skills = CODE_DOMAINS.get(domain, [])
        console.print(f"\n[cyan]💻 Code domain: {domain}[/cyan]")
        for s in skills:
            console.print(f"  [white]• {s}[/white]")
        console.print(f"\n[dim]Total in domain: {len(skills)}[/dim]")
        return

    # Show overview
    stats = get_code_stats()
    console.print(f"\n[bold cyan]💻 KURT Code Skills Catalog[/bold cyan]")
    console.print(f"[dim]Sourced from Claude's marketplace — {stats['total_skills']:,} unique skills[/dim]\n")

    table = Table(box=box.ROUNDED, border_style="cyan")
    table.add_column("Domain", style="cyan", width=22)
    table.add_column("Skills Count", style="white", justify="right", width=15)
    table.add_column("Sample Skills", style="dim", width=48)

    sample_map = {
        "agentic_frameworks": "agentic-council, Agent Engineering, atomic-agents",
        "code_review": "code-review, Deep Review, Adversarial Review",
        "security": "OWASP Security Audit, Semgrep Guardian, Aikido",
        "frontend": "liquid-glass-skills, Web Vitals Auditor, A11y Enforcer",
        "backend": "Go Backend Skills, laravel-boost, spring-standards",
        "cloud_devops": "aws-core, Kubernetes Mastery, terraform",
        "testing": "E2E Test Generator, Cypress, Test Coverage Intelligence",
        "ai_ml": "huggingface-skills, pydantic-ai, Langfuse Observability",
        "mobile": "Flutter Skills, expo, SwiftUI guidance for macOS",
        "data": "supabase, clickhouse-best-practices, DB Schema Spy",
        "workflow_automation": "n8n Knowledge Base, Temporal, sdlc-kit",
        "documentation": "diataxis, API Doc Generator, Mintlify",
        "game_dev": "Unity, Unreal Engine Skills, PlayCanvas",
        "enterprise": "D365FO X++ Development, boomi-integration, Celigo",
        "shopify": "shopify-ai-toolkit, liquid-skills, Shopify App Builder",
    }

    for domain_name, count in sorted(stats["domain_breakdown"].items(), key=lambda x: -x[1]):
        table.add_row(domain_name, str(count), sample_map.get(domain_name, ""))

    console.print(table)
    console.print(f"\n[dim]Use: kurt skill code --search <query>  or  kurt skill code --domain <name>[/dim]")
    console.print(f"[dim]Remaining {stats['total_skills'] - stats['domain_coverage']} skills are cross-domain/specialized[/dim]")


def list_files_docs_skills(domain: str = None, search: str = None):
    """List or search files & documents skills from Claude's marketplace"""
    if search:
        results = search_files_docs_skills(search)
        console.print(f"\n[cyan]🔍 Files & Documents skills matching '{search}':[/cyan]")
        for s in results[:20]:
            console.print(f"  [white]• {s}[/white]")
        if len(results) > 20:
            console.print(f"  [dim]... and {len(results) - 20} more[/dim]")
        console.print(f"\n[dim]Total matches: {len(results)}[/dim]")
        return

    if domain:
        skills = FILES_DOCS_DOMAINS.get(domain, [])
        console.print(f"\n[cyan]📄 Files & Documents domain: {domain}[/cyan]")
        for s in skills:
            console.print(f"  [white]• {s}[/white]")
        console.print(f"\n[dim]Total in domain: {len(skills)}[/dim]")
        return

    # Show overview
    stats = get_files_docs_stats()
    console.print(f"\n[bold cyan]📄 KURT Files & Documents Skills Catalog[/bold cyan]")
    console.print(f"[dim]Sourced from Claude's marketplace — {stats['total_skills']:,} unique skills[/dim]\n")

    table = Table(box=box.ROUNDED, border_style="cyan")
    table.add_column("Domain", style="cyan", width=22)
    table.add_column("Skills Count", style="white", justify="right", width=15)
    table.add_column("Sample Skills", style="dim", width=48)

    sample_map = {
        "document_creation": "diataxis, GitBook, PDFBolt, PlantUML, Miro",
        "seo_marketing": "SEO Audit, Ad Copy Preflight, B2B Personal Branding",
        "resume_career": "CV Builder, ATS Resume Checker, Career Compass",
        "legal_compliance": "commercial-legal, GDPRGard, PandaDoc, DocuSeal",
        "memory_context": "claude-memory, Memory Bank, Obsidian Notes",
        "writing_editing": "Copyedit & Proofreading, anti-ai-writing, DeepL",
        "productivity_tools": "research-superpowers, MeetNotes, Cite2FN",
        "data_spreadsheet": "CSV Cleanup, duckdb-skills, Datarails financeos",
        "file_management": "firecrawl, HandwritingOCR, google-cloud-storage",
        "project_management": "pm, sdlc-kit, Docket Tracker, roadmapsmith",
        "ai_integration": "AI Skills, pinecone, RAG Evaluation, databricks",
        "ecommerce_business": "Amazon Selling Partner, Invoice Generator, Replo",
    }

    for domain_name, count in sorted(stats["domain_breakdown"].items(), key=lambda x: -x[1]):
        table.add_row(domain_name, str(count), sample_map.get(domain_name, ""))

    console.print(table)
    console.print(f"\n[dim]Use: kurt skill files --search <query>  or  kurt skill files --domain <name>[/dim]")
    console.print(f"[dim]Remaining {stats['total_skills'] - stats['domain_coverage']} skills are cross-domain/specialized[/dim]")


def list_designs_media_skills(domain: str = None, search: str = None):
    """List or search designs & media skills from Claude's marketplace"""
    if search:
        results = search_designs_media_skills(search)
        console.print(f"\n[cyan]🔍 Designs & Media skills matching '{search}':[/cyan]")
        for s in results[:20]:
            console.print(f"  [white]• {s}[/white]")
        if len(results) > 20:
            console.print(f"  [dim]... and {len(results) - 20} more[/dim]")
        console.print(f"\n[dim]Total matches: {len(results)}[/dim]")
        return

    if domain:
        skills = DESIGNS_MEDIA_DOMAINS.get(domain, [])
        console.print(f"\n[cyan]🎨 Designs & Media domain: {domain}[/cyan]")
        for s in skills:
            console.print(f"  [white]• {s}[/white]")
        console.print(f"\n[dim]Total in domain: {len(skills)}[/dim]")
        return

    # Show overview
    stats = get_designs_media_stats()
    console.print(f"\n[bold cyan]🎨 KURT Designs & Media Skills Catalog[/bold cyan]")
    console.print(f"[dim]Sourced from Claude's marketplace — {stats['total_skills']:,} unique skills[/dim]\n")

    table = Table(box=box.ROUNDED, border_style="cyan")
    table.add_column("Domain", style="cyan", width=22)
    table.add_column("Skills Count", style="white", justify="right", width=15)
    table.add_column("Sample Skills", style="dim", width=48)

    sample_map = {
        "ui_ux_design": "Figma, Superdesign, Mobbin, Stark, design-skills",
        "video_creation": "Remotion, BlitzReels, Riverside, CutPro, CineFlo",
        "image_generation": "image-generation, Krea, Kling AI, Meshy, SVG.new",
        "social_media": "Posty, Postiz, Ayrshare, OmniSocials, Banger",
        "music_audio": "SoundWeaver, AudioPod, MuAPI, Electra One, Vocuno",
        "presentation_slides": "pptx-deck-plugin, Presenton, Slidely, ArcDeck",
        "web_design": "AnimatedWebs, liquid-glass, Shopify DevKit, PlayCanvas",
        "diagramming_visualization": "Diagrams, Whimsical, Miro, excalidraw, IcePanel",
        "brand_marketing": "brand-studio, AdMakeAI, Arcads AI, Bauhaus Digital",
        "tools_utilities": "YouTube Transcriber, FontHound, DeSlop, conversiontools",
        "game_creative": "Unity, Meta VR, novel-studio, SpriteCook, Dreambase",
        "analytics_insights": "vidIQ, Spytrend MCP Skills, Socialstats, Extract Alpha",
    }

    for domain_name, count in sorted(stats["domain_breakdown"].items(), key=lambda x: -x[1]):
        table.add_row(domain_name, str(count), sample_map.get(domain_name, ""))

    console.print(table)
    console.print(f"\n[dim]Use: kurt skill designs --search <query>  or  kurt skill designs --domain <name>[/dim]")
    console.print(f"[dim]Remaining {stats['total_skills'] - stats['domain_coverage']} skills are cross-domain/specialized[/dim]")


def list_pipelines_jobs_skills(domain: str = None, search: str = None):
    """List or search pipelines & jobs skills from Claude's marketplace"""
    if search:
        results = search_pipelines_jobs_skills(search)
        console.print(f"\n[cyan]🔍 Pipelines & Jobs skills matching '{search}':[/cyan]")
        for s in results[:20]:
            console.print(f"  [white]• {s}[/white]")
        if len(results) > 20:
            console.print(f"  [dim]... and {len(results) - 20} more[/dim]")
        console.print(f"\n[dim]Total matches: {len(results)}[/dim]")
        return

    if domain:
        skills = PIPELINES_JOBS_DOMAINS.get(domain, [])
        console.print(f"\n[cyan]⚙️ Pipelines & Jobs domain: {domain}[/cyan]")
        for s in skills:
            console.print(f"  [white]• {s}[/white]")
        console.print(f"\n[dim]Total in domain: {len(skills)}[/dim]")
        return

    # Show overview
    stats = get_pipelines_jobs_stats()
    console.print(f"\n[bold cyan]⚙️ KURT Pipelines & Jobs Skills Catalog[/bold cyan]")
    console.print(f"[dim]Sourced from Claude's marketplace — {stats['total_skills']:,} unique skills[/dim]\n")

    table = Table(box=box.ROUNDED, border_style="cyan")
    table.add_column("Domain", style="cyan", width=22)
    table.add_column("Skills Count", style="white", justify="right", width=15)
    table.add_column("Sample Skills", style="dim", width=48)

    sample_map = {
        "ci_cd_devops": "gitlab, harness, Checkly, deploycheck, Shipwright",
        "project_management": "asana, linear, AgileHero, Plane, roadmapsmith",
        "monitoring_observability": "Datadog, New Relic, Grafana MCP, Rootly, logfire",
        "data_pipeline": "databricks, dbt-toolkit, Prefect, Temporal, Alteryx",
        "cloud_infrastructure": "terraform, aws-core, docker-skills, Blaxel, NeonPanel",
        "ai_agents": "agentic-council, Factory, Controller AI, RAGOps, Rig",
        "testing_qa": "BugBug, TestAtlas, Checkly, functionize-mcp, assurance",
        "business_automation": "ActiveCampaign, Customer.io, Celigo, Knock, Inngest",
        "developer_tools": "postman, lovable, build-companion, superdevflow, Go Backend Skills",
        "security_compliance": "crowdstrike-falcon-foundry, TrustPin, genesis-governance-claude",
        "product_analytics": "amplitude, posthog, Mixpanel, Basedash, Qlik Agents",
        "sdlc_planning": "Agentic SDLC, Think Before You Build, estimator, Hypotize",
    }

    for domain_name, count in sorted(stats["domain_breakdown"].items(), key=lambda x: -x[1]):
        table.add_row(domain_name, str(count), sample_map.get(domain_name, ""))

    console.print(table)
    console.print(f"\n[dim]Use: kurt skill pipelines --search <query>  or  kurt skill pipelines --domain <name>[/dim]")
    console.print(f"[dim]Remaining {stats['total_skills'] - stats['domain_coverage']} skills are cross-domain/specialized[/dim]")


def list_tickets_tasks_skills(domain: str = None, search: str = None):
    """List or search tickets & tasks skills from Claude's marketplace"""
    if search:
        results = search_tickets_tasks_skills(search)
        console.print(f"\n[cyan]🔍 Tickets & Tasks skills matching '{search}':[/cyan]")
        for s in results[:20]:
            console.print(f"  [white]• {s}[/white]")
        if len(results) > 20:
            console.print(f"  [dim]... and {len(results) - 20} more[/dim]")
        console.print(f"\n[dim]Total matches: {len(results)}[/dim]")
        return

    if domain:
        skills = TICKETS_TASKS_DOMAINS.get(domain, [])
        console.print(f"\n[cyan]🎫 Tickets & Tasks domain: {domain}[/cyan]")
        for s in skills:
            console.print(f"  [white]• {s}[/white]")
        console.print(f"\n[dim]Total in domain: {len(skills)}[/dim]")
        return

    # Show overview
    stats = get_tickets_tasks_stats()
    console.print(f"\n[bold cyan]🎫 KURT Tickets & Tasks Skills Catalog[/bold cyan]")
    console.print(f"[dim]Sourced from Claude's marketplace — {stats['total_skills']:,} unique skills[/dim]\n")

    table = Table(box=box.ROUNDED, border_style="cyan")
    table.add_column("Domain", style="cyan", width=22)
    table.add_column("Skills Count", style="white", justify="right", width=15)
    table.add_column("Sample Skills", style="dim", width=48)

    sample_map = {
        "project_task_management": "asana, linear, ClickUp, notion, Jira, GTD Brain",
        "crm_sales": "HubSpot Sales, Sales Cloud, apollo, SalesEQ, Endgame",
        "legal_compliance": "commercial-legal, PandaDoc, GetSign, Casely, Freelaw",
        "hr_recruiting": "Greenhouse, comp-skills, Remote.com, ApplyArc, Joboostr",
        "customer_support": "SiteGPT, DocsBot, Quickchat AI, Landbot, SmartReply",
        "finance_accounting": "Intuit QuickBooks, NetSuite SuiteSkills, freee, Invoice Matcher",
        "project_planning": "AgileHero, lean-pm-skills, strategy-pack, Featurebase",
        "communication_meetings": "Meeting.ai, MeetNotes, Lark/Feishu, RingCentral",
        "ecommerce_operations": "Amazon Selling Partner, MakeBox for Etsy, PropertyMe",
        "monitoring_incident": "incident.io, Oncall, Rootly, paging-mcp, Uptimely",
        "productivity_tools": "notion-memory, MAI Second Brain, Briefcase, Kontext",
    }

    for domain_name, count in sorted(stats["domain_breakdown"].items(), key=lambda x: -x[1]):
        table.add_row(domain_name, str(count), sample_map.get(domain_name, ""))

    console.print(table)
    console.print(f"\n[dim]Use: kurt skill tickets --search <query>  or  kurt skill tickets --domain <name>[/dim]")
    console.print(f"[dim]Remaining {stats['total_skills'] - stats['domain_coverage']} skills are cross-domain/specialized[/dim]")


def list_notes_memory_skills(domain: str = None, search: str = None):
    """List or search notes & memory skills from Claude's marketplace"""
    if search:
        results = search_notes_memory_skills(search)
        console.print(f"\n[cyan]🔍 Notes & Memory skills matching '{search}':[/cyan]")
        for s in results[:20]:
            console.print(f"  [white]• {s}[/white]")
        if len(results) > 20:
            console.print(f"  [dim]... and {len(results) - 20} more[/dim]")
        console.print(f"\n[dim]Total matches: {len(results)}[/dim]")
        return

    if domain:
        skills = NOTES_MEMORY_DOMAINS.get(domain, [])
        console.print(f"\n[cyan]📓 Notes & Memory domain: {domain}[/cyan]")
        for s in skills:
            console.print(f"  [white]• {s}[/white]")
        console.print(f"\n[dim]Total in domain: {len(skills)}[/dim]")
        return

    # Show overview
    stats = get_notes_memory_stats()
    console.print(f"\n[bold cyan]📓 KURT Notes & Memory Skills Catalog[/bold cyan]")
    console.print(f"[dim]Sourced from Claude's marketplace — {stats['total_skills']:,} unique skills[/dim]\n")

    table = Table(box=box.ROUNDED, border_style="cyan")
    table.add_column("Domain", style="cyan", width=28)
    table.add_column("Skills Count", style="white", justify="right", width=15)
    table.add_column("Sample Skills", style="dim", width=42)

    sample_map = {
        "personal_knowledge_management": "Obsidian Notes, notion, Tana, GTD Brain, Reflect",
        "ai_memory_systems": "claude-memory, Cowork Memory, MAI Second Brain, AI Passport",
        "note_taking_apps": "Obsidian Notes, Reflect, Day One Journal, Jotbook",
        "learning_study": "ADHD Study Coach, Study Desk, Loopky flashcards, Finance Tutor",
        "writing_content": "Claude ghost writer, Online Writing, novel-studio, Prompt Coach",
        "productivity_context": "GTD Brain, AssistantLabs, workflow-toolkit, Busymate AI",
        "career_professional": "LinkedIn Career Intelligence, Career Compass, Founder OS",
        "social_community": "Social Media Skills, Ayrshare, Planable SMM, Famlore",
        "research_analysis": "Research Desk, Glean, Docbrain, Firmament, CompanyOS",
        "tools_integrations": "Google Drive → Markdown, Glean, Meeting Memory by Grain",
    }

    for domain_name, count in sorted(stats["domain_breakdown"].items(), key=lambda x: -x[1]):
        table.add_row(domain_name, str(count), sample_map.get(domain_name, ""))

    console.print(table)
    console.print(f"\n[dim]Use: kurt skill notes --search <query>  or  kurt skill notes --domain <name>[/dim]")
    console.print(f"[dim]Remaining {stats['total_skills'] - stats['domain_coverage']} skills are cross-domain/specialized[/dim]")


def list_apis_skills(domain: str = None, search: str = None):
    """List or search APIs skills from Claude's marketplace"""
    if search:
        results = search_apis_skills(search)
        console.print(f"\n[cyan]🔍 APIs skills matching '{search}':[/cyan]")
        for s in results[:20]:
            console.print(f"  [white]• {s}[/white]")
        if len(results) > 20:
            console.print(f"  [dim]... and {len(results) - 20} more[/dim]")
        console.print(f"\n[dim]Total matches: {len(results)}[/dim]")
        return

    if domain:
        skills = APIS_DOMAINS.get(domain, [])
        console.print(f"\n[cyan]🔌 APIs domain: {domain}[/cyan]")
        for s in skills:
            console.print(f"  [white]• {s}[/white]")
        console.print(f"\n[dim]Total in domain: {len(skills)}[/dim]")
        return

    # Show overview
    stats = get_apis_stats()
    console.print(f"\n[bold cyan]🔌 KURT APIs Skills Catalog[/bold cyan]")
    console.print(f"[dim]Sourced from Claude's marketplace — {stats['total_skills']:,} unique skills[/dim]\n")

    table = Table(box=box.ROUNDED, border_style="cyan")
    table.add_column("Domain", style="cyan", width=28)
    table.add_column("Skills Count", style="white", justify="right", width=15)
    table.add_column("Sample Skills", style="dim", width=42)

    sample_map = {
        "payment_billing": "Stripe, PayPal, Mercado Pago, Adapty, sumup",
        "cloud_infrastructure": "aws-core, Netlify, Cloudflare, terraform, neon",
        "developer_tools": "github, postman, Arcade, Checkly, 42crunch",
        "marketing_ads": "Windsor.ai, AdWhispr, AdMakeAI, SE Ranking, Supermetrics",
        "security_auth": "workos, Descope, crowdstrike, Fingerprint, Proofable",
        "data_analytics": "looker, Allium, diffbot, HasData, Qlik Agents",
        "communication_messaging": "slack, RingCentral, SignalWire, OneSignal, feishu",
        "commerce_ecommerce": "shopify-ai-toolkit, Shippo, Printago, Linkly, Clinch",
        "ai_ml_tools": "Plugin Management, claude-code-setup, lovable, ag2-tool-builder",
        "monitoring_devops": "incident.io, Checkly, groundcover, Treblle, kong-konnect",
        "finance_wealth": "Claude for Financial Advisors, Vanguard Advisor Tools, TradeOS AI",
        "enterprise_integrations": "Celigo, boomi-agentstudio, Supaflow, Form.io, Atlassian",
        "healthcare_bio": "Maven Bio, healthit-copilot, smarts.bio, open-targets",
        "legal_compliance": "cocounsel-legal, ip-legal, Civic, Proofable, Casely",
    }

    for domain_name, count in sorted(stats["domain_breakdown"].items(), key=lambda x: -x[1]):
        table.add_row(domain_name, str(count), sample_map.get(domain_name, ""))

    console.print(table)
    console.print(f"\n[dim]Use: kurt skill apis --search <query>  or  kurt skill apis --domain <name>[/dim]")
    console.print(f"[dim]Remaining {stats['total_skills'] - stats['domain_coverage']} skills are cross-domain/specialized[/dim]")


def list_reference_docs_skills(domain: str = None, search: str = None):
    """List or search Reference Docs skills from Claude's marketplace"""
    if search:
        results = search_reference_docs_skills(search)
        console.print(f"\n[cyan]🔍 Reference Docs skills matching '{search}':[/cyan]")
        for s in results[:20]:
            console.print(f"  [white]• {s}[/white]")
        if len(results) > 20:
            console.print(f"  [dim]... and {len(results) - 20} more[/dim]")
        console.print(f"\n[dim]Total matches: {len(results)}[/dim]")
        return

    if domain:
        skills = REFERENCE_DOCS_DOMAINS.get(domain, [])
        console.print(f"\n[cyan]📚 Reference Docs domain: {domain}[/cyan]")
        for s in skills:
            console.print(f"  [white]• {s}[/white]")
        console.print(f"\n[dim]Total in domain: {len(skills)}[/dim]")
        return

    # Show overview
    stats = get_reference_docs_stats()
    console.print(f"\n[bold cyan]📚 KURT Reference Docs Skills Catalog[/bold cyan]")
    console.print(f"[dim]Sourced from Claude's marketplace — {stats['total_skills']:,} unique skills[/dim]\n")

    table = Table(box=box.ROUNDED, border_style="cyan")
    table.add_column("Domain", style="cyan", width=28)
    table.add_column("Skills Count", style="white", justify="right", width=15)
    table.add_column("Sample Skills", style="dim", width=42)

    sample_map = {
        "legal_research": "litigation-legal, cocounsel-legal, Legalcode, LawDiver",
        "knowledge_documentation": "notion, GitBook, microsoft-docs, context7, diataxis",
        "market_research": "Research Desk, AIResearch, CompanyTrack, GovTribe",
        "medical_health": "pubmed, clinical-trials, fhir-format, medidata",
        "developer_reference": "duckdb-skills, DAX for agents, Ignite UI, dev-forge",
        "business_strategy": "strategy consultant, Sales Enablement Kit, Agile Product",
        "government_public_sector": "GovTribe, ArcKit USA, ArcKit EU, ArcKit UK NHS",
        "education_learning": "Oak National Academy, wikipedia, socratic-mentor, Citation Needed",
        "seo_marketing": "SE Ranking, SEOcrawl, Ubersuggest, Botify, Maquinable GEO",
        "finance_economics": "Fiscal.ai, FXMacroData, AIResearch, finsharpe, sp-global",
        "productivity_tools": "parallel, agent-context-kit, MMPM Cognitive OS, claude-war-room",
        "real_estate_property": "IQland Real Estate, Popety.io, Tenant Replies, Silicon Floor",
        "data_analytics": "duckdb-skills, holistics-reporting, ThoughtSpot, FactIQ",
        "niche_specialized": "重調クン, XiaoHongShu, GrappleMaps, MarineVerse, Pitwall F1",
    }

    for domain_name, count in sorted(stats["domain_breakdown"].items(), key=lambda x: -x[1]):
        table.add_row(domain_name, str(count), sample_map.get(domain_name, ""))

    console.print(table)
    console.print(f"\n[dim]Use: kurt skill refdocs --search <query>  or  kurt skill refdocs --domain <name>[/dim]")
    console.print(f"[dim]Remaining {stats['total_skills'] - stats['domain_coverage']} skills are cross-domain/specialized[/dim]")


def list_ai_models_agents_skills(domain: str = None, search: str = None):
    """List or search AI Models & Agents skills from Claude's marketplace"""
    if search:
        results = search_ai_models_agents_skills(search)
        console.print(f"\n[cyan]🔍 AI Models & Agents skills matching '{search}':[/cyan]")
        for s in results[:20]:
            console.print(f"  [white]• {s}[/white]")
        if len(results) > 20:
            console.print(f"  [dim]... and {len(results) - 20} more[/dim]")
        console.print(f"\n[dim]Total matches: {len(results)}[/dim]")
        return

    if domain:
        skills = AI_MODELS_AGENTS_DOMAINS.get(domain, [])
        console.print(f"\n[cyan]🤖 AI Models & Agents domain: {domain}[/cyan]")
        for s in skills:
            console.print(f"  [white]• {s}[/white]")
        console.print(f"\n[dim]Total in domain: {len(skills)}[/dim]")
        return

    # Show overview
    stats = get_ai_models_agents_stats()
    console.print(f"\n[bold cyan]🤖 KURT AI Models & Agents Skills Catalog[/bold cyan]")
    console.print(f"[dim]Sourced from Claude's marketplace — {stats['total_skills']:,} unique skills[/dim]\n")

    table = Table(box=box.ROUNDED, border_style="cyan")
    table.add_column("Domain", style="cyan", width=28)
    table.add_column("Skills Count", style="white", justify="right", width=15)
    table.add_column("Sample Skills", style="dim", width=42)

    sample_map = {
        "agent_frameworks": "Adaptive Agent, ag2-agent-guide, atomic-agents, pydantic-ai",
        "claude_tools": "Claude Code Survival Kit, skill-creator, megapowers, Superpowers",
        "prompt_engineering": "Prompt Brain, Prompt Optimizer, Prompt Tightener, PromptGuard",
        "llm_ops_monitoring": "Langfuse, MLflow, DeepEval, RAG Evaluation, Dynatrace",
        "cloud_ai_platforms": "aws-core, databricks, sagemaker-ai, neon, together-ai",
        "ai_governance_safety": "ai-governance-legal, Lexbeam EU AI, LORM, veritas-gate",
        "product_analytics": "posthog, amplitude, Mixpanel, Pendo Analytics, LaunchDarkly",
        "ml_research": "huggingface-skills, boltz, chembl, smarts.bio, TwelveLabs",
        "enterprise_ai": "Agentforce ADLC, harness, Celigo, boomi-agentstudio, JFrog",
        "chatbot_voice": "Synthflow, Quickchat AI, SiteGPT, YourGPT, Landbot",
        "developer_productivity": "docker-skills, githubclip, scriptify, Runway Dev, fleet",
        "knowledge_memory": "agent-memory, XMemo, Mnemoverse Memory, pinecone, Brainbase MCP",
        "startup_venture": "venture-capital-intelligence, POC Architect, solofounder, Incubator",
        "niche_specialized": "image-generation, AEO Brand Scan, consensus, AI YouTube OS",
    }

    for domain_name, count in sorted(stats["domain_breakdown"].items(), key=lambda x: -x[1]):
        table.add_row(domain_name, str(count), sample_map.get(domain_name, ""))

    console.print(table)
    console.print(f"\n[dim]Use: kurt skill aiagents --search <query>  or  kurt skill aiagents --domain <name>[/dim]")
    console.print(f"[dim]Remaining {stats['total_skills'] - stats['domain_coverage']} skills are cross-domain/specialized[/dim]")


def list_websites_skills(domain: str = None, search: str = None):
    """List or search Websites skills from Claude's marketplace"""
    if search:
        results = search_websites_skills(search)
        console.print(f"\n[cyan]🔍 Websites skills matching '{search}':[/cyan]")
        for s in results[:20]:
            console.print(f"  [white]• {s}[/white]")
        if len(results) > 20:
            console.print(f"  [dim]... and {len(results) - 20} more[/dim]")
        console.print(f"\n[dim]Total matches: {len(results)}[/dim]")
        return

    if domain:
        skills = WEBSITES_DOMAINS.get(domain, [])
        console.print(f"\n[cyan]🌐 Websites domain: {domain}[/cyan]")
        for s in skills:
            console.print(f"  [white]• {s}[/white]")
        console.print(f"\n[dim]Total in domain: {len(skills)}[/dim]")
        return

    # Show overview
    stats = get_websites_stats()
    console.print(f"\n[bold cyan]🌐 KURT Websites Skills Catalog[/bold cyan]")
    console.print(f"[dim]Sourced from Claude's marketplace — {stats['total_skills']:,} unique skills[/dim]\n")

    table = Table(box=box.ROUNDED, border_style="cyan")
    table.add_column("Domain", style="cyan", width=28)
    table.add_column("Skills Count", style="white", justify="right", width=15)
    table.add_column("Sample Skills", style="dim", width=42)

    sample_map = {
        "seo_tools": "Claude SEO, SE Ranking, Ubersuggest, Botify, AEOTester",
        "website_builders": "Shopify DevKit, Duda, wordpress-mcp, Brilliant Directories",
        "testing_qa": "playwright, BugBug, Checkly, Meticulous, Axe Accessibility",
        "analytics_tracking": "Leadfeeder, Fullstory, logrocket, Supermetrics, ViewsMax",
        "ecommerce": "Shopify App Builder, Magento 2, StoreConnect, Replo, Riskified",
        "content_marketing": "Blogr, Marky, Planable SMM, BAMF.ai, Genviral, Virlo",
        "ads_paid_media": "AdvisorPPC, Adspirer, Windsor.ai, Adzviser, Admaxxer",
        "web_scraping_data": "Apify, firecrawl, Bright Data, diffbot, HasData",
        "infrastructure_hosting": "Cloudflare, Netlify, Fastly, Porkbun, DomainKits",
        "chatbot_support": "SiteGPT, DocsBot, Quickchat AI, Landbot, FrontDesk Chat",
        "design_ux": "Superdesign, Mobbin, UXKIN, inhabited design, BOLD Studios",
        "portfolio_showcase": "Artist Portfolio, SuperCool Sites, StarTap, Brilliant Directories",
        "niche_specialized": "Talk to Anyone, Uniform, Flint, Cargo, Keytomic",
    }

    for domain_name, count in sorted(stats["domain_breakdown"].items(), key=lambda x: -x[1]):
        table.add_row(domain_name, str(count), sample_map.get(domain_name, ""))

    console.print(table)
    console.print(f"\n[dim]Use: kurt skill websites --search <query>  or  kurt skill websites --domain <name>[/dim]")
    console.print(f"[dim]Remaining {stats['total_skills'] - stats['domain_coverage']} skills are cross-domain/specialized[/dim]")


def list_servers_cloud_skills(domain: str = None, search: str = None):
    """List or search Servers & Cloud skills from Claude's marketplace"""
    if search:
        results = search_servers_cloud_skills(search)
        console.print(f"\n[cyan]🔍 Servers & Cloud skills matching '{search}':[/cyan]")
        for s in results[:20]:
            console.print(f"  [white]• {s}[/white]")
        if len(results) > 20:
            console.print(f"  [dim]... and {len(results) - 20} more[/dim]")
        console.print(f"\n[dim]Total matches: {len(results)}[/dim]")
        return

    if domain:
        skills = SERVERS_CLOUD_DOMAINS.get(domain, [])
        console.print(f"\n[cyan]☁️  Servers & Cloud domain: {domain}[/cyan]")
        for s in skills:
            console.print(f"  [white]• {s}[/white]")
        console.print(f"\n[dim]Total in domain: {len(skills)}[/dim]")
        return

    # Show overview
    stats = get_servers_cloud_stats()
    console.print(f"\n[bold cyan]☁️  KURT Servers & Cloud Skills Catalog[/bold cyan]")
    console.print(f"[dim]Sourced from Claude's marketplace — {stats['total_skills']:,} unique skills[/dim]\n")

    table = Table(box=box.ROUNDED, border_style="cyan")
    table.add_column("Domain", style="cyan", width=28)
    table.add_column("Skills Count", style="white", justify="right", width=15)
    table.add_column("Sample Skills", style="dim", width=42)

    sample_map = {
        "aws": "aws-core, aws-serverless, AWS Startup Advisor, deploy-on-aws",
        "gcp_azure": "google-cloud-storage, GCP DevKit, cloud-sql-postgresql, Azure DevKit",
        "kubernetes_containers": "docker-skills, Kubernetes Mastery, localstack, mirrord Agent Skills",
        "databases_cache": "supabase, neon, Upstash Redis, duckdb-skills, Qdrant",
        "monitoring_observability": "Grafana, Datadog, New Relic, Dynatrace, sentry",
        "security_devops": "ARMO Ctrl, Zscaler MCP Server, TrustPin, nightvision",
        "serverless_paas": "Netlify, railway, Render, Ship A Cloudflare Worker, Blaxel",
        "networking_cdn": "Cloudflare, Fastly, Ngrok Agent Skills, kong-konnect",
        "iac_automation": "terraform, Temporal, circle-skills, system-design-skills",
        "cloud_cost_finops": "Cloud FinOps by OptimNow, aws-cost-audit, Costory FinOps Agent",
        "data_platforms": "databricks, huggingface-skills, Elastic, OpenSearch Agent Skills",
        "developer_tools": "expo, lovable, appwrite, adb-mcp, Go Backend Skills",
        "enterprise_integrations": "Catalyst by Zoho, Celigo, Intuit Developer, Descope",
        "niche_specialized": "Unity, Unreal Engine, NVIDIA Skills, Meta VR, GeoAI Skills",
    }

    for domain_name, count in sorted(stats["domain_breakdown"].items(), key=lambda x: -x[1]):
        table.add_row(domain_name, str(count), sample_map.get(domain_name, ""))

    console.print(table)
    console.print(f"\n[dim]Use: kurt skill serverscloud --search <query>  or  kurt skill serverscloud --domain <name>[/dim]")
    console.print(f"[dim]Remaining {stats['total_skills'] - stats['domain_coverage']} skills are cross-domain/specialized[/dim]")


def list_contacts_leads_skills(domain: str = None, search: str = None):
    """List or search Contacts & Leads skills from Claude's marketplace"""
    if search:
        results = search_contacts_leads_skills(search)
        console.print(f"\n[cyan]🔍 Contacts & Leads skills matching '{search}':[/cyan]")
        for s in results[:20]:
            console.print(f"  [white]• {s}[/white]")
        if len(results) > 20:
            console.print(f"  [dim]... and {len(results) - 20} more[/dim]")
        console.print(f"\n[dim]Total matches: {len(results)}[/dim]")
        return

    if domain:
        skills = CONTACTS_LEADS_DOMAINS.get(domain, [])
        console.print(f"\n[cyan]📇 Contacts & Leads domain: {domain}[/cyan]")
        for s in skills:
            console.print(f"  [white]• {s}[/white]")
        console.print(f"\n[dim]Total in domain: {len(skills)}[/dim]")
        return

    # Show overview
    stats = get_contacts_leads_stats()
    console.print(f"\n[bold cyan]📇 KURT Contacts & Leads Skills Catalog[/bold cyan]")
    console.print(f"[dim]Sourced from Claude's marketplace — {stats['total_skills']:,} unique skills[/dim]\n")

    table = Table(box=box.ROUNDED, border_style="cyan")
    table.add_column("Domain", style="cyan", width=28)
    table.add_column("Skills Count", style="white", justify="right", width=15)
    table.add_column("Sample Skills", style="dim", width=42)

    sample_map = {
        "crm_sales": "HubSpot Sales, Sales Cloud, Wealthbox, Customer.io, Loops",
        "b2b_prospecting": "Hunter, apollo, RocketReach, VibeLeads, FullEnrich",
        "job_search_career": "Career Coaching, MagicInterview, GetEmployed, ApplyArc",
        "marketing_outreach": "ActiveCampaign, Mysocial Intelligence, Dash Social, Banger",
        "financial_advisors": "Claude for Financial Advisors, Zocks Advisor Intelligence",
        "hr_recruiting": "Greenhouse, Windmill HR, UKG Bryte, Lusha Talent Sourcing",
        "real_estate_property": "PropertyMe, cicada.guide, Funraise Taiwan Real Estate",
        "customer_success": "Customer Success: Churn and QBRs, SiteGPT, FrontDesk Chat",
        "data_enrichment": "HasData, diffbot, FullEnrich, Middesk, ClearBounce Email",
        "niche_specialized": "Leadfeeder, Revenue Grid, instagram, Voicenter API Skills",
    }

    for domain_name, count in sorted(stats["domain_breakdown"].items(), key=lambda x: -x[1]):
        table.add_row(domain_name, str(count), sample_map.get(domain_name, ""))

    console.print(table)
    console.print(f"\n[dim]Use: kurt skill contactsleads --search <query>  or  kurt skill contactsleads --domain <name>[/dim]")
    console.print(f"[dim]Remaining {stats['total_skills'] - stats['domain_coverage']} skills are cross-domain/specialized[/dim]")


def list_finance_skills(domain: str = None, search: str = None):
    """List or search Finance skills from Claude's marketplace"""
    if search:
        results = search_finance_skills(search)
        console.print(f"\n[cyan]🔍 Finance skills matching '{search}':[/cyan]")
        for s in results[:20]:
            console.print(f"  [white]• {s}[/white]")
        if len(results) > 20:
            console.print(f"  [dim]... and {len(results) - 20} more[/dim]")
        console.print(f"\n[dim]Total matches: {len(results)}[/dim]")
        return

    if domain:
        skills = FINANCE_DOMAINS.get(domain, [])
        console.print(f"\n[cyan]💰 Finance domain: {domain}[/cyan]")
        for s in skills:
            console.print(f"  [white]• {s}[/white]")
        console.print(f"\n[dim]Total in domain: {len(skills)}[/dim]")
        return

    # Show overview
    stats = get_finance_stats()
    console.print(f"\n[bold cyan]💰 KURT Finance Skills Catalog[/bold cyan]")
    console.print(f"[dim]Sourced from Claude's marketplace — {stats['total_skills']:,} unique skills[/dim]\n")

    table = Table(box=box.ROUNDED, border_style="cyan")
    table.add_column("Domain", style="cyan", width=28)
    table.add_column("Skills Count", style="white", justify="right", width=15)
    table.add_column("Sample Skills", style="dim", width=42)

    sample_map = {
        "investment_wealth": "BlackRock Advisor Center, Morningstar, lseg, sp-global",
        "accounting_erp": "NetSuite Finance Analyst, QuickBooks, freee, Datarails",
        "payments_fintech": "Stripe, PayPal, Mollie, Checkout Page, StreamPay",
        "trading_crypto": "TradingCalc, Blocksize Market Data, CryptoETF Flows",
        "risk_insurance": "RiskModels, pyvar-credit-risk, Swallow Insurance",
        "marketing_analytics": "Windsor.ai, AdCopilot, Supermetrics, Adspirer",
        "cloud_cost_ops": "Cloud FinOps by OptimNow, aws-cost-audit, DoiT",
        "niche_specialized": "cashflow, Small Business Operator, cofounders",
    }

    for domain_name, count in sorted(stats["domain_breakdown"].items(), key=lambda x: -x[1]):
        table.add_row(domain_name, str(count), sample_map.get(domain_name, ""))

    console.print(table)
    console.print(f"\n[dim]Use: kurt skill finance --search <query>  or  kurt skill finance --domain <name>[/dim]")
    console.print(f"[dim]Remaining {stats['total_skills'] - stats['domain_coverage']} skills are cross-domain/specialized[/dim]")


def list_databases_skills(domain: str = None, search: str = None):
    """List or search Databases skills from Claude's marketplace"""
    if search:
        results = search_databases_skills(search)
        console.print(f"\n[cyan]🔍 Databases skills matching '{search}':[/cyan]")
        for s in results[:20]:
            console.print(f"  [white]• {s}[/white]")
        if len(results) > 20:
            console.print(f"  [dim]... and {len(results) - 20} more[/dim]")
        console.print(f"\n[dim]Total matches: {len(results)}[/dim]")
        return

    if domain:
        skills = DATABASES_DOMAINS.get(domain, [])
        console.print(f"\n[cyan]🗄️  Databases domain: {domain}[/cyan]")
        for s in skills:
            console.print(f"  [white]• {s}[/white]")
        console.print(f"\n[dim]Total in domain: {len(skills)}[/dim]")
        return

    # Show overview
    stats = get_databases_stats()
    console.print(f"\n[bold cyan]🗄️  KURT Databases Skills Catalog[/bold cyan]")
    console.print(f"[dim]Sourced from Claude's marketplace — {stats['total_skills']:,} unique skills[/dim]\n")

    table = Table(box=box.ROUNDED, border_style="cyan")
    table.add_column("Domain", style="cyan", width=28)
    table.add_column("Skills Count", style="white", justify="right", width=15)
    table.add_column("Sample Skills", style="dim", width=42)

    sample_map = {
        "sql_relational": "supabase, neon, cloud-sql-postgresql, MongoDB, oracledb",
        "nosql_vector": "firebase, pinecone, Qdrant, zilliz, Azure Cosmos DB",
        "data_warehouse_analytics": "databricks, snowflake-cortex-code, bigquery, looker",
        "orm_migration": "Opinionated Prisma Skills, dbt-toolkit, db-migration-guard",
        "erp_enterprise": "NetSuite Finance Analyst, Odoo Tools, SAP HANA CLI",
        "cloud_data_platforms": "aws-core, sagemaker-ai, Elastic, OpenSearch Agent Skills",
        "test_seed_data": "Mock Data Hydrator, TDCv2, Stackhawk Data Seed, StringSpec",
        "niche_specialized": "Claude for Financial Advisors, Chronograph GP, fiftyone",
    }

    for domain_name, count in sorted(stats["domain_breakdown"].items(), key=lambda x: -x[1]):
        table.add_row(domain_name, str(count), sample_map.get(domain_name, ""))

    console.print(table)
    console.print(f"\n[dim]Use: kurt skill databases --search <query>  or  kurt skill databases --domain <name>[/dim]")
    console.print(f"[dim]Remaining {stats['total_skills'] - stats['domain_coverage']} skills are cross-domain/specialized[/dim]")


def remove_skill(skill_id: str):
    """Remove a custom skill"""
    init_skills()
    skill_file = SKILLS_DIR / f"{skill_id}.json"

    if not skill_file.exists():
        console.print(f"[red]❌ Skill not found: {skill_id}[/red]")
        return

    skill = get_skill(skill_id)
    if skill and skill.get("builtin"):
        console.print(f"[yellow]⚠️  Cannot remove built-in skill: {skill_id}[/yellow]")
        return

    skill_file.unlink()
    console.print(f"[green]✅ Skill removed: {skill_id}[/green]")


def create_skill_template(skill_id: str):
    """Create a new custom skill template"""
    template = {
        "id": skill_id,
        "name": f"My {skill_id.title()} Skill",
        "description": "Describe what this skill does",
        "version": "1.0.0",
        "author": "Daddy Tito",
        "system_prompt": f"You are an expert in {skill_id}. Add your instructions here.",
        "builtin": False
    }

    output_path = Path(f"{skill_id}.json")
    with open(output_path, "w") as f:
        json.dump(template, f, indent=2)

    console.print(f"[green]✅ Template created: {output_path}[/green]")
    console.print(f"[dim]Edit it then: kurt skill install {output_path}[/dim]")
