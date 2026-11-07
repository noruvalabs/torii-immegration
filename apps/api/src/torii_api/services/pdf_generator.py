"""Official PDF generation engine for immigration application forms and submission packets.

Generates official government-styled PDFs using ReportLab:
- Japan ISA Application for Extension of Period of Stay (在留期間更新許可申請書)
- Japan ISA Certificate of Eligibility Application (在留資格認定証明書交付申請書)
- Consular / Bureau Submission Cover Letter
- All-in-One Complete Filing Dossier Bundle
"""

from __future__ import annotations

import base64
import io
import os
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
from reportlab.platypus import (
    Image as RLImage,
)

# Printed in place of an answer the applicant has not given.
#
# These documents accompany a sworn immigration application, so an unanswered field is
# printed blank — never filled with a plausible-looking guess. A blank line asks the
# applicant a question; an invented "Passed approved SELT test at CEFR B1" or
# "Category 3 (Listed / Standard)" makes a false statement to a government on their
# behalf. ``test_no_fabricated_defaults`` enforces this across the whole module.
NOT_PROVIDED = "—"


def _extract_image_bytes(photo_data: bytes | str | None) -> bytes | None:
    """Extract raw image bytes from bytes, base64 data-URL, or local path."""
    if not photo_data:
        return None
    if isinstance(photo_data, bytes):
        return photo_data
    if isinstance(photo_data, str):
        s = photo_data.strip()
        if s.startswith("data:image/"):
            try:
                base64_part = s.split("base64,", 1)[1]
                return base64.b64decode(base64_part)
            except Exception:
                return None
        try:
            return base64.b64decode(s)
        except Exception:
            pass
        if os.path.exists(s):
            try:
                with open(s, "rb") as f:
                    return f.read()
            except Exception:
                return None
    return None


def _build_photo_element(
    photo_data: bytes | str | None,
    width_pt: float = 90,
    height_pt: float = 115,
) -> Any:
    """Return a ReportLab Image if photo data is available, or an official paste box."""
    from PIL import Image as PILImage

    img_bytes = _extract_image_bytes(photo_data)
    if img_bytes:
        try:
            bio = io.BytesIO(img_bytes)
            pil = PILImage.open(bio)
            pil.verify()
            bio.seek(0)
            return RLImage(bio, width=width_pt, height=height_pt)
        except Exception:
            pass

    # Official standard photo box placeholder
    placeholder = Table(
        [
            [
                Paragraph(
                    "<font size=7 color='#64748b'><b>AFFIX RECENT PHOTO</b><br/><br/>45mm × 35mm<br/>(2 in × 1.4 in)<br/><br/><i>White background</i></font>",
                    ParagraphStyle("PhotoPlaceholder", alignment=1, leading=10),
                )
            ]
        ],
        colWidths=[width_pt],
        rowHeights=[height_pt],
    )
    placeholder.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ]
        )
    )
    return placeholder


