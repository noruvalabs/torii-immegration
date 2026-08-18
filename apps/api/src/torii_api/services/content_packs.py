"""Load versioned jurisdiction content packs from ``docs/jurisdictions/*.yml``.

Ops-authored YAML is the source of truth for intake, eligibility, documents, and
forms (M0 in ``docs/plan/00_applicant_v1.md``). Seed materializes the same JSON
into the existing admin-editable tables; runtime rules evaluation never reads
YAML at request time — it reads the DB.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator

from torii_api.config import get_settings

StageCode = Literal["sponsor_petition", "applicant_filing", "school_completion"]
StageActor = Literal["applicant", "sponsor", "institution"]
HandoffArtifact = Literal["coe", "i20", "i129_approval"]

EFFECTIVE_KEYS = ("effective_from", "effective_until")


def parse_iso_date(value: str) -> date:
    """Parse an ISO-8601 date, rejecting anything that isn't a real calendar day."""
    return date.fromisoformat(value)


def effective_window(item: dict[str, Any]) -> tuple[date | None, date | None]:
    """Read the optional ``effective_from`` / ``effective_until`` window from a payload item.

    Returns ``(from, until)`` where either bound may be ``None`` (open-ended).
    Raises ``ValueError`` on a malformed date so bad pack data fails the ingest gate.
    """
    effective_from = item.get("effective_from")
    effective_until = item.get("effective_until")
    if effective_from is not None and not isinstance(effective_from, str):
        raise ValueError("effective_from must be an ISO-8601 string")
    if effective_until is not None and not isinstance(effective_until, str):
        raise ValueError("effective_until must be an ISO-8601 string")
    return (
        parse_iso_date(effective_from) if effective_from is not None else None,
        parse_iso_date(effective_until) if effective_until is not None else None,
    )


def is_effective_on(item: dict[str, Any], as_of: date) -> bool:
    """True when an item's validity window contains ``as_of`` (inclusive from, exclusive until).

    Items without any window are always effective. The engine answers "what were the
    requirements on the date this application was received", never "what are they today".
    """
    effective_from, effective_until = effective_window(item)
    if effective_from is not None and as_of < effective_from:
        return False
    if effective_until is not None and as_of >= effective_until:
        return False
    return True


class Citation(BaseModel):
    authority: str | None = None
    title: str | None = None
    url: str
    source_version: str | None = None
    retrieved: str | None = None

    @field_validator("url")
    @classmethod
    def _http_url(cls, value: str) -> str:
        if not value.startswith("http"):
            raise ValueError("citation.url must be an http(s) URL")
        return value


class PackStage(BaseModel):
    sequence: int = Field(ge=1)
    code: StageCode
    actor: StageActor
    handoff_artifact: HandoffArtifact | None = None


class PackFee(BaseModel):
    code: str
    amount: float | None = None
    currency: str | None = None
    channel: str | None = None
    published: bool = False
    citation: Citation | None = None
    note: str | None = None
    effective_from: str | None = None
    effective_until: str | None = None
    # Tiered schedules (e.g. the Oct 2026 ISA period-granted bands). Each tier is a
    # dict like {"period": "1y", "amount": 33000, "period_from": "2026-10-01"}.
    tiers: list[dict[str, Any]] | None = None

    @field_validator("effective_from", "effective_until")
    @classmethod
    def _iso_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parse_iso_date(value)
        return value


class PackSource(BaseModel):
    url: str
    retrieved: str | None = None
    title: str | None = None

    @field_validator("url")
    @classmethod
    def _http_url(cls, value: str) -> str:
        if not value.startswith("http"):
            raise ValueError("source.url must be an http(s) URL")
        return value


class PackForm(BaseModel):
    code: str
    version: str
    official_title: str
    citation: dict[str, Any]
    field_mappings: list[dict[str, Any]]

    def as_template_row(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "version": self.version,
            "official_title": self.official_title,
            "citation": self.citation,
            "field_mappings": self.field_mappings,
        }


class ScopeMeta(BaseModel):
    jurisdiction: str
    visa_category: str
    action: str
    is_live: bool = True
    name: str | None = None
    research_enabled: bool = False


