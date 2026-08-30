"""Admin edits to seeded pack content, and the reseed that used to destroy them.

The `/admin/ops` upserts write into the seeded rows, and `seed()` rewrites those rows from
`docs/jurisdictions` on every run. An edit saved that way lived until the next boot. These
tests hold the line that an override does not.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from torii_api.services.pack_overrides import (
    SECTION_DOCUMENTS,
    SECTION_INTAKE,
    SECTION_RULES,
    OverrideError,
    apply_overrides,
    parse_path,
    section_of,
    stale_overrides,
)

# ── The path grammar ───────────────────────────────────────────────────────────


def test_a_path_names_a_section_an_item_and_a_field() -> None:
    section, selector, field_path = parse_path("intake.questions[key=full_name].prompt")
    assert section == SECTION_INTAKE
    assert selector == ("key", "full_name")
    assert field_path == ["prompt"]

    # A nested field is addressable, which is what a localized document name needs.
    assert parse_path("documents[code=passport_original].name.en")[2] == ["name", "en"]
    assert section_of("eligibility.rules[key=criminal_record].failure_status") == SECTION_RULES


@pytest.mark.parametrize(
    "path",
    [
        "questions[key=full_name].prompt",  # no section
        "intake.questions.prompt",  # no item selected
        "intake.questions[key=full_name]",  # an item, but no field on it
        "documents",  # a section and nothing else
        "documents[code=x].name[en=1]",  # a selector where a field belongs
    ],
)
def test_a_path_that_addresses_nothing_is_refused(path: str) -> None:
    """Refused at write time, because the alternative is an edit that is stored, never
    applied, and never explained."""
    with pytest.raises(OverrideError):
        parse_path(path)


# ── Applying ───────────────────────────────────────────────────────────────────


def _questions() -> list[dict]:
    return [
        {"key": "full_name", "prompt": "What is your full name?", "type": "string"},
        {"key": "nationality", "prompt": "What is your nationality?", "type": "enum"},
    ]


def test_an_override_replaces_one_value_and_leaves_the_rest() -> None:
    items = _questions()
    result = apply_overrides(
        items,
        [{"path": "intake.questions[key=full_name].prompt", "value": "Your name, as printed?"}],
        section=SECTION_INTAKE,
    )
    assert result[0]["prompt"] == "Your name, as printed?"
    assert result[0]["type"] == "string"
    assert result[1] == items[1]


def test_applying_never_mutates_the_seeded_row() -> None:
    """The list handed in is SQLAlchemy-attached JSON. Editing it in place would write the
    override into the very row this mechanism exists to leave alone."""
    items = _questions()
    before = items[0]["prompt"]
    apply_overrides(
        items,
        [{"path": "intake.questions[key=full_name].prompt", "value": "changed"}],
        section=SECTION_INTAKE,
    )
    assert items[0]["prompt"] == before


def test_an_override_can_set_a_field_the_item_does_not_have_yet() -> None:
    result = apply_overrides(
        _questions(),
        [{"path": "intake.questions[key=nationality].required", "value": False}],
        section=SECTION_INTAKE,
    )
    assert result[1]["required"] is False


def test_a_nested_field_is_written_without_dropping_its_siblings() -> None:
    documents = [{"code": "passport_original", "name": {"en": "Passport", "ja": "旅券"}}]
    result = apply_overrides(
        documents,
        [{"path": "documents[code=passport_original].name.en", "value": "Passport (original)"}],
        section=SECTION_DOCUMENTS,
    )
    assert result[0]["name"] == {"en": "Passport (original)", "ja": "旅券"}


def test_an_override_for_another_section_is_left_alone() -> None:
    items = _questions()
    assert (
        apply_overrides(
            items,
            [{"path": "documents[code=passport_original].name", "value": "x"}],
            section=SECTION_INTAKE,
        )
        == items
    )


def test_an_override_whose_item_is_gone_is_skipped_not_misapplied() -> None:
    """The pack moved on. "Edit this question" does not mean "edit whichever question is
    there now", so the edit is dropped and reported instead."""
    overrides = [{"path": "intake.questions[key=middle_name].prompt", "value": "?"}]
    items = _questions()
    assert apply_overrides(items, overrides, section=SECTION_INTAKE) == items
    assert stale_overrides(items, overrides, section=SECTION_INTAKE) == [
        "intake.questions[key=middle_name].prompt"
    ]


