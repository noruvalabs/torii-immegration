"""OCR extract endpoint tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from torii_ai.main import create_app
from torii_ai.services.ocr import extract_document_fields


def test_extract_passport_from_hint() -> None:
    result = extract_document_fields(
        "passport",
        "scan.jpg",
        "name: Ada Lovelace\npassport number: AB1234567",
    )
    assert result.needs_recapture is False
    assert result.fields["passport_number"].value == "AB1234567"
    assert result.fields["full_name"].value == "Ada Lovelace"


@pytest.mark.asyncio
async def test_ocr_extract_endpoint() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/ai/ocr/extract",
                json={
                    "doc_type": "passport",
                    "filename": "passport.jpg",
                    "hint_text": "passport number: CD9999999",
                },
            )
    assert resp.status_code == 200
    body = resp.json()
    assert body["fields"]["passport_number"]["value"] == "CD9999999"
    assert body["needs_recapture"] is False
