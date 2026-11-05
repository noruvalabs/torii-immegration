"""Phase 3 — in-person track: readiness audit, Tasheer appointments, dossier.

Covers the audit aggregation (services.case_audit + GET /cases/{id}/audit),
the appointment request → confirm flow gated by the Saudi apply-route, the
route-specific instructions, and the dossier packet carrying the audit
summary and the booked appointment.
"""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine

from torii_api.services.case_audit import (
    assemble_audit,
    build_instructions,
    consistency_checks,
)
from torii_api.services.content_packs import load_pack_by_scope
from torii_api.services.eligibility import EligibilityResult
from torii_api.services.case_audit import DocumentAudit, IntakeAudit


async def _seed_sa(engine: AsyncEngine) -> None:
    """Seed the SA tourist scope from the real Phase 1 content pack."""
    pack = load_pack_by_scope("sa/tourist.new_application")
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO jurisdictions (code, name, is_live) VALUES ('SA', 'Saudi Arabia', 1)")
        )
        jid = (
            await conn.execute(text("SELECT id FROM jurisdictions WHERE code = 'SA'"))
        ).scalar_one()
        await conn.execute(
            text(
                "INSERT INTO visa_categories (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jid}, 'tourist', 'Tourist', 1)"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO case_actions (jurisdiction_id, code, name, is_live)"
                f" VALUES ({jid}, 'new_application', 'New application', 1)"
            )
        )
        vc_id = (
            await conn.execute(
                text(
                    "SELECT id FROM visa_categories WHERE jurisdiction_id ="
                    f" {jid} AND code = 'tourist'"
                )
            )
        ).scalar_one()
        ca_id = (
            await conn.execute(
                text(
                    "SELECT id FROM case_actions WHERE jurisdiction_id ="
                    f" {jid} AND code = 'new_application'"
                )
            )
        ).scalar_one()
        await conn.execute(
            text(
                "INSERT INTO intake_definitions"
                " (jurisdiction_id, visa_category_id, case_action_id, questions, is_live)"
                f" VALUES ({jid}, {vc_id}, {ca_id}, :q, 1)"
            ),
            {"q": json.dumps(pack.questions)},
        )
        await conn.execute(
            text(
                "INSERT INTO eligibility_rule_sets"
                " (jurisdiction_id, visa_category_id, case_action_id, rules, is_live)"
                f" VALUES ({jid}, {vc_id}, {ca_id}, :r, 1)"
            ),
            {"r": json.dumps(pack.rules)},
        )
        await conn.execute(
            text(
                "INSERT INTO document_requirement_sets"
                " (jurisdiction_id, visa_category_id, case_action_id, items, is_live)"
                f" VALUES ({jid}, {vc_id}, {ca_id}, :i, 1)"
            ),
            {"i": json.dumps(pack.document_items)},
        )
        for form in pack.forms:
            row = form.as_template_row()
            await conn.execute(
                text(
                    "INSERT INTO form_templates"
                    " (jurisdiction_id, visa_category_id, case_action_id, code, version,"
                    " is_live, official_title, citation, field_mappings)"
                    f" VALUES ({jid}, {vc_id}, {ca_id}, :code, :version, 1, :title, :cit, :maps)"
                ),
                {
                    "code": row["code"],
                    "version": row["version"],
                    "title": row["official_title"],
                    "cit": json.dumps(row["citation"]),
                    "maps": json.dumps(row["field_mappings"]),
                },
            )


async def _register_and_scope(client: AsyncClient, email: str) -> tuple[dict[str, str], int]:
    register = await client.post(
        "/v1/auth/register", json={"email": email, "password": "secure-pass"}
    )
    assert register.status_code == 201
    headers = {"Authorization": f"Bearer {register.json()['access_token']}"}
    scoped = await client.post(
        "/v1/cases/scope",
        json={
            "jurisdiction_code": "SA",
            "visa_category_code": "tourist",
            "action_code": "new_application",
            "locale": "en",
        },
        headers=headers,
    )
    assert scoped.status_code == 201
    return headers, scoped.json()["id"]


async def _answer_all(
    client: AsyncClient, headers: dict[str, str], case_id: int, answers: dict
) -> None:
    for key, value in answers.items():
        resp = await client.put(
            f"/v1/cases/{case_id}/intake/answer",
            json={"key": key, "value": value},
            headers=headers,
        )
        assert resp.status_code == 200, (key, resp.text)


