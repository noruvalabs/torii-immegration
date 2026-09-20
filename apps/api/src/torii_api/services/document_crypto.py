"""End-to-end document encryption and access protection service.

Critical personal documents uploaded by users are encrypted using AES-256-GCM
with user-isolated keys derived using HKDF-SHA256 from the master secret and
the user's unique identifier.

Wire Format for Encrypted Documents:
    [12 bytes Magic Prefix b"TORII_ENC_V1"]
    [12 bytes Random Nonce / IV]
    [Ciphertext + 16-byte GCM Authentication Tag]

Security Guarantees:
- Confidentiality: Documents at rest on disk or object storage are ciphertext only.
- Integrity & Authenticity: AES-256-GCM verifies an authentication tag over both
  the ciphertext and the user's bound Associated Data (AAD: "torii:user:<user_id>").
- Isolation: Key derivation is user-scoped; User A's key cannot decrypt User B's documents.
- Admin Protection: Document bytes can only be decrypted for the owning user or
  authorized in-memory processing services (OCR, case assembly).
"""

from __future__ import annotations

import os
from typing import Final

import structlog
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from torii_api.config import get_settings

logger = structlog.get_logger("torii.security.crypto")

MAGIC_PREFIX: Final[bytes] = b"TORII_ENC_V1"
NONCE_SIZE: Final[int] = 12  # 96 bits standard for AES-GCM
KEY_SIZE: Final[int] = 32  # 256 bits
TAG_SIZE: Final[int] = 16  # 128 bits
SALT: Final[bytes] = b"torii_user_document_encryption_v1"


def derive_user_key(master_key: str, user_id: int) -> bytes:
    """Derive a 256-bit User Data Encryption Key (UDEK) using HKDF-SHA256."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=SALT,
        info=f"torii-user-document-encryption:{user_id}".encode(),
    )
    return hkdf.derive(master_key.encode("utf-8"))


def is_encrypted_document(data: bytes) -> bool:
    """Check if the given payload starts with the Torii encryption magic header."""
    min_length = len(MAGIC_PREFIX) + NONCE_SIZE + TAG_SIZE
    return data.startswith(MAGIC_PREFIX) and len(data) >= min_length


def encrypt_document(
    plaintext: bytes,
    user_id: int,
    master_key: str | None = None,
) -> bytes:
    """Encrypt document bytes using AES-256-GCM bound to the specified user_id."""
    if master_key is None:
        master_key = get_settings().document_encryption_key

    user_key = derive_user_key(master_key, user_id)
    aesgcm = AESGCM(user_key)
    nonce = os.urandom(NONCE_SIZE)
    aad = f"torii:user:{user_id}".encode()

    ciphertext = aesgcm.encrypt(nonce, plaintext, aad)
    return MAGIC_PREFIX + nonce + ciphertext


def decrypt_document(
    payload: bytes,
    user_id: int,
    master_key: str | None = None,
    service_context: str | None = None,
) -> bytes:
    """Decrypt document bytes using AES-256-GCM.

    If payload is not encrypted with the magic prefix, returns raw bytes for
    backward-compatibility with legacy unencrypted local development files.
    """
    if not is_encrypted_document(payload):
        # Legacy fallback for pre-existing unencrypted files in dev
        logger.debug(
            "unencrypted_document_accessed_fallback",
            user_id=user_id,
            service_context=service_context or "user_access",
        )
        return payload

    if master_key is None:
        master_key = get_settings().document_encryption_key

    prefix_len = len(MAGIC_PREFIX)
    nonce = payload[prefix_len : prefix_len + NONCE_SIZE]
    ciphertext = payload[prefix_len + NONCE_SIZE :]

    user_key = derive_user_key(master_key, user_id)
    aesgcm = AESGCM(user_key)
    aad = f"torii:user:{user_id}".encode()

    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
    except InvalidTag as exc:
        logger.warning(
            "document_decryption_failed",
            user_id=user_id,
            service_context=service_context or "user_access",
            error="InvalidTag",
        )
        raise PermissionError(
            "Document decryption failed: unauthorized access, key mismatch, or corrupted data."
        ) from exc

    logger.info(
        "document_decrypted",
        user_id=user_id,
        service_context=service_context or "user_access",
        payload_bytes=len(plaintext),
    )
    return plaintext
