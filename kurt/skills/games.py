"""KURT Games Skills Catalog — 14 skills from Claude's marketplace"""
from pathlib import Path
from typing import Optional

GAMES_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_games.txt"

GAMES_DOMAINS = {
    "chess": ["Chess.com Skills", "Lichess", "Chess Tempo", "Chessable"],
    "board_games": ["Go Quest", "OGS (Online Go Server)", "Backgammon Galaxy"],
    "word_games": ["Scrabble GO", "Words With Friends", "Wordle Skills", "Quordle", "Nerdle", "Wordiply", "Globle"],
}

DOMAIN_PROMPTS = {
    "chess": "You are an expert chess coach. Help players improve their opening preparation, tactical patterns, endgame technique, and strategic understanding.",
    "board_games": "You are an expert in classic board games. Help players improve at Go, Backgammon, and other strategy games through pattern recognition and strategic concepts.",
    "word_games": "You are an expert in word games. Help with vocabulary, strategy, and solving techniques for Wordle, Scrabble, and similar word-based games.",
}

def load_all_skills() -> list[str]:
    if GAMES_SKILLS_FILE.exists():
        return [l.strip() for l in GAMES_SKILLS_FILE.read_text().splitlines() if l.strip()]
    return []

def search_skills(query: str) -> list[str]:
    return [s for s in load_all_skills() if query.lower() in s.lower()]

def get_domain_for_skill(skill_name: str) -> Optional[str]:
    sl = skill_name.lower()
    for domain, skills in GAMES_DOMAINS.items():
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
    domain_counts = {d: len(s) for d, s in GAMES_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(GAMES_DOMAINS), "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