class ContentPack(BaseModel):
    """One scope pack: e.g. ``jp/work.renewal``."""

    scope_id: str
    scope: ScopeMeta
    stages: list[PackStage] = Field(default_factory=list)
    intake: dict[str, Any]
    eligibility: dict[str, Any]
    documents: dict[str, Any]
    forms: list[PackForm]
    fees: list[PackFee] = Field(default_factory=list)
    sources: list[PackSource] = Field(default_factory=list)

    @property
    def questions(self) -> list[dict[str, Any]]:
        raw = self.intake.get("questions")
        if not isinstance(raw, list):
            raise ValueError(f"{self.scope_id}: intake.questions must be a list")
        return [dict(item) for item in raw]

    @property
    def rules(self) -> list[dict[str, Any]]:
        raw = self.eligibility.get("rules")
        if not isinstance(raw, list):
            raise ValueError(f"{self.scope_id}: eligibility.rules must be a list")
        return [dict(item) for item in raw]

    @property
    def document_items(self) -> list[dict[str, Any]]:
        raw = self.documents.get("items") or self.documents.get("requirements")
        if not isinstance(raw, list):
            raise ValueError(f"{self.scope_id}: documents.items must be a list")
        return [dict(item) for item in raw]

    @property
    def primary_form(self) -> dict[str, Any]:
        if not self.forms:
            raise ValueError(f"{self.scope_id}: at least one form is required")
        return self.forms[0].as_template_row()


class JurisdictionMeta(BaseModel):
    code: str
    name: str
    host_locale: str = "en"
    is_live: bool = False
    efile_enabled: bool = False
    self_filing_allowed: bool | None = None
    notes: str | None = None
    categories: list[dict[str, Any]] = Field(default_factory=list)
    actions: list[dict[str, Any]] = Field(default_factory=list)


