"""Generator for realistic dummy immigration documents using PyMuPDF."""

from __future__ import annotations

import pymupdf  # type: ignore


def _draw_header_badge(page: pymupdf.Page, title: str, subtitle: str, category_tag: str):
    rect = pymupdf.Rect(40, 35, 555, 95)
    page.draw_rect(rect, color=(0.15, 0.25, 0.45), fill=(0.95, 0.97, 1.0), width=1.5)
    page.insert_text((55, 62), title, fontsize=16, fontname="helv", color=(0.1, 0.18, 0.35))
    page.insert_text((55, 82), subtitle, fontsize=9, fontname="helv", color=(0.35, 0.4, 0.5))
    page.draw_rect(pymupdf.Rect(460, 50, 540, 72), color=(0.2, 0.5, 0.3), fill=(0.9, 0.96, 0.9), width=1)
    page.insert_text((472, 65), category_tag, fontsize=9, fontname="helv", color=(0.15, 0.45, 0.2))


def _draw_field_box(page: pymupdf.Page, x: float, y: float, w: float, h: float, label: str, value: str):
    rect = pymupdf.Rect(x, y, x + w, y + h)
    page.draw_rect(rect, color=(0.8, 0.82, 0.86), fill=(0.98, 0.98, 0.99), width=0.8)
    page.insert_text((x + 8, y + 14), label.upper(), fontsize=7, fontname="helv", color=(0.45, 0.5, 0.55))
    page.insert_text((x + 8, y + 32), value, fontsize=11, fontname="helv", color=(0.08, 0.12, 0.18))


