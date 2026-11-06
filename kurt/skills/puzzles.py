"""KURT Puzzles Skills Catalog — 25 skills from Claude's marketplace"""
from pathlib import Path
from typing import Optional

PUZZLES_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_puzzles.txt"

PUZZLES_DOMAINS = {
    "word_puzzles": ["Crossword Compiler", "CrosswordNexus", "Puzzle Baron", "Puzzlemaker"],
    "math_logic": ["Numerade Puzzles", "Brilliant.org Puzzles", "Art of Problem Solving", "Project Euler", "Nerdle"],
    "coding_challenges": ["Advent of Code", "LeetCode Puzzles", "HackerRank Puzzles", "Codewars", "Exercism", "Kata.ai", "Pramp", "Codingame", "CheckiO", "Edabit", "CodinGame"],
    "web_puzzles": ["CSSBattle", "FlexboxFroggy", "GridGarden", "CSS Diner", "VimAdventures", "Shortcut Foo"],
    "word_games": ["Wordle Skills", "Quordle", "Wordiply", "Globle"],
}

DOMAIN_PROMPTS = {
    "word_puzzles": "You are an expert in word puzzles and crosswords. Help create, solve, and explain word puzzles, cryptics, and crossword construction techniques.",
    "math_logic": "You are an expert in mathematical puzzles and logic problems. Help with number theory, combinatorics, and structured problem-solving approaches.",
    "coding_challenges": "You are an expert in competitive programming and coding challenges. Help solve algorithmic problems, optimize solutions, and explain CS concepts through puzzles.",
    "web_puzzles": "You are an expert in web development learning games. Help users learn CSS, HTML, and editor shortcuts through interactive puzzle-based platforms.",
    "word_games": "You are an expert in daily word games. Help with solving strategies, pattern recognition, and vocabulary building through games like Wordle.",
}

def load_all_skills() -> list[str]:
    if PUZZLES_SKILLS_FILE.exists():
        return [l.strip() for l in PUZZLES_SKILLS_FILE.read_text().splitlines() if l.strip()]
    return []

def search_skills(query: str) -> list[str]:
    return [s for s in load_all_skills() if query.lower() in s.lower()]

def get_domain_for_skill(skill_name: str) -> Optional[str]:
    sl = skill_name.lower()
    for domain, skills in PUZZLES_DOMAINS.items():
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
    domain_counts = {d: len(s) for d, s in PUZZLES_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(PUZZLES_DOMAINS), "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