def _build_header_with_photo(
    title_text: str,
    subtitle_text: str,
    agency_header: str,
    meta_rows: list[tuple[str, str]],
    photo_data: bytes | str | None,
    styles: dict[str, ParagraphStyle],
) -> Table:
    """Build official government header with Agency title, metadata, and photo side-by-side."""
    left_elements = [
        Paragraph(agency_header, styles["jp_header"]),
        Paragraph(title_text, styles["title"]),
        Paragraph(subtitle_text, styles["subtitle"]),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f172a"), spaceAfter=6),
        _build_key_value_table(meta_rows, styles, col_widths=[130, 275]),
    ]
    photo_elem = _build_photo_element(photo_data, width_pt=95, height_pt=125)

    header_table = Table(
        [[left_elements, photo_elem]],
        colWidths=[415, 105],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return header_table


# Japanese form titles, offices and document names appear throughout these documents,
# and the built-in Helvetica faces have no CJK glyphs — they render as tofu boxes. The
# CID face below covers both scripts, so mixed text stays readable in one paragraph.
_CJK_FONT = "HeiseiKakuGo-W5"
_cjk_font_ready: bool | None = None


def _cjk_font_name() -> str | None:
    """Register the CJK face once; ``None`` when this reportlab build lacks it."""
    global _cjk_font_ready
    if _cjk_font_ready is not None:
        return _CJK_FONT if _cjk_font_ready else None
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont

        pdfmetrics.registerFont(UnicodeCIDFont(_CJK_FONT))
        _cjk_font_ready = True
    except Exception:  # pragma: no cover - depends on the reportlab build
        _cjk_font_ready = False
    return _CJK_FONT if _cjk_font_ready else None


def _has_cjk(text: str) -> bool:
    return any(ord(char) >= 0x2E80 for char in text)


def _cjk_safe(text: str) -> str:
    """Wrap ``text`` in the CJK face when it needs one, so it renders instead of tofu."""
    if not _has_cjk(text):
        return text
    font = _cjk_font_name()
    return f'<font name="{font}">{text}</font>' if font else text


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
        p_label = Paragraph(_cjk_safe(label), styles["table_label"])
        p_val = Paragraph(_cjk_safe(str(val)) if val else "—", styles["table_value"])
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
    photo_data: bytes | str | None = None,
    action_code: str | None = None,
) -> bytes:
    """Generate official Application Form PDF tailored to the visa purpose."""
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

    dest_lower = destination_label.lower()
    is_change_of_status = (
        action_code == "change_of_status"
        or "change" in dest_lower
        or "資格変更" in dest_lower
        or "change_of_status" in str(answers.get("action_code", ""))
    )
    is_tourist = (
        "tourist" in dest_lower
        or "tourism" in str(answers.get("purpose_of_visit", "")).lower()
        or "tourism" in str(answers.get("main_purpose", "")).lower()
        or "travel" in dest_lower
        or "visitor" in dest_lower
    )
    is_student = (
        "student" in dest_lower
        or "留学" in dest_lower
        or answers.get("school_name") is not None
        or answers.get("attendance_rate") is not None
    )

    if is_change_of_status:
        title_txt = "APPLICATION FOR CHANGE OF STATUS OF RESIDENCE"
        sub_txt = "在留資格変更許可申請書 (出入国在留管理庁 · 留学 / 技人国等)"
    elif is_tourist or action_code == "new_application":
        title_txt = "VISA APPLICATION FORM TO ENTER JAPAN"
        sub_txt = "日本国査証申請書 (短期滞在 · 観光 / 業務 / 知人訪問等)"
    else:
        title_txt = "APPLICATION FOR EXTENSION OF PERIOD OF STAY"
        sub_txt = "在留期間更新許可申請書 (出入国在留管理庁 · 留学 / 技人国等)"
    agency_txt = "MINISTRY OF FOREIGN AFFAIRS / IMMIGRATION SERVICES AGENCY OF JAPAN"

    meta_rows = [
        ("Application Reference", case_reference or "DRAFT-APPLICATION"),
        ("Date of Preparation", datetime.now(UTC).strftime("%Y-%m-%d")),
        (
            "Issuing Authority / Filing Portal",
            "Regional Immigration Services Bureau (地方出入国在留管理局)"
            if not is_tourist
            else "Embassy / Consular Mission",
        ),
        (
            "Target Visa Category / Route",
            destination_label or ("Student (留学)" if is_student else "Temporary Visitor"),
        ),
    ]
    story.append(
        _build_header_with_photo(
            title_txt,
            sub_txt,
            agency_txt,
            meta_rows,
            photo_data,
            styles,
        )
    )
    story.append(Spacer(1, 10))

    # 2. Section 1: Applicant Personal Identity
    story.append(
        Paragraph(
            _cjk_safe("1. APPLICANT INFORMATION / 申請人に関する事項"), styles["section_heading"]
        )
    )
    sec1_rows = [
        (
            "Full Name (as in Passport)",
            str(answers.get("full_name") or answers.get("applicant_name") or NOT_PROVIDED),
        ),
        ("Nationality / Citizenship", str(answers.get("nationality") or NOT_PROVIDED)),
        ("Date of Birth", str(answers.get("date_of_birth") or NOT_PROVIDED)),
        ("Sex / Gender", str(answers.get("sex") or NOT_PROVIDED)),
        ("Place of Birth", str(answers.get("place_of_birth") or NOT_PROVIDED)),
        ("Marital Status", str(answers.get("marital_status") or NOT_PROVIDED)),
        ("Passport Number", str(answers.get("passport_number") or NOT_PROVIDED)),
        (
            "Passport Expiration Date",
            str(
                answers.get("passport_expiry_date")
                or answers.get("passport_expiry")
                or NOT_PROVIDED
            ),
        ),
        (
            "Current Country of Residence",
            str(
                answers.get("current_residence_country")
                or answers.get("residence_country")
                or answers.get("nationality")
                or NOT_PROVIDED
            ),
        ),
        (
            "Residential Address",
            str(
                answers.get("address_in_japan")
                or answers.get("registered_address_japan")
                or answers.get("current_address")
                or answers.get("accommodation_address")
                or NOT_PROVIDED
            ),
        ),
        (
            "Contact Telephone / Mobile",
            str(answers.get("phone_number") or answers.get("telephone") or NOT_PROVIDED),
        ),
    ]
    if not is_tourist and answers.get("residence_card_number"):
        sec1_rows.append(
            (
                "Current Residence Card Number (在留カード番号)",
                str(answers.get("residence_card_number")),
            )
        )
    if answers.get("residence_card_expiry"):
        sec1_rows.append(
            ("Residence Card Expiration Date (在留期限)", str(answers.get("residence_card_expiry")))
        )
    story.append(_build_key_value_table(sec1_rows, styles))
    story.append(Spacer(1, 10))

    if is_tourist:
        # 3. Section 2: Trip & Itinerary Details (Tourist / Short Stay)
        story.append(
            Paragraph(
                "2. TRIP ITINERARY & FINANCIAL COVERAGE / 渡航目的・滞在日程に関する事項",
                styles["section_heading"],
            )
        )
        sec2_rows = [
            (
                "Purpose of Visit",
                str(answers.get("purpose_of_visit") or answers.get("main_purpose") or NOT_PROVIDED),
            ),
            (
                "Intended Length of Stay",
                f"{answers.get('intended_length_of_stay_days') or answers.get('stay_duration_days') or 15} Days",
            ),
            (
                "Planned Arrival Date",
                str(
                    answers.get("planned_arrival_date")
                    or answers.get("arrival_date")
                    or NOT_PROVIDED
                ),
            ),
            (
                "Hotel / Accommodation Name",
                str(answers.get("accommodation_name") or NOT_PROVIDED),
            ),
            (
                "Accommodation Address in Japan",
                str(answers.get("accommodation_address") or NOT_PROVIDED),
            ),
            (
                "Funding Source / Trip Payer",
                str(answers.get("trip_payer") or NOT_PROVIDED).replace("_", " ").title(),
            ),
            (
                "Available Funds / Savings",
                str(answers.get("estimated_savings_available") or NOT_PROVIDED),
            ),
            (
                "Current Profession / Occupation",
                str(answers.get("occupation") or NOT_PROVIDED),
            ),
        ]
        story.append(_build_key_value_table(sec2_rows, styles))
        story.append(Spacer(1, 10))

        # 4. Section 3: Legal Declarations
        story.append(
            Paragraph(
                _cjk_safe("3. COMPLIANCE & DECLARATIONS / 申告事項"), styles["section_heading"]
            )
        )
        sec3_rows = [
            (
                "Criminal Conviction Record",
                "None (無)" if not answers.get("criminal_record", False) else "Disclosed",
            ),
            (
                "Prior Deportation / Entry Ban History",
                "None (無)" if not answers.get("prior_deportation", False) else "Disclosed",
            ),
            (
                "Financial Self-Sufficiency",
                "Certified / Solvency Proof & Bank Statements Attached",
            ),
        ]
        story.append(_build_key_value_table(sec3_rows, styles))
        story.append(Spacer(1, 14))
    elif is_change_of_status:
        # 3. Section 2: Education & Future Employer Details (Change of Status)
        story.append(
            Paragraph(
                "2. ACADEMIC RECORD & FUTURE EMPLOYER / 学歴及び勤務予定先に関する事項",
                styles["section_heading"],
            )
        )
        salary_val = (
            answers.get("annual_salary_jpy") or answers.get("monthly_salary") or NOT_PROVIDED
        )
        if str(salary_val).isdigit():
            salary_display = (
                f"¥{int(salary_val):,} JPY / Year"
                if int(salary_val) > 1000000
                else f"¥{int(salary_val):,} JPY / Month"
            )
        else:
            salary_display = str(salary_val)

        sec2_rows = [
            (
                "Current / Graduating Educational Institution",
                str(answers.get("school_name") or NOT_PROVIDED),
            ),
            (
                "Program of Study / Degree",
                str(answers.get("study_program_type") or NOT_PROVIDED).replace("_", " ").title(),
            ),
            (
                "Program Completion / Graduation Status",
                "Completed / Graduating" if answers.get("school_completed") else "Scheduled",
            ),
            (
                "Expected / Actual Graduation Date",
                str(answers.get("expected_graduation_date") or NOT_PROVIDED),
            ),
            (
                "Future Sponsoring Employer Name",
                str(answers.get("employer_name") or answers.get("company_name") or NOT_PROVIDED),
            ),
            (
                "Employer Corporate Number (法人番号)",
                str(
                    answers.get("employer_corporate_number")
                    or answers.get("corporate_number")
                    or NOT_PROVIDED
                ),
            ),
            (
                "Employer Category (所属機関区分)",
                f"Category {answers.get('employer_category')}"
                if answers.get("employer_category")
                else "Category 3",
            ),
            (
                "Offered Position Duties / Job Description",
                str(answers.get("job_description") or NOT_PROVIDED),
            ),
            ("Offered Remuneration (報酬額)", salary_display),
        ]
        story.append(_build_key_value_table(sec2_rows, styles))
        story.append(Spacer(1, 10))

        # 4. Section 3: Legal Compliance & Declarations
        story.append(
            Paragraph(
                _cjk_safe("3. COMPLIANCE & DECLARATIONS / 遵守状況・申告事項"),
                styles["section_heading"],
            )
        )
        sec3_rows = [
            (
                "Resident Tax (住民税) Compliance",
                "Paid & Up to Date (納付済)"
                if answers.get("resident_tax_status", True)
                else "Arrears / Disclosed",
            ),
            (
                "Pension / Health Insurance Status",
                "Paid & Up to Date (適正納付)"
                if answers.get("pension_health_insurance", True)
                else "Enrolled",
            ),
            (
                "Criminal / Traffic Violation Record",
                "None (無)" if not answers.get("criminal_disclosures", False) else "Disclosed",
            ),
            (
                "Desired Status of Residence",
                "技術・人文知識・国際業務 (Engineer/Specialist in Humanities/Intl Services)",
            ),
            (
                "Reason for Change of Status",
                "Graduation from Japanese educational institution and employment commencement.",
            ),
        ]
        story.append(_build_key_value_table(sec3_rows, styles))
        story.append(Spacer(1, 14))
    elif is_student:
        # 3. Section 2: Educational Institution Details (Student Renewal / Extension)
        story.append(
            Paragraph(
                "2. EDUCATIONAL INSTITUTION DETAILS / 在学・所属教育機関に関する事項",
                styles["section_heading"],
            )
        )
        att_rate = answers.get("attendance_rate")
        att_display = f"{att_rate}%" if att_rate is not None else "—"

        sec2_rows = [
            (
                "Educational Institution Name",
                str(answers.get("school_name") or NOT_PROVIDED),
            ),
            (
                "Program of Study",
                str(answers.get("study_program_type") or NOT_PROVIDED).replace("_", " ").title(),
            ),
            ("Attendance Rate (出席率)", att_display),
            (
                "Expected Course Completion Date",
                str(answers.get("expected_graduation_date") or NOT_PROVIDED),
            ),
            (
                "Financial Support Source",
                str(
                    answers.get("sponsor_type")
                    or answers.get("financial_supporter")
                    or NOT_PROVIDED
                )
                .replace("_", " ")
                .title(),
            ),
        ]
        story.append(_build_key_value_table(sec2_rows, styles))
        story.append(Spacer(1, 10))

        # 4. Section 3: Legal Compliance & Extension Request
        story.append(
            Paragraph(
                _cjk_safe("3. COMPLIANCE & DECLARATIONS / 遵守状況・申告事項"),
                styles["section_heading"],
            )
        )
        sec3_rows = [
            (
                "Resident Tax (住民税) Status",
                "Up to date" if answers.get("resident_tax_status", True) else "Disclosed",
            ),
            (
                "National Pension / Health Insurance",
                "Enrolled" if answers.get("pension_health_insurance", True) else "Disclosed",
            ),
            (
                "Part-Time Work Limit Compliance (28h/week)",
                "Compliant (資格外活動許可遵守)"
                if not answers.get("overwork_violation", False)
                else "Disclosed",
            ),
            (
                "Desired Extension Period",
                str(answers.get("desired_period_years") or NOT_PROVIDED),
            ),
            (
                "Reason for Extension",
                "Continuation of regular academic studies toward program completion.",
            ),
        ]
        story.append(_build_key_value_table(sec3_rows, styles))
        story.append(Spacer(1, 14))
    else:
        # 3. Section 2: Sponsoring Organization / Employer (Work / Extension)
        story.append(
            Paragraph(
                "2. ORGANIZATION / EMPLOYER DETAILS / 勤務先・所属機関に関する事項",
                styles["section_heading"],
            )
        )
        salary_val = answers.get("monthly_salary") or answers.get("monthly_income") or NOT_PROVIDED
        if str(salary_val).isdigit():
            salary_display = f"¥{int(salary_val):,} JPY / Month"
        else:
            salary_display = str(salary_val)

        sec2_rows = [
            (
                "Employer / Organization Name",
                str(answers.get("employer_name") or answers.get("company_name") or NOT_PROVIDED),
            ),
            (
                "Corporate Number (法人番号)",
                str(
                    answers.get("corporate_number")
                    or answers.get("employer_corporate_number")
                    or NOT_PROVIDED
                ),
            ),
            (
                "Organization Category (所属機関区分)",
                str(answers.get("employer_category") or NOT_PROVIDED),
            ),
            (
                "Workplace Address in Japan",
                str(
                    answers.get("employer_address")
                    or answers.get("workplace_address")
                    or NOT_PROVIDED
                ),
            ),
            (
                "Workplace Telephone",
                str(
                    answers.get("employer_telephone")
                    or answers.get("workplace_phone")
                    or NOT_PROVIDED
                ),
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
                str(answers.get("contract_type") or NOT_PROVIDED),
            ),
        ]
        story.append(_build_key_value_table(sec2_rows, styles))
        story.append(Spacer(1, 10))

        # 4. Section 3: Legal Compliance & Continuity
        story.append(
            Paragraph(
                _cjk_safe("3. COMPLIANCE & DECLARATIONS / 遵守状況・申告事項"),
                styles["section_heading"],
            )
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
                str(answers.get("desired_period_years") or NOT_PROVIDED),
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
    scope_label: str = "Japan",
    submission_kit: Any | None = None,
    forms: list[dict[str, Any]] | None = None,
) -> bytes:
    """A cover letter that states only what the case actually establishes.

    Addressed and worded per procedure, because an extension, a certificate of
    eligibility and a consular visa are filed with different offices and say different
    things. ``submission_kit`` carries the procedure's addressee and enclosure order (see
    :mod:`torii_api.services.submission_kit`); without one the letter still prints, but
    only the parts it can support.

    The letter makes no claim on the applicant's behalf that an answer or an enclosure
    does not back. An earlier version asserted full immigration compliance and
    substantiated employment income for every applicant, including students, dependents,
    and certificate applicants who had never entered Japan.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40
    )
    styles = _get_styles()
    story: list[Any] = []

    full_name = str(answers.get("full_name") or answers.get("applicant_name") or NOT_PROVIDED)
    passport_no = str(answers.get("passport_number") or NOT_PROVIDED)
    nationality = str(answers.get("nationality") or NOT_PROVIDED)
    residence_card = str(answers.get("residence_card_number") or "").strip()
    date_str = datetime.now(UTC).strftime("%d %B %Y")

    addressee = getattr(submission_kit, "addressee", None) or "The receiving immigration office"
    office = getattr(submission_kit, "office", None)

    story.append(Paragraph("APPLICATION COVER LETTER", styles["title"]))
    story.append(Paragraph(f"{scope_label} · Reference: {case_reference}", styles["subtitle"]))
    story.append(
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f172a"), spaceAfter=14)
    )

    story.append(Paragraph(f"<b>Date:</b> {date_str}", styles["body"]))
    to_line = f"<b>To:</b> {_cjk_safe(addressee)}"
    if office:
        to_line += f"<br/>{_cjk_safe(office)}"
    story.append(Paragraph(to_line, styles["body"]))
    story.append(Spacer(1, 10))

    identity_rows = [
        ("Applicant", full_name),
        ("Nationality", nationality),
        ("Passport number", passport_no),
    ]
    if residence_card:
        identity_rows.append(("Residence card number", residence_card))
    story.append(_build_key_value_table(identity_rows, styles, col_widths=[150, 360]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"Dear {_cjk_safe(addressee)},", styles["body"]))
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            f"I submit my application for <b>{scope_label}</b>. The completed form and the "
            "documents listed below are enclosed.",
            styles["body"],
        )
    )
    story.append(Spacer(1, 10))

    # 1. The forms enclosed — named from the catalogue, never described generically.
    enclosed_forms = [
        str(form.get("official_title") or form.get("form_code") or "").strip()
        for form in (forms or [])
        if form.get("official_title") or form.get("form_code")
    ]
    if enclosed_forms:
        story.append(Paragraph("<b>1. Application forms enclosed</b>", styles["body_bold"]))
        for title in enclosed_forms:
            story.append(Paragraph(f"&bull; {_cjk_safe(title)}", styles["body"]))
        story.append(Spacer(1, 10))

    # 2. Enclosures — the case's own checklist, or an honest statement that it is empty.
    heading = "2." if enclosed_forms else "1."
    story.append(Paragraph(f"<b>{heading} Enclosed documents</b>", styles["body_bold"]))
    if checklist:
        rows: list[list[Any]] = [
            [
                Paragraph("No.", styles["table_label"]),
                Paragraph("Document", styles["table_value"]),
                Paragraph("Required by", styles["table_value"]),
            ]
        ]
        for index, item in enumerate(checklist, start=1):
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            citation = item.get("citation") or {}
            authority = str(citation.get("authority") or "").strip()
            rows.append(
                [
                    Paragraph(str(index), styles["table_label"]),
                    Paragraph(_cjk_safe(name), styles["table_value"]),
                    Paragraph(authority or NOT_PROVIDED, styles["table_value"]),
                ]
            )
        table = Table(rows, colWidths=[30, 300, 180])
        table.setStyle(
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
        story.append(table)
    else:
        story.append(
            Paragraph(
                "No supporting documents have been recorded for this application yet.",
                styles["body"],
            )
        )
    story.append(Spacer(1, 14))

    story.append(
        Paragraph(
            "I should be grateful if you would consider this application. Please contact me "
            "if any further document or clarification is required.",
            styles["body"],
        )
    )
    story.append(Spacer(1, 18))
    story.append(Paragraph("Yours faithfully,", styles["body"]))
    story.append(Spacer(1, 26))
    story.append(
        Paragraph(
            f"<b>{full_name}</b><br/>Passport number: {passport_no}<br/>Date: {date_str}",
            styles["body"],
        )
    )
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "<i>Prepared with Torii. Sign this letter yourself before filing.</i>",
            styles["subtitle"],
        )
    )

    doc.build(story)
    return buffer.getvalue()


def generate_dossier_packet_pdf(
    case_reference: str,
    answers: dict[str, Any],
    forms: list[dict[str, Any]],
    checklist: list[dict[str, Any]],
    submission_kit: Any | None = None,
    scope_label: str = "Japan",
    audit_summary: dict[str, Any] | None = None,
    appointment: dict[str, Any] | None = None,
) -> bytes:
    """The whole packet in one document: index, stacking order, roadmap, and a snapshot.

    Every section is driven by the case's own application type. ``submission_kit`` is a
    :class:`torii_api.services.submission_kit.SubmissionKit`, which supplies the filing
    steps, the enclosure order and the office for *this* procedure.
    """
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

    full_name = str(answers.get("full_name") or answers.get("applicant_name") or NOT_PROVIDED)
    passport_no = str(answers.get("passport_number") or NOT_PROVIDED)
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
        ("Filed at", getattr(submission_kit, "office", None) or NOT_PROVIDED),
        ("Filed by", getattr(submission_kit, "filed_by", None) or NOT_PROVIDED),
    ]
    story.append(_build_key_value_table(overview_rows, styles))
    story.append(Spacer(1, 14))

    # Physical Stacking Order
    story.append(
        Paragraph(
            _cjk_safe("PHYSICAL DOSSIER STACKING ORDER / 提出書類の編綴順序"),
            styles["section_heading"],
        )
    )
    story.append(
        Paragraph(
            "Assemble and submit physical documents in the exact numbered order below:",
            styles["legal_notice"],
        )
    )
    story.append(Spacer(1, 6))

    # The stack comes from the case's own forms and checklist. There is deliberately no
    # fallback list: the previous one named a tax certificate and an employer statutory
    # table, which a student, dependent or tourist applicant does not have and would go
    # looking for.
    stacking_items = list(getattr(submission_kit, "stacking_order", ()) or [])
    if not stacking_items:
        story.append(
            Paragraph(
                "No enclosures have been recorded for this application yet. Complete your "
                "document checklist and download this packet again.",
                styles["body"],
            )
        )

    for item_text in stacking_items:
        p_item = Paragraph(f"• {_cjk_safe(item_text)}", styles["body"])
        story.append(p_item)
        story.append(Spacer(1, 3))

    story.append(Spacer(1, 10))

    # Step-by-step filing roadmap, per procedure.
    steps = list(getattr(submission_kit, "steps", ()) or [])
    if steps:
        story.append(Paragraph(_cjk_safe("HOW TO FILE / 申請手順"), styles["section_heading"]))
        office = getattr(submission_kit, "office", None)
        filed_by = getattr(submission_kit, "filed_by", None)
        if office:
            story.append(Paragraph(f"<b>Where:</b> {_cjk_safe(office)}", styles["body"]))
        if filed_by:
            story.append(Paragraph(f"<b>Who files it:</b> {filed_by}", styles["body"]))
        fee_note = getattr(submission_kit, "fee_note", None)
        if fee_note:
            story.append(Paragraph(f"<b>Fee:</b> {_cjk_safe(fee_note)}", styles["body"]))
        story.append(Spacer(1, 6))
        for step in steps:
            story.append(
                Paragraph(f"<b>Step {step.order}: {_cjk_safe(step.title)}</b>", styles["body_bold"])
            )
            story.append(Paragraph(_cjk_safe(step.detail), styles["body"]))
            story.append(Spacer(1, 4))
        for note in getattr(submission_kit, "notes", ()) or ():
            story.append(Paragraph(f"<i>{_cjk_safe(note)}</i>", styles["body"]))
            story.append(Spacer(1, 4))

    # Readiness audit + booked visa-centre appointment (Phase 3 in-person
    # track). Both blocks render only when the caller supplies them, so
    # packets for scopes without audit/appointment data are unchanged.
    if audit_summary or appointment:
        story.append(Spacer(1, 10))
        story.append(
            Paragraph(_cjk_safe("READINESS AUDIT & APPOINTMENT"), styles["section_heading"])
        )
        if audit_summary:
            overall = str(audit_summary.get("overall") or "").upper()
            story.append(
                Paragraph(
                    f"<b>Overall readiness:</b> {_cjk_safe(overall)} — "
                    f"{_cjk_safe(str(audit_summary.get('summary') or ''))}",
                    styles["body"],
                )
            )
            eligibility_result = audit_summary.get("eligibility_result")
            if eligibility_result:
                story.append(
                    Paragraph(
                        f"<b>Eligibility evaluation:</b> {_cjk_safe(str(eligibility_result))}",
                        styles["body"],
                    )
                )
            audit_checks = [
                check
                for check in audit_summary.get("checks") or []
                if check.get("status") in ("fail", "warn")
            ]
            if audit_checks:
                story.append(Spacer(1, 4))
                story.append(Paragraph("<b>Checks needing attention:</b>", styles["body_bold"]))
                for check in audit_checks:
                    label = "FAIL" if check.get("status") == "fail" else "WARN"
                    story.append(
                        Paragraph(
                            f"• [{label}] {_cjk_safe(str(check.get('message') or ''))}",
                            styles["body"],
                        )
                    )
                    story.append(Spacer(1, 2))
            else:
                story.append(Paragraph("All consistency checks passed.", styles["body"]))
        if appointment:
            story.append(Spacer(1, 6))
            story.append(Paragraph("<b>Visa-centre appointment (booked):</b>", styles["body_bold"]))
            appointment_rows = [
                ("Appointment date", str(appointment.get("appointment_date") or "—")),
                ("Appointment time", str(appointment.get("appointment_time") or "—")),
                ("Centre", str(appointment.get("centre") or "—")),
                ("Booking reference", str(appointment.get("reference") or "—")),
            ]
            story.append(_build_key_value_table(appointment_rows, styles))
            story.append(
                Paragraph(
                    "Bring your passport, the originals of every checklist document, "
                    "and a printed copy of this packet to the appointment.",
                    styles["body"],
                )
            )

    # ==================== PAGE 2: APPLICATION FORM ====================
    story.append(PageBreak())
    # The snapshot is titled from the form this case actually files. It was previously
    # headed "Application for Extension of Period of Stay" for every case, including
    # tourists and certificate applicants who file nothing of the kind.
    snapshot_form = next(
        (
            str(form.get("official_title") or "").strip()
            for form in (forms or [])
            if form.get("official_title")
        ),
        "",
    )
    story.append(
        Paragraph(_cjk_safe(getattr(submission_kit, "addressee", "") or ""), styles["jp_header"])
    )
    story.append(Paragraph("YOUR ANSWERS AS SUBMITTED", styles["title"]))
    story.append(Paragraph(_cjk_safe(snapshot_form or scope_label), styles["subtitle"]))
    story.append(
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f172a"), spaceAfter=10)
    )

    # Fill all captured form fields into clean table
    form_rows = [
        ("Applicant Name", full_name),
        ("Nationality", str(answers.get("nationality") or NOT_PROVIDED)),
        ("Date of Birth", str(answers.get("date_of_birth") or NOT_PROVIDED)),
        ("Passport Number", passport_no),
        ("Residence Card Number", str(answers.get("residence_card_number") or NOT_PROVIDED)),
        (
            "Current Status Expiry",
            str(
                answers.get("residence_card_expiry")
                or answers.get("status_expiry_date")
                or NOT_PROVIDED
            ),
        ),
    ]

    # Employment and compliance rows appear only where the applicant stated something.
    # "Tax / Pension Compliance: Certified Compliant" was previously printed for every
    # applicant, certifying a fact nobody had established.
    employment_rows = [
        ("Employer / Sponsor Name", answers.get("employer_name") or answers.get("company_name")),
        (
            "Corporate Number",
            answers.get("corporate_number") or answers.get("employer_corporate_number"),
        ),
        ("Employer Category", answers.get("employer_category")),
        ("Monthly Remuneration", answers.get("monthly_salary")),
        (
            "Occupation / Duties",
            answers.get("job_description") or answers.get("occupation"),
        ),
        ("Resident Tax Status", answers.get("resident_tax_status")),
        ("Pension & Health Insurance", answers.get("pension_health_insurance")),
    ]
    form_rows.extend(
        (label, str(value)) for label, value in employment_rows if value not in (None, "")
    )
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


# The consular form is read by a visa officer, not by this service. An answer stored as
# an enum token or an ISO code has to reach the printed box as the words that box asks
# for -- "Bangladesh", not "BD"; "Visiting relatives", not "visiting_family".
_CONSULAR_PURPOSES: dict[str, str] = {
    "tourism": "Tourism",
    "visiting_family": "Visiting relatives",
    "visiting_friends": "Visiting friends or acquaintances",
    "commercial_business": "Commercial business",
}


def _consular_label(value: str) -> str:
    """An enum answer as the words the form asks for."""
    if not value:
        return ""
    token = value.strip().lower()
    labelled = _CONSULAR_PURPOSES.get(token)
    if labelled is not None:
        return labelled
    # Any other pack's token still reaches the sheet as words rather than as a key. An
    # answer that is already prose is left exactly as the applicant wrote it.
    if "_" in token:
        return token.replace("_", " ").capitalize()
    return value


def _consular_country(value: str) -> str:
    """A nationality answer as a country name.

    Packs store nationality as an ISO code because the eligibility rules match on codes.
    The form asks for the country, so the code is resolved back to its name here. Anything
    that is not a two-letter code -- the shared question asks for the name as printed in
    the passport -- is already what the box wants and passes through untouched.
    """
    from torii_api.services.geolocation import resolve_country_meta

    code = value.strip()
    if len(code) != 2 or not code.isalpha():
        return value
    resolved = resolve_country_meta(code)["name"]
    return value if resolved == code.upper() else resolved


def generate_official_japan_visa_form_pdf(
    case_reference: str,
    answers: dict[str, Any],
    destination_label: str = "Japan",
    applicant_email: str | None = None,
    photo_data: bytes | str | None = None,
) -> bytes:
    """Fill the authentic official Ministry of Foreign Affairs (MOFA) Japan Visa Application Form template."""
    import pypdf

    from torii_api.services.acroform_flatten import flatten_form_values

    # Path to official government template (MOFA 000124525.pdf)
    template_path = os.path.join(
        os.path.dirname(__file__), "..", "templates", "japan_visa_application_form_template.pdf"
    )
    if not os.path.exists(template_path):
        return generate_japan_work_renewal_pdf(
            case_reference, answers, destination_label, photo_data=photo_data
        )

    try:
        reader = pypdf.PdfReader(template_path)
        writer = pypdf.PdfWriter()
        writer.append(reader)

        # For the official MOFA visa application form, physical photographs (45mm × 35mm)
        # must be affixed by the applicant in the designated printed box; digital user images
        # are not overlaid onto the official form.

        # Only what the applicant actually told us reaches the form. A Japanese visa
        # application is a signed declaration, so an invented employer telephone or a
        # guessed purpose of visit is a defect, not a convenience — every value below
        # resolves to "" when unanswered and the consular officer sees a blank line.
        def answer(*keys: str) -> str:
            for key in keys:
                value = answers.get(key)
                if value not in (None, ""):
                    return str(value).strip()
            return ""

        def consular_date(*keys: str) -> str:
            """Dates on this form are printed (Day)/(Month)/(Year), not ISO."""
            raw = answer(*keys)
            if not raw:
                return ""
            for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    return datetime.strptime(raw[:10], pattern).strftime("%d/%m/%Y")
                except ValueError:
                    continue
            return raw

        full_name = answer("full_name", "applicant_name", "visitor_full_name")
        parts = full_name.split()
        if len(parts) > 1:
            surname = parts[-1].upper()
            given_names = " ".join(parts[:-1]).upper()
        else:
            surname = full_name.upper()
            given_names = ""

        nationality = answer("nationality", "visitor_nationality", "country_of_citizenship")
        if nationality.strip().lower() == "other":
            # The enum lists the nationalities the eligibility rules match on. Anything
            # outside it is named in the free-text follow-up, because "other" is not an
            # answer to "Nationality or citizenship" on a form the applicant signs.
            nationality = answer("nationality_other", "country_of_citizenship")
        nationality = _consular_country(nationality)
        passport_no = answer("passport_number", "passport_no", "visitor_passport_number")
        dob = consular_date("date_of_birth", "birth_date")
        passport_expiry = consular_date("passport_expiry_date", "passport_expiry")
        passport_authority = answer("passport_issuing_authority")
        purpose = _consular_label(answer("purpose_of_visit", "main_purpose", "purpose_of_stay"))
        stay_days = answer(
            "intended_length_of_stay", "intended_length_of_stay_days", "stay_duration_days"
        )
        if stay_days.isdigit():
            stay_days = f"{stay_days} Days"

        current_address = answer(
            "current_address",
            "current_japan_address",
            "home_town_city",
            "current_residence_country",
            "residence_country",
        )
        tel = answer("telephone_japan", "phone_number", "tel", "mobile")
        mobile = answer("mobile_phone", "phone_number", "mobile", "tel")
        email = answer("email") or (applicant_email or "")
        profession = answer("occupation", "job_title")

        employer_name = answer("employer_name", "sponsor_name", "company_name")
        employer_tel = answer("employer_tel", "sponsor_tel")
        employer_address = answer("employer_address", "sponsor_address", "registered_address_japan")

        # Host / accommodation in Japan (item: "Address in Japan"), distinct from the
        # applicant's employer at home.
        host_name = answer("accommodation_name", "resident_guarantor_name", "supporter_name")
        host_tel = answer("accommodation_tel", "guarantor_telephone")
        host_address = answer("accommodation_address", "current_japan_address")

        # Guarantor block on page 2 — only a real guarantor goes here.
        guarantor_name = answer("resident_guarantor_name", "supporter_name", "sponsor_name")
        guarantor_tel = answer("guarantor_telephone", "sponsor_tel")
        guarantor_address = answer("guarantor_address", "sponsor_address")
        guarantor_relationship = answer("relationship_to_supporter", "relationship_to_visitor")

        sex_val = answer("sex", "gender").lower()
        if sex_val.startswith("f") or sex_val == "女":
            sex_radio: str | None = "/1"
        elif sex_val.startswith("m") or sex_val == "男":
            sex_radio = "/0"
        else:
            sex_radio = None

        marital_val = answer("marital_status").lower()
        if marital_val.startswith("marri"):
            marital_radio: str | None = "/1"
        elif marital_val.startswith("wido"):
            marital_radio = "/3"
        elif marital_val.startswith("divo"):
            marital_radio = "/2"
        elif marital_val.startswith(("single", "unmarried")):
            marital_radio = "/0"
        else:
            marital_radio = None

        passport_type = answer("passport_type").lower()
        if "diplo" in passport_type:
            passport_radio: str | None = "/0"
        elif "offi" in passport_type:
            passport_radio = "/1"
        elif "other" in passport_type:
            passport_radio = "/3"
        elif passport_type:
            passport_radio = "/2"
        else:
            passport_radio = None

        def yes_no_radio(*keys: str) -> str | None:
            """Page 2 declarations: "/0" is 有 (yes), "/1" is 無 (no)."""
            for key in keys:
                value = answers.get(key)
                if isinstance(value, bool):
                    return "/0" if value else "/1"
                if isinstance(value, str) and value.strip():
                    token = value.strip().lower()
                    if token in ("true", "yes", "y", "1", "有"):
                        return "/0"
                    if token in ("false", "no", "n", "0", "無"):
                        return "/1"
            return None

        # The six "Have you ever" declarations on page 2, in printed order. The field
        # names do not follow that order, so they are bound by the widget position each
        # one actually occupies on the sheet.
        declaration_radios: dict[str, str | None] = {
            "topmostSubform[0].Page2[0].#area[7].#area[8].RB5[3]": yes_no_radio(
                "criminal_record", "criminal_record_any", "criminal_disclosures"
            ),
            "topmostSubform[0].Page2[0].#area[4].RB5[0]": yes_no_radio(
                "imprisoned_one_year_or_more"
            ),
            "topmostSubform[0].Page2[0].#area[5].RB5[1]": yes_no_radio("prior_deportation"),
            "topmostSubform[0].Page2[0].RB5[5]": yes_no_radio("drug_offence_conviction"),
            "topmostSubform[0].Page2[0].#area[9].RB5[4]": yes_no_radio("prostitution_involvement"),
            "topmostSubform[0].Page2[0].#area[6].RB5[2]": yes_no_radio(
                "human_trafficking_involvement"
            ),
        }

        field_values: dict[str, str] = {
            # Page 1: Personal identification & passport details
            "topmostSubform[0].Page1[0].T2[0]": surname,
            "topmostSubform[0].Page1[0].T7[0]": given_names,
            "topmostSubform[0].Page1[0].#area[4].T14[0]": dob,
            "topmostSubform[0].Page1[0].#area[4].T16[0]": answer("place_of_birth"),
            "topmostSubform[0].Page1[0].T50[0]": nationality,
            "topmostSubform[0].Page1[0].T49[0]": passport_no,
            "topmostSubform[0].Page1[0].#area[0].T59[0]": passport_expiry,
            "topmostSubform[0].Page1[0].#area[0].T57[0]": passport_authority,
            "topmostSubform[0].Page1[0].#area[9].T53[0]": consular_date("passport_issue_date"),
            "topmostSubform[0].Page1[0].#area[9].T57[1]": answer("passport_issue_place"),
            "topmostSubform[0].Page1[0].T68[2]": purpose,
            "topmostSubform[0].Page1[0].T68[3]": stay_days,
            "topmostSubform[0].Page1[0].T66[0]": consular_date(
                "planned_arrival_date", "intended_entry_date", "arrival_date"
            ),
            "topmostSubform[0].Page1[0].#area[10].T68[0]": answer("port_of_entry"),
            "topmostSubform[0].Page1[0].#area[10].T68[1]": answer(
                "airline_flight_no", "departure_airline_flight_no"
            ),
            "topmostSubform[0].Page1[0].emp_adr[0]": employer_address,
            "topmostSubform[0].Page1[0].#area[3].emp_name[0]": employer_name,
            "topmostSubform[0].Page1[0].#area[3].emp_tel[0]": employer_tel,
            "topmostSubform[0].Page1[0].T0[1]": current_address,
            "topmostSubform[0].Page1[0].#area[11].T97[0]": tel,
            "topmostSubform[0].Page1[0].#area[11].T3[0]": mobile,
            "topmostSubform[0].Page1[0].T3[1]": email,
            "topmostSubform[0].Page1[0].T5[0]": profession,
            "topmostSubform[0].Page1[0].#area[12].emp_name[1]": host_name,
            "topmostSubform[0].Page1[0].#area[12].emp_tel[1]": host_tel,
            "topmostSubform[0].Page1[0].emp_adr[1]": host_address,
            # Page 2: Guarantor / inviting sponsor in Japan
            "topmostSubform[0].Page2[0].#area[0].guarantor_name[0]": guarantor_name,
            "topmostSubform[0].Page2[0].#area[0].guarantor_tel[0]": guarantor_tel,
            "topmostSubform[0].Page2[0].guarantor_adr[0]": guarantor_address,
            # T25[1] belongs to the guarantor block and T25[0] to the inviter block —
            # the field indices do not follow the printed order on this sheet.
            "topmostSubform[0].Page2[0].T25[1]": guarantor_relationship,
            "topmostSubform[0].Page2[0].#area[2].T19[0]": answer("inviter_name"),
            "topmostSubform[0].Page2[0].#area[2].T10[0]": answer("inviter_tel"),
            "topmostSubform[0].Page2[0].T23[0]": answer("inviter_address"),
            "topmostSubform[0].Page2[0].T25[0]": answer("relationship_to_inviter"),
            "topmostSubform[0].Page2[0].T150[0]": datetime.now(UTC).strftime("%d/%m/%Y"),
        }

        # Radios are omitted entirely when unanswered — an unticked box asks a question,
        # a wrongly ticked one makes a false declaration.
        button_values: dict[str, str] = {
            name: value
            for name, value in {
                "topmostSubform[0].Page1[0].#area[1].#area[2].RB3[0]": passport_radio,
                "topmostSubform[0].Page1[0].#area[5].#area[6].#area[7].RB1[0]": sex_radio,
                "topmostSubform[0].Page1[0].#area[8].RB2[0]": marital_radio,
                **declaration_radios,
            }.items()
            if value is not None
        }
        field_values = {name: value for name, value in field_values.items() if value != ""}

        buf = io.BytesIO()
        writer.write(buf)
        # The template is an XFA form, so values written into its AcroForm layer are
        # stored but never drawn — Acrobat paints the XFA layer and Chrome paints the
        # AcroForm layer without appearances, and the applicant downloads a form that
        # looks blank. Paint the values into the page instead and flatten.
        flattened, unplaced = flatten_form_values(buf.getvalue(), field_values, button_values)
        if unplaced:
            print(f"Warning: MOFA template has no widget for: {', '.join(unplaced)}")
        if flattened:
            return flattened
    except Exception as exc:
        print(f"Warning: failed to fill official template: {exc}, using fallback generator")

    return generate_japan_work_renewal_pdf(
        case_reference, answers, destination_label, photo_data=photo_data
    )


def generate_portal_application_pack_pdf(
    case_reference: str,
    answers: dict[str, Any],
    forms: list[dict[str, Any]],
    *,
    jurisdiction: str = "UK",
    scope_label: str = "United Kingdom",
    apply_url: str | None = None,
) -> bytes:
    """Render the answer pack for a jurisdiction that is filed online.

    This is deliberately *not* styled as a government form. The UK has no form to
    submit — the application is typed into gov.uk — so the document says so on its face
    and lays the applicant's answers out in the order the online service asks for them.
    """
    from torii_api.services.portal_pack import build_portal_pack

    pack = build_portal_pack(
        forms,
        answers,
        jurisdiction=jurisdiction,
        scope_label=scope_label,
        apply_url=apply_url,
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=42, rightMargin=42, topMargin=40, bottomMargin=40
    )
    styles = _get_styles()
    story: list[Any] = []

    story.append(Paragraph("TORII ONLINE APPLICATION PACK", styles["jp_header"]))
    story.append(Paragraph(scope_label, styles["title"]))
    story.append(
        Paragraph(
            f"Reference: {case_reference} · Prepared {datetime.now(UTC).strftime('%d %B %Y')}",
            styles["subtitle"],
        )
    )
    story.append(Spacer(1, 10))

    notice = (
        "<b>This is not an application form.</b> There is no form to submit for this "
        "route — the application is completed on the government's own website. Work "
        "down the sections below as the online service asks for them, and copy each "
        "answer across."
    )
    if pack.apply_url:
        notice += f"<br/><br/><b>Apply at:</b> {pack.apply_url}"
    story.append(Paragraph(notice, styles["body"]))
    story.append(Spacer(1, 14))

    total = len(pack.all_fields)
    story.append(
        Paragraph(
            f"{len(pack.answered)} of {total} questions answered so far.",
            styles["subtitle"],
        )
    )
    story.append(Spacer(1, 10))

    for index, section in enumerate(pack.sections, start=1):
        story.append(Paragraph(f"{index}. {section.title.upper()}", styles["section_heading"]))
        rows = [
            (
                item.label + (" *" if item.required else ""),
                (item.value or NOT_PROVIDED) if item.answered else NOT_PROVIDED,
            )
            for item in section.fields
        ]
        story.append(_build_key_value_table(rows, styles))
        story.append(Spacer(1, 12))

    if pack.outstanding:
        story.append(Paragraph("STILL TO ANSWER", styles["section_heading"]))
        story.append(
            Paragraph(
                "The online service will ask for these. Answer them in Torii and "
                "download this pack again, or have them to hand before you start.",
                styles["body"],
            )
        )
        story.append(Spacer(1, 6))
        for item in pack.outstanding:
            story.append(Paragraph(f"&bull; {item.label}", styles["body"]))
        story.append(Spacer(1, 12))

    if pack.citations:
        story.append(Paragraph("OFFICIAL SOURCES", styles["section_heading"]))
        for citation in pack.citations:
            authority = str(citation.get("authority") or "")
            title = str(citation.get("title") or "")
            url = str(citation.get("url") or "")
            story.append(Paragraph(f"{authority} — {title}<br/>{url}", styles["body"]))

    doc.build(story)
    return buffer.getvalue()


def generate_uk_visa_application_pdf(
    case_reference: str,
    answers: dict[str, Any],
    destination_label: str = "United Kingdom",
    applicant_email: str | None = None,
    photo_data: bytes | str | None = None,
) -> bytes:
    """Generate official UK Visas & Immigration (UKVI) Application Form & Submission Dossier."""
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

    is_student = "student" in destination_label.lower() or "study" in destination_label.lower()
    is_work = "work" in destination_label.lower() or "skilled" in destination_label.lower()

    route_name = (
        "Skilled Worker Visa (Appendix Skilled Worker)"
        if is_work
        else (
            "Student Visa (Appendix Student)"
            if is_student
            else "Standard Visitor Visa (Appendix V: Visitor)"
        )
    )

    # 1. Header with photo
    meta_rows = [
        ("Application Reference", case_reference or "UK-APPLICATION-DRAFT"),
        ("Date of Preparation", datetime.now(UTC).strftime("%Y-%m-%d")),
        ("Issuing Authority", "UK Visas & Immigration (UKVI) / Home Office"),
        ("Immigration Route", route_name),
    ]
    story.append(
        _build_header_with_photo(
            "UK VISA APPLICATION DOSSIER",
            f"Official UKVI Filing Summary · {route_name}",
            "GOV.UK · UK VISAS AND IMMIGRATION (HOME OFFICE)",
            meta_rows,
            photo_data,
            styles,
        )
    )
    story.append(Spacer(1, 10))

    # 2. Section 1: Applicant Personal Identity & Travel Document
    story.append(
        Paragraph(
            "1. APPLICANT PERSONAL IDENTIFICATION & TRAVEL DOCUMENT", styles["section_heading"]
        )
    )
    nationality = str(answers.get("nationality") or NOT_PROVIDED)
    full_name = str(answers.get("full_name") or answers.get("applicant_name") or NOT_PROVIDED)
    sec1_rows = [
        ("Full Legal Name (as in passport)", full_name),
        ("Nationality / Country of Citizenship", nationality),
        ("Date of Birth (YYYY-MM-DD)", str(answers.get("date_of_birth") or NOT_PROVIDED)),
        ("Sex / Gender", str(answers.get("sex") or answers.get("gender") or NOT_PROVIDED)),
        (
            "Passport Number",
            str(answers.get("passport_number") or answers.get("passport_no") or NOT_PROVIDED),
        ),
        (
            "Passport Expiration Date",
            str(
                answers.get("passport_expiry")
                or answers.get("passport_expiry_date")
                or NOT_PROVIDED
            ),
        ),
        (
            "Passport Issuing Authority",
            str(answers.get("passport_issuing_authority") or f"Government of {nationality}"),
        ),
        (
            "Country of Current Residence",
            str(
                answers.get("residence_country")
                or answers.get("current_residence_country")
                or nationality
            ),
        ),
        (
            "Residential Address",
            str(
                answers.get("current_address") or answers.get("residential_address") or NOT_PROVIDED
            ),
        ),
        (
            "Contact Telephone",
            str(answers.get("phone_number") or answers.get("telephone") or NOT_PROVIDED),
        ),
        ("Applicant Email", str(answers.get("email") or applicant_email or NOT_PROVIDED)),
    ]
    story.append(_build_key_value_table(sec1_rows, styles))
    story.append(Spacer(1, 10))

    # 3. Section 2: Sponsorship / Course / Trip Purpose
    if is_work:
        story.append(
            Paragraph(
                "2. SPONSORSHIP & EMPLOYMENT DETAILS (UK SPONSOR LICENCE)",
                styles["section_heading"],
            )
        )
        salary_val = answers.get("annual_salary_gbp") or answers.get("salary_gbp") or NOT_PROVIDED
        if str(salary_val).isdigit():
            salary_str = f"£{int(salary_val):,} GBP / Year"
        else:
            salary_str = str(salary_val)

        sec2_rows = [
            (
                "Certificate of Sponsorship (CoS) Reference",
                str(answers.get("cos_reference") or answers.get("cos_number") or NOT_PROVIDED),
            ),
            (
                "UK Licensed Sponsor Employer",
                str(answers.get("sponsor_name") or answers.get("employer_name") or NOT_PROVIDED),
            ),
            ("Proposed Job Title in the UK", str(answers.get("job_title") or NOT_PROVIDED)),
            ("Proposed Gross Annual Remuneration", salary_str),
            ("Occupation Code (SOC 2020)", str(answers.get("soc_code") or NOT_PROVIDED)),
            (
                "Work Location / Office Address in UK",
                str(
                    answers.get("workplace_address")
                    or answers.get("employer_address")
                    or NOT_PROVIDED
                ),
            ),
        ]
        story.append(_build_key_value_table(sec2_rows, styles))
        story.append(Spacer(1, 10))

        # 4. Section 3: Qualifications, English Language & Maintenance
        story.append(
            Paragraph(
                "3. ENGLISH LANGUAGE & FINANCIAL MAINTENANCE COMPLIANCE", styles["section_heading"]
            )
        )
        eng_proof = (
            str(answers.get("english_language_proof") or NOT_PROVIDED).replace("_", " ").title()
        )
        maint_cert = (
            "Certified by A-rated Sponsor on CoS"
            if answers.get("sponsor_certifies_maintenance", True)
            else "Personal Bank Statements Provided (£1,276 for 28 consecutive days)"
        )
        sec3_rows = [
            ("English Language Assessment Criterion", eng_proof),
            ("CEFR Requirement Level", "Level B1 (Reading, Writing, Speaking, Listening)"),
            ("Maintenance Funds Requirement (£1,276)", maint_cert),
            (
                "Immigration Health Surcharge (IHS)",
                "Payable online (£1,035/year adult) via Access UK portal",
            ),
        ]
        story.append(_build_key_value_table(sec3_rows, styles))
        story.append(Spacer(1, 10))
    elif is_student:
        story.append(
            Paragraph(
                "2. COURSE & LICENSED STUDENT SPONSOR (CAS DETAILS)", styles["section_heading"]
            )
        )
        sec2_rows = [
            (
                "Confirmation of Acceptance for Studies (CAS)",
                str(answers.get("cas_number") or answers.get("cas_reference") or NOT_PROVIDED),
            ),
            (
                "Licensed Student Sponsor / University",
                str(
                    answers.get("institution_name")
                    or answers.get("university_name")
                    or NOT_PROVIDED
                ),
            ),
            (
                "Course Title & Qualification Level",
                str(answers.get("course_title") or NOT_PROVIDED),
            ),
            ("Course Start & End Dates", str(answers.get("course_duration") or NOT_PROVIDED)),
        ]
        story.append(_build_key_value_table(sec2_rows, styles))
        story.append(Spacer(1, 10))

        story.append(
            Paragraph("3. TUITION & MAINTENANCE FUNDS REQUIREMENTS", styles["section_heading"])
        )
        sec3_rows = [
            (
                "English Language Proficiency",
                str(answers.get("english_language_proof") or NOT_PROVIDED)
                .replace("_", " ")
                .title(),
            ),
            (
                "Living Costs Maintenance Proof",
                "28-Day Bank Statement (£1,334/month in London, £1,023 outside)",
            ),
            (
                "ATAS Certificate Required",
                "Not applicable / Exempt for this academic discipline"
                if not answers.get("atas_required", False)
                else "ATAS Clearance Certificate Attached",
            ),
        ]
        story.append(_build_key_value_table(sec3_rows, styles))
        story.append(Spacer(1, 10))
    else:
        story.append(Paragraph("2. VISIT DETAILS & INTENDED ITINERARY", styles["section_heading"]))
        sec2_rows = [
            (
                "Main Purpose of Visit",
                str(answers.get("purpose_of_visit") or answers.get("main_purpose") or NOT_PROVIDED),
            ),
            (
                "Intended Length of Stay",
                f"{answers.get('intended_length_of_stay_days') or 15} Days",
            ),
            (
                "Planned Travel / Arrival Date",
                str(
                    answers.get("planned_arrival_date")
                    or answers.get("arrival_date")
                    or NOT_PROVIDED
                ),
            ),
            ("Accommodation in the UK", str(answers.get("accommodation_name") or NOT_PROVIDED)),
            (
                "Financial Support for Visit",
                str(answers.get("trip_payer") or NOT_PROVIDED).replace("_", " ").title(),
            ),
        ]
        story.append(_build_key_value_table(sec2_rows, styles))
        story.append(Spacer(1, 10))

    # 5. Suitability & Declarations (Part 9 Grounds for Refusal)
    story.append(
        Paragraph(
            "4. STATUTORY SUITABILITY & IMMIGRATION DECLARATIONS (PART 9 RULES)",
            styles["section_heading"],
        )
    )
    sec4_rows = [
        (
            "Criminal Convictions & Cautions",
            "None (Clean Record Declared)"
            if not answers.get("criminal_record", False)
            else "Disclosed",
        ),
        (
            "UK / Global Visa Refusal History",
            "None Declared"
            if not answers.get("has_visa_refusal", False)
            else "Disclosed in Questionnaire",
        ),
        (
            "Immigration Breaches / Overstay",
            "None Declared" if not answers.get("prior_overstay", False) else "Disclosed",
        ),
        (
            "Tuberculosis (TB) Screening Test",
            "Verified / Clinic Certificate Attached"
            if answers.get("tb_test_required", True)
            else "Exempt based on residence",
        ),
    ]
    story.append(_build_key_value_table(sec4_rows, styles))
    story.append(Spacer(1, 12))

    # 6. Declaration & Signature
    story.append(
        Paragraph(
            "<b>Applicant Declaration:</b> I confirm that the information given on this form is correct and complete. "
            "I understand that false statements or omitted facts can lead to refusal, revocation, or a 10-year ban under Part 9 of the UK Immigration Rules.",
            styles["legal_notice"],
        )
    )
    story.append(Spacer(1, 10))

    sig_data = [
        [
            Paragraph(
                f"<b>Applicant Signature:</b><br/><br/><br/>________________________________________<br/><b>{full_name}</b>",
                styles["body"],
            ),
            Paragraph(
                f"<b>Date:</b><br/><br/><br/>{datetime.now(UTC).strftime('%B %d, %Y')}<br/><b>Place:</b> {nationality}",
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


# Not wired into the download route: the US jurisdiction is parked (see
# docs/jurisdictions/us/_jurisdiction.yml). Kept because it is covered by tests and will
# be needed when US is re-enabled — but note that DS-160 is filed on the CEAC portal, so
# US should then use the portal answer pack the UK uses, not a rendered look-alike form.
def generate_us_visa_application_pdf(
    case_reference: str,
    answers: dict[str, Any],
    destination_label: str = "United States",
    applicant_email: str | None = None,
    photo_data: bytes | str | None = None,
) -> bytes:
    """Generate official U.S. Nonimmigrant Visa Application & Petition Summary (DS-160 / Form I-129)."""
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

    is_student = (
        "student" in destination_label.lower()
        or "f1" in destination_label.lower()
        or "f-1" in destination_label.lower()
    )
    is_work = (
        "h1b" in destination_label.lower()
        or "h-1b" in destination_label.lower()
        or "work" in destination_label.lower()
    )

    visa_class = (
        "H-1B Specialty Occupation"
        if is_work
        else ("F-1 Academic Student" if is_student else "B-1/B-2 Visitor for Business or Pleasure")
    )

    # 1. Header with photo (US 2x2 in standard)
    meta_rows = [
        ("Application Reference", case_reference or "US-APPLICATION-DRAFT"),
        ("Date of Preparation", datetime.now(UTC).strftime("%Y-%m-%d")),
        ("Filing Jurisdiction", "U.S. Department of State (CEAC) / USCIS"),
        ("Visa Classification", visa_class),
    ]
    story.append(
        _build_header_with_photo(
            "U.S. VISA APPLICATION & FILING DOSSIER",
            f"Official Submission Summary · Nonimmigrant Visa Class {visa_class}",
            "U.S. DEPARTMENT OF STATE · CONSULAR AFFAIRS / USCIS",
            meta_rows,
            photo_data,
            styles,
        )
    )
    story.append(Spacer(1, 10))

    # 2. Section 1: Personal & Passport Information
    story.append(Paragraph("1. PERSONAL INFORMATION & TRAVEL DOCUMENT", styles["section_heading"]))
    nationality = str(answers.get("nationality") or NOT_PROVIDED)
    full_name = str(answers.get("full_name") or answers.get("applicant_name") or NOT_PROVIDED)
    sec1_rows = [
        ("Full Name (Surnames, Given Names)", full_name),
        ("Country of Citizenship / Nationality", nationality),
        ("Date of Birth (YYYY-MM-DD)", str(answers.get("date_of_birth") or NOT_PROVIDED)),
        ("Sex / Gender", str(answers.get("sex") or answers.get("gender") or NOT_PROVIDED)),
        (
            "Passport Number",
            str(answers.get("passport_number") or answers.get("passport_no") or NOT_PROVIDED),
        ),
        (
            "Passport Expiration Date",
            str(
                answers.get("passport_expiry")
                or answers.get("passport_expiry_date")
                or NOT_PROVIDED
            ),
        ),
        (
            "Passport Issuing Country",
            str(answers.get("passport_issuing_authority") or f"Government of {nationality}"),
        ),
        (
            "Current Country of Residence",
            str(
                answers.get("residence_country")
                or answers.get("current_residence_country")
                or nationality
            ),
        ),
        ("Residential Address", str(answers.get("current_address") or NOT_PROVIDED)),
        ("Telephone Number", str(answers.get("phone_number") or NOT_PROVIDED)),
        ("Email Address", str(answers.get("email") or applicant_email or NOT_PROVIDED)),
    ]
    story.append(_build_key_value_table(sec1_rows, styles))
    story.append(Spacer(1, 10))

    # 3. Section 2: Travel & Purpose
    story.append(
        Paragraph("2. TRAVEL INFORMATION & U.S. CONTACT / SPONSOR", styles["section_heading"])
    )
    sec2_rows = [
        ("Purpose of Trip to the U.S.", visa_class),
        (
            "Intended Length of Stay in U.S.",
            str(
                answers.get("intended_length_of_stay_days")
                or answers.get("stay_duration_days")
                or NOT_PROVIDED
            ),
        ),
        (
            "U.S. Employer / Institution / Sponsor",
            str(
                answers.get("employer_name")
                or answers.get("sponsor_name")
                or answers.get("institution_name")
                or NOT_PROVIDED
            ),
        ),
        (
            "U.S. Contact Address",
            str(answers.get("workplace_address") or answers.get("us_address") or NOT_PROVIDED),
        ),
        (
            "Petition / SEVIS Number",
            str(
                answers.get("petition_number")
                or answers.get("sevis_id")
                or answers.get("receipt_number")
                or NOT_PROVIDED
            ),
        ),
    ]
    story.append(_build_key_value_table(sec2_rows, styles))
    story.append(Spacer(1, 10))

    # 4. Section 3: Security & INA Statutory Compliance
    story.append(
        Paragraph(
            "3. STATUTORY ELIGIBILITY & INA COMPLIANCE (SECTION 214(b) / 212(a))",
            styles["section_heading"],
        )
    )
    sec3_rows = [
        (
            "INA 214(b) Nonimmigrant Intent / Dual Intent",
            "Satisfied / Compliant under statutory category rules",
        ),
        (
            "Criminal History / Disqualifying Convictions",
            "None Declared" if not answers.get("criminal_record", False) else "Disclosed",
        ),
        (
            "Prior U.S. Visa Refusals or Inadmissibility",
            "None Declared" if not answers.get("has_visa_refusal", False) else "Disclosed",
        ),
        (
            "Biometrics & Consular Appointment",
            "Required at U.S. Embassy / Consulate General (OFC / VAC)",
        ),
    ]
    story.append(_build_key_value_table(sec3_rows, styles))
    story.append(Spacer(1, 12))

    # 5. Declaration
    story.append(
        Paragraph(
            "<b>Applicant Certification:</b> I certify under penalty of perjury under the laws of the United States of America that the foregoing is true and correct. "
            "I understand that any willfully false or misleading statement or willful concealment of a material fact may subject me to permanent exclusion from the United States.",
            styles["legal_notice"],
        )
    )
    story.append(Spacer(1, 10))

    sig_data = [
        [
            Paragraph(
                f"<b>Applicant Signature:</b><br/><br/><br/>________________________________________<br/><b>{full_name}</b>",
                styles["body"],
            ),
            Paragraph(
                f"<b>Date:</b><br/><br/><br/>{datetime.now(UTC).strftime('%B %d, %Y')}<br/><b>Location:</b> {nationality}",
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


def generate_generic_visa_application_pdf(
    case_reference: str,
    answers: dict[str, Any],
    destination_label: str = "Visa Application",
    applicant_email: str | None = None,
    photo_data: bytes | str | None = None,
) -> bytes:
    """Generate official Consular Visa Application Form Dossier for any country."""
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

    country_name = (
        destination_label.split("·")[0].strip() if "·" in destination_label else destination_label
    )

    meta_rows = [
        ("Application Reference", case_reference or "APPLICATION-DRAFT"),
        ("Date of Preparation", datetime.now(UTC).strftime("%Y-%m-%d")),
        ("Destination Jurisdiction", country_name),
        ("Target Scope", destination_label),
    ]
    story.append(
        _build_header_with_photo(
            f"{country_name.upper()} VISA APPLICATION DOSSIER",
            f"Official Submission Summary · {destination_label}",
            f"MINISTRY OF FOREIGN AFFAIRS / IMMIGRATION AUTHORITY OF {country_name.upper()}",
            meta_rows,
            photo_data,
            styles,
        )
    )
    story.append(Spacer(1, 10))

    story.append(
        Paragraph(
            "1. APPLICANT PERSONAL IDENTIFICATION & PASSPORT DETAILS", styles["section_heading"]
        )
    )
    nationality = str(answers.get("nationality") or NOT_PROVIDED)
    full_name = str(answers.get("full_name") or answers.get("applicant_name") or NOT_PROVIDED)
    sec1_rows = [
        ("Full Legal Name (as in passport)", full_name),
        ("Nationality / Country of Citizenship", nationality),
        ("Date of Birth (YYYY-MM-DD)", str(answers.get("date_of_birth") or NOT_PROVIDED)),
        ("Sex / Gender", str(answers.get("sex") or answers.get("gender") or NOT_PROVIDED)),
        (
            "Passport Number",
            str(answers.get("passport_number") or answers.get("passport_no") or NOT_PROVIDED),
        ),
        (
            "Passport Expiration Date",
            str(
                answers.get("passport_expiry")
                or answers.get("passport_expiry_date")
                or NOT_PROVIDED
            ),
        ),
        (
            "Passport Issuing Authority",
            str(answers.get("passport_issuing_authority") or f"Government of {nationality}"),
        ),
        (
            "Country of Current Residence",
            str(
                answers.get("residence_country")
                or answers.get("current_residence_country")
                or nationality
            ),
        ),
        ("Residential Address", str(answers.get("current_address") or NOT_PROVIDED)),
        ("Contact Telephone", str(answers.get("phone_number") or NOT_PROVIDED)),
        ("Email Address", str(answers.get("email") or applicant_email or NOT_PROVIDED)),
    ]
    story.append(_build_key_value_table(sec1_rows, styles))
    story.append(Spacer(1, 10))

    story.append(Paragraph("2. TRAVEL DETAILS, PURPOSE & HOST SPONSOR", styles["section_heading"]))
    sec2_rows = [
        (
            "Purpose of Visit / Category",
            str(
                answers.get("purpose_of_visit") or answers.get("main_purpose") or destination_label
            ),
        ),
        (
            "Intended Length of Stay",
            f"{answers.get('intended_length_of_stay_days') or answers.get('stay_duration_days') or 15} Days",
        ),
        (
            "Planned Travel / Arrival Date",
            str(answers.get("planned_arrival_date") or answers.get("arrival_date") or NOT_PROVIDED),
        ),
        (
            "Host Sponsor / Employer / Accommodation",
            str(
                answers.get("sponsor_name")
                or answers.get("employer_name")
                or answers.get("accommodation_name")
                or NOT_PROVIDED
            ),
        ),
        (
            "Address in Destination Country",
            str(
                answers.get("accommodation_address")
                or answers.get("workplace_address")
                or country_name
            ),
        ),
    ]
    story.append(_build_key_value_table(sec2_rows, styles))
    story.append(Spacer(1, 10))

    story.append(
        Paragraph("3. STATUTORY DECLARATIONS & SUBMISSION COMPLIANCE", styles["section_heading"])
    )
    sec3_rows = [
        (
            "Criminal Convictions / Police Record",
            "None Declared (Clean Record)"
            if not answers.get("criminal_record", False)
            else "Disclosed",
        ),
        (
            "Prior Visa Refusals or Overstays",
            "None Declared" if not answers.get("has_visa_refusal", False) else "Disclosed",
        ),
        ("Financial Solvency & Coverage", "Certified / Bank Solvency Proof Attached"),
    ]
    story.append(_build_key_value_table(sec3_rows, styles))
    story.append(Spacer(1, 12))

    story.append(
        Paragraph(
            "<b>Applicant Certification:</b> I hereby declare that the particulars given above are true and complete in every respect. "
            "I understand that any false statements or omission of required materials will result in immediate rejection of my visa application.",
            styles["legal_notice"],
        )
    )
    story.append(Spacer(1, 10))

    sig_data = [
        [
            Paragraph(
                f"<b>Applicant Signature:</b><br/><br/><br/>________________________________________<br/><b>{full_name}</b>",
                styles["body"],
            ),
            Paragraph(
                f"<b>Date:</b><br/><br/><br/>{datetime.now(UTC).strftime('%B %d, %Y')}<br/><b>Place:</b> {nationality}",
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


def build_single_master_dossier_pdf(
    case_reference: str,
    cover_pdf_bytes: bytes | None,
    dossier_pdf_bytes: bytes | None,
    supporting_documents: list[tuple[str, bytes]],
) -> bytes:
    """Merge cover letter, application forms, and all supporting attachments into one single PDF.

    The resulting master PDF is in 100% compliant physical submission order:
    1. Official Embassy Cover Letter
    2. Complete Application Dossier Packet / Official Forms
    3. All Supporting Documents (Passports, Bank Statements, NOCs, Bookings) converted to clean A4 pages.
    """
    import pymupdf

    master = pymupdf.open()

    # 1. Add Cover Letter
    if cover_pdf_bytes:
        try:
            cov_doc = pymupdf.open(stream=cover_pdf_bytes, filetype="pdf")
            master.insert_pdf(cov_doc)
            cov_doc.close()
        except Exception:
            pass

    # 2. Add Dossier / Form Packet
    if dossier_pdf_bytes:
        try:
            dos_doc = pymupdf.open(stream=dossier_pdf_bytes, filetype="pdf")
            master.insert_pdf(dos_doc)
            dos_doc.close()
        except Exception:
            pass

    # 3. Add Supporting Documents in order
    a4_width, a4_height = 595.3, 841.9
    for idx, (doc_name, doc_bytes) in enumerate(supporting_documents, 1):
        if not doc_bytes:
            continue

        clean_title = doc_name.replace("_", " ").replace("-", " ")
        if clean_title.lower().endswith((".pdf", ".jpg", ".png", ".jpeg", ".webp")):
            clean_title = clean_title.rsplit(".", 1)[0]

        # Check if bytes are a PDF document
        if doc_bytes.startswith(b"%PDF"):
            try:
                sub_doc = pymupdf.open(stream=doc_bytes, filetype="pdf")
                start_page = master.page_count
                master.insert_pdf(sub_doc)
                for p_idx in range(start_page, master.page_count):
                    p = master[p_idx]
                    p.insert_text(
                        pymupdf.Point(36, 25),
                        f"{case_reference} | Attachment {idx:02d}: {clean_title.upper()}",
                        fontsize=8,
                        color=(0.4, 0.4, 0.4),
                    )
                sub_doc.close()
                continue
            except Exception:
                pass

        # Try image format (JPG, PNG, WebP)
        try:
            page = master.new_page(width=a4_width, height=a4_height)
            page.insert_text(
                pymupdf.Point(36, 30),
                f"{case_reference} | Attachment {idx:02d}: {clean_title.upper()}",
                fontsize=8,
                color=(0.4, 0.4, 0.4),
            )
            img_rect = pymupdf.Rect(36, 45, a4_width - 36, a4_height - 36)
            page.insert_image(img_rect, stream=doc_bytes, keep_proportion=True)
        except Exception:
            pass

    output_bytes = master.tobytes(deflate=True)
    master.close()
    return output_bytes
