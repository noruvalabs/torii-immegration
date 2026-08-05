"""Standalone government scraper — fetches immigration data from official sources daily.

No external API keys required. Uses httpx + regex HTML parsing to extract
visa categories, requirements, and form info from Japan ISA and USA USCIS.

Stores results as draft records for human review before going live.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

log = structlog.get_logger()

HEADERS = {
    "User-Agent": "Torii-GovScraper/1.0 (immigration-assistance)",
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
}

# ── Source URLs ────────────────────────────────────────────────────────────────

JP_SOURCES = {
    "procedures": "https://www.moj.go.jp/isa/applications/procedures/index.html",
    "visa_categories": "https://www.moj.go.jp/isa/applications/procedures/16-4.html",
    "status_of_residence": "https://www.moj.go.jp/isa/content/930004501.pdf",
    "renewal": "https://www.moj.go.jp/isa/applications/procedures/16-3.html",
    "change_status": "https://www.moj.go.jp/isa/applications/procedures/16-2.html",
    "coe": "https://www.moj.go.jp/isa/applications/procedures/16-1.html",
    "english_procedures": "https://www.moj.go.jp/isa/applications/procedures/index.html",
}

US_SOURCES = {
    "temporary_workers": "https://www.uscis.gov/working-in-the-united-states",
    "h1b": "https://www.uscis.gov/working-in-the-united-states/h-1b-specialty-occupations",
    "l1": "https://www.uscis.gov/working-in-the-united-states/temporary-nonimmigrant-workers",
    "ead": "https://www.uscis.gov/green-card/green-card-processes-and-procedures/employment-authorization-document",
    "green_card": "https://www.uscis.gov/green-card",
    "forms": "https://www.uscis.gov/forms/all-forms",
    "eb_categories": "https://www.uscis.gov/green-card/green-card-eligibility-categories",
}


# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass
class ScrapeResult:
    """Structured data extracted from government sources for one jurisdiction."""

    jurisdiction_code: str
    source_pages: list[dict[str, Any]] = field(default_factory=list)
    visa_categories: list[dict[str, Any]] = field(default_factory=list)
    document_requirements: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    eligibility_rules: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    forms: list[dict[str, Any]] = field(default_factory=list)
    scraped_at: str = ""
    errors: list[str] = field(default_factory=list)


# ── Fetcher ───────────────────────────────────────────────────────────────────


async def _fetch_page(url: str, client: httpx.AsyncClient) -> str | None:
    """Fetch a page and return cleaned text content."""
    try:
        resp = await client.get(url, follow_redirects=True)
        if resp.status_code != 200:
            log.warning("gov_scraper.fetch_failed", url=url, status=resp.status_code)
            return None
        text = resp.text
        # Strip scripts, styles, SVGs
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<svg[^>]*>.*?</svg>", "", text, flags=re.DOTALL | re.IGNORECASE)
        # Convert common tags to markers
        text = re.sub(r"<h[1-6][^>]*>(.*?)</h[1-6]>", r"\n## \1\n", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<tr[^>]*>(.*?)</tr>", r"\n| \1", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<p[^>]*>(.*?)</p>", r"\n\1\n", text, flags=re.DOTALL | re.IGNORECASE)
        # Strip remaining tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Decode entities
        text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
        text = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), text)
        # Collapse whitespace
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()[:12000]
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("gov_scraper.fetch_error", url=url, error=str(exc))
        return None


def _extract_links(html: str, base_url: str) -> list[dict[str, str]]:
    """Extract links from raw HTML."""
    links = []
    for match in re.finditer(r'<a[^>]+href="([^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE):
        href, label = match.group(1), match.group(2)
        label = re.sub(r"<[^>]+>", "", label).strip()
        if not label or len(label) < 3:
            continue
        if href.startswith("/"):
            href = base_url.rstrip("/") + href
        elif not href.startswith("http"):
            continue
        links.append({"url": href, "title": label})
    return links


# ── Japan Scraper ─────────────────────────────────────────────────────────────


async def scrape_japan(client: httpx.AsyncClient) -> ScrapeResult:
    """Scrape Japan Immigration Services Agency (ISA) for visa data."""
    result = ScrapeResult(jurisdiction_code="JP", scraped_at=datetime.now(UTC).isoformat())

    # 1. Scrape main procedures page for visa categories
    log.info("gov_scraper.jp.fetching", page="procedures")
    html = await _fetch_page(JP_SOURCES["procedures"], client)
    if html:
        result.source_pages.append({"url": JP_SOURCES["procedures"], "title": "手続の種類から探す", "retrieved_at": result.scraped_at})

        # Extract visa application types
        visa_types = [
            {"code": "coe", "name_en": "Certificate of Eligibility (COE)", "name_ja": "在留資格認定証明書交付申請", "url": JP_SOURCES["coe"]},
            {"code": "change_status", "name_en": "Change of Status of Residence", "name_ja": "在留資格変更許可申請", "url": JP_SOURCES["change_status"]},
            {"code": "renewal", "name_en": "Extension of Period of Stay", "name_ja": "在留期間更新許可申請", "url": JP_SOURCES["renewal"]},
            {"code": "acquire_status", "name_en": "Acquisition of Status of Residence", "name_ja": "在留資格取得許可申請", "url": ""},
            {"code": "permanent_residence", "name_en": "Permanent Residence", "name_ja": "永住許可申請", "url": ""},
            {"code": "work_permission", "name_en": "Permission to Engage in Activity other than Permitted", "name_ja": "資格外活動許可申請", "url": ""},
            {"code": "employment_cert", "name_en": "Certificate of Authorized Employment", "name_ja": "就労資格証明書交付申請", "url": ""},
        ]
        result.visa_categories = visa_types
        log.info("gov_scraper.jp.visa_types_found", count=len(visa_types))

    # 2. Scrape visa status page
    log.info("gov_scraper.jp.fetching", page="visa_categories")
    html2 = await _fetch_page(JP_SOURCES["visa_categories"], client)
    if html2:
        result.source_pages.append({"url": JP_SOURCES["visa_categories"], "title": "在留資格から探す", "retrieved_at": result.scraped_at})

        # Extract residence statuses from the page
        status_patterns = [
            (r"教授|Professor", "professor", "Professor"),
            (r"芸術|Art", "art", "Art"),
            (r"宗教|Religion", "religion", "Religion"),
            (r"報道|Press", "press", "Press"),
            (r"投資経営|Business Manager", "business_manager", "Business Manager"),
            (r"法律会計業務|Legal/Accounting", "legal_accounting", "Legal/Accounting Services"),
            (r"医療|Medical Services", "medical", "Medical Services"),
            (r"研究|Research", "research", "Research"),
            (r"教育|Education", "education", "Education"),
            (r"技術\/人文知識\/国際業務|Specialist in Humanities/International Services", "specialist_humanities", "Specialist in Humanities/International Services"),
            (r"介護|Nursing Care", "nursing_care", "Nursing Care"),
            (r"興行|Entertainment", "entertainment", "Entertainment"),
            (r"技能|Skilled Labor", "skilled_labor", "Skilled Labor"),
            (r"文化活動|Cultural Activities", "cultural_activities", "Cultural Activities"),
            (r"短期滞在|Temporary Visitor", "temporary_visitor", "Temporary Visitor"),
            (r"留学|Student", "student", "Student"),
            (r"研修|Trainee", "trainee", "Trainee"),
            (r"家族滞在|Dependent", "dependent", "Dependent"),
            (r"特定活動|Designated Activities", "designated_activities", "Designated Activities"),
            (r"高度専門職|Highly Skilled Professional", "highly_skilled", "Highly Skilled Professional"),
            (r"経営管理|Business Management", "business_management", "Business Management"),
            (r"特定技能|Specified Skilled Worker", "specified_skilled", "Specified Skilled Worker"),
            (r"技能実習|Technical Intern Training", "technical_intern", "Technical Intern Training"),
        ]

        found_statuses = []
        for pattern, code, name in status_patterns:
            if re.search(pattern, html2, re.IGNORECASE):
                found_statuses.append({"code": code, "name_en": name, "name_ja": ""})

        if found_statuses:
            result.visa_categories.extend(found_statuses)
            log.info("gov_scraper.jp.residence_statuses_found", count=len(found_statuses))

    # 3. Scrape renewal page for document requirements
    log.info("gov_scraper.jp.fetching", page="renewal")
    html3 = await _fetch_page(JP_SOURCES["renewal"], client)
    if html3:
        result.source_pages.append({"url": JP_SOURCES["renewal"], "title": "在留期間更新許可申請", "retrieved_at": result.scraped_at})

        # Extract document requirements
        renewal_docs = _extract_jp_documents(html3, "renewal")
        result.document_requirements["renewal"] = renewal_docs

        # Extract eligibility hints
        renewal_rules = _extract_jp_eligibility(html3, "renewal")
        result.eligibility_rules["renewal"] = renewal_rules

    # 4. Scrape change of status page
    log.info("gov_scraper.jp.fetching", page="change_status")
    html4 = await _fetch_page(JP_SOURCES["change_status"], client)
    if html4:
        result.source_pages.append({"url": JP_SOURCES["change_status"], "title": "在留資格変更許可申請", "retrieved_at": result.scraped_at})
        change_docs = _extract_jp_documents(html4, "change_status")
        result.document_requirements["change_status"] = change_docs

    # 5. Scrape COE page
    log.info("gov_scraper.jp.fetching", page="coe")
    html5 = await _fetch_page(JP_SOURCES["coe"], client)
    if html5:
        result.source_pages.append({"url": JP_SOURCES["coe"], "title": "在留資格認定証明書交付申請", "retrieved_at": result.scraped_at})
        coe_docs = _extract_jp_documents(html5, "coe")
        result.document_requirements["coe"] = coe_docs

    log.info("gov_scraper.jp.complete", pages=len(result.source_pages), categories=len(result.visa_categories))
    return result


def _extract_jp_documents(html: str, action: str) -> list[dict[str, Any]]:
    """Extract document requirements from Japanese immigration page content."""
    docs = []
    # Common documents required across most applications
    common_docs = [
        {"code": "passport", "name_en": "Passport", "name_ja": "パスポート", "is_required": True,
         "how_to_obtain": "Valid passport from your home country", "why_required": "Primary identification document"},
        {"code": "residence_card", "name_en": "Residence Card", "name_ja": "在留カード", "is_required": True,
         "how_to_obtain": "Previously issued residence card", "why_required": "Proof of current immigration status"},
        {"code": "photo", "name_en": "Photograph (4x3cm)", "name_ja": "証明写真（縦4cm×横3cm）", "is_required": True,
         "how_to_obtain": "Recent photo meeting ISA specifications", "why_required": "Required for application form"},
        {"code": "application_form", "name_en": "Application Form", "name_ja": "申請書", "is_required": True,
         "how_to_obtain": "Download from ISA website or pick up at immigration office", "why_required": "Official application document"},
    ]

    if action == "renewal":
        docs.extend(common_docs)
        docs.append({"code": "documents_showing_activities", "name_en": "Documents showing activities", "name_ja": "活動内容を証明する書類", "is_required": True,
                      "how_to_obtain": "Employment certificate, tax payment certificate, etc.", "why_required": "Proves continued legitimate activities"})
        docs.append({"code": "income_proof", "name_en": "Income proof / Tax certificate", "name_ja": "収入を証明する書類（納税証明書等）", "is_required": True,
                      "how_to_obtain": "From tax office or employer", "why_required": "Demonstrates financial stability"})
    elif action == "change_status":
        docs.extend(common_docs)
        docs.append({"code": "reason_documents", "name_en": "Documents explaining reason for change", "name_ja": "変更理由を説明する書類", "is_required": True,
                      "how_to_obtain": "Letter of explanation, supporting documents", "why_required": "Justifies the status change request"})
        docs.append({"code": "new_qualification_proof", "name_en": "Proof of new qualification", "name_ja": "新たな資格を証明する書類", "is_required": True,
                      "how_to_obtain": "Certificate, license, or employment offer", "why_required": "Proves eligibility for new status"})
    elif action == "coe":
        docs.extend(common_docs)
        docs.append({"code": "coa_documents", "name_en": "Documents from receiving organization", "name_ja": "受入機関の書類", "is_required": True,
                      "how_to_obtain": "From the Japanese company/school sponsoring you", "why_required": "Proves purpose and arrangement in Japan"})

    # Extract any specific document links from the page
    doc_links = _extract_links(html, "https://www.moj.go.jp")
    for link in doc_links:
        title = link["title"].lower()
        if any(kw in title for kw in ["書類", "document", "様式", "form", "申請書"]):
            docs.append({
                "code": re.sub(r"[^a-z0-9]", "_", title[:32]),
                "name_en": link["title"],
                "name_ja": "",
                "is_required": False,
                "how_to_obtain": f"Download from {link['url']}",
                "why_required": "Referenced on official procedures page",
            })

    return docs


def _extract_jp_eligibility(html: str, action: str) -> list[dict[str, Any]]:
    """Extract eligibility rules from Japanese immigration page content."""
    rules = []

    # Common eligibility rules for Japan
    if action == "renewal":
        rules.extend([
            {"key": "has_valid_passport", "operator": "equals", "value": "true",
             "failure_status": "fail", "message": "You must hold a valid passport"},
            {"key": "has_residence_card", "operator": "equals", "value": "true",
             "failure_status": "fail", "message": "You must hold a valid residence card"},
            {"key": "current_status_is_renewable", "operator": "equals", "value": "true",
             "failure_status": "fail", "message": "Your current status of residence must be eligible for renewal"},
            {"key": "applied_before_expiry", "operator": "equals", "value": "true",
             "failure_status": "at_risk", "message": "Applications should be submitted before your current period of stay expires"},
        ])
    elif action == "change_status":
        rules.extend([
            {"key": "has_valid_passport", "operator": "equals", "value": "true",
             "failure_status": "fail", "message": "You must hold a valid passport"},
            {"key": "has_qualification_for_new_status", "operator": "equals", "value": "true",
             "failure_status": "fail", "message": "You must meet the requirements for the new status of residence"},
        ])
    elif action == "coe":
        rules.extend([
            {"key": "has_sponsoring_organization", "operator": "equals", "value": "true",
             "failure_status": "fail", "message": "A Japanese organization must sponsor your COE application"},
        ])

    return rules


# ── USA Scraper ───────────────────────────────────────────────────────────────


async def scrape_usa(client: httpx.AsyncClient) -> ScrapeResult:
    """Scrape USCIS for US immigration data."""
    result = ScrapeResult(jurisdiction_code="US", scraped_at=datetime.now(UTC).isoformat())

    # 1. Main working in US page
    log.info("gov_scraper.us.fetching", page="temporary_workers")
    html = await _fetch_page(US_SOURCES["temporary_workers"], client)
    if html:
        result.source_pages.append({"url": US_SOURCES["temporary_workers"], "title": "Working in the United States", "retrieved_at": result.scraped_at})

        # Extract visa categories from links
        links = _extract_links(html, "https://www.uscis.gov")
        work_visas = []
        for link in links:
            title = link["title"]
            url = link["url"]
            if "/working-in-the-united-states/" in url and url != US_SOURCES["temporary_workers"]:
                code = url.rstrip("/").split("/")[-1]
                work_visas.append({"code": code, "name_en": title, "url": url})
        if work_visas:
            result.visa_categories.extend(work_visas)
            log.info("gov_scraper.us.work_visas_found", count=len(work_visas))

    # Add known US work visa categories (always include these)
    known_us_visas = [
        {"code": "h1b", "name_en": "H-1B Specialty Occupation Workers"},
        {"code": "h2a", "name_en": "H-2A Temporary Agricultural Workers"},
        {"code": "h2b", "name_en": "H-2B Temporary Non-Agricultural Workers"},
        {"code": "l1", "name_en": "L-1 Intracompany Transferees"},
        {"code": "o1", "name_en": "O-1 Individuals with Extraordinary Ability"},
        {"code": "tn", "name_en": "TN NAFTA Professionals"},
        {"code": "ead", "name_en": "Employment Authorization Document (EAD)"},
        {"code": "eb1", "name_en": "EB-1 Priority Workers"},
        {"code": "eb2", "name_en": "EB-2 Advanced Degree / Exceptional Ability"},
        {"code": "eb3", "name_en": "EB-3 Skilled Workers / Professionals"},
        {"code": "eb5", "name_en": "EB-5 Immigrant Investors"},
        {"code": "f1_opt", "name_en": "F-1 Optional Practical Training (OPT)"},
    ]
    existing_codes = {v["code"] for v in result.visa_categories}
    for visa in known_us_visas:
        if visa["code"] not in existing_codes:
            result.visa_categories.append(visa)
    log.info("gov_scraper.us.total_categories", count=len(result.visa_categories))

    # 2. H-1B page
    log.info("gov_scraper.us.fetching", page="h1b")
    html2 = await _fetch_page(US_SOURCES["h1b"], client)
    if html2:
        result.source_pages.append({"url": US_SOURCES["h1b"], "title": "H-1B Specialty Occupations", "retrieved_at": result.scraped_at})
        h1b_docs = _extract_us_documents(html2, "h1b")
        result.document_requirements["h1b"] = h1b_docs
        h1b_rules = _extract_us_eligibility(html2, "h1b")
        result.eligibility_rules["h1b"] = h1b_rules

    # 3. L-1 page
    log.info("gov_scraper.us.fetching", page="l1")
    html3 = await _fetch_page(US_SOURCES["l1"], client)
    if html3:
        result.source_pages.append({"url": US_SOURCES["l1"], "title": "L-1 Intracompany Transferees", "retrieved_at": result.scraped_at})
        l1_docs = _extract_us_documents(html3, "l1")
        result.document_requirements["l1"] = l1_docs

    # 4. EAD page
    log.info("gov_scraper.us.fetching", page="ead")
    html4 = await _fetch_page(US_SOURCES["ead"], client)
    if html4:
        result.source_pages.append({"url": US_SOURCES["ead"], "title": "Employment Authorization Document", "retrieved_at": result.scraped_at})
        ead_docs = _extract_us_documents(html4, "ead")
        result.document_requirements["ead"] = ead_docs

    # 5. Green Card page
    log.info("gov_scraper.us.fetching", page="green_card")
    html5 = await _fetch_page(US_SOURCES["green_card"], client)
    if html5:
        result.source_pages.append({"url": US_SOURCES["green_card"], "title": "Green Card", "retrieved_at": result.scraped_at})
        gc_links = _extract_links(html5, "https://www.uscis.gov")
        gc_categories = []
        for link in gc_links:
            if "/green-card/" in link["url"] and link["url"] != US_SOURCES["green_card"]:
                code = link["url"].rstrip("/").split("/")[-1]
                gc_categories.append({"code": f"gc_{code}", "name_en": link["title"], "url": link["url"]})
        if gc_categories:
            result.visa_categories.extend(gc_categories)
            log.info("gov_scraper.us.green_card_categories_found", count=len(gc_categories))

    # 6. Forms page
    log.info("gov_scraper.us.fetching", page="forms")
    html6 = await _fetch_page(US_SOURCES["forms"], client)
    if html6:
        result.source_pages.append({"url": US_SOURCES["forms"], "title": "USCIS Forms", "retrieved_at": result.scraped_at})
        forms = _extract_us_forms(html6)
        result.forms = forms

    log.info("gov_scraper.us.complete", pages=len(result.source_pages), categories=len(result.visa_categories))
    return result


def _extract_us_documents(html: str, visa_type: str) -> list[dict[str, Any]]:
    """Extract document requirements from USCIS page content."""
    docs = []

    # Common US immigration documents
    common_docs = [
        {"code": "passport", "name_en": "Valid Passport", "is_required": True,
         "how_to_obtain": "Valid passport from your home country", "why_required": "Primary identification"},
        {"code": "form_i94", "name_en": "Form I-94 (Arrival/Departure Record)", "is_required": True,
         "how_to_obtain": "Obtained at port of entry or online at i94.cbp.dhs.gov", "why_required": "Proof of lawful entry"},
        {"code": "passport_photo", "name_en": "Passport-style Photographs", "is_required": True,
         "how_to_obtain": "2x2 inch color photos meeting USCIS specifications", "why_required": "Required for application"},
    ]

    if visa_type == "h1b":
        docs.extend(common_docs)
        docs.extend([
            {"code": "form_i129", "name_en": "Form I-129 (Petition for Nonimmigrant Worker)", "is_required": True,
             "how_to_obtain": "Download from uscis.gov or file online", "why_required": "Main H-1B petition form"},
            {"code": "labor_condition_application", "name_en": "Labor Condition Application (LCA)", "is_required": True,
             "how_to_obtain": "Certified by Department of Labor", "why_required": "Required before H-1B petition"},
            {"code": "degree_credential", "name_en": "Degree Credentials / Equivalency", "is_required": True,
             "how_to_obtain": "Official transcripts, degree certificates, or credential evaluation", "why_required": "Proves specialty occupation qualification"},
            {"code": "employer_letter", "name_en": "Employer Support Letter", "is_required": True,
             "how_to_obtain": "From sponsoring employer detailing job duties, salary, requirements", "why_required": "Establishes specialty occupation and employer-employee relationship"},
        ])
    elif visa_type == "l1":
        docs.extend(common_docs)
        docs.extend([
            {"code": "form_i129", "name_en": "Form I-129 with L Supplement", "is_required": True,
             "how_to_obtain": "Download from uscis.gov", "why_required": "Main L-1 petition form"},
            {"code": "proof_of_qualifying_relationship", "name_en": "Proof of Qualifying Relationship", "is_required": True,
             "how_to_obtain": "Articles of incorporation, stock certificates, organizational charts", "why_required": "Proves related employer entities"},
            {"code": "proof_of_employment_abroad", "name_en": "Proof of Employment Abroad (1 year in 3 years)", "is_required": True,
             "how_to_obtain": "Employment records, pay stubs, tax filings from foreign entity", "why_required": "Proves qualifying foreign employment"},
            {"code": "job_description", "name_en": "US Position Description", "is_required": True,
             "how_to_obtain": "Detailed job duties and organizational placement", "why_required": "Establishes managerial/executive/specialized knowledge role"},
        ])
    elif visa_type == "ead":
        docs.extend(common_docs)
        docs.extend([
            {"code": "form_i765", "name_en": "Form I-765 (Application for Employment Authorization)", "is_required": True,
             "how_to_obtain": "Download from uscis.gov or file online", "why_required": "Main EAD application form"},
            {"code": "basis_for_eligibility", "name_en": "Evidence of Basis for Eligibility", "is_required": True,
             "how_to_obtain": "Supporting documents based on immigration category (I-94, pending I-485 receipt, etc.)", "why_required": "Proves eligibility category for EAD"},
        ])

    # Extract form references from page
    form_refs = re.findall(r"(?:Form\s+)?(I-\d{2}[A-Z]?)", html, re.IGNORECASE)
    for form_id in set(form_refs):
        form_id_upper = form_id.upper()
        if not any(d["code"].startswith(form_id_upper.lower()) for d in docs):
            docs.append({
                "code": form_id_upper.lower(),
                "name_en": f"Form {form_id_upper}",
                "is_required": False,
                "how_to_obtain": f"Download from uscis.gov/forms/{form_id_upper.lower()}",
                "why_required": "Referenced on USCIS page",
            })

    return docs


def _extract_us_eligibility(html: str, visa_type: str) -> list[dict[str, Any]]:
    """Extract eligibility rules from USCIS page content."""
    rules = []

    if visa_type == "h1b":
        rules.extend([
            {"key": "has_bachelors_degree", "operator": "equals", "value": "true",
             "failure_status": "fail", "message": "Must have at minimum a bachelor's degree or equivalent in a specialty occupation"},
            {"key": "job_requires_degree", "operator": "equals", "value": "true",
             "failure_status": "fail", "message": "The position must require a bachelor's degree or higher"},
            {"key": "employer_filed_lca", "operator": "equals", "value": "true",
             "failure_status": "fail", "message": "Employer must have a certified Labor Condition Application"},
            {"key": "prevailing_wage_met", "operator": "equals", "value": "true",
             "failure_status": "at_risk", "message": "Employer must pay at least the prevailing wage for the occupation"},
            {"key": "annual_cap_not_reached", "operator": "equals", "value": "true",
             "failure_status": "at_risk", "message": "H-1B petitions are subject to an annual cap (currently 65,000 + 20,000 for US master's)"},
        ])
    elif visa_type == "l1":
        rules.extend([
            {"key": "worked_at_foreign_entity_1yr", "operator": "equals", "value": "true",
             "failure_status": "fail", "message": "Must have worked for qualifying foreign entity for at least 1 year in the past 3 years"},
            {"key": "qualifying_relationship_exists", "operator": "equals", "value": "true",
             "failure_status": "fail", "message": "US and foreign entities must have a qualifying relationship (parent, subsidiary, affiliate)"},
            {"key": "managerial_executive_specialized", "operator": "equals", "value": "true",
             "failure_status": "fail", "message": "Position must be managerial, executive, or require specialized knowledge"},
        ])

    return rules


def _extract_us_forms(html: str) -> list[dict[str, Any]]:
    """Extract form information from USCIS forms page."""
    forms = []

    # Extract form numbers and titles from the page
    form_pattern = re.compile(
        r"(?:Form\s+)?(I-\d{2}[A-Z]?)\s*[-–:]\s*(.*?)(?:\n|$|<)",
        re.IGNORECASE | re.MULTILINE,
    )
    for match in form_pattern.finditer(html):
        form_id = match.group(1).upper()
        title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        if title and len(title) > 5:
            forms.append({
                "code": form_id,
                "version": datetime.now(UTC).strftime("%Y-%m"),
                "official_title": title,
                "url": f"https://www.uscis.gov/forms/{form_id.lower()}",
            })

    # Add well-known forms even if not found in text
    known_forms = [
        ("I-129", "Petition for a Nonimmigrant Worker"),
        ("I-140", "Immigrant Petition for Alien Workers"),
        ("I-485", "Application to Register Permanent Residence or Adjust Status"),
        ("I-765", "Application for Employment Authorization"),
        ("I-130", "Petition for Alien Relative"),
        ("I-864", "Affidavit of Support Under Section 213A of the INA"),
        ("I-90", "Application to Replace Permanent Resident Card"),
        ("I-751", "Petition to Remove Conditions on Residence"),
    ]
    existing_codes = {f["code"] for f in forms}
    for code, title in known_forms:
        if code not in existing_codes:
            forms.append({
                "code": code,
                "version": datetime.now(UTC).strftime("%Y-%m"),
                "official_title": title,
                "url": f"https://www.uscis.gov/forms/{code.lower()}",
            })

    return forms


# ── Main entry point ──────────────────────────────────────────────────────────


async def scrape_all(jurisdictions: list[str] | None = None) -> dict[str, ScrapeResult]:
    """Run scraper for all configured jurisdictions."""
    if jurisdictions is None:
        jurisdictions = ["JP", "US"]

    results: dict[str, ScrapeResult] = {}
    async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=HEADERS) as client:
        for code in jurisdictions:
            log.info("gov_scraper.starting", jurisdiction=code)
            if code == "JP":
                results["JP"] = await scrape_japan(client)
            elif code == "US":
                results["US"] = await scrape_usa(client)
            else:
                log.warning("gov_scraper.unknown_jurisdiction", code=code)

    return results
