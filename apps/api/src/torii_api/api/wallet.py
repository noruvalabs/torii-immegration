"""Document wallet endpoints for reusable documents."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, status
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.auth.deps import CurrentUserDep
from torii_api.db.session import get_session
from torii_api.services.wallet import (
    get_document_content,
    get_document_types,
    get_document_versions,
    get_user_wallet,
    get_wallet_summary,
    mark_document_expired,
    save_document_content,
    upload_document,
)

router = APIRouter(prefix="/v1/wallet", tags=["wallet"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ── Response schemas ──────────────────────────────────────────────────────────


class DocumentTypeOut(BaseModel):
    code: str
    name: str
    category: str


class WalletDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doc_type: str
    name: str
    version: int
    filename: str
    content_type: str
    file_size: int | None = None
    issued_date: str | None = None
    expiry_date: str | None = None
    extracted_fields: dict[str, Any] | None = None
    extraction_confidence: float | None = None
    status: str
    created_at: datetime | None = None


class DocumentVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    filename: str
    content_type: str
    file_size: int | None = None
    extracted_fields: dict[str, Any] | None = None
    extraction_confidence: float | None = None
    notes: str | None = None
    created_at: datetime | None = None


class WalletSummaryOut(BaseModel):
    total_documents: int
    documents_by_category: dict[str, list[dict[str, Any]]]
    expiring_soon: list[dict[str, Any]]


class WalletUploadOut(BaseModel):
    id: int
    doc_type: str
    name: str
    version: int
    filename: str
    storage_key: str
    extracted_fields: dict[str, Any] | None = None
    extraction_confidence: float | None = None
    message: str


class DocumentTypesOut(BaseModel):
    document_types: list[DocumentTypeOut]


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/document-types", response_model=DocumentTypesOut)
async def list_document_types() -> DocumentTypesOut:
    """List all supported document types."""
    doc_types = get_document_types()
    return DocumentTypesOut(document_types=[DocumentTypeOut(**dt) for dt in doc_types])


@router.get("", response_model=list[WalletDocumentOut])
@router.get("/", response_model=list[WalletDocumentOut], include_in_schema=False)
async def get_wallet(
    current_user: CurrentUserDep,
    session: SessionDep,
) -> list[WalletDocumentOut]:
    """Get all active documents in user's wallet."""
    wallet = await get_user_wallet(db=session, user_id=current_user.id)
    return [WalletDocumentOut.model_validate(doc) for doc in wallet]


@router.get("/summary", response_model=WalletSummaryOut)
async def get_wallet_summary_endpoint(
    current_user: CurrentUserDep,
    session: SessionDep,
) -> WalletSummaryOut:
    """Get a summary of the user's document wallet."""
    summary = await get_wallet_summary(db=session, user_id=current_user.id)
    return WalletSummaryOut(**summary)


@router.post("/upload", response_model=WalletUploadOut, status_code=status.HTTP_201_CREATED)
async def upload_wallet_document(
    current_user: CurrentUserDep,
    session: SessionDep,
    file: UploadFile,
    doc_type: str,
    name: str | None = None,
    issued_date: str | None = None,
    expiry_date: str | None = None,
    notes: str | None = None,
) -> WalletUploadOut:
    """Upload a document to the wallet."""
    from torii_api.services.wallet import normalize_doc_type

    doc_type = normalize_doc_type(doc_type)

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Run PyMuPDF / OCR structured extraction
    from torii_api.services.ocr_extractor import extract_document_metadata

    extracted_fields, confidence = await extract_document_metadata(
        file_bytes=content,
        doc_type=doc_type,
        filename=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
    )

    # Auto-populate dates if extracted and not explicitly given
    if not expiry_date:
        if exp := extracted_fields.get("expiry_date") or extracted_fields.get("passport_expiry"):
            expiry_date = exp.get("value") if isinstance(exp, dict) else str(exp)
    if not issued_date:
        if iss := extracted_fields.get("issued_date") or extracted_fields.get("issue_date"):
            issued_date = iss.get("value") if isinstance(iss, dict) else str(iss)

    document = await upload_document(
        db=session,
        user_id=current_user.id,
        doc_type=doc_type,
        name=name or doc_type.replace("_", " ").title(),
        filename=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
        file_size=file_size,
        extracted_fields=extracted_fields,
        extraction_confidence=confidence,
        issued_date=issued_date,
        expiry_date=expiry_date,
        notes=notes,
    )
    save_document_content(document.storage_key, content)

    return WalletUploadOut(
        id=document.id,
        doc_type=document.doc_type,
        name=document.name,
        version=document.version,
        filename=document.filename,
        storage_key=document.storage_key,
        extracted_fields=document.extracted_fields,
        extraction_confidence=document.extraction_confidence,
        message="Document uploaded and processed successfully",
    )


