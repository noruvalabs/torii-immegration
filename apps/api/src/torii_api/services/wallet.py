"""Document wallet service with versioning and reuse."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from torii_api.db.models import (
    DocumentWalletItem,
    DocumentWalletItemVersion,
)
from torii_api.services.document_crypto import decrypt_document, encrypt_document

log = structlog.get_logger()

# Common document types for visa applications
DOCUMENT_TYPES: dict[str, dict[str, str]] = {
    "passport": {"name": "Passport", "category": "identity"},
    "national_id": {"name": "National ID Card", "category": "identity"},
    "photo": {"name": "Photograph", "category": "identity"},
    "bank_statement": {"name": "Bank Statement", "category": "financial"},
    "proof_of_funds": {"name": "Proof of Funds", "category": "financial"},
    "tax_return": {"name": "Tax Return", "category": "financial"},
    "employment_letter": {"name": "Employment Letter", "category": "employment"},
    "employment_contract": {"name": "Employment Contract", "category": "employment"},
    "pay_slips": {"name": "Pay Slips", "category": "employment"},
    "business_registration": {"name": "Business Registration", "category": "employment"},
    "academic_certificate": {"name": "Academic Certificate", "category": "education"},
    "enrollment_letter": {"name": "Enrollment Letter", "category": "education"},
    "transcript": {"name": "Transcript", "category": "education"},
    "flight_itinerary": {"name": "Flight Itinerary", "category": "travel"},
    "travel_itinerary": {"name": "Travel Itinerary", "category": "travel"},
    "hotel_booking": {"name": "Hotel Booking", "category": "travel"},
    "travel_insurance": {"name": "Travel Insurance", "category": "travel"},
    "invitation_letter": {"name": "Invitation Letter", "category": "support"},
    "guarantor_letter": {"name": "Guarantor Letter", "category": "support"},
    "residence_card": {"name": "Residence Card", "category": "immigration"},
    "visa_copy": {"name": "Previous Visa", "category": "immigration"},
    "other": {"name": "Other Document", "category": "support"},
}

DOC_TYPE_ALIASES: dict[str, str] = {
    "passport_photo": "photo",
}


def normalize_doc_type(code: str) -> str:
    """Normalize a document type code, handling aliases and fallbacks gracefully."""
    code_clean = (code or "").lower().strip()
    if code_clean in DOCUMENT_TYPES:
        return code_clean
    if code_clean in DOC_TYPE_ALIASES:
        return DOC_TYPE_ALIASES[code_clean]
    return "other"


def get_document_types() -> list[dict[str, str]]:
    """Get list of supported document types."""
    return [
        {"code": code, "name": info["name"], "category": info["category"]}
        for code, info in DOCUMENT_TYPES.items()
    ]


def generate_storage_key(user_id: int, doc_type: str, filename: str) -> str:
    """Generate a unique storage key for a document."""
    unique_id = uuid.uuid4().hex[:16]
    return f"wallets/{user_id}/{doc_type}/{unique_id}/{filename}"


_STORAGE_DIR = Path("data/wallet_storage")
_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _extract_user_id_from_storage_key(storage_key: str) -> int | None:
    """Extract user_id from a storage key formatted as wallets/{user_id}/..."""
    parts = storage_key.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "wallets" and parts[1].isdigit():
        return int(parts[1])
    return None


def save_document_content(
    storage_key: str,
    content: bytes,
    user_id: int | None = None,
) -> Path:
    """Save document bytes to disk storage with end-to-end AES-256-GCM encryption."""
    if user_id is None:
        user_id = _extract_user_id_from_storage_key(storage_key)

    if user_id is not None:
        payload = encrypt_document(content, user_id=user_id)
    else:
        payload = content

    target = _STORAGE_DIR / storage_key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return target


def get_document_content(
    storage_key: str,
    user_id: int | None = None,
    service_context: str | None = None,
) -> bytes | None:
    """Retrieve and decrypt document bytes from disk storage."""
    target = _STORAGE_DIR / storage_key
    if not target.is_file():
        return None

    raw_bytes = target.read_bytes()
    if user_id is None:
        user_id = _extract_user_id_from_storage_key(storage_key)

    if user_id is not None:
        return decrypt_document(raw_bytes, user_id=user_id, service_context=service_context)
    return decrypt_document(raw_bytes, user_id=0, service_context=service_context)


async def upload_document(
    db: AsyncSession,
    user_id: int,
    doc_type: str,
    name: str,
    filename: str,
    content_type: str,
    file_size: int | None = None,
    extracted_fields: dict[str, Any] | None = None,
    extraction_confidence: float | None = None,
    issued_date: str | None = None,
    expiry_date: str | None = None,
    notes: str | None = None,
) -> DocumentWalletItem:
    """Upload a new document to the wallet."""
    # Check if user already has an active document of this type
    existing = await get_active_document_by_type(db, user_id, doc_type)

    if existing:
        # Create a new version instead of replacing
        return await update_document(
            db=db,
            document_id=existing.id,
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            extracted_fields=extracted_fields,
            extraction_confidence=extraction_confidence,
            issued_date=issued_date,
            expiry_date=expiry_date,
            notes=notes,
        )

    storage_key = generate_storage_key(user_id, doc_type, filename)

    document = DocumentWalletItem(
        user_id=user_id,
        doc_type=doc_type,
        name=name,
        version=1,
        is_latest=True,
        storage_key=storage_key,
        filename=filename,
        content_type=content_type,
        file_size=file_size,
        extracted_fields=extracted_fields or {},
        extraction_confidence=extraction_confidence,
        issued_date=issued_date,
        expiry_date=expiry_date,
        status="active",
        notes=notes,
    )
    db.add(document)
    await db.flush()

    # Create initial version record
    version = DocumentWalletItemVersion(
        document_id=document.id,
        version=1,
        storage_key=storage_key,
        filename=filename,
        content_type=content_type,
        file_size=file_size,
        extracted_fields=extracted_fields or {},
        extraction_confidence=extraction_confidence,
        notes=notes,
    )
    db.add(version)
    await db.flush()

    log.info(
        "wallet.document_uploaded",
        document_id=document.id,
        user_id=user_id,
        doc_type=doc_type,
        version=1,
    )
    return document


async def update_document(
    db: AsyncSession,
    document_id: int,
    user_id: int,
    filename: str,
    content_type: str,
    file_size: int | None = None,
    extracted_fields: dict[str, Any] | None = None,
    extraction_confidence: float | None = None,
    issued_date: str | None = None,
    expiry_date: str | None = None,
    notes: str | None = None,
) -> DocumentWalletItem:
    """Update a document with a new version."""
    result = await db.execute(
        select(DocumentWalletItem).where(
            DocumentWalletItem.id == document_id,
            DocumentWalletItem.user_id == user_id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise ValueError("Document not found")

    # Increment version
    new_version = document.version + 1
    document.version = new_version
    document.filename = filename
    document.content_type = content_type
    document.file_size = file_size
    if extracted_fields is not None:
        document.extracted_fields = extracted_fields
    if extraction_confidence is not None:
        document.extraction_confidence = extraction_confidence
    if issued_date is not None:
        document.issued_date = issued_date
    if expiry_date is not None:
        document.expiry_date = expiry_date
    if notes is not None:
        document.notes = notes

    # Generate new storage key for versioning
    storage_key = generate_storage_key(user_id, document.doc_type, filename)
    document.storage_key = storage_key

    # Create version record
    version = DocumentWalletItemVersion(
        document_id=document_id,
        version=new_version,
        storage_key=storage_key,
        filename=filename,
        content_type=content_type,
        file_size=file_size,
        extracted_fields=extracted_fields or document.extracted_fields,
        extraction_confidence=extraction_confidence or document.extraction_confidence,
        notes=notes,
    )
    db.add(version)
    await db.flush()

    log.info(
        "wallet.document_updated",
        document_id=document_id,
        user_id=user_id,
        new_version=new_version,
    )
    return document


async def get_active_document_by_type(
    db: AsyncSession,
    user_id: int,
    doc_type: str,
) -> DocumentWalletItem | None:
    """Get the active (latest) document of a specific type."""
    result = await db.execute(
        select(DocumentWalletItem).where(
            DocumentWalletItem.user_id == user_id,
            DocumentWalletItem.doc_type == doc_type,
            DocumentWalletItem.is_latest == True,  # noqa: E712
            DocumentWalletItem.status == "active",
        )
    )
    return result.scalar_one_or_none()


async def get_user_wallet(
    db: AsyncSession,
    user_id: int,
    include_expired: bool = False,
) -> list[DocumentWalletItem]:
    """Get all active documents in user's wallet."""
    query = (
        select(DocumentWalletItem)
        .where(
            DocumentWalletItem.user_id == user_id,
            DocumentWalletItem.is_latest == True,  # noqa: E712
        )
        .order_by(DocumentWalletItem.doc_type)
    )

    if not include_expired:
        query = query.where(DocumentWalletItem.status == "active")

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_document_versions(
    db: AsyncSession,
    document_id: int,
    user_id: int,
) -> list[DocumentWalletItemVersion]:
    """Get all versions of a document."""
    result = await db.execute(
        select(DocumentWalletItemVersion)
        .join(DocumentWalletItem)
        .where(
            DocumentWalletItemVersion.document_id == document_id,
            DocumentWalletItem.user_id == user_id,
        )
        .order_by(DocumentWalletItemVersion.version.desc())
    )
    return list(result.scalars().all())


