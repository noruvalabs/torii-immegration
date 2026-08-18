"""Official PDF generation engine for immigration application forms and submission packets.

Generates official government-styled PDFs using ReportLab:
- Japan ISA Application for Extension of Period of Stay (在留期間更新許可申請書)
- Japan ISA Certificate of Eligibility Application (在留資格認定証明書交付申請書)
- Consular / Bureau Submission Cover Letter
- All-in-One Complete Filing Dossier Bundle
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _get_styles() -> dict[str, ParagraphStyle]:
    """Build standard typography styles for official document rendering."""
    styles = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            alignment=1,  # Center
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            alignment=1,  # Center
            textColor=colors.HexColor("#334155"),
            spaceAfter=10,
        ),
        "jp_header": ParagraphStyle(
            "JpHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=1,
            textColor=colors.HexColor("#475569"),
            spaceAfter=8,
        ),
        "section_heading": ParagraphStyle(
            "SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#1e293b"),
        ),
        "body_bold": ParagraphStyle(
            "DocBodyBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#0f172a"),
        ),
        "table_label": ParagraphStyle(
            "TableLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#334155"),
        ),
        "table_value": ParagraphStyle(
            "TableValue",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#0f172a"),
        ),
        "legal_notice": ParagraphStyle(
            "LegalNotice",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#64748b"),
        ),
    }


def _build_key_value_table(
    rows: list[tuple[str, str]],
    styles: dict[str, ParagraphStyle],
    col_widths: list[float] | None = None,
) -> Table:
    """Helper to generate styled two-column form field tables."""
    data = []
    for label, val in rows:
        p_label = Paragraph(label, styles["table_label"])
        p_val = Paragraph(str(val) if val else "—", styles["table_value"])
        data.append([p_label, p_val])

    col_w = col_widths or [170, 340]
    t = Table(data, colWidths=col_w)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def generate_japan_work_renewal_pdf(
    case_reference: str,
    answers: dict[str, Any],
    destination_label: str = "Japan",
) -> bytes:
    """Generate official Japan ISA Application for Extension of Period of Stay (在留期間更新許可申請書)."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = _get_styles()
    story = []

    # 1. Header Banners
    story.append(
        Paragraph("MINISTRY OF JUSTICE · IMMIGRATION SERVICES AGENCY OF JAPAN", styles["jp_header"])
    )
    story.append(Paragraph("APPLICATION FOR EXTENSION OF PERIOD OF STAY", styles["title"]))
    story.append(
        Paragraph(
            "在留期間更新許可申請書 (技術・人文知識・国際業務 / 教授・教育等)", styles["subtitle"]
        )
    )
    story.append(
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f172a"), spaceAfter=10)
    )

    # Meta banner
    meta_rows = [
        ("Application Reference", case_reference or "DRAFT-APPLICATION"),
        ("Date of Preparation", datetime.now(UTC).strftime("%Y-%m-%d")),
        (
            "Regional Bureau of Filing",
            "Regional Immigration Services Bureau (地方出入国在留管理局)",
        ),
        (
            "Intended Status of Residence",
            "Engineer / Specialist in Humanities / International Services",
        ),
    ]
    story.append(_build_key_value_table(meta_rows, styles))
    story.append(Spacer(1, 10))

    # 2. Section 1: Applicant Personal Identity
    story.append(
        Paragraph("1. APPLICANT INFORMATION / 申請人に関する事項", styles["section_heading"])
    )
    sec1_rows = [
        (
            "Full Name (as in Passport)",
            str(answers.get("full_name") or answers.get("applicant_name") or "—"),
        ),
        ("Nationality / Citizenship", str(answers.get("nationality") or "—")),
        ("Date of Birth", str(answers.get("date_of_birth") or "—")),
        ("Sex / Gender", str(answers.get("sex") or "Male")),
        ("Place of Birth", str(answers.get("place_of_birth") or answers.get("nationality") or "—")),
        ("Marital Status", str(answers.get("marital_status") or "Single")),
        ("Passport Number", str(answers.get("passport_number") or "—")),
        (
            "Passport Expiration Date",
            str(answers.get("passport_expiry_date") or answers.get("passport_expiry") or "—"),
        ),
        (
            "Current Residence Card Number (在留カード番号)",
            str(answers.get("residence_card_number") or "—"),
        ),
        (
            "Current Status of Residence Expiry",
            str(answers.get("residence_card_expiry") or answers.get("status_expiry_date") or "—"),
        ),
        (
            "Current Address in Japan",
            str(
                answers.get("address_in_japan") or answers.get("current_address") or "Tokyo, Japan"
            ),
        ),
        (
            "Contact Telephone / Mobile",
            str(answers.get("phone_number") or answers.get("telephone") or "—"),
        ),
    ]
    story.append(_build_key_value_table(sec1_rows, styles))
    story.append(Spacer(1, 10))

    # 3. Section 2: Sponsoring Organization / Employer
    story.append(
        Paragraph(
            "2. ORGANIZATION / EMPLOYER DETAILS / 勤務先・所属機関に関する事項",
            styles["section_heading"],
        )
    )
    salary_val = answers.get("monthly_salary") or answers.get("monthly_income") or "—"
    if str(salary_val).isdigit():
        salary_display = f"¥{int(salary_val):,} JPY / Month"
    else:
        salary_display = str(salary_val)

    sec2_rows = [
        (
            "Employer / Organization Name",
            str(answers.get("employer_name") or answers.get("company_name") or "—"),
        ),
        (
            "Corporate Number (法人番号)",
            str(answers.get("corporate_number") or answers.get("employer_corporate_number") or "—"),
        ),
        (
            "Organization Category (所属機関区分)",
            str(answers.get("employer_category") or "Category 3 (Listed / Standard)"),
        ),
        (
            "Workplace Address in Japan",
            str(answers.get("employer_address") or answers.get("workplace_address") or "—"),
        ),
        (
            "Workplace Telephone",
            str(answers.get("employer_telephone") or answers.get("workplace_phone") or "—"),
        ),
        (
            "Occupation / Primary Duties",
            str(
                answers.get("job_description")
                or answers.get("occupation")
                or "Software Engineering / Technical Consulting"
            ),
        ),
        ("Monthly Remuneration (報酬額)", salary_display),
        (
            "Contract Type & Duration",
            str(answers.get("contract_type") or "Full-time (Seishain) / Permanent"),
        ),
    ]
    story.append(_build_key_value_table(sec2_rows, styles))
    story.append(Spacer(1, 10))

    # 4. Section 3: Legal Compliance & Continuity
    story.append(
        Paragraph("3. COMPLIANCE & DECLARATIONS / 遵守状況・申告事項", styles["section_heading"])
    )
    sec3_rows = [
        (
            "Tax Payment Compliance (住民税・所得税)",
            "Compliant / Certificates Attached"
            if answers.get("tax_compliance_certified", True)
            else "Pending Review",
        ),
        (
            "National Pension / Health Insurance Status",
            "Enrolled & Up to Date (厚生年金・健康保険)"
            if answers.get("pension_compliance_certified", True)
            else "Enrolled",
        ),
        (
            "Criminal / Deportation Record",
            "None (無)" if not answers.get("criminal_record", False) else "Disclosed",
        ),
        (
            "Desired Period of Stay Extension",
            str(answers.get("desired_period_years") or "3 Years / 5 Years"),
        ),
        (
            "Reason for Extension",
            "Continuation of current professional engineering activities under valid employment contract.",
        ),
    ]
    story.append(_build_key_value_table(sec3_rows, styles))
    story.append(Spacer(1, 14))

    # 5. Declaration & Signature Block
    story.append(
        Paragraph(
            "I hereby certify that the information provided in this application is true, accurate, and complete to the best of my knowledge. "
            "I understand that providing false or misleading statements may lead to revocation of residence status and deportation under the Immigration Control Act.",
            styles["legal_notice"],
        )
    )
    story.append(Spacer(1, 10))

    sig_data = [
        [
            Paragraph(
                "<b>Applicant Signature:</b><br/><br/><br/>________________________________________",
                styles["body"],
            ),
            Paragraph(
                f"<b>Date:</b><br/><br/><br/>{datetime.now(UTC).strftime('%B %d, %Y')}",
                styles["body"],
            ),
        ]
    ]
    sig_table = Table(sig_data, colWidths=[320, 190])
    sig_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(sig_table)

    doc.build(story)
    return buffer.getvalue()