@router.get("/{document_id}", response_model=WalletDocumentOut)
async def get_wallet_document(
    current_user: CurrentUserDep,
    session: SessionDep,
    document_id: int,
) -> WalletDocumentOut:
    """Get a specific document from the wallet."""
    from sqlalchemy import select

    from torii_api.db.models import DocumentWalletItem

    result = await session.execute(
        select(DocumentWalletItem).where(
            DocumentWalletItem.id == document_id,
            DocumentWalletItem.user_id == current_user.id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return WalletDocumentOut.model_validate(document)


@router.get("/{document_id}/versions", response_model=list[DocumentVersionOut])
async def get_document_version_history(
    current_user: CurrentUserDep,
    session: SessionDep,
    document_id: int,
) -> list[DocumentVersionOut]:
    """Get version history for a document."""
    versions = await get_document_versions(
        db=session, document_id=document_id, user_id=current_user.id
    )
    return [DocumentVersionOut.model_validate(v) for v in versions]


@router.post("/{document_id}/expire", response_model=WalletDocumentOut)
async def expire_document(
    current_user: CurrentUserDep,
    session: SessionDep,
    document_id: int,
) -> WalletDocumentOut:
    """Mark a document as expired."""
    try:
        document = await mark_document_expired(
            db=session, document_id=document_id, user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return WalletDocumentOut.model_validate(document)


class WalletDocumentUpdateIn(BaseModel):
    name: str | None = None
    issued_date: str | None = None
    expiry_date: str | None = None
    notes: str | None = None


@router.patch("/{document_id}", response_model=WalletDocumentOut)
async def update_wallet_document_metadata(
    current_user: CurrentUserDep,
    session: SessionDep,
    document_id: int,
    payload: WalletDocumentUpdateIn,
) -> WalletDocumentOut:
    """Update metadata for a document (name, issued_date, expiry_date)."""
    from sqlalchemy import select

    from torii_api.db.models import DocumentWalletItem

    result = await session.execute(
        select(DocumentWalletItem).where(
            DocumentWalletItem.id == document_id,
            DocumentWalletItem.user_id == current_user.id,
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if payload.name is not None:
        document.name = payload.name.strip()
    if payload.issued_date is not None:
        document.issued_date = payload.issued_date
    if payload.expiry_date is not None:
        document.expiry_date = payload.expiry_date
    if payload.notes is not None:
        document.notes = payload.notes

    await session.flush()
    await session.refresh(document)
    return WalletDocumentOut.model_validate(document)


@router.delete("/{document_id}")
async def delete_wallet_document(
    current_user: CurrentUserDep,
    session: SessionDep,
    document_id: int,
):
    """Delete a document from the wallet (soft delete by marking as inactive)."""
    from sqlalchemy import select, update

    from torii_api.db.models import DocumentWalletItem

    result = await session.execute(
        select(DocumentWalletItem).where(
            DocumentWalletItem.id == document_id,
            DocumentWalletItem.user_id == current_user.id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Soft delete
    await session.execute(
        update(DocumentWalletItem)
        .where(DocumentWalletItem.id == document_id)
        .values(status="deleted", is_latest=False)
    )
    await session.flush()


@router.post("/{document_id}/apply-to-case/{case_id}")
async def apply_document_to_case(
    current_user: CurrentUserDep,
    session: SessionDep,
    document_id: int,
    case_id: int,
) -> dict[str, Any]:
    """Apply structured extracted metadata from this wallet document to a visa case intake answers and user profile."""
    from sqlalchemy import select

    from torii_api.api.case_workflow import _apply_extracted_fields_to_case_and_user
    from torii_api.db.models import Case, CaseChecklistItem, DocumentWalletItem

    doc = await session.scalar(
        select(DocumentWalletItem).where(
            DocumentWalletItem.id == document_id,
            DocumentWalletItem.user_id == current_user.id,
        )
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    case = await session.scalar(
        select(Case).where(
            Case.id == case_id,
            Case.user_id == current_user.id,
        )
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    extracted = doc.extracted_fields or {}
    if extracted:
        _apply_extracted_fields_to_case_and_user(case, current_user, extracted)

    # Link/update matching checklist item if present
    checklist_item = await session.scalar(
        select(CaseChecklistItem).where(
            CaseChecklistItem.case_id == case.id,
            CaseChecklistItem.code == doc.doc_type,
        )
    )
    if checklist_item and checklist_item.status != "approved":
        checklist_item.status = "uploaded"

    await session.flush()
    return {
        "success": True,
        "message": f"Applied {len(extracted)} extracted fields to Case #{case_id}",
        "intake_answers": case.intake_answers,
        "fields_applied": list(extracted.keys()),
    }


@router.post("/{document_id}/apply-to-profile")
async def apply_document_to_profile(
    current_user: CurrentUserDep,
    session: SessionDep,
    document_id: int,
) -> dict[str, Any]:
    """Apply structured extracted metadata from this wallet document to user profile."""
    from sqlalchemy import select

    from torii_api.api.case_workflow import _normalize_extracted_key
    from torii_api.db.models import DocumentWalletItem

    doc = await session.scalar(
        select(DocumentWalletItem).where(
            DocumentWalletItem.id == document_id,
            DocumentWalletItem.user_id == current_user.id,
        )
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    extracted = doc.extracted_fields or {}
    for key, raw_val in extracted.items():
        val = raw_val.get("value") if isinstance(raw_val, dict) else raw_val
        if not val:
            continue
        val_str = str(val).strip()
        norm_key = _normalize_extracted_key(key).lower().strip()
        if norm_key in ("full_name", "applicant_name", "name", "legal_name"):
            current_user.full_name = val_str
        elif norm_key in ("nationality", "citizenship"):
            current_user.nationality = val_str
        elif norm_key in ("passport_number", "passport_no"):
            current_user.passport_number = val_str
        elif norm_key in ("passport_expiry", "expiry_date"):
            current_user.passport_expiry = val_str
        elif norm_key in ("date_of_birth", "dob"):
            current_user.date_of_birth = val_str
        elif norm_key in ("current_country", "residence_country"):
            current_user.current_country = val_str

    await session.flush()
    return {
        "success": True,
        "message": "User profile updated from document metadata",
        "user": {
            "full_name": current_user.full_name,
            "nationality": current_user.nationality,
            "passport_number": current_user.passport_number,
            "passport_expiry": current_user.passport_expiry,
            "date_of_birth": current_user.date_of_birth,
            "current_country": current_user.current_country,
        },
    }


@router.post("/{document_id}/re-extract", response_model=WalletDocumentOut)
async def reextract_document(
    current_user: CurrentUserDep,
    session: SessionDep,
    document_id: int,
) -> WalletDocumentOut:
    """Re-run extraction heuristics on an existing document."""
    from sqlalchemy import select

    from torii_api.db.models import DocumentWalletItem
    from torii_api.services.ocr_extractor import parse_structured_fields_from_text

    doc = await session.scalar(
        select(DocumentWalletItem).where(
            DocumentWalletItem.id == document_id,
            DocumentWalletItem.user_id == current_user.id,
        )
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    fields, confidence = parse_structured_fields_from_text(
        doc_type=doc.doc_type,
        text=doc.notes or "",
        filename=doc.filename or doc.name,
    )
    if fields:
        doc.extracted_fields = {**(doc.extracted_fields or {}), **fields}
        doc.extraction_confidence = max(doc.extraction_confidence or 0.0, confidence)
        await session.flush()

    return WalletDocumentOut.model_validate(doc)


@router.get("/{document_id}/file")
async def get_wallet_document_file(
    session: SessionDep,
    document_id: int,
    token: str | None = None,
    authorization: str | None = Header(default=None),
) -> Response:
    """Stream raw document file for inline browser viewing (e.g. in an iframe)."""
    from sqlalchemy import select

    from torii_api.auth.security import decode_access_token
    from torii_api.config import get_settings
    from torii_api.db.models import DocumentWalletItem, User
    from torii_api.services.dummy_generator import generate_dummy_pdf
    from torii_api.services.wallet import save_document_content

    auth_token = token
    if not auth_token and authorization and authorization.startswith("Bearer "):
        auth_token = authorization.replace("Bearer ", "").strip()

    if not auth_token:
        raise HTTPException(status_code=401, detail="Authentication token required")

    settings = get_settings()
    try:
        claims = decode_access_token(auth_token, settings)
        user_id = int(claims["sub"])
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid auth token: {e}") from e

    user = await session.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    doc = await session.scalar(
        select(DocumentWalletItem).where(
            DocumentWalletItem.id == document_id,
            DocumentWalletItem.user_id == user.id,
        )
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    content = get_document_content(doc.storage_key)
    if not content:
        # Synthesize dummy PDF on the fly if not on disk
        content, _, _ = generate_dummy_pdf(doc.doc_type, user.full_name or "Kenji Sato")
        save_document_content(doc.storage_key, content)

    media_type = (
        doc.content_type if doc.content_type and "pdf" in doc.content_type else "application/pdf"
    )
    if doc.filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        media_type = doc.content_type or "image/jpeg"

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{doc.filename}"',
            "Cache-Control": "public, max-age=3600",
        },
    )


def _render_pdf_page(content: bytes, page_number: int = 1, dpi: int = 150) -> tuple[bytes, int]:
    """Render a PDF page to PNG bytes and return (png_bytes, total_pages)."""
    import pymupdf  # type: ignore

    doc = pymupdf.open(stream=content, filetype="pdf")
    total_pages = len(doc)
    page_idx = max(0, min(page_number - 1, total_pages - 1))
    page = doc[page_idx]
    pix = page.get_pixmap(dpi=dpi)
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes, total_pages


@router.get("/{document_id}/page/{page_number}")
async def get_wallet_document_page_preview(
    session: SessionDep,
    document_id: int,
    page_number: int = 1,
    token: str | None = None,
    authorization: str | None = Header(default=None),
) -> Response:
    """Render a specific document page as a high-resolution PNG image for embedded viewing."""
    from sqlalchemy import select

    from torii_api.auth.security import decode_access_token
    from torii_api.config import get_settings
    from torii_api.db.models import DocumentWalletItem, User
    from torii_api.services.dummy_generator import generate_dummy_pdf

    auth_token = token
    if not auth_token and authorization and authorization.startswith("Bearer "):
        auth_token = authorization.replace("Bearer ", "").strip()

    if not auth_token:
        raise HTTPException(status_code=401, detail="Authentication token required")

    settings = get_settings()
    try:
        claims = decode_access_token(auth_token, settings)
        user_id = int(claims["sub"])
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid auth token: {e}") from e

    user = await session.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    doc = await session.scalar(
        select(DocumentWalletItem).where(
            DocumentWalletItem.id == document_id,
            DocumentWalletItem.user_id == user.id,
        )
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    content = get_document_content(doc.storage_key)
    if not content:
        content, _, _ = generate_dummy_pdf(doc.doc_type, user.full_name or "Kenji Sato")
        save_document_content(doc.storage_key, content)

    if doc.filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        return Response(content=content, media_type=doc.content_type or "image/jpeg")

    try:
        png_bytes, _ = _render_pdf_page(content, page_number=page_number, dpi=150)
        return Response(
            content=png_bytes,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to render document page: {e}") from e


@router.get("/{document_id}/view", response_class=HTMLResponse)
async def get_wallet_document_html_view(
    session: SessionDep,
    document_id: int,
    token: str | None = None,
    authorization: str | None = Header(default=None),
) -> HTMLResponse:
    """Return a standalone HTML document viewer optimized for embedding in iframes."""
    from sqlalchemy import select

    from torii_api.auth.security import decode_access_token
    from torii_api.config import get_settings
    from torii_api.db.models import DocumentWalletItem, User
    from torii_api.services.dummy_generator import generate_dummy_pdf

    auth_token = token
    if not auth_token and authorization and authorization.startswith("Bearer "):
        auth_token = authorization.replace("Bearer ", "").strip()

    if not auth_token:
        raise HTTPException(status_code=401, detail="Authentication token required")

    settings = get_settings()
    try:
        claims = decode_access_token(auth_token, settings)
        user_id = int(claims["sub"])
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid auth token: {e}") from e

    user = await session.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    doc = await session.scalar(
        select(DocumentWalletItem).where(
            DocumentWalletItem.id == document_id,
            DocumentWalletItem.user_id == user.id,
        )
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    content = get_document_content(doc.storage_key)
    if not content:
        content, _, _ = generate_dummy_pdf(doc.doc_type, user.full_name or "Kenji Sato")
        save_document_content(doc.storage_key, content)

    is_image = doc.filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    total_pages = 1
    if not is_image:
        try:
            import pymupdf  # type: ignore

            mupdf_doc = pymupdf.open(stream=content, filetype="pdf")
            total_pages = max(1, len(mupdf_doc))
            mupdf_doc.close()
        except Exception:
            total_pages = 1

    file_url = f"/backend/v1/wallet/{document_id}/file?token={auth_token}"
    page_url_base = f"/backend/v1/wallet/{document_id}/page"
    initial_img_src = f"{page_url_base}/1?token={auth_token}" if not is_image else file_url

    pagination_buttons = (
        f'<button class="btn" id="prevBtn" onclick="changePage(-1)" disabled>&larr;</button>'
        f'<span id="pageIndicator" style="font-weight: 500; font-size: 11px; min-width: 65px; text-align: center;">Page 1 / {total_pages}</span>'
        f'<button class="btn" id="nextBtn" onclick="changePage(1)" {"disabled" if total_pages <= 1 else ""}>&rarr;</button>'
        f'<div style="width: 1px; height: 14px; background: #334155; margin: 0 4px;"></div>'
        if total_pages > 1
        else ""
    )

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{doc.name}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #090d16;
    color: #f8fafc;
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }}
  .toolbar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 14px;
    background: #1e293b;
    border-bottom: 1px solid #334155;
    font-size: 12px;
    flex-shrink: 0;
    gap: 8px;
  }}
  .toolbar-left, .toolbar-center, .toolbar-right {{
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .title {{
    font-weight: 600;
    color: #e2e8f0;
    max-width: 240px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .badge {{
    background: #334155;
    color: #94a3b8;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    font-family: monospace;
  }}
  .btn {{
    background: #334155;
    color: #f1f5f9;
    border: none;
    padding: 4px 8px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 11px;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    text-decoration: none;
    transition: background 0.15s;
  }}
  .btn:hover {{ background: #475569; }}
  .btn:disabled {{ opacity: 0.35; cursor: not-allowed; }}
  .viewport {{
    flex: 1;
    overflow: auto;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding: 16px;
    background: #090d16;
  }}
  .page-container {{
    box-shadow: 0 10px 25px -5px rgba(0,0,0,0.6), 0 8px 10px -6px rgba(0,0,0,0.6);
    border-radius: 4px;
    background: white;
    transition: transform 0.15s ease;
    transform-origin: top center;
    max-width: 100%;
  }}
  .page-container img {{
    display: block;
    max-width: 100%;
    height: auto;
    border-radius: 4px;
  }}
</style>
</head>
<body>
<div class="toolbar">
  <div class="toolbar-left">
    <span class="title">{doc.name}</span>
    <span class="badge">{doc.doc_type}</span>
  </div>
  <div class="toolbar-center">
    {pagination_buttons}
    <button class="btn" onclick="zoom(-0.15)" title="Zoom Out">&minus;</button>
    <span id="zoomLevel" style="font-size: 11px; min-width: 35px; text-align: center;">100%</span>
    <button class="btn" onclick="zoom(0.15)" title="Zoom In">&plus;</button>
    <button class="btn" onclick="resetZoom()" title="Reset Zoom">Fit</button>
  </div>
  <div class="toolbar-right">
    <a class="btn" href="{file_url}" download="{doc.filename}">Download PDF</a>
  </div>
</div>
<div class="viewport" id="viewport">
  <div class="page-container" id="pageContainer">
    <img id="pageImg" src="{initial_img_src}" alt="{doc.name}" />
  </div>
</div>
<script>
  let currentPage = 1;
  const totalPages = {total_pages};
  let currentZoom = 1.0;
  const pageImg = document.getElementById('pageImg');
  const pageContainer = document.getElementById('pageContainer');
  const pageIndicator = document.getElementById('pageIndicator');
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');
  const zoomLevel = document.getElementById('zoomLevel');

  function changePage(delta) {{
    const newPage = currentPage + delta;
    if (newPage >= 1 && newPage <= totalPages) {{
      currentPage = newPage;
      pageImg.src = `{page_url_base}/` + currentPage + `?token={auth_token}`;
      if (pageIndicator) pageIndicator.innerText = `Page ` + currentPage + ` / ` + totalPages;
      if (prevBtn) prevBtn.disabled = currentPage === 1;
      if (nextBtn) nextBtn.disabled = currentPage === totalPages;
    }}
  }}

  function zoom(delta) {{
    currentZoom = Math.min(2.0, Math.max(0.6, currentZoom + delta));
    applyZoom();
  }}

  function resetZoom() {{
    currentZoom = 1.0;
    applyZoom();
  }}

  function applyZoom() {{
    pageContainer.style.transform = `scale(` + currentZoom + `)`;
    zoomLevel.innerText = Math.round(currentZoom * 100) + '%';
  }}
</script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


@router.post("/seed-dummy-documents", response_model=dict[str, Any])
async def seed_dummy_documents_endpoint(
    current_user: CurrentUserDep,
    session: SessionDep,
) -> dict[str, Any]:
    """Generate and upload realistic dummy documents for all 10 types with PyMuPDF extraction."""
    from torii_api.services.dummy_generator import generate_dummy_pdf
    from torii_api.services.ocr_extractor import extract_document_metadata
    from torii_api.services.wallet import save_document_content, upload_document

    all_types = [
        ("passport", "Valid Passport"),
        ("photo", "Photograph / ID Photo"),
        ("bank_statement", "Official Bank Statement"),
        ("proof_of_funds", "Proof of Funds Certificate"),
        ("flight_itinerary", "Flight Itinerary (ANA)"),
        ("travel_itinerary", "Travel Schedule & Itinerary"),
        ("employment_letter", "Letter of Employment"),
        ("employment_contract", "Employment Contract"),
        ("residence_card", "Residence Card (Zairyu)"),
        ("tax_return", "Tax Certificate / Declaration"),
    ]

    user_name = current_user.full_name or "Kenji Sato"
    seeded_docs = []

    for doc_type, default_label in all_types:
        pdf_bytes, filename, name = generate_dummy_pdf(doc_type, user_name)
        extracted_fields, confidence = await extract_document_metadata(
            file_bytes=pdf_bytes,
            doc_type=doc_type,
            filename=filename,
            content_type="application/pdf",
        )

        expiry_date = None
        if exp := extracted_fields.get("expiry_date") or extracted_fields.get("passport_expiry"):
            expiry_date = exp.get("value") if isinstance(exp, dict) else str(exp)

        issued_date = None
        if iss := extracted_fields.get("issued_date") or extracted_fields.get("issue_date"):
            issued_date = iss.get("value") if isinstance(iss, dict) else str(iss)

        doc = await upload_document(
            db=session,
            user_id=current_user.id,
            doc_type=doc_type,
            name=f"{default_label}",
            filename=filename,
            content_type="application/pdf",
            file_size=len(pdf_bytes),
            extracted_fields=extracted_fields,
            extraction_confidence=confidence,
            issued_date=issued_date,
            expiry_date=expiry_date,
            notes=f"Auto-generated sample dummy document for {default_label}",
        )
        save_document_content(doc.storage_key, pdf_bytes)
        seeded_docs.append(
            {
                "id": doc.id,
                "doc_type": doc.doc_type,
                "name": doc.name,
                "filename": doc.filename,
                "fields_count": len(extracted_fields),
            }
        )

    await session.flush()
    return {
        "success": True,
        "message": f"Generated and processed {len(seeded_docs)} sample dummy documents with PyMuPDF",
        "documents": seeded_docs,
    }