# ── Through the API, across a reseed ───────────────────────────────────────────


async def _admin_token(client: AsyncClient, engine: AsyncEngine) -> str:
    from torii_api.auth.security import hash_password

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (email, password_hash, role, is_active, email_verified)"
                " VALUES (:email, :pw, 'admin', 1, 1)"
            ),
            {"email": "ops@example.com", "pw": hash_password("ops-pass-123")},
        )
    login = await client.post(
        "/v1/auth/login",
        json={"email_or_username": "ops@example.com", "password": "ops-pass-123"},
    )
    return login.json()["access_token"]


async def _seed(engine: AsyncEngine) -> None:
    from torii_api.db.engine import create_session_factory
    from torii_api.management.seed import seed

    await seed(session_factory=create_session_factory(engine))


async def test_an_override_survives_the_reseed_that_erased_the_old_edits(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    token = await _admin_token(client, engine)
    headers = {"Authorization": f"Bearer {token}"}
    await _seed(engine)

    scope = {
        "jurisdiction_code": "JP",
        "visa_category": "tourist",
        "action": "new_application",
    }
    created = await client.put(
        "/v1/admin/ops/pack-overrides",
        headers=headers,
        json={
            **scope,
            "path": "eligibility.rules[key=criminal_record].failure_status",
            "value": "fail",
            "reason": "consular counsel wants any conviction escalated for this corridor",
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["created_by"] == "ops@example.com"

    # The reseed rewrites the seeded rows from the packs. It does not touch this table.
    await _seed(engine)

    listed = await client.get("/v1/admin/ops/pack-overrides", headers=headers, params=scope)
    assert listed.status_code == 200
    body = listed.json()
    assert [o["path"] for o in body["overrides"]] == [
        "eligibility.rules[key=criminal_record].failure_status"
    ]
    assert body["stale"] == []


async def test_an_override_is_refused_for_a_path_that_addresses_nothing(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    token = await _admin_token(client, engine)
    headers = {"Authorization": f"Bearer {token}"}
    await _seed(engine)

    resp = await client.put(
        "/v1/admin/ops/pack-overrides",
        headers=headers,
        json={
            "jurisdiction_code": "JP",
            "visa_category": "tourist",
            "action": "new_application",
            "path": "intake.questions[key=no_such_question].prompt",
            "value": "?",
        },
    )
    assert resp.status_code == 404
    assert "addresses nothing" in resp.json()["detail"]


async def test_editing_the_same_path_twice_replaces_the_edit(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """One live value per path, so "what is live" has one answer."""
    token = await _admin_token(client, engine)
    headers = {"Authorization": f"Bearer {token}"}
    await _seed(engine)

    scope = {
        "jurisdiction_code": "JP",
        "visa_category": "tourist",
        "action": "new_application",
    }
    path = "intake.questions[key=occupation].prompt"
    for value in ("First wording", "Second wording"):
        resp = await client.put(
            "/v1/admin/ops/pack-overrides",
            headers=headers,
            json={**scope, "path": path, "value": value},
        )
        assert resp.status_code == 200

    listed = await client.get("/v1/admin/ops/pack-overrides", headers=headers, params=scope)
    overrides = listed.json()["overrides"]
    assert len(overrides) == 1
    assert overrides[0]["value"] == "Second wording"


async def test_deleting_an_override_returns_the_scope_to_the_pack(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    token = await _admin_token(client, engine)
    headers = {"Authorization": f"Bearer {token}"}
    await _seed(engine)

    scope = {
        "jurisdiction_code": "JP",
        "visa_category": "tourist",
        "action": "new_application",
    }
    created = await client.put(
        "/v1/admin/ops/pack-overrides",
        headers=headers,
        json={**scope, "path": "intake.questions[key=occupation].prompt", "value": "Job?"},
    )
    override_id = created.json()["id"]

    deleted = await client.delete(f"/v1/admin/ops/pack-overrides/{override_id}", headers=headers)
    assert deleted.status_code == 204

    listed = await client.get("/v1/admin/ops/pack-overrides", headers=headers, params=scope)
    assert listed.json()["overrides"] == []


async def test_an_applicant_cannot_edit_a_pack(client: AsyncClient) -> None:
    await client.post(
        "/v1/auth/register",
        json={"email": "applicant@example.com", "password": "applicant-pass-1"},
    )
    login = await client.post(
        "/v1/auth/login",
        json={"email_or_username": "applicant@example.com", "password": "applicant-pass-1"},
    )
    token = login.json()["access_token"]
    resp = await client.put(
        "/v1/admin/ops/pack-overrides",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "jurisdiction_code": "JP",
            "visa_category": "tourist",
            "action": "new_application",
            "path": "intake.questions[key=occupation].prompt",
            "value": "anything",
        },
    )
    assert resp.status_code in (401, 403)


async def test_an_edit_reaches_the_applicant_and_reverting_it_puts_the_pack_back(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """The point of the whole mechanism: what ops change is what the applicant is asked."""
    admin = {"Authorization": f"Bearer {await _admin_token(client, engine)}"}
    await _seed(engine)

    register = await client.post(
        "/v1/auth/register",
        json={"email": "traveller@example.com", "password": "secure-pass"},
    )
    applicant = {"Authorization": f"Bearer {register.json()['access_token']}"}
    scoped = await client.post(
        "/v1/cases/scope",
        json={
            "jurisdiction_code": "JP",
            "visa_category_code": "tourist",
            "action_code": "new_application",
        },
        headers=applicant,
    )
    assert scoped.status_code == 201
    case_id = scoped.json()["id"]

    def prompt_of(body: dict, key: str) -> str:
        return next(q["prompt"] for q in body["questions"] if q["key"] == key)

    before = await client.get(f"/v1/cases/{case_id}/intake", headers=applicant)
    assert before.status_code == 200
    packed = prompt_of(before.json(), "occupation")

    edit = await client.put(
        "/v1/admin/ops/pack-overrides",
        headers=admin,
        json={
            "jurisdiction_code": "JP",
            "visa_category": "tourist",
            "action": "new_application",
            "path": "intake.questions[key=occupation].prompt",
            "value": "What do you do for a living?",
            "reason": "applicants read the old wording as asking for an employer",
        },
    )
    assert edit.status_code == 200

    after = await client.get(f"/v1/cases/{case_id}/intake", headers=applicant)
    assert prompt_of(after.json(), "occupation") == "What do you do for a living?"

    reverted = await client.delete(
        f"/v1/admin/ops/pack-overrides/{edit.json()['id']}", headers=admin
    )
    assert reverted.status_code == 204

    restored = await client.get(f"/v1/cases/{case_id}/intake", headers=applicant)
    assert prompt_of(restored.json(), "occupation") == packed


async def test_an_edit_to_a_document_reaches_the_checklist(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """The rules and documents seam is wired the same way as intake, and separately."""
    admin = {"Authorization": f"Bearer {await _admin_token(client, engine)}"}
    await _seed(engine)

    register = await client.post(
        "/v1/auth/register",
        json={"email": "checklist@example.com", "password": "secure-pass"},
    )
    applicant = {"Authorization": f"Bearer {register.json()['access_token']}"}
    scoped = await client.post(
        "/v1/cases/scope",
        json={
            "jurisdiction_code": "JP",
            "visa_category_code": "tourist",
            "action_code": "new_application",
        },
        headers=applicant,
    )
    case_id = scoped.json()["id"]

    edit = await client.put(
        "/v1/admin/ops/pack-overrides",
        headers=admin,
        json={
            "jurisdiction_code": "JP",
            "visa_category": "tourist",
            "action": "new_application",
            "path": "documents[code=passport_original].name.en",
            "value": "Passport — the original book, not a copy",
            "reason": "applicants kept uploading a scan",
        },
    )
    assert edit.status_code == 200, edit.text

    refreshed = await client.post(f"/v1/cases/{case_id}/checklist/refresh", headers=applicant)
    assert refreshed.status_code == 200, refreshed.text
    names = [item["name"] for item in refreshed.json()]
    assert "Passport — the original book, not a copy" in names