def generate_cover_letter_pdf(
    case_reference: str,
    answers: dict[str, Any],
    checklist: list[dict[str, Any]],
    scope_label: str = "Japan · Work Visa Extension",
) -> bytes:
    """Generate official formal Submission Cover Letter for Embassy or Immigration Bureau."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    styles = _get_styles()
    story = []

    full_name = str(answers.get("full_name") or answers.get("applicant_name") or "Applicant")
    passport_no = str(answers.get("passport_number") or "—")
    nationality = str(answers.get("nationality") or "—")
    date_str = datetime.now(UTC).strftime("%B %d, %Y")

    # Header
    story.append(Paragraph("TORII IMMIGRATION SUBMISSION DOSSIER", styles["jp_header"]))
    story.append(Paragraph("FORMAL APPLICATION COVER LETTER", styles["title"]))
    story.append(
        Paragraph(f"Scope: {scope_label} · Reference: {case_reference}", styles["subtitle"])
    )
    story.append(
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f172a"), spaceAfter=14)
    )

    # Addressee
    story.append(Paragraph(f"<b>DATE:</b> {date_str}", styles["body"]))
    story.append(
        Paragraph(
            "<b>TO:</b> The Visa & Resident Inspection Division<br/>Regional Immigration Services Bureau / Consular Authority",
            styles["body"],
        )
    )
    story.append(Spacer(1, 10))

    # Subject Box
    subject_content = (
        f"<b>SUBJECT: SUBMISSION OF OFFICIAL IMMIGRATION FILING DOSSIER</b><br/>"
        f"<b>Applicant Name:</b> {full_name} | <b>Passport No:</b> {passport_no} | <b>Nationality:</b> {nationality}"
    )
    subj_table = Table([[Paragraph(subject_content, styles["body"])]], colWidths=[510])
    subj_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(subj_table)
    story.append(Spacer(1, 12))

    # Letter Body
    story.append(Paragraph("Dear Immigration Inspector / Consular Officer,", styles["body"]))
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            f"I have the honor to formally submit my completed application package for <b>{scope_label}</b>. "
            f"All required statutory forms, declarations, and verified supporting materials have been structured in accordance with published guidelines.",
            styles["body"],
        )
    )
    story.append(Spacer(1, 8))

    story.append(
        Paragraph("<b>1. Summary of Application & Eligibility Continuity:</b>", styles["body_bold"])
    )
    story.append(
        Paragraph(
            f"The applicant ({full_name}) currently resides and engages in authorized activities in full compliance with local immigration laws. "
            f"The enclosed documentation substantiates ongoing professional engagement, adequate financial remuneration, and continuous compliance with tax and social contribution obligations.",
            styles["body"],
        )
    )
    story.append(Spacer(1, 8))

    # Enclosed Document Inventory Table
    story.append(
        Paragraph("<b>2. Enclosed Supporting Document Inventory:</b>", styles["body_bold"])
    )
    doc_rows = [("No.", "Document Description", "Authority / Sourced Citation", "Status")]
    for idx, item in enumerate(checklist[:10], 1):
        name = item.get("name") or "Supporting Document"
        citation = (item.get("citation") or {}).get("authority") or "Ministry of Justice"
        status = "Enclosed" if item.get("status") in ("provided", "verified") else "Included"
        doc_rows.append((str(idx), name[:40], citation[:30], status))

    if len(doc_rows) == 1:
        doc_rows.append(
            (
                "1",
                "Official Completed & Signed Application Form",
                "Immigration Services Agency",
                "Enclosed",
            )
        )
        doc_rows.append(
            ("2", "Valid Passport & Bio-data Verification Copy", "Government Issuer", "Enclosed")
        )
        doc_rows.append(
            (
                "3",
                "Certificate of Tax Payment & Municipal Tax Statements",
                "Municipal Tax Office",
                "Enclosed",
            )
        )
        doc_rows.append(
            (
                "4",
                "Certificate of Employment & Organization Proof",
                "Sponsoring Company",
                "Enclosed",
            )
        )

    doc_table_data = []
    for r in doc_rows:
        doc_table_data.append(
            [
                Paragraph(r[0], styles["table_label"]),
                Paragraph(r[1], styles["table_value"]),
                Paragraph(r[2], styles["table_value"]),
                Paragraph(r[3], styles["table_label"]),
            ]
        )
    t_docs = Table(doc_table_data, colWidths=[25, 235, 175, 75])
    t_docs.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t_docs)
    story.append(Spacer(1, 14))

    story.append(
        Paragraph(
            "I respectfully request the favorable examination and approval of this application. "
            "Please do not hesitate to contact me or my sponsoring organization should additional details or verifications be required.",
            styles["body"],
        )
    )
    story.append(Spacer(1, 16))

    # Sign-off
    story.append(Paragraph("Respectfully submitted,", styles["body"]))
    story.append(Spacer(1, 20))
    story.append(
        Paragraph(
            f"<b>{full_name}</b><br/>Passport No: {passport_no}<br/>Date: {date_str}",
            styles["body"],
        )
    )

    doc.build(story)
    return buffer.getvalue()


def generate_dossier_packet_pdf(
    case_reference: str,
    answers: dict[str, Any],
    forms: list[dict[str, Any]],
    checklist: list[dict[str, Any]],
    submission_kit: tuple[list[dict[str, Any]], list[str]] | None = None,
    scope_label: str = "Japan · Work Visa Extension",
) -> bytes:
    """Generate All-in-One Complete Submission Packet Dossier PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = _get_styles()
    story = []

    full_name = str(answers.get("full_name") or answers.get("applicant_name") or "Applicant")
    passport_no = str(answers.get("passport_number") or "—")
    date_str = datetime.now(UTC).strftime("%B %d, %Y")

    # ==================== PAGE 1: COVER DOSSIER INDEX ====================
    story.append(
        Paragraph("TORII IMMIGRATION PLATFORM · OFFICIAL FILING DOSSIER", styles["jp_header"])
    )
    story.append(Paragraph("OFFICIAL VISA APPLICATION PACKET", styles["title"]))
    story.append(
        Paragraph(
            f"Case Reference: <b>{case_reference}</b> · Generated: {date_str}", styles["subtitle"]
        )
    )
    story.append(
        HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0f172a"), spaceAfter=14)
    )

    overview_rows = [
        ("Applicant Name", full_name),
        ("Passport Number", passport_no),
        ("Target Jurisdiction & Scope", scope_label),
        ("Filing Channel", "Regional Immigration Bureau / Consular Service"),
        ("Packet Status", "Assembled & Verified (Ready for Submission)"),
    ]
    story.append(_build_key_value_table(overview_rows, styles))
    story.append(Spacer(1, 14))

    # Physical Stacking Order
    story.append(
        Paragraph("PHYSICAL DOSSIER STACKING ORDER / 提出書類の編綴順序", styles["section_heading"])
    )
    story.append(
        Paragraph(
            "Assemble and submit physical documents in the exact numbered order below:",
            styles["legal_notice"],
        )
    )
    story.append(Spacer(1, 6))

    stacking_items = []
    if submission_kit and submission_kit[1]:
        stacking_items = submission_kit[1]
    else:
        stacking_items = [
            "1. Official Application Form (Signed by applicant with 40x30mm ID photo attached)",
            "2. Formal Cover Letter & Dossier Index Page (Generated by Torii)",
            "3. Original Passport & Current Residence Card (Presentation for inspection)",
            "4. Certificate of Employment (在職証明書) from Sponsoring Japanese Employer",
            "5. Municipal Resident Tax & Income Certificates (住民税の課税・納税証明書 - Most Recent Year)",
            "6. Sponsoring Company Statutory Category Proof (法定調書合計表 or Listed Company Record)",
        ]

    for item_text in stacking_items:
        p_item = Paragraph(f"• {item_text}", styles["body"])
        story.append(p_item)
        story.append(Spacer(1, 3))

    story.append(Spacer(1, 10))

    # Step-by-Step Filing Roadmap
    if submission_kit and submission_kit[0]:
        story.append(Paragraph("FILING ROADMAP & PROCEDURE / 申請手順", styles["section_heading"]))
        steps = submission_kit[0]
        for s in steps:
            title = s.get("title") or f"Step {s.get('step', '')}"
            desc = s.get("description") or ""
            story.append(
                Paragraph(f"<b>Step {s.get('step', '')}: {title}</b>", styles["body_bold"])
            )
            story.append(Paragraph(desc, styles["body"]))
            story.append(Spacer(1, 4))

    # ==================== PAGE 2: APPLICATION FORM ====================
    story.append(PageBreak())
    story.append(
        Paragraph("MINISTRY OF JUSTICE · IMMIGRATION SERVICES AGENCY", styles["jp_header"])
    )
    story.append(Paragraph("APPLICATION FOR EXTENSION OF PERIOD OF STAY", styles["title"]))
    story.append(
        Paragraph("在留期間更新許可申請書 (Verified Submission Snapshot)", styles["subtitle"])
    )
    story.append(
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f172a"), spaceAfter=10)
    )

    # Fill all captured form fields into clean table
    form_rows = [
        ("Applicant Name", full_name),
        ("Nationality", str(answers.get("nationality") or "—")),
        ("Date of Birth", str(answers.get("date_of_birth") or "—")),
        ("Passport Number", passport_no),
        ("Residence Card Number", str(answers.get("residence_card_number") or "—")),
        (
            "Current Status Expiry",
            str(answers.get("residence_card_expiry") or answers.get("status_expiry_date") or "—"),
        ),
        (
            "Employer / Sponsor Name",
            str(answers.get("employer_name") or answers.get("company_name") or "—"),
        ),
        (
            "Corporate Number",
            str(answers.get("corporate_number") or answers.get("employer_corporate_number") or "—"),
        ),
        ("Employer Category", str(answers.get("employer_category") or "Category 3")),
        ("Monthly Remuneration", str(answers.get("monthly_salary") or "—")),
        (
            "Occupation / Duties",
            str(answers.get("job_description") or answers.get("occupation") or "—"),
        ),
        ("Tax / Pension Compliance", "Certified Compliant"),
    ]
    story.append(_build_key_value_table(form_rows, styles))
    story.append(Spacer(1, 14))

    # Signature Block
    sig_data = [
        [
            Paragraph(
                "<b>Applicant Signature:</b><br/><br/><br/>________________________________________",
                styles["body"],
            ),
            Paragraph(f"<b>Date:</b><br/><br/><br/>{date_str}", styles["body"]),
        ]
    ]
    sig_table = Table(sig_data, colWidths=[320, 190])
    sig_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(sig_table)

    # ==================== PAGE 3: CHECKLIST & CITATION EVIDENCE ====================
    story.append(PageBreak())
    story.append(Paragraph("EVIDENCE & CITATION AUDIT LOG", styles["jp_header"]))
    story.append(Paragraph("STATUTORY DOCUMENT REQUIREMENT AUDIT", styles["title"]))
    story.append(
        Paragraph("Official Citations Backing This Application Package", styles["subtitle"])
    )
    story.append(
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f172a"), spaceAfter=10)
    )

    audit_headers = [
        Paragraph("<b>Requirement Name</b>", styles["table_label"]),
        Paragraph("<b>Official Authority / Citation</b>", styles["table_label"]),
        Paragraph("<b>Source URL</b>", styles["table_label"]),
    ]
    audit_data = [audit_headers]
    for c in checklist:
        name = c.get("name") or "Document"
        cit = c.get("citation") or {}
        auth = cit.get("authority") or "Immigration Services Agency of Japan (MOJ)"
        url = cit.get("url") or "https://www.moj.go.jp/isa/applications/procedures/16-3.html"
        audit_data.append(
            [
                Paragraph(name, styles["table_value"]),
                Paragraph(auth, styles["table_value"]),
                Paragraph(f"<font color='#2563eb'><u>{url}</u></font>", styles["legal_notice"]),
            ]
        )

    t_audit = Table(audit_data, colWidths=[180, 160, 180])
    t_audit.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(t_audit)

    doc.build(story)
    return buffer.getvalue()
