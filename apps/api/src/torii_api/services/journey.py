"""The whole application, start to finish — every stage, and what happens outside Torii.

The workflow steps (intake, eligibility, checklist, forms, review, packet) tell the
applicant what Torii is doing *now*. They never showed the shape of the whole thing: that
a visa starts with choosing the procedure and ends with a decision collected at a
counter, that several of the required items are not documents Torii can produce — a hotel
booking, a return flight reservation, an insurance certificate, a bank balance letter, a
translation — and that those have lead times which decide whether the filing date is
achievable at all.

This module assembles that end-to-end view from what the case already holds:

* the workflow stages, with their real status taken from the case's own progress;
* the filing steps, from :mod:`torii_api.services.submission_kit` (already cited);
* what must be arranged elsewhere, derived **only** from the case's own checklist, so no
  requirement is asserted that the jurisdiction pack or the research did not state.

The category table below adds no requirements. It classifies a checklist item the case
already has — who issues it, how long it usually takes to get, and where that kind of
thing is arranged — so the applicant can sequence the work. Where a category names
commercial services they are listed as unaffiliated examples, never as a requirement or
an endorsement, and the requirement text itself always comes from the pack.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Who does the work in a stage — the UI colours the timeline by this.
OWNER_TORII = "torii"
OWNER_YOU = "you"
OWNER_AUTHORITY = "authority"
OWNER_THIRD_PARTY = "third_party"

STATUS_DONE = "done"
STATUS_CURRENT = "current"
STATUS_TODO = "todo"

# Workflow phases in the order the applicant walks them, used to decide which stage is
# "current" and which are already behind them.
_PHASE_ORDER: tuple[str, ...] = (
    "research",
    "intake",
    "eligibility",
    "checklist",
    "forms",
    "review",
    "packet",
    "done",
)


@dataclass(frozen=True)
class ExternalOption:
    """Somewhere this kind of item is commonly arranged. Never a recommendation."""

    label: str
    url: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"label": self.label, "url": self.url}


@dataclass(frozen=True)
class ExternalCategory:
    """A class of requirement that is obtained outside Torii."""

    code: str
    label: str
    arranged_with: str
    lead_time: str
    guidance: str
    pattern: re.Pattern[str]
    options: tuple[ExternalOption, ...] = ()


@dataclass(frozen=True)
class ExternalTask:
    """One checklist requirement the applicant has to obtain somewhere else."""

    code: str
    category: str
    categories: tuple[str, ...]
    title: str
    arranged_with: str
    lead_time: str
    guidance: str
    how_to_obtain: str
    why_required: str
    is_required: bool
    status: str
    checklist_item_id: int | None = None
    citation_url: str | None = None
    options: tuple[ExternalOption, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "category": self.category,
            "categories": list(self.categories),
            "title": self.title,
            "arranged_with": self.arranged_with,
            "lead_time": self.lead_time,
            "guidance": self.guidance,
            "how_to_obtain": self.how_to_obtain,
            "why_required": self.why_required,
            "is_required": self.is_required,
            "status": self.status,
            "checklist_item_id": self.checklist_item_id,
            "official_citation_url": self.citation_url,
            "options": [option.as_dict() for option in self.options],
        }


@dataclass(frozen=True)
class JourneyStage:
    """One stage of the whole application, in order."""

    key: str
    order: int
    title: str
    detail: str
    owner: str
    status: str
    phase: str | None = None
    done_count: int | None = None
    total_count: int | None = None
    authority: str | None = None
    citation_url: str | None = None
    portal_url: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "order": self.order,
            "title": self.title,
            "detail": self.detail,
            "owner": self.owner,
            "status": self.status,
            "phase": self.phase,
            "done_count": self.done_count,
            "total_count": self.total_count,
            "authority": self.authority,
            "official_citation_url": self.citation_url,
            "portal_url": self.portal_url,
            "notes": list(self.notes),
        }


# ── What is obtained outside Torii ────────────────────────────────────────────────
# Patterns match the checklist item's code, name and how-to-obtain text. A category
# only ever describes an item the case already carries.

_CATEGORIES: tuple[ExternalCategory, ...] = (
    ExternalCategory(
        code="accommodation",
        label="Accommodation booking",
        arranged_with="Your hotel, host, or a booking platform",
        lead_time="Book once your dates are fixed — a free-cancellation reservation is enough "
        "to file with, so this does not have to be paid for in advance.",
        guidance="The confirmation has to show your own name, the address of the place you are "
        "staying and dates that cover the whole stay you are applying for. If you are staying "
        "with a host rather than in a hotel, what the mission wants instead is a letter from "
        "them with their address and contact details.",
        pattern=re.compile(
            r"accommodation|hotel|lodging|宿泊|booking confirmation|place of stay|host",
            re.IGNORECASE,
        ),
        options=(
            ExternalOption("Booking.com", "https://www.booking.com"),
            ExternalOption("Agoda", "https://www.agoda.com"),
            ExternalOption("Airbnb", "https://www.airbnb.com"),
        ),
    ),
    ExternalCategory(
        code="travel_booking",
        label="Flight or travel booking",
        arranged_with="An airline or travel agency",
        lead_time="Reserve as soon as the dates are settled; keep the ticket refundable or "
        "unpaid until the decision, because the visa is not guaranteed.",
        guidance="Both directions are normally required — the onward or return leg matters as "
        "much as the inbound one. A reservation or itinerary in your name is what is asked "
        "for; a paid ticket is not usually required before a decision.",
        pattern=re.compile(
            r"flight|airline|itinerary|air ticket|航空券|onward|return travel|travel booking",
            re.IGNORECASE,
        ),
        options=(
            ExternalOption("Google Flights", "https://www.google.com/travel/flights"),
            ExternalOption("Your airline's own booking page"),
            ExternalOption("A licensed travel agency"),
        ),
    ),
    ExternalCategory(
        code="insurance",
        label="Travel or medical insurance",
        arranged_with="An insurer or broker",
        lead_time="Same day to a few days. Buy it to start on your planned arrival date.",
        guidance="Check the certificate names you, states the coverage amount and covers every "
        "day of the stay you are applying for.",
        pattern=re.compile(r"insurance|保険|medical cover|health cover", re.IGNORECASE),
        options=(ExternalOption("Your own insurer, bank or broker"),),
    ),
    ExternalCategory(
        code="funds",
        label="Proof of funds from your bank",
        arranged_with="Your bank",
        lead_time="A few days — balance certificates are usually issued over the counter, but "
        "some banks take up to a week, and statements must be recent when you file.",
        guidance="Ask for both the balance certificate and the printed statement history the "
        "requirement names. Statements are read for the pattern of money coming in, so a "
        "balance moved in shortly before applying tends to be questioned.",
        pattern=re.compile(
            r"bank|balance|statement|solvency|残高|預金|funds|financial capacity|income proof",
            re.IGNORECASE,
        ),
        options=(ExternalOption("Your bank's branch or online request form"),),
    ),
    ExternalCategory(
        code="photograph",
        label="Passport photograph to specification",
        arranged_with="A photo studio or a compliant photo booth",
        lead_time="Same day.",
        guidance="Size, background and how recent the photograph is are all fixed by the "
        "requirement — a photo that does not match the stated dimensions is the single most "
        "common reason a form is handed back at the counter.",
        pattern=re.compile(r"photograph|photo\b|写真|45mm|35mm", re.IGNORECASE),
    ),
    ExternalCategory(
        code="translation",
        label="Certified translation",
        arranged_with="A translator or translation agency",
        lead_time="Several days. Start early — it depends on having the original document first.",
        guidance="The translation is filed alongside the original, not instead of it. Where a "
        "certified or sworn translator is required, an unsigned self-translation is refused.",
        pattern=re.compile(r"translat|翻訳", re.IGNORECASE),
        options=(ExternalOption("A certified or sworn translator in your country"),),
    ),
    ExternalCategory(
        code="legalisation",
        label="Notarisation, apostille or legalisation",
        arranged_with="A notary, your foreign ministry, or the mission",
        lead_time="Two to six weeks in many countries. This is usually the longest lead time in "
        "the whole application — begin with it.",
        guidance="Each step depends on the one before it: the document is issued, then "
        "notarised, then apostilled or legalised. Confirm which of those your case needs "
        "before paying for all three.",
        pattern=re.compile(r"apostille|legalis|legaliz|notari|公証|認証", re.IGNORECASE),
    ),
    ExternalCategory(
        code="police_certificate",
        label="Police or criminal record certificate",
        arranged_with="The police or justice authority of the country concerned",
        lead_time="Two to eight weeks, and often longer when it has to come from a country you "
        "no longer live in. Request it first.",
        guidance="Certificates are usually required from every country you have lived in for a "
        "stated period, not only from your own. Many expire within three to six months of "
        "issue, so check the validity window against your filing date.",
        pattern=re.compile(r"police|criminal record|good conduct|犯罪経歴|無犯罪", re.IGNORECASE),
    ),
    ExternalCategory(
        code="medical",
        label="Medical examination or health certificate",
        arranged_with="An approved clinic or panel physician",
        lead_time="One to four weeks, including the wait for results.",
        guidance="Where a panel of approved clinics is published, a certificate from any other "
        "doctor is not accepted — check the panel before booking.",
        pattern=re.compile(
            r"medical|health check|tuberculosis|\btb\b|chest x-?ray|健康診断", re.IGNORECASE
        ),
    ),
    ExternalCategory(
        code="passport",
        label="Passport",
        arranged_with="Your own passport authority",
        lead_time="Weeks to months if it needs renewing. Check the expiry date before anything "
        "else — everything downstream is booked against this document.",
        guidance="Validity has to cover the whole stay you are applying for, and blank pages are "
        "needed for the visa itself. Renew first if either is short.",
        pattern=re.compile(r"passport|旅券|パスポート", re.IGNORECASE),
    ),
    ExternalCategory(
        code="employer",
        label="Employer document",
        arranged_with="Your employer",
        lead_time="Days to weeks, depending on how quickly your HR department turns it round.",
        guidance="Ask for it in writing and say what it has to state — most employers issue a "
        "generic letter first, which then has to be re-issued.",
        pattern=re.compile(
            r"employ|employer|job offer|contract of|在職|雇用|company registration|salary slip|"
            r"payslip|withholding",
            re.IGNORECASE,
        ),
    ),
    ExternalCategory(
        code="school",
        label="School or university document",
        arranged_with="Your school, college or university",
        lead_time="Days to weeks — issuing offices are slow around term boundaries.",
        guidance="Admission, enrolment and transcript documents are issued by different offices "
        "in most institutions; request them together so they do not queue one after another.",
        pattern=re.compile(
            r"admission|enrol|enroll|transcript|diploma|graduation|在学|入学|学校|academic record",
            re.IGNORECASE,
        ),
    ),
    ExternalCategory(
        code="sponsor",
        label="Sponsor, guarantor or inviting party document",
        arranged_with="The person or organisation supporting your application",
        lead_time="Weeks — it is filled in by someone else, often abroad, and posted to you.",
        guidance="This part is not yours to write. Send the person the blank form and tell them "
        "what it needs, since the application is not accepted without their part completed.",
        pattern=re.compile(
            r"sponsor|guarantor|invit|身元保証|招へい|supporter|letter of support", re.IGNORECASE
        ),
    ),
    ExternalCategory(
        code="civil_status",
        label="Civil status record",
        arranged_with="The registry office that holds the record",
        lead_time="One to four weeks, plus translation and legalisation time on top.",
        guidance="Ask for the long-form certified copy where one exists; short extracts are "
        "frequently refused, and re-ordering costs another cycle.",
        pattern=re.compile(
            r"birth certificate|marriage certificate|family register|戸籍|divorce|death certificate",
            re.IGNORECASE,
        ),
    ),
    ExternalCategory(
        code="tax",
        label="Tax or municipal certificate",
        arranged_with="Your tax office or city hall",
        lead_time="Same day to two weeks, depending on the office.",
        guidance="These are issued for a specific tax year — check which year the requirement "
        "asks for before queuing.",
        pattern=re.compile(r"tax|課税|納税|residence certificate|住民票|municipal", re.IGNORECASE),
    ),
)


def _text_of(value: Any) -> str:
    """Checklist text is either a string or a locale map; read both."""
    if isinstance(value, dict):
        return " ".join(str(item) for item in value.values())
    return str(value or "")


def _match_categories(item: dict[str, Any]) -> tuple[ExternalCategory, ...]:
    """Every category a checklist item falls into, most specific first.

    An item can genuinely be two things at once — Japan's short-stay pack asks for
    "flight itinerary and accommodation bookings" as one requirement — and telling the
    applicant only about the hotel would drop the return flight from their plan.
    """
    haystack = " ".join(
        (
            str(item.get("code") or ""),
            _text_of(item.get("name")),
            _text_of(item.get("how_to_obtain")),
        )
    )
    return tuple(category for category in _CATEGORIES if category.pattern.search(haystack))


def external_tasks(checklist: list[dict[str, Any]]) -> tuple[ExternalTask, ...]:
    """The checklist items that have to be obtained somewhere other than Torii.

    Derived entirely from the case's own checklist — this adds no requirement of its own,
    it only says who issues each one and how long it usually takes.
    """
    tasks: list[ExternalTask] = []
    for item in checklist:
        matched = _match_categories(item)
        if not matched:
            continue
        category = matched[0]
        # At most two categories are described: past that the card stops being a plan and
        # becomes a wall of text.
        described = matched[:2]
        citation = item.get("citation") if isinstance(item.get("citation"), dict) else {}
        url = citation.get("url") if isinstance(citation, dict) else None
        options: list[ExternalOption] = []
        for entry in described:
            for option in entry.options:
                if option not in options:
                    options.append(option)
        tasks.append(
            ExternalTask(
                code=str(item.get("code") or category.code),
                category=category.code,
                categories=tuple(entry.code for entry in matched),
                title=_text_of(item.get("name")).strip() or category.label,
                arranged_with=" · ".join(dict.fromkeys(entry.arranged_with for entry in described)),
                lead_time=category.lead_time,
                guidance=" ".join(entry.guidance for entry in described),
                how_to_obtain=_text_of(item.get("how_to_obtain")).strip(),
                why_required=_text_of(item.get("why_required")).strip(),
                is_required=bool(item.get("is_required", True)),
                status=str(item.get("status") or "needed"),
                checklist_item_id=item.get("id") if isinstance(item.get("id"), int) else None,
                citation_url=str(url) if isinstance(url, str) and url.startswith("http") else None,
                options=tuple(options),
            )
        )

    # Longest lead time first: an applicant reading this needs to know what to start today,
    # not what happens to sit first in the checklist.
    order = {category.code: index for index, category in enumerate(_CATEGORIES)}
    priority = {"passport": 0, "police_certificate": 1, "legalisation": 2, "medical": 3}
    return tuple(
        sorted(
            tasks,
            key=lambda task: (
                priority.get(task.category, 10),
                order.get(task.category, 99),
                task.title,
            ),
        )
    )


def _phase_status(stage_phase: str, current_phase: str) -> str:
    """Where a workflow stage sits relative to the phase the case is actually in."""
    if current_phase == "blocked":
        current_phase = "intake"
    try:
        stage_index = _PHASE_ORDER.index(stage_phase)
        current_index = _PHASE_ORDER.index(current_phase)
    except ValueError:
        return STATUS_TODO
    if stage_index < current_index:
        return STATUS_DONE
    return STATUS_CURRENT if stage_index == current_index else STATUS_TODO


def _outstanding_status(stage_phase: str, current_phase: str, done: int, total: int) -> str:
    """Like :func:`_phase_status`, but a stage with work left never reads as finished.

    The workflow lets an applicant assemble the kit while documents are still outstanding.
    Marking the gathering stage "done" because the phase moved past it would tell them the
    opposite of what their own checklist says.
    """
    status = _phase_status(stage_phase, current_phase)
    if total and done < total and status == STATUS_DONE:
        return STATUS_CURRENT
    if total and done >= total and status == STATUS_CURRENT:
        return STATUS_DONE
    return status


def _counts(items: list[dict[str, Any]]) -> tuple[int, int]:
    required = [item for item in items if item.get("is_required", True)]
    done = [item for item in required if item.get("status") in ("gathered", "uploaded")]
    return len(done), len(required)


def build_journey(
    *,
    reference: str,
    scope_label: str,
    phase: str,
    case_status: str,
    checklist: list[dict[str, Any]],
    forms: list[dict[str, Any]],
    submission_kit: Any | None,
    filing_mode: str = "official_form_pdf",
    apply_url: str | None = None,
    has_research: bool = False,
) -> dict[str, Any]:
    """The full journey for one case: preparation, filing, and what follows the decision."""
    submitted = case_status == "submitted"
    tasks = external_tasks(checklist)
    gathered, required_total = _counts(checklist)
    external_done = sum(1 for task in tasks if task.status in ("gathered", "uploaded"))
    missing_form_fields = sum(
        len(form.get("missing_required_fields") or []) for form in forms if isinstance(form, dict)
    )

    stages: list[JourneyStage] = []

    def add(**kwargs: Any) -> None:
        stages.append(JourneyStage(order=len(stages) + 1, **kwargs))

    add(
        key="scope",
        title="Choose where you are going and which procedure applies",
        detail=(
            f"Your case is scoped to {scope_label}. The procedure decides everything after "
            "it — which form, which office, which documents — so a change of purpose or "
            "action starts a different application, not an edit of this one."
        ),
        owner=OWNER_YOU,
        status=STATUS_DONE,
        phase="research",
    )

    if has_research:
        add(
            key="research",
            title="Torii reads the current government rules for your corridor",
            detail=(
                "Requirements differ by nationality and country of residence, not only by "
                "destination. Torii collects the rules published for your corridor and cites "
                "the page each one came from, so you can check anything it tells you."
            ),
            owner=OWNER_TORII,
            status=_phase_status("research", phase),
            phase="research",
        )

    add(
        key="intake",
        title="Answer the intake questions",
        detail=(
            "Every answer here is reused: it fills the official form, decides which documents "
            "your checklist asks for, and is what the drafted letters are written from. "
            "Answers save as you type, so you can stop and come back."
        ),
        owner=OWNER_YOU,
        status=_phase_status("intake", phase),
        phase="intake",
    )
    add(
        key="eligibility",
        title="Check that you qualify before spending money",
        detail=(
            "Torii tests your answers against the published criteria for this procedure and "
            "shows which rule each result comes from. A blocking result here is worth far "
            "less than the same result found at a counter after fees are paid."
        ),
        owner=OWNER_TORII,
        status=_phase_status("eligibility", phase),
        phase="eligibility",
    )
    add(
        key="documents",
        title="Gather the documents on your checklist",
        detail=(
            "Your checklist is built from the requirements published for this procedure, each "
            "with its source. Mark items as you collect them — the filing kit lists exactly "
            "what you recorded, so anything unmarked is missing from the dossier too."
        ),
        owner=OWNER_YOU,
        status=_outstanding_status("checklist", phase, gathered, required_total),
        phase="checklist",
        done_count=gathered,
        total_count=required_total,
    )

    if tasks:
        longest = tasks[0]
        add(
            key="external",
            title="Arrange the items that come from outside Torii",
            detail=(
                f"{len(tasks)} of your checklist items are issued by someone else — a bank, an "
                "airline, a hotel, an employer, a government office in your own country. Torii "
                "cannot produce or book these, and their lead times, not the paperwork, are "
                f"what usually decide your filing date. Start with: {longest.title}."
            ),
            owner=OWNER_THIRD_PARTY,
            status=_outstanding_status("checklist", phase, external_done, len(tasks)),
            phase="checklist",
            done_count=external_done,
            total_count=len(tasks),
        )

    add(
        key="forms",
        title="Torii fills the official form from your answers",
        detail=(
            "The statutory form is filled from your intake answers and left blank wherever you "
            "have not answered — nothing is guessed on a document you sign. "
            + (
                f"{missing_form_fields} required field(s) are still waiting on an answer."
                if missing_form_fields
                else "Check every entry against your passport before you sign."
            )
        ),
        owner=OWNER_TORII,
        status=_phase_status("forms", phase),
        phase="forms",
    )
    add(
        key="review",
        title="Pre-submission review",
        detail=(
            "Torii re-reads the whole case for the things that get applications handed back: "
            "missing required answers, unrecorded documents, a form template that changed "
            "since you started."
        ),
        owner=OWNER_TORII,
        status=_phase_status("review", phase),
        phase="review",
    )
    add(
        key="packet",
        title="Assemble and download your filing kit",
        detail=(
            "The official form, the cover letter and the supporting drafts, as PDF or Word "
            "files. Print them, check every entry, and sign by hand where a signature is asked "
            "for."
        ),
        owner=OWNER_TORII,
        status=_phase_status("packet", phase),
        phase="packet",
    )

    filing_steps = list(getattr(submission_kit, "steps", ()) or ())
    for step in filing_steps:
        add(
            key=f"filing_{getattr(step, 'order', len(stages))}",
            title=getattr(step, "title", ""),
            detail=getattr(step, "detail", ""),
            owner=OWNER_YOU,
            status=STATUS_DONE if submitted else STATUS_TODO,
            authority=getattr(step, "authority", None) or None,
            citation_url=getattr(step, "citation_url", None),
            portal_url=getattr(step, "portal_url", None),
        )
    if not filing_steps:
        add(
            key="filing",
            title="File your application",
            detail=(
                "Torii has no cited filing route for this scope yet, so it will not invent one. "
                + (
                    f"Start from the official application service: {apply_url}"
                    if apply_url
                    else "Check the page of the office that will receive your application for "
                    "how and where it is filed."
                )
            ),
            owner=OWNER_YOU,
            status=STATUS_DONE if submitted else STATUS_TODO,
            portal_url=apply_url,
        )

    add(
        key="record",
        title="Record the submission in Torii",
        detail=(
            "Marking the case submitted freezes the packet you actually filed, so what you sent "
            "can be reproduced later — when a mission asks for an additional document, or when "
            "the next renewal reuses this application."
        ),
        owner=OWNER_YOU,
        status=STATUS_DONE if submitted else STATUS_TODO,
    )
    add(
        key="await_decision",
        title="Wait, and answer any additional request quickly",
        detail=(
            "Keep the receipt or reference you are given — it is what you quote for status and "
            "collection. If the office asks for a further document, the clock usually stops "
            "until you supply it, so a slow reply costs more than the document itself."
        ),
        owner=OWNER_AUTHORITY,
        status=STATUS_CURRENT if submitted else STATUS_TODO,
        notes=tuple(getattr(submission_kit, "notes", ()) or ()),
    )
    add(
        key="outcome",
        title="Check the decision before you leave the counter",
        detail=(
            "Check the entry type, the validity dates and the number of entries on what you are "
            "given, while you can still ask about them. A visa permits you to seek entry; the "
            "decision at the border is made by the immigration inspector."
        ),
        owner=OWNER_YOU,
        status=STATUS_TODO,
    )
    add(
        key="renewal",
        title="Record the expiry date for the next application",
        detail=(
            "Torii tracks the deadline from the expiry date on the permission you receive and "
            "warns you before the renewal window opens, which is when the same documents can be "
            "reused rather than re-collected."
        ),
        owner=OWNER_TORII,
        status=STATUS_TODO,
    )

    fee_note = getattr(submission_kit, "fee_note", None)
    return {
        "reference": reference,
        "scope_label": scope_label,
        "phase": phase,
        "filing_mode": filing_mode,
        "apply_url": apply_url,
        "submitted": submitted,
        "stages": [stage.as_dict() for stage in stages],
        "external_tasks": [task.as_dict() for task in tasks],
        "checklist_progress": {"done": gathered, "total": required_total},
        "external_progress": {"done": external_done, "total": len(tasks)},
        "office": getattr(submission_kit, "office", None),
        "filed_by": getattr(submission_kit, "filed_by", None),
        "fee_note": fee_note,
        "notes": list(getattr(submission_kit, "notes", ()) or ()),
    }


__all__ = ["ExternalTask", "JourneyStage", "build_journey", "external_tasks"]
