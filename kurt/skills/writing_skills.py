"""KURT Writing Skills Catalog — 29 skills from Claude's marketplace"""
from pathlib import Path
from typing import Optional

WRITING_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_writing.txt"

WRITING_DOMAINS = {
    "grammar_editing": ["Grammarly Skills", "Hemingway Editor", "ProWritingAid", "WordTune", "QuillBot"],
    "ai_copywriting": ["Jasper AI", "Copy.ai", "Writesonic", "Rytr"],
    "fiction_creative": ["Sudowrite", "NovelAI", "Squibler", "LivingWriter", "Dabble", "Plottr", "Campfire Writing", "World Anvil", "StoryShop"],
    "book_publishing": ["Reedsy", "Atticus", "Vellum"],
    "long_form": ["Scrivener Skills", "Ulysses Skills", "iA Writer", "Obsidian Writing", "Draft", "Milanote Writing", "Notion Writing", "Craft Writing"],
}

DOMAIN_PROMPTS = {
    "grammar_editing": "You are an expert in grammar, style, and editing tools. Help improve clarity, correct errors, rephrase sentences, and maintain consistent voice across writing.",
    "ai_copywriting": "You are an expert in AI copywriting tools. Help generate marketing copy, blog posts, ad creatives, and persuasive content using AI writing assistants.",
    "fiction_creative": "You are an expert in fiction and creative writing tools. Help develop plots, characters, worldbuilding, and narrative structure for stories and novels.",
    "book_publishing": "You are an expert in book formatting and self-publishing tools. Help authors format manuscripts for print and ebook, design interiors, and prepare for publishing.",
    "long_form": "You are an expert in long-form writing and PKM tools. Help structure large projects, manage research, and maintain writing focus using distraction-free tools.",
}

def load_all_skills() -> list[str]:
    if WRITING_SKILLS_FILE.exists():
        return [l.strip() for l in WRITING_SKILLS_FILE.read_text().splitlines() if l.strip()]
    return []

def search_skills(query: str) -> list[str]:
    return [s for s in load_all_skills() if query.lower() in s.lower()]

def get_domain_for_skill(skill_name: str) -> Optional[str]:
    sl = skill_name.lower()
    for domain, skills in WRITING_DOMAINS.items():
        if any(sl == s.lower() or sl in s.lower() for s in skills):
            return domain
    return None

def get_domain_prompt(domain: str) -> Optional[str]:
    return DOMAIN_PROMPTS.get(domain)

def get_skill_context(skill_name: str) -> str:
    domain = get_domain_for_skill(skill_name)
    base = DOMAIN_PROMPTS.get(domain, "") if domain else ""
    return f"You are an expert in {skill_name}.\n{base}\nApply the specific practices from '{skill_name}'."

def get_stats() -> dict:
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in WRITING_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(WRITING_DOMAINS), "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