def generate_passport_pdf(
    full_name: str = "Kenji Sato",
    passport_number: str = "TR8765432",
    nationality: str = "Japan",
    dob: str = "1990-05-12",
    expiry: str = "2032-06-14",
    issue_date: str = "2022-06-15",
) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=420)  # Landscape passport spread
    
    _draw_header_badge(
        page,
        "JAPAN PASSPORT / PASSEPORT DU JAPON",
        "Ministry of Foreign Affairs / Ministère des Affaires Étrangères",
        "IDENTITY",
    )

    # Photo box placeholder
    photo_rect = pymupdf.Rect(55, 115, 175, 275)
    page.draw_rect(photo_rect, color=(0.7, 0.75, 0.8), fill=(0.92, 0.94, 0.97), width=1)
    page.insert_text((85, 195), "[ PHOTOGRAPH ]\n   35mm x 45mm\n  ICAO 9303 SPEC", fontsize=8, fontname="helv", color=(0.4, 0.45, 0.55))

    # Details grid
    _draw_field_box(page, 190, 115, 170, 42, "Type / Country", "P / JPN")
    _draw_field_box(page, 370, 115, 170, 42, "Passport No", f"Passport No: {passport_number}")
    _draw_field_box(page, 190, 165, 350, 42, "Full Name / Nom", f"Full Name: {full_name}")
    _draw_field_box(page, 190, 215, 170, 42, "Nationality", f"Nationality: {nationality}")
    _draw_field_box(page, 370, 215, 170, 42, "Date of Birth", f"Date of Birth: {dob}")
    _draw_field_box(page, 190, 265, 170, 42, "Date of Issue", f"Issue Date: {issue_date}")
    _draw_field_box(page, 370, 265, 170, 42, "Date of Expiry", f"Expiry Date: {expiry}")

    # MRZ machine-readable lines
    mrz_rect = pymupdf.Rect(40, 325, 555, 395)
    page.draw_rect(mrz_rect, color=(0.85, 0.87, 0.9), fill=(0.96, 0.96, 0.96), width=1)
    clean_name = full_name.upper().replace(" ", "<<")
    mrz1 = f"P<JPN{clean_name}<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<"[:44]
    mrz2 = f"{passport_number}4JPN9005121M3206148<<<<<<<<<<<<<<<4"[:44]
    page.insert_text((55, 352), mrz1, fontsize=12, fontname="courier", color=(0.1, 0.1, 0.1))
    page.insert_text((55, 378), mrz2, fontsize=12, fontname="courier", color=(0.1, 0.1, 0.1))

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def generate_bank_statement_pdf(
    account_holder: str = "Kenji Sato",
    bank_name: str = "Sumitomo Mitsui Banking Corporation",
    balance: str = "JPY 3,450,000",
    account_no: str = "****6782",
    statement_date: str = "2026-03-01",
) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # A4 Portrait

    _draw_header_badge(
        page,
        f"{bank_name}",
        "CERTIFICATE OF BALANCE & SOLVENCY / 残高証明書",
        "FINANCIAL",
    )

    _draw_field_box(page, 45, 115, 245, 45, "Account Holder", f"Account Holder: {account_holder}")
    _draw_field_box(page, 305, 115, 245, 45, "Account Number", f"Account: {account_no}")
    _draw_field_box(page, 45, 170, 245, 45, "Bank / Institution", f"Bank: {bank_name}")
    _draw_field_box(page, 305, 170, 245, 45, "Statement Date", f"Statement Date: {statement_date}")
    _draw_field_box(page, 45, 225, 505, 55, "Available Balance / Total Solvency", f"Available Balance: {balance}")

    # Transaction summary table
    table_rect = pymupdf.Rect(45, 300, 550, 520)
    page.draw_rect(table_rect, color=(0.8, 0.82, 0.86), fill=(1.0, 1.0, 1.0), width=1)
    page.draw_rect(pymupdf.Rect(45, 300, 550, 328), color=(0.2, 0.3, 0.45), fill=(0.2, 0.3, 0.45), width=1)
    page.insert_text((55, 318), "Date          Description                       Deposit           Withdrawal      Balance", fontsize=9, fontname="courier", color=(1.0, 1.0, 1.0))

    txs = [
        ("2026-02-25", "Salary Deposit - Tech Corp", "+ JPY 480,000", "—", "JPY 3,450,000"),
        ("2026-02-18", "Apartment Rent Tokyo", "—", "- JPY 120,000", "JPY 2,970,000"),
        ("2026-02-10", "Utility & Internet Bill", "—", "- JPY 18,500", "JPY 3,090,000"),
        ("2026-01-25", "Salary Deposit - Tech Corp", "+ JPY 480,000", "—", "JPY 3,108,500"),
        ("2026-01-15", "Consulting Fee Credit", "+ JPY 150,000", "—", "JPY 2,628,500"),
    ]
    y_tx = 350
    for dt, desc, dep, wdr, bal in txs:
        line = f"{dt:<13} {desc:<30} {dep:<17} {wdr:<15} {bal}"
        page.insert_text((55, y_tx), line, fontsize=8, fontname="courier", color=(0.15, 0.15, 0.2))
        page.draw_line(pymupdf.Point(45, y_tx + 8), pymupdf.Point(550, y_tx + 8), color=(0.9, 0.9, 0.9), width=0.5)
        y_tx += 28

    # Official Seal
    seal_rect = pymupdf.Rect(380, 550, 520, 650)
    page.draw_rect(seal_rect, color=(0.7, 0.2, 0.2), width=1.5)
    page.insert_text((400, 585), "OFFICIAL BANK SEAL\n   SMBC TOKYO\n  AUTHORIZED OFFICER\n    [VERIFIED]", fontsize=9, fontname="helv", color=(0.7, 0.2, 0.2))

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def generate_residence_card_pdf(
    full_name: str = "Kenji Sato",
    card_number: str = "AB12345678CD",
    dob: str = "1990-05-12",
    status_of_residence: str = "Engineer / Specialist in Humanities",
    expiry: str = "2027-04-30",
) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=420)

    _draw_header_badge(
        page,
        "RESIDENCE CARD / 在留カード",
        "Immigration Services Agency of Japan / 出入国在留管理庁",
        "IMMIGRATION",
    )

    photo_rect = pymupdf.Rect(55, 115, 165, 275)
    page.draw_rect(photo_rect, color=(0.7, 0.75, 0.8), fill=(0.92, 0.94, 0.97), width=1)
    page.insert_text((75, 195), "[ PHOTO / 写真 ]\n   30mm x 40mm\n Official Card Holder", fontsize=8, fontname="helv", color=(0.4, 0.45, 0.55))

    _draw_field_box(page, 180, 115, 360, 42, "Full Name", f"Full Name: {full_name}")
    _draw_field_box(page, 180, 165, 175, 42, "Card Number", f"Card No: {card_number}")
    _draw_field_box(page, 365, 165, 175, 42, "Date of Birth", f"Date of Birth: {dob}")
    _draw_field_box(page, 180, 215, 360, 42, "Status of Residence", f"Status of Residence: {status_of_residence}")
    _draw_field_box(page, 180, 265, 175, 42, "Period of Stay (Expiry)", f"Expiry Date: {expiry}")
    _draw_field_box(page, 365, 265, 175, 42, "Permission", "Permission to Work: Allowed")

    # IC chip and hologram indicator
    ic_rect = pymupdf.Rect(55, 290, 165, 360)
    page.draw_rect(ic_rect, color=(0.75, 0.6, 0.2), fill=(0.98, 0.95, 0.85), width=1)
    page.insert_text((70, 328), "[ EMBEDDED IC CHIP ]\n  Ministry of Justice", fontsize=8, fontname="helv", color=(0.5, 0.4, 0.1))

    # Anti-counterfeit text
    page.insert_text((180, 340), "THIS IS AN OFFICIAL RESIDENCE CERTIFICATE UNDER THE IMMIGRATION CONTROL ACT", fontsize=7, fontname="helv", color=(0.5, 0.5, 0.5))

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def generate_employment_letter_pdf(
    employee_name: str = "Kenji Sato",
    employer_name: str = "Rakuten Group Inc.",
    position: str = "Senior Software Architect",
    monthly_salary: str = "JPY 650,000",
    start_date: str = "2021-04-01",
) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)

    _draw_header_badge(
        page,
        f"{employer_name}",
        "CERTIFICATE OF EMPLOYMENT & SALARY / 在職証明書",
        "EMPLOYMENT",
    )

    page.insert_text((45, 125), "To: Immigration Services Agency of Japan", fontsize=10, fontname="helv", color=(0.2, 0.2, 0.3))
    page.insert_text(
        (45, 150),
        "This is to certify that the individual named below is currently employed in good standing\n"
        f"with {employer_name} under the following terms and conditions:",
        fontsize=10,
        fontname="helv",
        color=(0.15, 0.15, 0.2),
    )

    _draw_field_box(page, 45, 185, 245, 45, "Employee Name", f"Full Name: {employee_name}")
    _draw_field_box(page, 305, 185, 245, 45, "Employer / Sponsor", f"Employer: {employer_name}")
    _draw_field_box(page, 45, 240, 245, 45, "Job Title / Position", f"Position: {position}")
    _draw_field_box(page, 305, 240, 245, 45, "Employment Start Date", f"Start Date: {start_date}")
    _draw_field_box(page, 45, 295, 505, 45, "Monthly Remuneration / Salary", f"Monthly Salary: {monthly_salary}")

    # Duties statement
    duties_rect = pymupdf.Rect(45, 355, 550, 480)
    page.draw_rect(duties_rect, color=(0.85, 0.87, 0.9), fill=(0.98, 0.98, 0.99), width=1)
    page.insert_text((55, 375), "SUMMARY OF RESPONSIBILITIES & QUALIFICATIONS:", fontsize=9, fontname="helv", color=(0.3, 0.3, 0.4))
    page.insert_text(
        (55, 395),
        "1. Leads high-availability microservice development for core commerce services.\n"
        "2. Manages architecture design compliant with Japanese immigration technical guidelines.\n"
        "3. Full-time regular employee (Seishain) on an open-ended employment contract.\n"
        "4. Sponsoring organization guarantees full legal and immigration compliance.",
        fontsize=9,
        fontname="helv",
        color=(0.2, 0.2, 0.25),
    )

    # Corporate Seal & Signature
    page.insert_text((45, 530), f"Issued by: Human Resources Department\nCompany: {employer_name}\nAddress: 1-14-1 Tamagawa, Setagaya-ku, Tokyo, Japan", fontsize=9, fontname="helv", color=(0.3, 0.3, 0.35))
    
    seal_rect = pymupdf.Rect(380, 520, 520, 620)
    page.draw_rect(seal_rect, color=(0.75, 0.15, 0.15), width=1.5)
    page.insert_text((400, 555), f"CORPORATE SEAL\n  {employer_name[:16].upper()}\n REPRESENTATIVE DIRECTOR\n   [REGISTERED]", fontsize=8, fontname="helv", color=(0.75, 0.15, 0.15))

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def generate_flight_itinerary_pdf(
    traveler_name: str = "Kenji Sato",
    booking_ref: str = "NH982341",
    airline: str = "All Nippon Airways (ANA)",
    dep_date: str = "2026-10-15",
    ret_date: str = "2026-10-30",
    destination: str = "Tokyo (Haneda - HND)",
) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)

    _draw_header_badge(
        page,
        f"{airline}",
        "ELECTRONIC TICKET PASSENGER ITINERARY & RECEIPT",
        "TRAVEL",
    )

    _draw_field_box(page, 45, 115, 245, 45, "Passenger Name", f"Full Name: {traveler_name}")
    _draw_field_box(page, 305, 115, 245, 45, "Booking Reference (PNR)", f"Booking Ref: {booking_ref}")
    _draw_field_box(page, 45, 170, 245, 45, "Departure Date", f"Departure Date: {dep_date}")
    _draw_field_box(page, 305, 170, 245, 45, "Destination", f"Destination: {destination}")

    # Flights card
    f_rect = pymupdf.Rect(45, 235, 550, 420)
    page.draw_rect(f_rect, color=(0.8, 0.85, 0.9), fill=(0.97, 0.98, 1.0), width=1)
    page.insert_text((60, 260), "OUTBOUND FLIGHT: ANA NH842", fontsize=11, fontname="helv", color=(0.1, 0.2, 0.4))
    page.insert_text((60, 285), f"Date: {dep_date} | Singapore (SIN) 11:00 -> Tokyo Haneda (HND) 19:00 | Class: Economy (M) | Status: Confirmed", fontsize=8, fontname="helv", color=(0.2, 0.25, 0.35))
    page.draw_line(pymupdf.Point(60, 310), pymupdf.Point(535, 310), color=(0.85, 0.85, 0.85), width=0.8)

    page.insert_text((60, 335), "RETURN FLIGHT: ANA NH841", fontsize=11, fontname="helv", color=(0.1, 0.2, 0.4))
    page.insert_text((60, 360), f"Date: {ret_date} | Tokyo Haneda (HND) 10:50 -> Singapore (SIN) 17:30 | Class: Economy (M) | Status: Confirmed", fontsize=8, fontname="helv", color=(0.2, 0.25, 0.35))

    page.insert_text((45, 450), "Baggage Allowance: 2 Pieces (23kg each) | Electronic Ticket Issued | Validated for MOFA Visa Filing", fontsize=8, fontname="helv", color=(0.4, 0.4, 0.45))

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def generate_tax_return_pdf(
    full_name: str = "Kenji Sato",
    tax_year: str = "2025",
    gross_income: str = "JPY 7,800,000",
    taxable_income: str = "JPY 5,640,000",
    paid_tax: str = "JPY 625,400",
) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)

    _draw_header_badge(
        page,
        "TAXATION & INCOME CERTIFICATE / 課税・所得証明書",
        "Municipal Taxation Bureau / 特別区都税事務所・市町村役場",
        "FINANCIAL",
    )

    _draw_field_box(page, 45, 115, 245, 45, "Taxpayer Name", f"Full Name: {full_name}")
    _draw_field_box(page, 305, 115, 245, 45, "Assessment Year", f"Tax Year: {tax_year}")
    _draw_field_box(page, 45, 170, 245, 45, "Gross Remuneration", f"Gross Salary: {gross_income}")
    _draw_field_box(page, 305, 170, 245, 45, "Taxable Income", f"Taxable Amount: {taxable_income}")
    _draw_field_box(page, 45, 225, 505, 45, "Total Income Tax Paid (Nozei)", f"Balance: {paid_tax}")

    # Legal clause
    box = pymupdf.Rect(45, 290, 550, 420)
    page.draw_rect(box, color=(0.85, 0.85, 0.9), fill=(0.98, 0.98, 0.99), width=1)
    page.insert_text((55, 315), "DECLARATION OF STATUTORY TAX COMPLIANCE:", fontsize=9, fontname="helv", color=(0.2, 0.2, 0.3))
    page.insert_text(
        (55, 340),
        "This official certificate confirms that the aforementioned taxpayer has fully declared\n"
        "all worldwide income and has no outstanding municipal, prefectural, or national tax arrears\n"
        "under Article 132 of the Local Tax Act of Japan.",
        fontsize=9,
        fontname="helv",
        color=(0.15, 0.15, 0.2),
    )

    seal_rect = pymupdf.Rect(380, 460, 520, 560)
    page.draw_rect(seal_rect, color=(0.7, 0.2, 0.2), width=1.5)
    page.insert_text((400, 495), "MUNICIPAL TAX SEAL\n  SHIBUYA WARD TAX\n    OFFICIAL STAMP\n   [PAID IN FULL]", fontsize=8, fontname="helv", color=(0.7, 0.2, 0.2))

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def generate_dummy_pdf(doc_type: str, user_name: str = "Kenji Sato") -> tuple[bytes, str, str]:
    """Dispatch to generator based on doc_type. Returns (bytes, filename, default_name)."""
    dt = (doc_type or "").lower().strip()
    if dt == "passport":
        return generate_passport_pdf(full_name=user_name), "official_passport.pdf", "Valid Passport"
    elif dt in ("bank_statement", "proof_of_funds"):
        return generate_bank_statement_pdf(account_holder=user_name), "bank_statement.pdf", "Bank Statement / Solvency Certificate"
    elif dt == "residence_card":
        return generate_residence_card_pdf(full_name=user_name), "residence_card.pdf", "Residence Card (Zairyu Card)"
    elif dt in ("employment_letter", "employment_contract"):
        return generate_employment_letter_pdf(employee_name=user_name), "employment_letter.pdf", "Employment Letter & Contract"
    elif dt in ("flight_itinerary", "travel_itinerary"):
        return generate_flight_itinerary_pdf(traveler_name=user_name), "flight_itinerary.pdf", "Flight Itinerary & Booking"
    elif dt == "tax_return":
        return generate_tax_return_pdf(full_name=user_name), "tax_certificate.pdf", "Tax Certificate / Declaration"
    elif dt == "photo":
        # Generate official ID photo card format
        return generate_passport_pdf(full_name=user_name), "passport_photograph.pdf", "Official Photograph"
    else:
        # Generic supporting document
        return generate_passport_pdf(full_name=user_name), "supporting_document.pdf", "Supporting Immigration Document"
