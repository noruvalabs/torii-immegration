"""Export all 10 dummy immigration documents into dummy_documents/ folder for manual user testing."""

from pathlib import Path
import sys

# Ensure torii_api is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "api" / "src"))

from torii_api.services.dummy_generator import generate_dummy_pdf
import pymupdf

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "dummy_documents"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DOC_TYPES = [
    ("passport", "01_passport.pdf", "Valid Passport"),
    ("photo", "02_passport_photo.pdf", "Passport Photo"),
    ("bank_statement", "03_bank_statement.pdf", "Official Bank Statement"),
    ("proof_of_funds", "04_proof_of_funds.pdf", "Proof of Funds Certificate"),
    ("flight_itinerary", "05_flight_itinerary.pdf", "Flight Itinerary (ANA)"),
    ("travel_itinerary", "06_travel_itinerary.pdf", "Travel Schedule & Itinerary"),
    ("employment_letter", "07_employment_letter.pdf", "Letter of Employment"),
    ("employment_contract", "08_employment_contract.pdf", "Employment Contract"),
    ("residence_card", "09_residence_card.pdf", "Residence Card (Zairyu)"),
    ("tax_return", "10_tax_certificate.pdf", "Tax Certificate / Declaration"),
]

def export_all():
    print(f"Exporting dummy test documents to: {OUTPUT_DIR}")
    for doc_type, custom_filename, label in DOC_TYPES:
        pdf_bytes, _, _ = generate_dummy_pdf(doc_type, user_name="Kenji Sato")
        target_path = OUTPUT_DIR / custom_filename
        target_path.write_bytes(pdf_bytes)
        print(f"  [OK] {custom_filename} ({len(pdf_bytes)} bytes) - {label}")

    # Also export a photo image (JPG) for testing image uploads
    photo_pdf_bytes, _, _ = generate_dummy_pdf("photo", user_name="Kenji Sato")
    doc = pymupdf.open(stream=photo_pdf_bytes, filetype="pdf")
    pix = doc[0].get_pixmap(dpi=150)
    img_path = OUTPUT_DIR / "02b_id_photo.jpg"
    pix.pil_save(str(img_path))
    doc.close()
    print(f"  [OK] 02b_id_photo.jpg ({img_path.stat().st_size} bytes) - ID Photo Image")

    print("\nAll 10+ dummy test documents successfully created!")

if __name__ == "__main__":
    export_all()