def resolve_packs_dir(explicit: str | Path | None = None) -> Path:
    """Locate ``docs/jurisdictions`` in the monorepo or via settings."""
    if explicit:
        path = Path(explicit)
        if path.is_dir():
            return path.resolve()
        raise FileNotFoundError(f"jurisdictions dir not found: {path}")

    settings = get_settings()
    if settings.jurisdictions_dir:
        path = Path(settings.jurisdictions_dir)
        if path.is_dir():
            return path.resolve()
        raise FileNotFoundError(f"TORII_JURISDICTIONS_DIR not found: {path}")

    here = Path(__file__).resolve()
    candidates = [
        here.parents[5] / "docs" / "jurisdictions",  # monorepo root from services/
        Path.cwd() / "docs" / "jurisdictions",
        Path.cwd().parent.parent / "docs" / "jurisdictions",  # from apps/api
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve()
    raise FileNotFoundError(
        "Could not find docs/jurisdictions. Set TORII_JURISDICTIONS_DIR or run from the monorepo."
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping at the root")
    return data


def _scope_id_from_path(path: Path, packs_dir: Path) -> str:
    rel = path.relative_to(packs_dir)
    return f"{rel.parent.as_posix()}/{rel.stem}"


def parse_pack(data: dict[str, Any], *, scope_id: str) -> ContentPack:
    forms_raw = data.get("forms") or []
    if isinstance(forms_raw, dict):
        forms_raw = [forms_raw]
    return ContentPack(
        scope_id=scope_id,
        scope=ScopeMeta.model_validate(data["scope"]),
        stages=[PackStage.model_validate(s) for s in (data.get("stages") or [])],
        intake=dict(data.get("intake") or {}),
        eligibility=dict(data.get("eligibility") or {}),
        documents=dict(data.get("documents") or {}),
        forms=[PackForm.model_validate(f) for f in forms_raw],
        fees=[PackFee.model_validate(f) for f in (data.get("fees") or [])],
        sources=[PackSource.model_validate(s) for s in (data.get("sources") or [])],
    )


def load_pack(path: Path, *, packs_dir: Path | None = None) -> ContentPack:
    root = packs_dir or path.parent.parent
    if path.parent.name not in ("jp", "us") and packs_dir is None:
        root = path.parent
    scope_id = _scope_id_from_path(path, root) if packs_dir else f"{path.parent.name}/{path.stem}"
    if packs_dir is not None:
        scope_id = _scope_id_from_path(path, packs_dir)
    return parse_pack(_load_yaml(path), scope_id=scope_id)


def iter_pack_paths(packs_dir: Path | None = None) -> list[Path]:
    root = packs_dir or resolve_packs_dir()
    paths = sorted(
        p
        for p in root.rglob("*.yml")
        if p.is_file() and not p.name.startswith("_") and p.name != "README.yml"
    )
    return paths


@lru_cache(maxsize=1)
def load_all_packs(packs_dir: str | None = None) -> dict[str, ContentPack]:
    root = resolve_packs_dir(packs_dir)
    packs: dict[str, ContentPack] = {}
    for path in iter_pack_paths(root):
        pack = load_pack(path, packs_dir=root)
        packs[pack.scope_id] = pack
    return packs


def load_pack_by_scope(scope_id: str, packs_dir: str | None = None) -> ContentPack:
    packs = load_all_packs(packs_dir)
    try:
        return packs[scope_id]
    except KeyError as exc:
        raise KeyError(f"content pack not found: {scope_id}") from exc


def load_jurisdiction_meta(code: str, packs_dir: Path | None = None) -> JurisdictionMeta | None:
    root = packs_dir or resolve_packs_dir()
    path = root / code.lower() / "_jurisdiction.yml"
    if not path.is_file():
        return None
    return JurisdictionMeta.model_validate(_load_yaml(path))


def list_jurisdiction_metas(packs_dir: Path | None = None) -> list[JurisdictionMeta]:
    root = packs_dir or resolve_packs_dir()
    metas: list[JurisdictionMeta] = []
    for path in sorted(root.glob("*/_jurisdiction.yml")):
        metas.append(JurisdictionMeta.model_validate(_load_yaml(path)))
    return metas


def workflow_rows_from_packs(
    packs: dict[str, ContentPack] | None = None,
) -> list[dict[str, Any]]:
    """Flatten packs into the shape ``seed._seed_workflow`` expects."""
    source = packs if packs is not None else load_all_packs()
    rows: list[dict[str, Any]] = []
    for pack in sorted(source.values(), key=lambda p: p.scope_id):
        if not pack.scope.is_live:
            continue
        rows.append(
            {
                "scope_id": pack.scope_id,
                "jurisdiction": pack.scope.jurisdiction.upper(),
                "visa_category": pack.scope.visa_category.lower(),
                "action": pack.scope.action.lower(),
                "questions": pack.questions,
                "rules": pack.rules,
                "documents": pack.document_items,
                "form": pack.primary_form,
                "forms": [f.as_template_row() for f in pack.forms],
                "stages": [s.model_dump(mode="json") for s in pack.stages],
                "fees": [f.model_dump(mode="json") for f in pack.fees],
            }
        )
    return rows


def clear_pack_cache() -> None:
    """Reset the pack cache (tests / after pack edits)."""
    load_all_packs.cache_clear()


def resolve_fee(
    fees: list[PackFee],
    *,
    as_of: date,
    channel: str | None = None,
    period: str | None = None,
) -> PackFee | None:
    """Return the fee applicable on ``as_of`` for an optional channel and granted period.

    ``period`` selects a tier (e.g. ``"1y"``) from ``fee.tiers``; the tier's amount then wins
    over the flat ``amount``. Only ``published`` fees are returned — draft figures (like the
    October 2026 ISA schedule) stay hidden until confirmed (NF-2).
    """
    candidates = [fee for fee in fees if fee.published and is_effective_on(fee.model_dump(), as_of)]
    if channel:
        by_channel = [fee for fee in candidates if fee.channel == channel]
        if by_channel:
            candidates = by_channel
    if not candidates:
        return None
    best = sorted(candidates, key=lambda f: f.effective_from or "0000-00-00", reverse=True)[0]
    if period and best.tiers:
        for tier in best.tiers:
            if tier.get("period") == period:
                selected = best.model_copy(
                    update={"amount": tier.get("amount"), "note": tier.get("note", best.note)}
                )
                return selected
    return best
