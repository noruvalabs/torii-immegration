"""Document wallet endpoints for reusable documents."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.auth.deps import CurrentUserDep
from torii_api.db.session import get_session
from torii_api.services.wallet import (
    get_document_types,
    get_document_versions,
    get_user_wallet,
    get_wallet_summary,
    mark_document_expired,
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
    status: str
    created_at: str | None = None


class DocumentVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    filename: str
    content_type: str
    file_size: int | None = None
    notes: str | None = None
    created_at: str | None = None


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
    message: str


class DocumentTypesOut(BaseModel):
    document_types: list[DocumentTypeOut]


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/document-types", response_model=DocumentTypesOut)
async def list_document_types() -> DocumentTypesOut:
    """List all supported document types."""
    doc_types = get_document_types()
    return DocumentTypesOut(
        document_types=[DocumentTypeOut(**dt) for dt in doc_types]
    )


@router.get("/", response_model=list[WalletDocumentOut])
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
    from torii_api.services.wallet import DOCUMENT_TYPES

    # Validate document type
    if doc_type not in DOCUMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document type: {doc_type}. Valid types: {list(DOCUMENT_TYPES.keys())}",
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    # TODO: In production, upload to encrypted storage (S3, etc.)
    # For now, we just record the metadata
    document = await upload_document(
        db=session,
        user_id=current_user.id,
        doc_type=doc_type,
        name=name or doc_type.replace("_", " ").title(),
        filename=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
        file_size=file_size,
        issued_date=issued_date,
        expiry_date=expiry_date,
        notes=notes,
    )

    return WalletUploadOut(
        id=document.id,
        doc_type=document.doc_type,
        name=document.name,
        version=document.version,
        filename=document.filename,
        storage_key=document.storage_key,
        message="Document uploaded successfully",
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
