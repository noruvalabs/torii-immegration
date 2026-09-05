"""Adding a country, discovering what it offers, and the switch that decides who sees it.

The admin panel's country and route toggles used to be `is_live` — the same column `seed()`
rewrites from `docs/jurisdictions` on every run, so an admin switching something off had it
switched back on by the next deploy. And adding a country wrote three generic routes
(work / student / tourist) and switched them on, whatever the country actually publishes.

These tests hold three lines: the admin switch survives a reseed, a discovered route reaches
nobody until an admin turns it on, and an uncited route is not stored at all (NF-2).
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from torii_api.services import scope_discovery
from torii_api.services.scope_discovery import (
    SOURCE_DISCOVERED,
    DiscoveredScope,
    DiscoveryResult,
    ScopeDiscoveryUnavailable,
    discover_scopes,
)

ISA = "https://www.isa.go.jp/en/applications/procedures/16-1.html"


# ── Fixtures and helpers ───────────────────────────────────────────────────────


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


async def _applicant_token(client: AsyncClient, email: str = "applicant@example.com") -> str:
    await client.post("/v1/auth/register", json={"email": email, "password": "secure-pass"})
    login = await client.post(
        "/v1/auth/login",
        json={"email_or_username": email, "password": "secure-pass"},
    )
    return login.json()["access_token"]


def _discovery_payload(
    *,
    categories: list[dict[str, Any]] | None = None,
    actions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "jurisdiction_code": "JP",
        "visa_categories": categories
        if categories is not None
        else [
            {
                "code": "hsp",
                "name": "Highly Skilled Professional",
                "description": "Points-based fast track to permanent residency.",
                "citation": {"authority": "ISA", "title": "HSP", "url": ISA},
            }
        ],
        "case_actions": actions
        if actions is not None
        else [
            {
                "code": "permanent_residence",
                "name": "Permanent residence application",
                "description": "Apply for permanent resident status.",
                "citation": {"authority": "ISA", "title": "Procedures", "url": ISA},
            }
        ],
        "source_pages": [{"url": ISA, "retrieved_at": "2026-08-31T00:00:00+00:00"}],
        "discovered_at": "2026-08-31T00:00:00+00:00",
    }


# Captured before any test patches it, so re-stubbing inside one test does not wrap a stub.
_REAL_ASYNC_CLIENT = httpx.AsyncClient


def _stub_ai(monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any] | None, status: int = 200):
    """Stub the AI service at the transport boundary, and record what was asked of it."""
    calls: list[dict[str, Any]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append({"url": str(request.url), "body": request.read().decode()})
        return httpx.Response(status, json=payload if payload is not None else {})

    def build(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs.pop("timeout", None)
        return _REAL_ASYNC_CLIENT(*args, transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(scope_discovery.httpx, "AsyncClient", build)
    return calls


# ── The transport boundary ─────────────────────────────────────────────────────


async def test_discovery_reads_the_ai_services_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _stub_ai(monkeypatch, _discovery_payload())

    result = await discover_scopes("jp", origin_country="bd")

    assert calls[0]["url"].endswith("/ai/ops/discover-scopes")
    # Both codes are normalized upward before they leave, so the AI service never has to.
    assert json.loads(calls[0]["body"]) == {"jurisdiction_code": "JP", "origin_country": "BD"}
    assert [c.code for c in result.visa_categories] == ["hsp"]
    assert result.visa_categories[0].citation["url"] == ISA
    assert [a.code for a in result.case_actions] == ["permanent_residence"]


async def test_an_uncited_route_does_not_survive_the_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The AI service drops uncited items; this is the check that keeps them out of the
    database even if that ever stops being true (NF-2)."""
    _stub_ai(
        monkeypatch,
        _discovery_payload(
            categories=[
                {"code": "invented", "name": "Invented Route"},
                {"code": "no_url", "name": "No URL", "citation": {"authority": "ISA"}},
                {"code": "not_http", "name": "Not HTTP", "citation": {"url": "isa.go.jp/x"}},
                {
                    "code": "real",
                    "name": "Real Route",
                    "citation": {"authority": "ISA", "url": ISA},
                },
            ]
        ),
    )

    result = await discover_scopes("JP")

    assert [c.code for c in result.visa_categories] == ["real"]


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        (None, 500),  # the AI service failed
        ({"visa_categories": "not a list"}, 200),  # it answered with a shape we cannot read
    ],
)
async def test_an_unreachable_service_is_said_so_not_read_as_empty(
    monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any] | None, status: int
) -> None:
    """ "This country publishes nothing" and "we could not ask" are different answers."""
    _stub_ai(monkeypatch, payload, status=status)

    if status != 200:
        with pytest.raises(ScopeDiscoveryUnavailable):
            await discover_scopes("JP")
    else:
        # A readable envelope with an unreadable slice yields no routes, not an exception.
        result = await discover_scopes("JP")
        assert result.visa_categories == []