async def _ops_headers(client: AsyncClient, engine: AsyncEngine) -> dict[str, str]:
    from torii_api.auth.security import hash_password
    from torii_api.db.engine import create_session_factory
    from torii_api.db.models import User, UserRole

    factory = create_session_factory(engine)
    async with factory() as session:
        session.add(
            User(
                email="ops@torii.test",
                password_hash=hash_password("ops-pass-123"),
                role=UserRole.OPS,
                full_name="Torii Ops",
                email_verified=True,
            )
        )
        await session.commit()
    login = await client.post(
        "/v1/auth/login",
        json={"email_or_username": "ops@torii.test", "password": "ops-pass-123"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _complete_answers(nationality: str, **overrides) -> dict:
    answers = {
        "full_name": "TEST APPLICANT",
        "nationality": nationality,
        "residence_country": nationality,
        "date_of_birth": "1990-01-15",
        "passport_number": "A01234567",
        "passport_expiry_date": "2032-01-01",
        "passport_valid_six_months": True,
        "purpose_of_visit": "tourism",
        "planned_arrival_date": "2026-12-20",
        "intended_length_of_stay_days": 7,
        "accommodation_name": "Hotel in Riyadh",
        "has_return_ticket": True,
        "email_address": "applicant@example.com",
        "phone_number": "+8801700000000",
        "has_used_us_uk_schengen_visa": False,
        "western_permanent_residence": False,
        "gcc_residence": False,
        "employment_status": "employed",
        "occupation": "Engineer",
        "has_sufficient_funds": True,
    }
    answers.update(overrides)
    return answers


# ── Audit: aggregation and readiness transitions ─────────────────────────────


@pytest.mark.asyncio
async def test_audit_incomplete_intake_is_blocked(client: AsyncClient, engine: AsyncEngine) -> None:
    await _seed_sa(engine)
    headers, case_id = await _register_and_scope(client, "audit-blocked@example.com")
    await _answer_all(client, headers, case_id, {"nationality": "LK"})

    resp = await client.get(f"/v1/cases/{case_id}/audit", headers=headers)
    assert resp.status_code == 200, resp.text
    audit = resp.json()
    assert audit["route"] == "in_person"
    assert audit["overall"] == "blocked"
    assert audit["intake"]["complete"] is False
    assert "passport_number" in audit["intake"]["missing_required"]
    # In-person instructions travel with the audit.
    titles = " ".join(step["title"] for step in audit["instructions"])
    assert "Tasheer" in titles


@pytest.mark.asyncio
async def test_audit_complete_in_person_case(client: AsyncClient, engine: AsyncEngine) -> None:
    await _seed_sa(engine)
    headers, case_id = await _register_and_scope(client, "audit-complete@example.com")
    await _answer_all(client, headers, case_id, _complete_answers("LK"))
    refresh = await client.post(f"/v1/cases/{case_id}/checklist/refresh", headers=headers)
    assert refresh.status_code == 200, refresh.text

    resp = await client.get(f"/v1/cases/{case_id}/audit", headers=headers)
    assert resp.status_code == 200, resp.text
    audit = resp.json()
    assert audit["route"] == "in_person"
    assert audit["intake"]["complete"] is True
    # Sri Lanka is not eVisa-eligible: the nationality rule reads at_risk with
    # route guidance, so a complete case is needs_attention, never a hard fail.
    assert audit["eligibility"]["result"] == "at_risk"
    checks = {check["key"]: check["status"] for check in audit["checks"]}
    assert checks["passport_six_month_validity"] == "pass"
    assert checks["stay_within_90_days"] == "pass"
    assert checks["return_not_before_arrival"] == "pass"
    assert checks["contact_email_present"] == "pass"
    # The intake answer endpoint auto-syncs name/passport into the profile,
    # so by audit time profile and intake agree.
    assert checks["identity_consistency"] == "pass"
    assert audit["overall"] == "needs_attention"
    # The documents section reflects the refreshed checklist: 7 required items
    # for an employed LK tourist, none gathered yet.
    assert audit["documents"]["required_total"] == 7
    assert audit["documents"]["required_satisfied"] == 0
    assert len(audit["documents"]["missing_required"]) == 7


def test_assemble_audit_ready_only_when_everything_passes() -> None:
    ready = assemble_audit(
        case_id=1,
        reference="SA-TEST-1",
        jurisdiction_code="SA",
        route="in_person",
        intake=IntakeAudit(total_required=3, answered_required=3, missing_required=[], complete=True),
        eligibility=EligibilityResult(result="pass", findings=[]),
        documents=DocumentAudit(total_items=2, required_total=2, required_satisfied=2),
        uploaded=[],
        checks=[],
    )
    assert ready.overall == "ready"

    no_evaluation = assemble_audit(
        case_id=1,
        reference="SA-TEST-1",
        jurisdiction_code="SA",
        route="in_person",
        intake=IntakeAudit(total_required=3, answered_required=3, missing_required=[], complete=True),
        eligibility=None,
        documents=DocumentAudit(total_items=2, required_total=2, required_satisfied=2),
        uploaded=[],
        checks=[],
    )
    assert no_evaluation.overall == "needs_attention"


# ── Consistency checks ───────────────────────────────────────────────────────


def test_consistency_checks_fail_on_contradictions() -> None:
    short_passport = consistency_checks(
        {
            "full_name": "TEST APPLICANT",
            "passport_number": "A01234567",
            "planned_arrival_date": "2026-12-20",
            "passport_expiry_date": "2027-03-01",  # < arrival + 6 months
            "intended_length_of_stay_days": 7,
            "has_return_ticket": True,
        },
        contact_email="applicant@example.com",
    )
    by_key = {check.key: check.status for check in short_passport}
    assert by_key["passport_six_month_validity"] == "fail"

    backwards_trip = consistency_checks(
        {
            "full_name": "TEST APPLICANT",
            "passport_number": "A01234567",
            "planned_arrival_date": "2026-12-20",
            "passport_expiry_date": "2032-01-01",
            "departure_date": "2026-12-01",  # returns before arriving
            "intended_length_of_stay_days": 120,  # beyond the 90-day cap
        },
        contact_email=None,
    )
    by_key = {check.key: check.status for check in backwards_trip}
    assert by_key["return_not_before_arrival"] == "fail"
    assert by_key["stay_within_90_days"] == "fail"
    assert by_key["contact_email_present"] == "fail"

    mismatch = consistency_checks(
        {
            "full_name": "INTAKE NAME",
            "passport_number": "A01234567",
            "passport_expiry_date": "2032-01-01",
            "planned_arrival_date": "2026-12-20",
            "intended_length_of_stay_days": 7,
            "has_return_ticket": True,
        },
        profile_full_name="PROFILE NAME",
        profile_passport_number="A01234567",
        contact_email="applicant@example.com",
    )
    by_key = {check.key: check.status for check in mismatch}
    assert by_key["identity_consistency"] == "fail"


# ── Instructions per route ───────────────────────────────────────────────────


def test_instructions_per_route() -> None:
    consular = build_instructions("in_person")
    titles = [step.title for step in consular]
    assert any("Tasheer" in title for title in titles)
    assert any("biometric" in title.lower() for title in titles)
    # The embassy decision step is marked as an estimate, not a promise.
    decision = next(step for step in consular if "decision" in step.title.lower())
    assert "estimate" in decision.detail
    assert consular[0].citation is None or isinstance(consular[0].citation, dict)

    package = build_instructions("online_package")
    assert [s.title for s in package] == titles

    umrah = build_instructions("agent_umrah")
    assert any("Nusuk Masar" in step.detail for step in umrah)
    assert any("licensed" in step.title.lower() or "licensed" in step.detail.lower() for step in umrah)

    online = build_instructions("online_evisa")
    assert len(online) == 1
    assert "ksavisa.sa" in online[0].detail

    assert build_instructions(None) == []


# ── Appointments ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_appointment_flow_in_person(client: AsyncClient, engine: AsyncEngine) -> None:
    await _seed_sa(engine)
    headers, case_id = await _register_and_scope(client, "appt-inperson@example.com")
    await _answer_all(client, headers, case_id, _complete_answers("LK"))
    ops = await _ops_headers(client, engine)

    none = await client.get(f"/v1/cases/{case_id}/appointment", headers=headers)
    assert none.status_code == 200
    body = none.json()
    assert body["status"] == "none"
    assert body["booking_url"] == "https://vc.tasheer.com"
    assert body["prefill"]["full_name"] == "TEST APPLICANT"
    assert body["prefill"]["passport_number"] == "A01234567"

    first = await client.post(
        f"/v1/cases/{case_id}/appointment/request",
        json={"preferred_date": "2026-11-16", "preferred_time_window": "morning"},
        headers=headers,
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "requested"
    assert first.json()["centre"].startswith("Tasheer Saudi Visa Service Centre")

    # A second request supersedes the pending one.
    second = await client.post(
        f"/v1/cases/{case_id}/appointment/request",
        json={"preferred_date": "2026-11-18"},
        headers=headers,
    )
    assert second.status_code == 200, second.text
    assert second.json()["preferred_date"] == "2026-11-18"

    from torii_api.db.engine import create_session_factory
    from torii_api.db.models import CaseAppointment

    factory = create_session_factory(engine)
    async with factory() as session:
        rows = (
            await session.scalars(
                select(CaseAppointment).where(CaseAppointment.case_id == case_id)
            )
        ).all()
    assert sorted(row.status for row in rows) == ["requested", "superseded"]

    # Applicants cannot confirm their own booking — that is an ops action.
    denied = await client.post(
        f"/v1/cases/{case_id}/appointment/confirm",
        json={
            "appointment_date": "2026-11-18",
            "appointment_time": "10:30 AM",
            "reference": "TSH-TEST-001",
        },
        headers=headers,
    )
    assert denied.status_code == 403

    booked = await client.post(
        f"/v1/cases/{case_id}/appointment/confirm",
        json={
            "appointment_date": "2026-11-18",
            "appointment_time": "10:30 AM",
            "reference": "TSH-TEST-001",
        },
        headers=ops,
    )
    assert booked.status_code == 200, booked.text
    assert booked.json()["status"] == "booked"
    assert booked.json()["reference"] == "TSH-TEST-001"
    assert any("biometric" in step["title"].lower() for step in booked.json()["instructions"])

    current = await client.get(f"/v1/cases/{case_id}/appointment", headers=headers)
    assert current.json()["status"] == "booked"
    assert current.json()["appointment_date"] == "2026-11-18"

    # A booked appointment blocks further requests.
    again = await client.post(
        f"/v1/cases/{case_id}/appointment/request",
        json={"preferred_date": "2026-11-20"},
        headers=headers,
    )
    assert again.status_code == 400
    assert "already booked" in again.json()["detail"]


@pytest.mark.asyncio
async def test_appointment_allowed_for_package_route(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_sa(engine)
    headers, case_id = await _register_and_scope(client, "appt-package@example.com")
    await _answer_all(client, headers, case_id, _complete_answers("BD"))

    audit = await client.get(f"/v1/cases/{case_id}/audit", headers=headers)
    assert audit.json()["route"] == "online_package"

    resp = await client.post(
        f"/v1/cases/{case_id}/appointment/request",
        json={"preferred_date": "2026-11-16"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "requested"


@pytest.mark.asyncio
async def test_appointment_rejected_for_online_route(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_sa(engine)
    headers, case_id = await _register_and_scope(client, "appt-online@example.com")
    await _answer_all(
        client, headers, case_id, {"nationality": "US", "purpose_of_visit": "tourism"}
    )
    resp = await client.post(
        f"/v1/cases/{case_id}/appointment/request",
        json={"preferred_date": "2026-11-16"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "online" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_appointment_rejected_for_umrah_agent_route(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_sa(engine)
    headers, case_id = await _register_and_scope(client, "appt-umrah@example.com")
    await _answer_all(
        client, headers, case_id, {"nationality": "BD", "purpose_of_visit": "umrah"}
    )
    resp = await client.post(
        f"/v1/cases/{case_id}/appointment/request",
        json={"preferred_date": "2026-11-16"},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "Nusuk Masar" in resp.json()["detail"]


# ── Dossier ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dossier_pdf_carries_audit_and_appointment(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    await _seed_sa(engine)
    headers, case_id = await _register_and_scope(client, "dossier@example.com")
    await _answer_all(client, headers, case_id, _complete_answers("LK"))
    ops = await _ops_headers(client, engine)
    await client.post(
        f"/v1/cases/{case_id}/appointment/request",
        json={"preferred_date": "2026-11-18"},
        headers=headers,
    )
    booked = await client.post(
        f"/v1/cases/{case_id}/appointment/confirm",
        json={
            "appointment_date": "2026-11-18",
            "appointment_time": "10:30 AM",
            "reference": "TSH-TEST-001",
        },
        headers=ops,
    )
    assert booked.status_code == 200, booked.text

    resp = await client.get(f"/v1/cases/{case_id}/export/dossier-packet", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.content[:4] == b"%PDF"
    assert len(resp.content) > 2000

    try:
        import io

        from pypdf import PdfReader
    except ImportError:
        pytest.skip("pypdf not available for text-level dossier assertions")
    text_out = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(resp.content)).pages)
    assert "READINESS AUDIT" in text_out
    assert "TSH-TEST-001" in text_out
    assert "Tasheer" in text_out
