"""
KURT Skills Manager - Install, list, remove skills
Skills = domain knowledge na nag-ggguide sa AI behavior

Includes 1,203 Engineering skills from Claude's marketplace.
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