# ── Through the API ────────────────────────────────────────────────────────────


async def test_discover_requires_admin(client: AsyncClient, engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO jurisdictions (code, name, is_live) VALUES ('JP', 'Japan', 1)")
        )
    token = await _applicant_token(client)
    resp = await client.post(
        "/v1/jurisdictions/1/discover", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


async def test_a_new_country_starts_with_every_route_switched_off(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """The starter routes are a floor so the screen is never empty — not an offer."""
    admin = {"Authorization": f"Bearer {await _admin_token(client, engine)}"}
    created = await client.post(
        "/v1/jurisdictions", json={"code": "ca", "name": "Canada", "is_live": True}, headers=admin
    )
    assert created.status_code == 201
    jid = created.json()["id"]

    routes = (await client.get(f"/v1/jurisdictions/{jid}/visa-categories", headers=admin)).json()
    assert {r["code"] for r in routes} == {"work", "student", "tourist"}
    assert all(r["is_enabled"] is False for r in routes)
    assert all(r["source"] == "manual" for r in routes)

    # And so nothing is offered to an applicant yet.
    offered = await client.get(f"/v1/jurisdictions/{jid}/visa-categories?live_only=true")
    assert offered.json() == []


async def test_discovery_writes_candidates_switched_off_and_is_re_runnable(
    client: AsyncClient, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin = {"Authorization": f"Bearer {await _admin_token(client, engine)}"}
    jid = (
        await client.post(
            "/v1/jurisdictions",
            json={"code": "jp", "name": "Japan", "is_live": True},
            headers=admin,
        )
    ).json()["id"]

    _stub_ai(monkeypatch, _discovery_payload())
    first = await client.post(f"/v1/jurisdictions/{jid}/discover", headers=admin)
    assert first.status_code == 200
    body = first.json()
    assert body["created"] == 2
    assert [c["outcome"] for c in body["visa_categories"]] == ["created"]
    assert body["source_pages"][0]["url"] == ISA

    routes = (await client.get(f"/v1/jurisdictions/{jid}/visa-categories", headers=admin)).json()
    hsp = next(r for r in routes if r["code"] == "hsp")
    assert hsp["is_enabled"] is False, "a search result is a proposal, not a decision"
    assert hsp["is_live"] is False, "nothing seeded backs a discovered route"
    assert hsp["research_enabled"] is True, "its requirements come from live research"
    assert hsp["source"] == SOURCE_DISCOVERED
    assert hsp["citation"]["url"] == ISA
    assert hsp["description"].startswith("Points-based")

    # An admin curates: switches one on, and renames it.
    await client.patch(
        f"/v1/jurisdictions/{jid}/visa-categories/{hsp['id']}",
        json={"is_enabled": True, "name": "Highly Skilled Professional - 高度専門職"},
        headers=admin,
    )

    # A route on its own is not yet something to apply on: a case needs a procedure too,
    # and ``scope_case`` refuses a scope whose procedure is switched off. Switching the
    # discovered procedure on is the other half of the same curation.
    pr_action = next(
        a
        for a in (await client.get(f"/v1/jurisdictions/{jid}/case-actions", headers=admin)).json()
        if a["code"] == "permanent_residence"
    )
    await client.patch(
        f"/v1/jurisdictions/{jid}/case-actions/{pr_action['id']}",
        json={"is_enabled": True},
        headers=admin,
    )

    # Re-running discovery finds nothing new and leaves the admin's work alone.
    _stub_ai(monkeypatch, _discovery_payload())
    second = await client.post(f"/v1/jurisdictions/{jid}/discover", headers=admin)
    assert second.json()["created"] == 0
    assert [c["outcome"] for c in second.json()["visa_categories"]] == ["unchanged"]

    routes = (await client.get(f"/v1/jurisdictions/{jid}/visa-categories", headers=admin)).json()
    hsp = next(r for r in routes if r["code"] == "hsp")
    assert hsp["is_enabled"] is True
    assert hsp["name"] == "Highly Skilled Professional - 高度専門職"

    # Once on, it is what the applicant is offered, described in the country's own words.
    offered = (await client.get(f"/v1/jurisdictions/{jid}/visa-categories?live_only=true")).json()
    assert [r["code"] for r in offered] == ["hsp"]

    applicant = {"Authorization": f"Bearer {await _applicant_token(client)}"}
    visa_types = (await client.get("/v1/geo/visa-types?destination=JP", headers=applicant)).json()
    assert [v["code"] for v in visa_types] == ["hsp"]
    assert visa_types[0]["description"].startswith("Points-based")


async def test_an_unreachable_research_service_is_a_502_not_an_empty_country(
    client: AsyncClient, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin = {"Authorization": f"Bearer {await _admin_token(client, engine)}"}
    jid = (
        await client.post("/v1/jurisdictions", json={"code": "ca", "name": "Canada"}, headers=admin)
    ).json()["id"]

    _stub_ai(monkeypatch, None, status=503)
    resp = await client.post(f"/v1/jurisdictions/{jid}/discover", headers=admin)
    assert resp.status_code == 502
    assert "Could not discover routes for CA" in resp.json()["detail"]


async def test_discovery_that_reads_nothing_says_so(
    client: AsyncClient, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin = {"Authorization": f"Bearer {await _admin_token(client, engine)}"}
    jid = (
        await client.post("/v1/jurisdictions", json={"code": "ca", "name": "Canada"}, headers=admin)
    ).json()["id"]

    _stub_ai(monkeypatch, _discovery_payload(categories=[], actions=[]))
    resp = await client.post(f"/v1/jurisdictions/{jid}/discover", headers=admin)
    assert resp.status_code == 200
    assert resp.json()["created"] == 0
    # Pages were read and none yielded a route: the admin is told that, and where to look.
    assert "could not read a single route off them" in resp.json()["message"]


async def test_discovery_that_reaches_nothing_says_that_instead(
    client: AsyncClient, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Read nothing and understood nothing are different, and read differently."""
    admin = {"Authorization": f"Bearer {await _admin_token(client, engine)}"}
    jid = (
        await client.post("/v1/jurisdictions", json={"code": "ca", "name": "Canada"}, headers=admin)
    ).json()["id"]

    payload = _discovery_payload(categories=[], actions=[])
    payload["source_pages"] = []
    _stub_ai(monkeypatch, payload)

    resp = await client.post(f"/v1/jurisdictions/{jid}/discover", headers=admin)
    assert "No official pages" in resp.json()["message"]


# ── The switch, and the reseed that used to undo it ────────────────────────────


async def test_the_admin_switch_survives_a_reseed(client: AsyncClient, engine: AsyncEngine) -> None:
    """The reason `is_enabled` exists rather than reusing `is_live`."""
    from torii_api.db.engine import create_session_factory
    from torii_api.management.seed import seed

    admin = {"Authorization": f"Bearer {await _admin_token(client, engine)}"}
    session_factory = create_session_factory(engine)
    await seed(session_factory=session_factory)

    jurisdictions = (await client.get("/v1/jurisdictions", headers=admin)).json()
    jp = next(j for j in jurisdictions if j["code"] == "JP")
    assert jp["is_enabled"] is True

    routes = (
        await client.get(f"/v1/jurisdictions/{jp['id']}/visa-categories", headers=admin)
    ).json()
    student = next(r for r in routes if r["code"] == "student")
    assert student["source"] == "pack"

    # Ops switches Japan's student route off, and then Japan itself.
    await client.patch(
        f"/v1/jurisdictions/{jp['id']}/visa-categories/{student['id']}",
        json={"is_enabled": False},
        headers=admin,
    )
    await client.patch(f"/v1/jurisdictions/{jp['id']}", json={"is_enabled": False}, headers=admin)

    # A deploy runs seed() again — which rewrites is_live from the packs.
    await seed(session_factory=session_factory)

    jurisdictions = (await client.get("/v1/jurisdictions", headers=admin)).json()
    jp_after = next(j for j in jurisdictions if j["code"] == "JP")
    assert jp_after["is_live"] is True, "the pack still says Japan has live content"
    assert jp_after["is_enabled"] is False, "and ops still says it is not being offered"

    routes = (
        await client.get(f"/v1/jurisdictions/{jp['id']}/visa-categories", headers=admin)
    ).json()
    student_after = next(r for r in routes if r["code"] == "student")
    assert student_after["is_live"] is True
    assert student_after["is_enabled"] is False

    # Neither is offered, and neither can be scoped by posting the codes directly.
    offered_countries = (await client.get("/v1/jurisdictions?live_only=true")).json()
    assert "JP" not in {j["code"] for j in offered_countries}
    applicant = await _applicant_token(client)
    scoped = await client.post(
        "/v1/cases/scope",
        json={"jurisdiction_code": "JP", "visa_category_code": "student", "action_code": "renewal"},
        headers={"Authorization": f"Bearer {applicant}"},
    )
    assert scoped.status_code == 400
    assert scoped.json()["detail"] == "this case scope is not available"


async def test_a_switched_off_route_is_hidden_but_its_siblings_are_not(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    from torii_api.db.engine import create_session_factory
    from torii_api.management.seed import seed

    admin = {"Authorization": f"Bearer {await _admin_token(client, engine)}"}
    await seed(session_factory=create_session_factory(engine))
    jurisdictions = (await client.get("/v1/jurisdictions", headers=admin)).json()
    jp = next(j for j in jurisdictions if j["code"] == "JP")

    routes = (
        await client.get(f"/v1/jurisdictions/{jp['id']}/visa-categories", headers=admin)
    ).json()
    work = next(r for r in routes if r["code"] == "work")
    await client.patch(
        f"/v1/jurisdictions/{jp['id']}/visa-categories/{work['id']}",
        json={"is_enabled": False},
        headers=admin,
    )

    applicant = {"Authorization": f"Bearer {await _applicant_token(client)}"}
    offered = (
        await client.get("/v1/cases/visa-categories?jurisdiction_code=JP&live_only=true")
    ).json()
    codes = {r["code"] for r in offered}
    assert "work" not in codes
    assert "student" in codes

    visa_types = (await client.get("/v1/geo/visa-types?destination=JP", headers=applicant)).json()
    assert "work" not in {v["code"] for v in visa_types}


async def test_a_packs_own_wording_reaches_the_applicant(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """The visa-type step used to repeat the route name back as its own subtitle."""
    from torii_api.db.engine import create_session_factory
    from torii_api.management.seed import seed

    await seed(session_factory=create_session_factory(engine))
    applicant = {"Authorization": f"Bearer {await _applicant_token(client)}"}

    visa_types = (await client.get("/v1/geo/visa-types?destination=JP", headers=applicant)).json()
    dependent = next(v for v in visa_types if v["code"] == "dependent")
    assert dependent["description"] != dependent["name"]
    assert "spouse and children" in dependent["description"]

    app_types = (
        await client.get(
            "/v1/geo/application-types?destination=JP&visa_type=work", headers=applicant
        )
    ).json()
    renewal = next(a for a in app_types if a["code"] == "renewal")
    assert "before it expires" in renewal["description"]


# ── Applying candidates, without the HTTP hop ─────────────────────────────────


async def test_applying_fills_a_gap_but_never_overwrites(engine: AsyncEngine) -> None:
    """An existing route's name and switches belong to whoever set them."""
    from torii_api.db.engine import create_session_factory
    from torii_api.db.models import Jurisdiction, VisaCategory

    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        jurisdiction = Jurisdiction(code="JP", name="Japan", is_live=True)
        session.add(jurisdiction)
        await session.flush()
        session.add(
            VisaCategory(
                jurisdiction_id=jurisdiction.id,
                code="work",
                name="A name an admin chose",
                is_live=True,
                is_enabled=True,
                research_enabled=False,
                source="pack",
            )
        )
        await session.commit()

    async with session_factory() as session:
        from sqlalchemy import select

        jurisdiction = (await session.scalars(select(Jurisdiction))).one()
        applied = await scope_discovery.apply_discovery(
            session,
            jurisdiction,
            DiscoveryResult(
                jurisdiction_code="JP",
                visa_categories=[
                    DiscoveredScope(
                        code="work",
                        name="A name the model preferred",
                        description="Employment activities.",
                        citation={"url": ISA},
                    )
                ],
            ),
        )
        await session.commit()

        assert [item.outcome for item in applied.visa_categories] == ["enriched"]
        row = (await session.scalars(select(VisaCategory))).one()
        assert row.name == "A name an admin chose"
        assert row.is_enabled is True
        assert row.is_live is True
        assert row.research_enabled is False
        # Only the gaps were filled.
        assert row.description == "Employment activities."
        assert row.citation["url"] == ISA


# ── The listing and the create agree ───────────────────────────────────────────


async def _scope_fixture(client: AsyncClient, engine: AsyncEngine) -> tuple[dict[str, str], int]:
    admin = {"Authorization": f"Bearer {await _admin_token(client, engine)}"}
    jid = (
        await client.post(
            "/v1/jurisdictions",
            json={"code": "jp", "name": "Japan", "is_live": True},
            headers=admin,
        )
    ).json()["id"]
    return admin, jid


async def _set_scope_row(
    client: AsyncClient,
    admin: dict[str, str],
    jid: int,
    kind: str,
    code: str,
    name: str | None = None,
    **flags: bool,
) -> None:
    """Set a route's or procedure's flags, whether or not the starter set already has it."""
    rows = (await client.get(f"/v1/jurisdictions/{jid}/{kind}", headers=admin)).json()
    existing = next((r for r in rows if r["code"] == code), None)
    body: dict[str, Any] = dict(flags)
    if name is not None:
        body["name"] = name
    if existing is None:
        resp = await client.post(
            f"/v1/jurisdictions/{jid}/{kind}",
            json={"code": code, "name": name or code.replace("_", " ").title(), **flags},
            headers=admin,
        )
        assert resp.status_code == 201, resp.text
        return
    resp = await client.patch(
        f"/v1/jurisdictions/{jid}/{kind}/{existing['id']}", json=body, headers=admin
    )
    assert resp.status_code == 200, resp.text


async def _set_action(
    client: AsyncClient, admin: dict[str, str], jid: int, code: str, **flags: bool
) -> None:
    await _set_scope_row(client, admin, jid, "case-actions", code, **flags)


async def _set_route(
    client: AsyncClient,
    admin: dict[str, str],
    jid: int,
    code: str,
    name: str | None = None,
    **flags: bool,
) -> None:
    await _set_scope_row(client, admin, jid, "visa-categories", code, name, **flags)


async def test_a_listed_route_is_one_an_applicant_can_actually_open_a_case_on(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """The listing endpoints and ``scope_case`` used to disagree about the same scope.

    A route with a content pack paired with a procedure served by research passed each of
    the two per-row filters the geo endpoints applied, so it was offered — and then
    ``scope_case`` refused it, because it asks whether the *scope* is sourced one way or
    the other. The applicant met that as a bare "this case scope is not available" on the
    last click of a five-step flow.
    """
    admin, jid = await _scope_fixture(client, engine)

    # A packed route, and a procedure that is only research-enabled: neither is wrong on
    # its own, and together they are not a scope anyone can be served.
    await _set_route(
        client, admin, jid, "work", is_live=True, is_enabled=True, research_enabled=False
    )
    await _set_action(
        client, admin, jid, "renewal", is_enabled=True, is_live=False, research_enabled=True
    )

    applicant = {"Authorization": f"Bearer {await _applicant_token(client)}"}
    visa_types = (await client.get("/v1/geo/visa-types?destination=JP", headers=applicant)).json()
    assert visa_types == [], "a route with no procedure it pairs with is not an offer"

    # Give it a procedure sourced the same way, and it becomes a real offer.
    await _set_action(client, admin, jid, "new", is_enabled=True, is_live=True)
    visa_types = (await client.get("/v1/geo/visa-types?destination=JP", headers=applicant)).json()
    assert [v["code"] for v in visa_types] == ["work"]

    actions = (
        await client.get(
            "/v1/geo/application-types?destination=JP&visa_type=work", headers=applicant
        )
    ).json()
    assert [a["code"] for a in actions] == ["new"], "the mismatched renewal is not offered"

    # Everything still listed survives the last click.
    for a in actions:
        created = await client.post(
            "/v1/cases/scope",
            json={
                "jurisdiction_code": "JP",
                "visa_category_code": "work",
                "action_code": a["code"],
            },
            headers=applicant,
        )
        assert created.status_code == 201, created.text


async def test_a_known_destination_never_falls_back_to_the_generic_route_list(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """An empty country offers nothing, rather than three routes it has no rows for."""
    await _scope_fixture(client, engine)
    applicant = {"Authorization": f"Bearer {await _applicant_token(client)}"}

    visa_types = (await client.get("/v1/geo/visa-types?destination=JP", headers=applicant)).json()
    assert visa_types == []

    app_types = (
        await client.get(
            "/v1/geo/application-types?destination=JP&visa_type=work", headers=applicant
        )
    ).json()
    assert app_types == []


async def test_the_route_list_leads_with_the_routes_people_ask_for(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """Ordering by the internal handle buried work and tourist under the rarer routes."""
    admin, jid = await _scope_fixture(client, engine)
    await _set_action(client, admin, jid, "new", is_enabled=True, is_live=True)
    for code, name in [
        ("dependent", "Dependent Visa"),
        ("work", "Work Visa"),
        ("hsp", "Highly Skilled Professional"),
        ("student", "Student Visa"),
    ]:
        await _set_route(client, admin, jid, code, name, is_live=True, is_enabled=True)

    applicant = {"Authorization": f"Bearer {await _applicant_token(client)}"}
    visa_types = (await client.get("/v1/geo/visa-types?destination=JP", headers=applicant)).json()
    assert [v["code"] for v in visa_types] == ["work", "student", "dependent", "hsp"]


async def test_a_research_only_route_says_so(client: AsyncClient, engine: AsyncEngine) -> None:
    """The applicant can tell a reviewed route from one researched on demand."""
    admin, jid = await _scope_fixture(client, engine)
    await _set_action(client, admin, jid, "new", is_enabled=True, is_live=True)
    await _set_action(
        client, admin, jid, "renewal", is_enabled=True, is_live=False, research_enabled=True
    )
    await _set_route(client, admin, jid, "work", "Work Visa", is_live=True, is_enabled=True)
    await _set_route(
        client, admin, jid, "hsp", "HSP", is_live=False, is_enabled=True, research_enabled=True
    )

    applicant = {"Authorization": f"Bearer {await _applicant_token(client)}"}
    visa_types = (await client.get("/v1/geo/visa-types?destination=JP", headers=applicant)).json()
    flags = {v["code"]: v["is_research"] for v in visa_types}
    assert flags == {"work": False, "hsp": True}


async def test_a_route_carries_no_description_it_did_not_come_with(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    """The generic per-code lines only repeated what the name already said."""
    admin, jid = await _scope_fixture(client, engine)
    await _set_action(client, admin, jid, "new", is_enabled=True, is_live=True)
    await _set_route(
        client,
        admin,
        jid,
        "student",
        "Student Visa - 留学 (Study at a university, college, or language school)",
        is_live=True,
        is_enabled=True,
    )

    applicant = {"Authorization": f"Bearer {await _applicant_token(client)}"}
    visa_types = (await client.get("/v1/geo/visa-types?destination=JP", headers=applicant)).json()
    assert visa_types[0]["description"] == ""
