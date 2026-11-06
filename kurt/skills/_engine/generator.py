"""
KURT Skill Generator Engine
Programmatically generate skill modules for any profession/category.

Usage:
    from kurt.skills._engine.generator import generate_category
    generate_category("healthcare", domains, output_dir="kurt/skills/healthcare/")
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────
# Data models
# ─────────────────────────────────────────

@dataclass
class SkillDefinition:
    """Single skill entry"""
    name: str                        # e.g. "product-listing-optimizer"
    display: str                     # Human label
    description: str                 # One-liner: what this skill does
    domain: str                      # Which domain group it belongs to
    system_prompt: str               # The actual AI instruction for this skill
    tags: list[str] = field(default_factory=list)
    example_prompts: list[str] = field(default_factory=list)


@dataclass
class SkillDomain:
    """Group of related skills"""
    name: str                        # e.g. "product_listing"
    label: str                       # Human label
    description: str                 # Domain description
    skills: list[SkillDefinition] = field(default_factory=list)
    base_prompt: str = ""            # Shared context injected before each skill's prompt


# ─────────────────────────────────────────
# Code generation
# ─────────────────────────────────────────

def _escape(s: str) -> str:
    """Escape triple-quoted strings"""
    return s.replace('\\', '\\\\').replace('"""', '\\"\\"\\"')


def build_skill_module(
    category_name: str,
    category_label: str,
    domains: list[SkillDomain],
    module_docstring: str = "",
) -> str:
    """
    Generate a complete Python skill module as a string.
    Compatible with the existing KURT skill system pattern.
    """

    all_skills = []
    for domain in domains:
        for skill in domain.skills:
            all_skills.append((domain.name, skill))

    domains_dict_lines = []
    for domain in domains:
        skill_names = [f'"{s.name}"' for s in domain.skills]
        domains_dict_lines.append(
            f'    "{domain.name}": [{", ".join(skill_names)}],'
        )

    domain_prompts_lines = []
    for domain in domains:
        escaped = _escape(domain.base_prompt or domain.description)
        domain_prompts_lines.append(f'    "{domain.name}": """{escaped}""",')

    skills_data_lines = []
    for domain in domains:
        for skill in domain.skills:
            sp_escaped = _escape(skill.system_prompt)
            tags_repr = repr(skill.tags)
            examples_repr = repr(skill.example_prompts)
            skills_data_lines.append(
                f'    "{skill.name}": {{\n'
                f'        "display": {repr(skill.display)},\n'
                f'        "description": {repr(skill.description)},\n'
                f'        "domain": {repr(skill.domain)},\n'
                f'        "tags": {tags_repr},\n'
                f'        "example_prompts": {examples_repr},\n'
                f'        "system_prompt": """{sp_escaped}""",\n'
                f'    }},'
            )

    module_doc = module_docstring or f"KURT {category_label} Skills Catalog"

    code = f'''"""
{_escape(module_doc)}
"""

from typing import Optional


# ─────────────────────────────────────────────────────────────
# Domain → Skills mapping
# ─────────────────────────────────────────────────────────────

DOMAINS = {{
{chr(10).join(domains_dict_lines)}
}}

DOMAIN_PROMPTS = {{
{chr(10).join(domain_prompts_lines)}
}}

# ─────────────────────────────────────────────────────────────
# Full skill registry
# ─────────────────────────────────────────────────────────────

SKILLS = {{
{chr(10).join(skills_data_lines)}
}}


# ─────────────────────────────────────────────────────────────
# Public API (matches KURT skill system pattern)
# ─────────────────────────────────────────────────────────────

def load_all_skills() -> list[dict]:
    """Return all skills as a list of dicts"""
    return [
        {{"name": name, **data}}
        for name, data in SKILLS.items()
    ]


def search_skills(query: str) -> list[dict]:
    """Search skills by name, description, or tags"""
    q = query.lower()
    results = []
    for name, data in SKILLS.items():
        if (q in name.lower()
                or q in data["description"].lower()
                or q in data["display"].lower()
                or any(q in t.lower() for t in data["tags"])):
            results.append({{"name": name, **data}})
    return results


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    """Return the domain name for a skill"""
    if skill_name in SKILLS:
        return SKILLS[skill_name]["domain"]
    # Fuzzy match
    skill_lower = skill_name.lower()
    for name, data in SKILLS.items():
        if skill_lower in name.lower():
            return data["domain"]
    return None


def get_skill_context(skill_name: str) -> str:
    """Return full system prompt for a skill"""
    if skill_name in SKILLS:
        data = SKILLS[skill_name]
        domain = data["domain"]
        base = DOMAIN_PROMPTS.get(domain, "")
        return f"{{base}}\\n\\n{{data[\'system_prompt\']}}" if base else data["system_prompt"]
    # Fuzzy match
    skill_lower = skill_name.lower()
    for name, data in SKILLS.items():
        if skill_lower in name.lower():
            domain = data["domain"]
            base = DOMAIN_PROMPTS.get(domain, "")
            return f"{{base}}\\n\\n{{data[\'system_prompt\']}}" if base else data["system_prompt"]
    return f"You are an expert in {{skill_name}}. Apply your expertise to help the user."


def get_stats() -> dict:
    """Return stats about this skill category"""
    domain_counts = {{d: len(skills) for d, skills in DOMAINS.items()}}
    return {{
        "total_skills": len(SKILLS),
        "domains": len(DOMAINS),
        "domain_coverage": sum(domain_counts.values()),
        "domain_breakdown": domain_counts,
    }}


def list_domains() -> list[dict]:
    """Return domain summaries"""
    return [
        {{
            "name": domain,
            "skills": skills,
            "count": len(skills),
            "description": DOMAIN_PROMPTS.get(domain, "")[:200],
        }}
        for domain, skills in DOMAINS.items()
    ]
'''
    return code


def generate_category(
    category_name: str,
    category_label: str,
    domains: list[SkillDomain],
    output_dir: Optional[str] = None,
    module_docstring: str = "",
) -> str:
    """
    Generate and optionally write a skill module for a category.

    Returns the generated source code.
    If output_dir is given, writes to output_dir/__init__.py
    """
    code = build_skill_module(category_name, category_label, domains, module_docstring)

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        init_path = out / "__init__.py"
        init_path.write_text(code)
        print(f"✅ Written: {init_path}  ({len(domains)} domains, "
              f"{sum(len(d.skills) for d in domains)} skills)")

    return code
