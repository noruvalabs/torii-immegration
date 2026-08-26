"""Build the answer pack for a jurisdiction that is filed online.

The UK publishes no application form. Every route is completed on gov.uk, so there is
nothing to fill in and hand over — and producing a PDF that looks like a UK application
form misrepresents the process to the applicant. What genuinely helps is their own
answers laid out in the order the online service asks for them, so they can work down
the screen, plus an explicit list of what the service will ask that they have not
answered yet.

Everything here is derived from the pack's declared ``field_mappings`` and the
jurisdiction's ``apply_url``. Adding a country needs no code: declare
``filing_mode: online_portal`` in its ``_jurisdiction.yml`` and give its forms
``section.field_name`` mappings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Sections the online services ask about, in the order they normally appear. A section
# the pack names but this list does not is kept, ordered after the known ones.
_SECTION_ORDER: tuple[str, ...] = (
    "applicant",
    "personal",
    "identity",
    "passport",
    "contact",
    "address",
    "sponsor",
    "employer",
    "employment",
    "course",
    "study",
    "finances",
    "financial",
    "travel",
    "trip",
    "accommodation",
    "history",
    "immigration_history",
    "declarations",
    "security",
)

_SECTION_TITLES: dict[str, str] = {
    "applicant": "About you",
    "personal": "Personal details",
    "identity": "Identity",
    "passport": "Passport and travel document",
    "contact": "Contact details",
    "address": "Address",
    "sponsor": "Your sponsor",
    "employer": "Your employer",
    "employment": "Employment",
    "course": "Your course",
    "study": "Study",
    "finances": "Money and finances",
    "financial": "Money and finances",
    "travel": "Travel plans",
    "trip": "Travel plans",
    "accommodation": "Where you will stay",
    "history": "Immigration history",
    "immigration_history": "Immigration history",
    "declarations": "Declarations",
    "security": "Security questions",
}


def _humanise(token: str) -> str:
    return token.replace("_", " ").replace(".", " ").strip().capitalize()


@dataclass
class PortalField:
    """One question the online service asks, and the applicant's answer for it."""

    field: str
    label: str
    answer_key: str
    value: str | None
    required: bool

    @property
    def answered(self) -> bool:
        return self.value is not None and self.value != ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "label": self.label,
            "answer_key": self.answer_key,
            "value": self.value,
            "required": self.required,
            "answered": self.answered,
        }


@dataclass
class PortalSection:
    key: str
    title: str
    fields: list[PortalField] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "fields": [item.as_dict() for item in self.fields],
        }


@dataclass
class PortalPack:
    """Everything the applicant needs in front of them while filling the real form."""

    jurisdiction: str
    scope_label: str
    apply_url: str | None
    sections: list[PortalSection] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)

    @property
    def all_fields(self) -> list[PortalField]:
        return [item for section in self.sections for item in section.fields]

    @property
    def answered(self) -> list[PortalField]:
        return [item for item in self.all_fields if item.answered]

    @property
    def outstanding(self) -> list[PortalField]:
        return [item for item in self.all_fields if not item.answered]

    def as_dict(self) -> dict[str, Any]:
        return {
            "jurisdiction": self.jurisdiction,
            "scope_label": self.scope_label,
            "apply_url": self.apply_url,
            "sections": [section.as_dict() for section in self.sections],
            "citations": self.citations,
            "answered_count": len(self.answered),
            "outstanding_count": len(self.outstanding),
            "outstanding": [item.label for item in self.outstanding],
        }


def _split_field(form_field: str) -> tuple[str, str]:
    """``"applicant.full_name"`` → ``("applicant", "full_name")``."""
    if "." in form_field:
        section, _, name = form_field.partition(".")
        return section.strip().lower(), name.strip()
    return "general", form_field.strip()


def _format(value: Any) -> str:
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value).strip()


def build_portal_pack(
    forms: list[dict[str, Any]],
    answers: dict[str, Any],
    *,
    jurisdiction: str,
    scope_label: str,
    apply_url: str | None = None,
) -> PortalPack:
    """Group a scope's declared field mappings into the sections the portal asks about.

    Answers are printed only where the applicant actually gave one; an unanswered field
    keeps its question and is listed as outstanding rather than filled with a guess.
    """
    buckets: dict[str, PortalSection] = {}
    citations: list[dict[str, Any]] = []
    seen_fields: set[str] = set()

    for form in forms:
        citation = form.get("citation")
        if isinstance(citation, dict) and citation.get("url"):
            if citation not in citations:
                citations.append(dict(citation))
        if apply_url is None and isinstance(citation, dict):
            candidate = str(citation.get("url") or "")
            if candidate.startswith("http"):
                apply_url = candidate

        for mapping in form.get("field_mappings") or []:
            if not isinstance(mapping, dict):
                continue
            raw_field = mapping.get("form_field")
            answer_key = mapping.get("answer_key")
            if not raw_field or not answer_key:
                continue
            form_field = str(raw_field)
            if form_field in seen_fields:
                continue
            seen_fields.add(form_field)

            section_key, name = _split_field(form_field)
            section = buckets.get(section_key)
            if section is None:
                section = PortalSection(
                    key=section_key,
                    title=_SECTION_TITLES.get(section_key, _humanise(section_key)),
                )
                buckets[section_key] = section

            raw_value = answers.get(str(answer_key))
            value = _format(raw_value) if raw_value not in (None, "") else None
            section.fields.append(
                PortalField(
                    field=form_field,
                    label=_humanise(name),
                    answer_key=str(answer_key),
                    value=value,
                    required=bool(mapping.get("required", False)),
                )
            )

    def order(key: str) -> tuple[int, str]:
        return (_SECTION_ORDER.index(key) if key in _SECTION_ORDER else len(_SECTION_ORDER), key)

    sections = [buckets[key] for key in sorted(buckets, key=order)]
    return PortalPack(
        jurisdiction=jurisdiction,
        scope_label=scope_label,
        apply_url=apply_url,
        sections=sections,
        citations=citations,
    )
