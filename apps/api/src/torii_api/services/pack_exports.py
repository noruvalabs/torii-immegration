"""Helpers to re-export pack-authored content for tests and legacy imports."""

from __future__ import annotations

from typing import Any

from torii_api.services.content_packs import load_pack_by_scope


def pack_questions(scope_id: str) -> list[dict[str, Any]]:
    return load_pack_by_scope(scope_id).questions


def pack_rules(scope_id: str) -> list[dict[str, Any]]:
    return load_pack_by_scope(scope_id).rules


def pack_documents(scope_id: str) -> list[dict[str, Any]]:
    return load_pack_by_scope(scope_id).document_items


def pack_form(scope_id: str) -> dict[str, Any]:
    return load_pack_by_scope(scope_id).primary_form
