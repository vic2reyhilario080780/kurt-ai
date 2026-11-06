"""
KURT Legal Skills Catalog
Lahat ng 74 Legal skills mula sa Claude's marketplace
Organized by domain para sa smart routing at lookup
"""

from pathlib import Path
from typing import Optional

LEGAL_SKILLS_FILE = Path(__file__).parent.parent.parent / "skills_legal.txt"

LEGAL_DOMAINS = {
    "enterprise_legal": [
        "GC AI", "commercial-legal", "ai-governance-legal", "litigation-legal",
        "corporate-legal", "legal-builder-hub", "privacy-legal", "employment-legal",
        "cocounsel-legal", "ip-legal", "legal-clinic", "product-legal",
        "regulatory-legal", "verification-foundation",
    ],
    "contracts_compliance": [
        "AAA ClauseBuilder", "GDPRGard Compliance Skills", "Contracko",
        "Data Protection", "Compliance ES", "Cite2FN", "Kube by Kuberno",
        "ALCBar AI Practice Risk Check", "Lexbeam EU AI Governance",
        "Sammati DPDP Readiness", "Normlotse", "ShareSign",
    ],
    "regional_eu": [
        "ArcKit Austrian Overlay", "ArcKit EU Overlay", "Litigación Civil España",
        "Litigación Contencioso-Administrativa España", "Litigación Laboral España",
        "Litigación Penal España", "Contratos Civiles y Mercantiles",
        "Contratos Laborales y Asesoría Empresarial", "Extranjería España",
        "Codigo Civil Formulacion Juridica", "Polskie Prawo",
    ],
    "regional_india": [
        "indian-contracts-drafting", "indian-hc-drafting", "indian-consumer-drafting",
        "indian-company-drafting", "indian-rent-control-drafting", "indian-ip-drafting",
        "indian-family-drafting", "indian-property-drafting", "indian-labour-drafting",
        "indian-mact-drafting",
    ],
    "litigation_courts": [
        "district-court-drafting", "supreme-court-drafting", "Demand from the File",
        "Docket Tracker", "OpenCase", "LienDeadline", "Freelaw Studio",
        "Ragjur", "重調クン (Jucho-kun)", "realLaw AI",
        "Reclamos de consumo Perú",
    ],
    "ip_patents": [
        "FluidityIQ Patent Intelligence", "Competition Checker", "LawDiver",
        "Legalcode", "CREparser Lease Abstraction", "cortellis",
        "vectorgov", "Menas", "Referent",
    ],
    "niche_specialized": [
        "legalzoom", "LVAI Pro", "Propper", "regai — Vietnamese Legal Consultant",
        "IFG", "Mibba", "Seudonimizador Clinico Juridico",
    ],
}

DOMAIN_PROMPTS = {
    "enterprise_legal": """You are an expert enterprise legal counsel.
Your expertise covers:
- Contract review and negotiation strategy
- Corporate governance and compliance
- Employment law and HR legal matters
- Intellectual property strategy
- Privacy and data protection compliance
- Product liability and regulatory risk
- AI governance and responsible AI use
- Litigation management and strategy
Deliver strategic legal guidance for complex organizations.""",

    "contracts_compliance": """You are an expert in contracts and compliance.
Your expertise covers:
- Contract drafting and clause negotiation
- GDPR and privacy regulation compliance
- AI Act and emerging tech regulation
- Data protection impact assessments
- Regulatory compliance frameworks
- Contract lifecycle management
- Risk assessment and mitigation
- Compliance program design
Build robust, compliant contractual frameworks.""",

    "regional_eu": """You are an expert in European legal systems.
Your expertise covers:
- Spanish civil, labor, criminal, and administrative litigation
- EU regulatory frameworks and overlays
- Polish, Austrian, and regional legal systems
- Contract drafting under civil law traditions
- Immigration and residency law
- EU AI governance requirements
- Cross-border legal harmonization
Navigate European legal complexity with expertise.""",

    "regional_india": """You are an expert in Indian law and legal drafting.
Your expertise covers:
- Indian contract, company, and property law
- High Court and consumer court procedures
- IP, family, labor, and rent control law
- Motor accident claim tribunals (MACT)
- Indian regulatory and compliance frameworks
- Judicial drafting for Indian courts
Deliver precise Indian legal expertise.""",

    "litigation_courts": """You are an expert in litigation and court proceedings.
Your expertise covers:
- Court document drafting and filing
- Demand letters and pre-litigation strategy
- Docket management and deadline tracking
- Case analysis and legal research
- Deposition and discovery preparation
- Settlement negotiation support
- Appellate practice
Master litigation workflows from filing to judgment.""",

    "ip_patents": """You are an expert in intellectual property law.
Your expertise covers:
- Patent search, analysis, and prosecution
- Trademark clearance and registration
- Copyright protection and licensing
- Trade secret protection
- IP portfolio management
- Competitive intelligence through patents
- IP due diligence in M&A
- Licensing and monetization strategy
Protect and leverage intellectual property assets.""",

    "niche_specialized": """You are a specialist in niche legal tools.
Your expertise covers specialized solutions for:
- Online legal services and consumer law
- Regional and language-specific legal systems
- Clinical and medical legal documentation
- Government and public sector legal needs
- Specialized court and tribunal drafting
Apply targeted legal expertise to unique challenges.""",
}


def load_all_skills() -> list[str]:
    if LEGAL_SKILLS_FILE.exists():
        return [line.strip() for line in LEGAL_SKILLS_FILE.read_text().splitlines() if line.strip()]
    return []


def search_skills(query: str) -> list[str]:
    all_skills = load_all_skills()
    return [s for s in all_skills if query.lower() in s.lower()]


def get_domain_for_skill(skill_name: str) -> Optional[str]:
    skill_lower = skill_name.lower()
    for domain, skills in LEGAL_DOMAINS.items():
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
Apply legal best practices:
- Research applicable law thoroughly before advising
- Identify and clearly communicate legal risks
- Draft precise, unambiguous legal language
- Consider jurisdiction-specific requirements
- Maintain client confidentiality and professional ethics
- Document all legal reasoning and sources
- Advise on both legal rights and practical outcomes
- Stay current with regulatory changes"""


def get_stats() -> dict:
    all_skills = load_all_skills()
    domain_counts = {d: len(s) for d, s in LEGAL_DOMAINS.items()}
    return {"total_skills": len(all_skills), "domains": len(LEGAL_DOMAINS),
            "domain_coverage": sum(domain_counts.values()), "domain_breakdown": domain_counts}
