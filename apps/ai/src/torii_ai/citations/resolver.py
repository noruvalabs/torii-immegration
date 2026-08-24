"""Specific official source citation resolver for AI and OPS scraper.

Ensures each eligibility finding, checklist document, and question has its own
distinct official government authority, statutory regulation title, and official URL.
"""

from __future__ import annotations

from typing import Any

_SPECIFIC_CITATIONS: dict[str, dict[str, dict[str, str]]] = {
    "JP": {
        "passport": {
            "authority": "Ministry of Foreign Affairs of Japan (MOFA)",
            "title": "Statutory Passport & Identity Verification Standards (旅券・身元確認要領)",
            "url": "https://www.mofa.go.jp/j_info/visit/visa/index.html",
        },
        "photo": {
            "authority": "Immigration Services Agency of Japan (ISA)",
            "title": "Photograph Requirements for Residence & Visa Applications (写真の規格)",
            "url": "https://www.moj.go.jp/isa/applications/procedures/photo_info.html",
        },
        "residence_card": {
            "authority": "Immigration Services Agency of Japan (ISA)",
            "title": "Residence Card Registry & Continuity Verification (在留カード等確認)",
            "url": "https://www.isa.go.jp/en/applications/guide/residencecard.html",
        },
        "tax": {
            "authority": "National Tax Agency of Japan (国税庁) & Municipal Tax Law",
            "title": "Individual Resident Tax (住民税) & Municipal Tax Compliance Guidelines",
            "url": "https://www.nta.go.jp/taxes/tetsuzuki/shinsei/annai/hotei/23100051.htm",
        },
        "pension": {
            "authority": "Japan Pension Service (日本年金機構) & MHLW",
            "title": "Employees' Pension & National Health Insurance Contribution Requirements",
            "url": "https://www.nenkin.go.jp/international/index.html",
        },
        "work": {
            "authority": "Immigration Services Agency of Japan (ISA)",
            "title": "Status of Residence: Engineer / Specialist in Humanities / International Services (技術・人文知識・国際業務)",
            "url": "https://www.isa.go.jp/en/applications/procedures/nyuukokukanri07_00093.html",
        },
        "student": {
            "authority": "Immigration Services Agency of Japan (ISA)",
            "title": "Status of Residence: Student (留学資格基準・在留資格認定)",
            "url": "https://www.isa.go.jp/en/applications/procedures/zairyu_shikaku10.html",
        },
        "tourist": {
            "authority": "Ministry of Foreign Affairs of Japan (MOFA)",
            "title": "Temporary Visitor (Tourism/Visit) Visa Application Procedures (短期滞在ビザ基準)",
            "url": "https://www.mofa.go.jp/j_info/visit/visa/short/novisa.html",
        },
        "funds": {
            "authority": "Immigration Services Agency of Japan (ISA)",
            "title": "Verification Standards for Living Expenses & Financial Capacity (経費支弁能力審査基準)",
            "url": "https://www.isa.go.jp/en/applications/procedures/zairyu_shikaku10.html",
        },
        "criminal": {
            "authority": "Immigration Control and Refugee Recognition Act (Article 5 & 24)",
            "title": "Statutory Grounds for Refusal of Landing & Deportation Review (上陸拒否・退去強制事由審査)",
            "url": "https://www.isa.go.jp/en/applications/procedures/index.html",
        },
        "company_registry": {
            "authority": "Ministry of Justice Legal Affairs Bureau (法務省民事局)",
            "title": "Commercial and Corporate Registration Certification (商業・法人登記)",
            "url": "https://www.moj.go.jp/MINJI/minji06.html",
        },
    },
    "US": {
        "passport": {
            "authority": "U.S. Department of State (Bureau of Consular Affairs)",
            "title": "Form DS-160 Online Nonimmigrant Visa Application & Passport Standards",
            "url": "https://travel.state.gov/content/travel/en/us-visas/visa-information-resources/forms/ds-160-online-nonimmigrant-visa-application.html",
        },
        "work": {
            "authority": "U.S. Citizenship and Immigration Services (USCIS)",
            "title": "H-1B Specialty Occupations & Form I-129 Nonimmigrant Worker Regulations",
            "url": "https://www.uscis.gov/working-in-the-united-states/temporary-workers/h-1b-specialty-occupations",
        },
        "lca": {
            "authority": "U.S. Department of Labor (Employment & Training Administration)",
            "title": "Office of Foreign Labor Certification: Form ETA-9035 LCA Compliance",
            "url": "https://www.dol.gov/agencies/eta/foreign-labor/programs/h-1b",
        },
        "student": {
            "authority": "U.S. Department of State & SEVP",
            "title": "Student Visa (F-1/M-1) & Form I-20 Eligibility Certificate Guidelines",
            "url": "https://travel.state.gov/content/travel/en/us-visas/study/student-visa.html",
        },
        "tourist": {
            "authority": "U.S. Department of State (Bureau of Consular Affairs)",
            "title": "Visitor Visa (B-1/B-2) & INA Section 214(b) Nonimmigrant Intent",
            "url": "https://travel.state.gov/content/travel/en/us-visas/tourism-visit/visitor.html",
        },
        "funds": {
            "authority": "U.S. Citizenship and Immigration Services (USCIS)",
            "title": "Form I-134 Declaration of Financial Support Requirements",
            "url": "https://www.uscis.gov/i-134",
        },
        "criminal": {
            "authority": "Immigration and Nationality Act (INA Section 212(a))",
            "title": "Statutory Inadmissibility Grounds under 8 U.S.C. 1182 (INA § 212)",
            "url": "https://www.uscis.gov/laws-and-policy/legislation/immigration-and-nationality-act",
        },
    },
    "UK": {
        "passport": {
            "authority": "UK Visas and Immigration (UKVI / Home Office)",
            "title": "Identity and Passport Verification Guidelines",
            "url": "https://www.gov.uk/government/publications/biometric-information-enrolment-guidance",
        },
        "work": {
            "authority": "UK Visas and Immigration (UKVI / Home Office)",
            "title": "Skilled Worker Visa: Overview, CoS & Eligibility Requirements",
            "url": "https://www.gov.uk/skilled-worker-visa",
        },
        "sponsor": {
            "authority": "UK Visas and Immigration (UKVI / Home Office)",
            "title": "UK Visa Sponsorship for Employers: Eligibility and Verification",
            "url": "https://www.gov.uk/uk-visa-sponsorship-employers",
        },
        "salary": {
            "authority": "UK Visas and Immigration (UKVI / Home Office)",
            "title": "Skilled Worker Visa: Eligible Occupations, Going Rates & Salary Thresholds",
            "url": "https://www.gov.uk/government/publications/skilled-worker-visa-going-rates-for-eligible-occupations",
        },
        "student": {
            "authority": "UK Visas and Immigration (UKVI / Home Office)",
            "title": "Student Visa: Confirmation of Acceptance for Studies (CAS) Requirements",
            "url": "https://www.gov.uk/student-visa",
        },
        "tourist": {
            "authority": "UK Visas and Immigration (UKVI / Home Office)",
            "title": "Standard Visitor Visa: Eligibility, Purpose & Permitted Activities",
            "url": "https://www.gov.uk/standard-visitor",
        },
        "funds": {
            "authority": "UK Visas and Immigration (UKVI / Home Office)",
            "title": "Financial Evidence for Sponsored Routes & 28-day Maintenance Rule",
            "url": "https://www.gov.uk/guidance/financial-evidence-for-sponsored-or-endorsed-work-routes",
        },
        "english": {
            "authority": "UK Visas and Immigration (UKVI / Home Office)",
            "title": "Knowledge of English: Approved Secure English Language Tests (SELT)",
            "url": "https://www.gov.uk/skilled-worker-visa/knowledge-of-english",
        },
        "tb": {
            "authority": "UK Visas and Immigration (UKVI / Home Office)",
            "title": "Tuberculosis (TB) Testing for UK Visa Applicants",
            "url": "https://www.gov.uk/tb-test-visa",
        },
        "criminal": {
            "authority": "UK Immigration Rules (Part 9: Grounds for Refusal)",
            "title": "Immigration Rules Part 9: General Grounds for Refusal & Suitability",
            "url": "https://www.gov.uk/guidance/immigration-rules/immigration-rules-part-9-grounds-for-refusal",
        },
    },
}

