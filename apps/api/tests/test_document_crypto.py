"""Unit tests for document encryption service (AES-256-GCM + HKDF)."""

from __future__ import annotations

import pytest

from torii_api.services.document_crypto import (
    MAGIC_PREFIX,
    NONCE_SIZE,
    decrypt_document,
    derive_user_key,
    encrypt_document,
    is_encrypted_document,
)

SAMPLE_DOC = b"%PDF-1.4 ... Fake confidential passport document content ..."
MASTER_KEY = "test-master-secret-key-32bytes-long!!"


def test_derive_user_key_is_deterministic_and_unique_per_user():
    """Different user IDs must derive distinct encryption keys."""
    key_user_1 = derive_user_key(MASTER_KEY, user_id=1)
    key_user_1_repeat = derive_user_key(MASTER_KEY, user_id=1)
    key_user_2 = derive_user_key(MASTER_KEY, user_id=2)

    assert key_user_1 == key_user_1_repeat
    assert key_user_1 != key_user_2
    assert len(key_user_1) == 32
    assert len(key_user_2) == 32


def test_encrypt_document_format():
    """Encrypted document must start with magic header and nonce."""
    encrypted = encrypt_document(SAMPLE_DOC, user_id=42, master_key=MASTER_KEY)

    assert is_encrypted_document(encrypted)
    assert encrypted.startswith(MAGIC_PREFIX)
    # Total length: prefix (12) + nonce (12) + ciphertext + tag (16)
    expected_min_len = len(MAGIC_PREFIX) + NONCE_SIZE + len(SAMPLE_DOC) + 16
    assert len(encrypted) == expected_min_len


def test_encryption_roundtrip_success():
    """Authorized user can decrypt their own document."""
    encrypted = encrypt_document(SAMPLE_DOC, user_id=101, master_key=MASTER_KEY)
    decrypted = decrypt_document(
        encrypted, user_id=101, master_key=MASTER_KEY, service_context="test"
    )

    assert decrypted == SAMPLE_DOC


def test_cross_user_decryption_fails():
    """User B cannot decrypt User A's document."""
    encrypted_for_user_a = encrypt_document(SAMPLE_DOC, user_id=1, master_key=MASTER_KEY)

    with pytest.raises(PermissionError) as exc_info:
        decrypt_document(encrypted_for_user_a, user_id=2, master_key=MASTER_KEY)

    assert "Document decryption failed" in str(exc_info.value)


def test_tampered_ciphertext_fails():
    """Any modification to the ciphertext triggers authentication failure."""
    encrypted = bytearray(encrypt_document(SAMPLE_DOC, user_id=5, master_key=MASTER_KEY))

    # Flip a bit in the ciphertext payload
    encrypted[-5] ^= 0xFF

    with pytest.raises(PermissionError) as exc_info:
        decrypt_document(bytes(encrypted), user_id=5, master_key=MASTER_KEY)

    assert "Document decryption failed" in str(exc_info.value)


def test_tampered_nonce_fails():
    """Altering the nonce triggers decryption authentication failure."""
    encrypted = bytearray(encrypt_document(SAMPLE_DOC, user_id=5, master_key=MASTER_KEY))

    # Corrupt nonce byte
    nonce_start = len(MAGIC_PREFIX)
    encrypted[nonce_start] ^= 0x01

    with pytest.raises(PermissionError):
        decrypt_document(bytes(encrypted), user_id=5, master_key=MASTER_KEY)


def test_legacy_unencrypted_fallback():
    """Unencrypted legacy files pass through without crashing."""
    plain = b"Legacy unencrypted plaintext file"
    assert not is_encrypted_document(plain)

    result = decrypt_document(plain, user_id=10, master_key=MASTER_KEY)
    assert result == plain