async def mark_document_expired(
    db: AsyncSession,
    document_id: int,
    user_id: int,
) -> DocumentWalletItem:
    """Mark a document as expired."""
    result = await db.execute(
        select(DocumentWalletItem).where(
            DocumentWalletItem.id == document_id,
            DocumentWalletItem.user_id == user_id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise ValueError("Document not found")

    document.status = "expired"
    await db.flush()

    log.info("wallet.document_expired", document_id=document_id, user_id=user_id)
    return document


async def check_document_expiry(
    db: AsyncSession,
    user_id: int,
) -> list[DocumentWalletItem]:
    """Check for documents expiring soon (within 30 days)."""
    from datetime import timedelta

    now = datetime.now(UTC)
    threshold = (now + timedelta(days=30)).strftime("%Y-%m-%d")

    result = await db.execute(
        select(DocumentWalletItem).where(
            DocumentWalletItem.user_id == user_id,
            DocumentWalletItem.is_latest == True,  # noqa: E712
            DocumentWalletItem.status == "active",
            DocumentWalletItem.expiry_date.isnot(None),
            DocumentWalletItem.expiry_date <= threshold,
        )
    )
    return list(result.scalars().all())


async def get_wallet_summary(db: AsyncSession, user_id: int) -> dict[str, Any]:
    """Get a summary of the user's document wallet."""
    wallet = await get_user_wallet(db, user_id)
    expiring = await check_document_expiry(db, user_id)

    # Group by category
    by_category: dict[str, list[dict[str, Any]]] = {}
    for doc in wallet:
        doc_info = DOCUMENT_TYPES.get(doc.doc_type, {})
        category = doc_info.get("category", "other")
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(
            {
                "id": doc.id,
                "doc_type": doc.doc_type,
                "name": doc.name,
                "version": doc.version,
                "filename": doc.filename,
                "issued_date": doc.issued_date,
                "expiry_date": doc.expiry_date,
                "status": doc.status,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
        )

    return {
        "total_documents": len(wallet),
        "documents_by_category": by_category,
        "expiring_soon": [
            {
                "id": doc.id,
                "doc_type": doc.doc_type,
                "name": doc.name,
                "expiry_date": doc.expiry_date,
            }
            for doc in expiring
        ],
    }