_SPECIFIC_CITATIONS["GB"] = _SPECIFIC_CITATIONS["UK"]


def resolve_official_citation(
    jurisdiction_code: str,
    visa_category: str = "",
    item_key_or_code: str = "",
    existing_citation: dict[str, Any] | None = None,
    default_version: str = "2026-04",
) -> dict[str, Any]:
    jur = (jurisdiction_code or "JP").upper()
    cat = (visa_category or "").lower()
    key = (item_key_or_code or "").lower()

    if existing_citation and isinstance(existing_citation, dict):
        url = existing_citation.get("url")
        auth = existing_citation.get("authority")
        title = existing_citation.get("title")
        if url and auth and title:
            is_generic_jp = (
                jur == "JP"
                and str(url).endswith("16-3.html")
                and (
                    "tax" in key
                    or "pension" in key
                    or "passport" in key
                    or "student" in key
                    or "tourist" in key
                    or "criminal" in key
                    or "registry" in key
                )
            )
            is_generic_us = (
                jur == "US"
                and "visitor.html" in str(url)
                and ("h1b" in key or "work" in key or "student" in key or "f1" in key)
            )
            if not is_generic_jp and not is_generic_us:
                return {
                    "authority": auth,
                    "title": title,
                    "url": url,
                    "source_version": existing_citation.get("source_version") or default_version,
                }

    jur_map = _SPECIFIC_CITATIONS.get(jur, _SPECIFIC_CITATIONS["JP"])

    topic = "passport"
    if "tax" in key or "withholding" in key or "resident_tax" in key:
        topic = "tax"
    elif "pension" in key or "insurance" in key or "health" in key:
        topic = "pension"
    elif "residence_card" in key or "years_in_japan" in key:
        topic = "residence_card"
    elif "corporate" in key or "registry" in key or "registration" in key:
        topic = "company_registry" if jur == "JP" else "sponsor"
    elif "photo" in key or "picture" in key:
        topic = "photo"
    elif "lca" in key or "labor" in key or "prevailing_wage" in key:
        topic = "lca" if jur == "US" else "work"
    elif "cos" in key or "sponsor" in key or "employer_name" in key:
        topic = "sponsor" if jur in ("UK", "GB") else "work"
    elif "salary" in key or "soc" in key or "rate" in key:
        topic = "salary" if jur in ("UK", "GB") else "work"
    elif "english" in key or "selt" in key or "language" in key:
        topic = "english"
    elif "tb" in key or "tuberculosis" in key:
        topic = "tb"
    elif "student" in key or "cas" in key or "i20" in key or "school" in key or "university" in key or cat == "student":
        topic = "student"
    elif "tourist" in key or "visitor" in key or "itinerary" in key or cat in ("tourist", "b1b2", "visitor"):
        topic = "tourist"
    elif "fund" in key or "bank" in key or "saving" in key or "financial" in key or "maintenance" in key:
        topic = "funds"
    elif "criminal" in key or "violation" in key or "overstay" in key or "deportation" in key or "refusal" in key:
        topic = "criminal"
    elif "work" in key or "job" in key or "h1b" in key or "employed" in key or cat in ("work", "h1b"):
        topic = "work"

    selected = jur_map.get(topic) or jur_map.get("work") or jur_map.get("passport") or {}
    return {
        "authority": selected.get("authority", f"{jur} Immigration Authority"),
        "title": selected.get("title", "Official Immigration Regulation"),
        "url": selected.get("url", f"https://www.gov.{jur.lower()}/visa"),
        "source_version": default_version,
    }
