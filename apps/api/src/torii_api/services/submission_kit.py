"""What the applicant must actually do to file, derived from their application type.

The filing steps, the office that receives them, the addressee of the cover letter and
the order the paper is stacked in all differ by *procedure*, not by country. A
certificate of eligibility is filed in Japan by a proxy before the applicant has ever
entered; an extension is filed by the resident themselves; a consular visa is filed at an
embassy abroad. Telling all three the same thing is wrong for at least two of them.

Everything here is derived from data the product already holds — the form catalogue, the
pack's published fees, the case's own checklist — so nothing is asserted that cannot be
traced. Where a fact is not known (an unpublished fee, an office that depends on the
applicant's address) the step says so instead of inventing a figure or a URL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from torii_api.services.content_packs import PackFee, resolve_fee
from torii_api.services.jp_official_forms import (
    ISA_AUTHORITY,
    MOFA_AUTHORITY,
    OfficialForm,
    forms_for_scope,
)

# Step categories, reused by the UI to pick an icon.
STEP_FORM = "form"
STEP_DOCUMENTS = "documents"
STEP_FEE = "fee_payment"
STEP_SUBMIT = "physical_submission"
STEP_ONLINE = "online_portal"
STEP_COLLECT = "collect_outcome"

_ISA_PROCEDURES_URL = "https://www.moj.go.jp/isa/applications/procedures/index.html"
_ISA_OFFICE_DIRECTORY = "https://www.moj.go.jp/isa/about/region/index.html"
_ISA_ONLINE_URL = "https://www.moj.go.jp/isa/applications/online/onlineshinsei.html"
_MOFA_MISSION_DIRECTORY = "https://www.mofa.go.jp/about/emb_cons/mofaserv.html"


@dataclass(frozen=True)
class FilingStep:
    """One thing the applicant does, in order."""

    order: int
    title: str
    detail: str
    authority: str
    category: str
    citation_url: str | None = None
    portal_url: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "step": self.order,
            "title": self.title,
            "description": self.detail,
            "authority": self.authority,
            "category": self.category,
            "official_citation_url": self.citation_url,
            "portal_url": self.portal_url,
        }


@dataclass(frozen=True)
class SubmissionKit:
    """Filing instructions for one application type."""

    # Who the cover letter is addressed to, exactly as the official form words it.
    addressee: str
    # Where the application is handed in.
    office: str
    filed_by: str
    steps: tuple[FilingStep, ...] = ()
    # The paper stack, in submission order — built from the case's real enclosures.
    stacking_order: tuple[str, ...] = ()
    fee_note: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "addressee": self.addressee,
            "office": self.office,
            "filed_by": self.filed_by,
            "steps": [step.as_dict() for step in self.steps],
            "stacking_order": list(self.stacking_order),
            "fee_note": self.fee_note,
            "notes": list(self.notes),
        }


# ── Per-procedure filing facts ─────────────────────────────────────────────────────
# Addressees are quoted from the forms themselves: every ISA residence application is
# headed 法務大臣殿 ("To the Minister of Justice"), which is why one addressee covers
# them all. The consular form is filed at a mission instead.

_ISA_ADDRESSEE = "法務大臣殿 (To the Minister of Justice)"
_ISA_OFFICE = "Regional Immigration Services Bureau with jurisdiction over your address"

_PROCEDURE_FACTS: dict[str, dict[str, str]] = {
    "coe": {
        "addressee": _ISA_ADDRESSEE,
        "office": _ISA_OFFICE,
        "filed_by": (
            "Your employer, school or a relative in Japan acting as proxy — this is filed "
            "in Japan before you travel, so you cannot file it yourself from abroad."
        ),
    },
    "change_of_status": {
        "addressee": _ISA_ADDRESSEE,
        "office": _ISA_OFFICE,
        "filed_by": "You, in person, while resident in Japan",
    },
    "extension": {
        "addressee": _ISA_ADDRESSEE,
        "office": _ISA_OFFICE,
        "filed_by": "You, in person, while resident in Japan",
    },
    "permanent_residence": {
        "addressee": _ISA_ADDRESSEE,
        "office": _ISA_OFFICE,
        "filed_by": "You, in person, while resident in Japan",
    },
    "consular_visa": {
        "addressee": "The Consular Section, Embassy or Consulate-General of Japan",
        "office": "The Japanese embassy or consulate with jurisdiction over your residence",
        "filed_by": (
            "You, or an accredited travel agency where the mission requires applications "
            "to be filed through one"
        ),
    },
}


def _fee_note(fees: list[PackFee], as_of: date, procedure: str) -> str | None:
    """A fee sentence only when the pack publishes a figure with a citation (NF-2)."""
    if procedure == "coe":
        # The certificate itself is free; the fee falls due on the permission that follows.
        return "No fee is charged for the certificate of eligibility itself."
    fee = resolve_fee(fees, as_of=as_of, channel="counter") or resolve_fee(fees, as_of=as_of)
    if fee is None or fee.amount is None:
        return None
    currency = fee.currency or ""
    amount = f"{int(fee.amount):,}" if float(fee.amount).is_integer() else str(fee.amount)
    return f"{amount} {currency}".strip() + ", payable by revenue stamp (収入印紙) on approval."


def _isa_steps(
    forms: tuple[OfficialForm, ...],
    procedure: str,
    fee_note: str | None,
    has_organisation_part: bool,
) -> tuple[FilingStep, ...]:
    """Steps for an application filed with the Immigration Services Agency."""
    primary = forms[0]
    steps: list[FilingStep] = [
        FilingStep(
            order=1,
            title=f"Complete and sign {primary.title_ja}",
            detail=(
                f"Torii fills the applicant part of {primary.title_en} from your answers. "
                "Print it, check every entry against your passport and residence card, and "
                "sign it. Any box Torii could not fill is listed on the form itself."
            ),
            authority=primary.authority,
            category=STEP_FORM,
            citation_url=primary.source_page_url,
        )
    ]
    if has_organisation_part:
        steps.append(
            FilingStep(
                order=len(steps) + 1,
                title="Have your employer, school or supporter complete their part",
                detail=(
                    "The later sheets of the same form (所属機関等作成用) are completed and "
                    "sealed by the organisation supporting your application. They are not "
                    "yours to fill in, and the application is not accepted without them."
                ),
                authority=primary.authority,
                category=STEP_DOCUMENTS,
                citation_url=primary.source_page_url,
            )
        )
    steps.append(
        FilingStep(
            order=len(steps) + 1,
            title="Gather the supporting documents on your checklist",
            detail=(
                "Your checklist lists what this application requires and where each item "
                "comes from. Bring originals unless the checklist says a copy is accepted."
            ),
            authority=primary.authority,
            category=STEP_DOCUMENTS,
            citation_url=primary.source_page_url,
        )
    )
    steps.append(
        FilingStep(
            order=len(steps) + 1,
            title="File at your Regional Immigration Services Bureau",
            detail=(
                "Applications are accepted in person on weekdays; postal submission is not "
                "accepted. Which office serves you depends on your address in Japan — check "
                "the directory before travelling. Filing online is also possible once you "
                "are registered for the ISA online system."
            ),
            authority=ISA_AUTHORITY,
            category=STEP_SUBMIT,
            citation_url=_ISA_OFFICE_DIRECTORY,
            portal_url=_ISA_ONLINE_URL,
        )
    )
    collect_detail = (
        "The bureau notifies you by post when a decision is made."
        if procedure == "coe"
        else "The bureau notifies you by post when a decision is made. Bring the notice, "
        "your passport and your residence card to collect the result."
    )
    if fee_note:
        collect_detail += f" Fee: {fee_note}"
    steps.append(
        FilingStep(
            order=len(steps) + 1,
            title=(
                "Receive the certificate of eligibility"
                if procedure == "coe"
                else "Collect the decision and your new residence card"
            ),
            detail=collect_detail,
            authority=ISA_AUTHORITY,
            category=STEP_FEE if fee_note else STEP_COLLECT,
            citation_url=_ISA_PROCEDURES_URL,
        )
    )
    return tuple(steps)


def _consular_steps(form: OfficialForm) -> tuple[FilingStep, ...]:
    """Steps for the visa filed at a Japanese mission abroad."""
    return (
        FilingStep(
            order=1,
            title=f"Complete and sign {form.title_ja}",
            detail=(
                f"Torii fills {form.title_en} from your answers. Print it, attach a "
                "45mm × 35mm photograph taken within the last six months, and sign it."
            ),
            authority=form.authority,
            category=STEP_FORM,
            citation_url=form.source_page_url,
        ),
        FilingStep(
            order=2,
            title="Confirm what your own mission requires",
            detail=(
                "Requirements and whether applications must go through an accredited agency "
                "are set by each embassy or consulate, not centrally. Check the page for the "
                "mission that covers where you live before you travel to it."
            ),
            authority=MOFA_AUTHORITY,
            category=STEP_DOCUMENTS,
            citation_url=_MOFA_MISSION_DIRECTORY,
        ),
        FilingStep(
            order=3,
            title="Submit your application to the mission",
            detail=(
                "Hand in the signed form, your passport and the supporting documents on your "
                "checklist. Processing normally takes at least five working days from a "
                "complete application."
            ),
            authority=MOFA_AUTHORITY,
            category=STEP_SUBMIT,
            citation_url=form.source_page_url,
        ),
        FilingStep(
            order=4,
            title="Collect your passport with the visa",
            detail=(
                "The visa is issued as a sticker in your passport. Check the entry type and "
                "validity on collection — a visa permits you to seek entry, and the decision "
                "at the border is made by the immigration inspector."
            ),
            authority=MOFA_AUTHORITY,
            category=STEP_COLLECT,
            citation_url=form.source_page_url,
        ),
    )


def _stacking_order(
    forms: tuple[OfficialForm, ...], checklist: list[dict[str, Any]]
) -> tuple[str, ...]:
    """The paper stack, built from the forms this scope needs and the case's own checklist.

    Only what the case actually has is listed. The previous implementation fell back to a
    fixed list naming a tax certificate and an employment certificate, which a student or
    dependent applicant does not have and would go looking for.
    """
    stack: list[str] = ["Cover letter and submission index (prepared by Torii)"]
    for form in forms:
        stack.append(f"{form.title_ja} — signed")
    for item in checklist:
        name = str(item.get("name") or "").strip()
        if name:
            stack.append(name)
    return tuple(f"{index}. {entry}" for index, entry in enumerate(stack, start=1))


def build_submission_kit(
    *,
    jurisdiction_code: str | None,
    visa_category: str | None,
    action: str | None,
    checklist: list[dict[str, Any]] | None = None,
    fees: list[PackFee] | None = None,
    as_of: date | None = None,
) -> SubmissionKit | None:
    """Filing instructions for one application type, or ``None`` when not modelled.

    Returning ``None`` is deliberate: a scope this function does not know how to file is
    better served by saying nothing than by generic steps that cite another country's
    ministry, which is what the previous default branch did.
    """
    if (jurisdiction_code or "").upper() != "JP":
        return None

    forms = forms_for_scope(visa_category or "", action or "")
    if not forms:
        return None

    primary = forms[0]
    facts = _PROCEDURE_FACTS.get(primary.procedure)
    if facts is None:
        return None

    note = _fee_note(fees or [], as_of or date.today(), primary.procedure)
    if primary.procedure == "consular_visa":
        steps = _consular_steps(primary)
    else:
        has_organisation_part = primary.pages > (
            1 + len(primary.extra_layouts) + 1  # applicant sheets plus the selector sheet
        )
        steps = _isa_steps(forms, primary.procedure, note, has_organisation_part)

    notes: list[str] = []
    if len(forms) > 1:
        follow_on = ", ".join(form.title_ja for form in forms[1:])
        notes.append(
            "This application has two stages: once the certificate is issued, you file "
            f"{follow_on} at a Japanese embassy or consulate to obtain the visa itself."
        )
    if primary.note:
        notes.append(primary.note)

    return SubmissionKit(
        addressee=facts["addressee"],
        office=facts["office"],
        filed_by=facts["filed_by"],
        steps=steps,
        stacking_order=_stacking_order(forms, checklist or []),
        fee_note=note,
        notes=tuple(notes),
    )
