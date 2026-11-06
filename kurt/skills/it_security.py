"""
KURT IT & Security Skills Catalog
Lahat ng 55 IT & security skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

IT_SECURITY_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_it_security.txt"

IT_SECURITY_DOMAINS = {
    "cybersecurity": [
        "Reverse Engineering", "security-watchdog", "AgentAvow Trust",
        "maisecrets", "d0ma1n", "ARMO Ctrl", "crowdstrike-falcon-fusion",
        "CrowdSec Skill", "Sola Security", "protect-mcp", "Forge PII Scan",
        "VPNDetection", "ScanMalware", "TLS Radar", "Phished",
        "Open Voice Shield", "Varlock Skill", "Botscope",
    ],
    "governance_compliance": [
        "Ansvar Compliance Skills", "BigID", "drata-grc-skills",
        "MCP Conduct Register", "MO§ES™ Governance for Cowork",
        "sosa-governor", "Cataam Compliance", "ComplyOnSite",
        "SDSentry HazCom", "Sovrnti", "Verity", "norma-claude-skill",
    ],
    "sector_overlays": [
        "ArcKit UK NHS Clinical Safety Overlay", "ArcKit French Public Sector Overlay",
        "ArcKit USA Federal Civilian Overlay", "ArcKit UAE Federal Overlay",
        "ArcKit Australian Energy Sector Overlay", "ArcKit Netherlands Public Sector Overlay",
        "ADA PDF Compliance",
    ],
    "infrastructure_ops": [
        "Zscaler MCP Server", "amg-toolkit", "gen-sage", "Anomity",
        "Install Checkpoint", "Vet Before Install", "Healthcheckemail",
        "paging-mcp", "ShiftControl", "MORVS", "InternetData",
        "Internet Tools",
    ],
    "niche_specialized": [
        "Above Security", "In Case Of Crisis", "Tuteliq", "Eon",
        "SIEM Lab Coach", "Skill Discovery",
    ],
}

DOMAIN_PROMPTS = {
    "cybersecurity": """You are an expert in cybersecurity.
Your expertise covers:
- Threat detection and incident response
- Vulnerability assessment and penetration testing
- Malware analysis and reverse engineering
- Secret and credential security
- MCP and AI agent security
- Network security and TLS/SSL
- PII scanning and data protection
- Phishing detection and prevention
Defend systems against evolving cyber threats.""",

    "governance_compliance": """You are an expert in IT governance and compliance.
Your expertise covers:
- GRC frameworks (SOC2, ISO 27001, NIST)
- Data privacy regulation (GDPR, DPDP, CCPA)
- Security policy development and enforcement
- Compliance automation and evidence collection
- Risk assessment and management
- Audit preparation and documentation
- Hazardous material communication compliance
- AI governance and responsible use policies
Build compliant, well-governed IT organizations.""",

    "sector_overlays": """You are an expert in sector-specific IT and security requirements.
Your expertise covers:
- Healthcare IT security (NHS Clinical Safety, HIPAA)
- Government and federal IT standards (FedRAMP, FISMA)
- Energy sector security requirements
- EU regulatory IT compliance
- UAE federal digital governance
- Accessibility compliance (ADA, WCAG)
- Public sector IT procurement and governance
Navigate complex sector-specific security requirements.""",

    "infrastructure_ops": """You are an expert in IT infrastructure and operations.
Your expertise covers:
- Network security and zero-trust architecture
- Endpoint detection and response
- IT asset management and inventory
- Incident alerting and on-call management
- System health monitoring
- Change management and deployment safety
- DNS and internet infrastructure security
- Operations automation and runbooks
Keep infrastructure secure and operational.""",

    "niche_specialized": """You are a specialist in niche IT security tools.
Your expertise covers specialized solutions for:
- Crisis communication and incident management
- Security training and awareness
- Specialized monitoring and detection
- Emerging security technology platforms
Apply targeted expertise to unique security challenges.""",
}


def load_all_skills() -> list[str]:
    if IT_SECURITY_SKILLS_FILE.exists():
        return [line.strip() for line in IT_SECURITY_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    all_skills = load_all_skills()
    return [s for s in all_skills if query.lower() in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    skill_lower = skill_name.lower()
    for domain, skills in IT_SECURITY_DOMAINS.items():
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
Apply IT security best practices:
- Apply defense-in-depth security principles
- Follow zero-trust architecture principles
- Document all security findings and remediations
- Prioritize risks by likelihood and impact
- Automate security controls where possible
- Conduct regular security assessments
- Maintain incident response playbooks
- Train and educate teams on security awareness"""


def get_stats() -> dict:
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in IT_SECURITY_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(IT_SECURITY_DOMAINS),
            "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
