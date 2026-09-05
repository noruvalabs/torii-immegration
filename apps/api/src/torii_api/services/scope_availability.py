"""One answer to "can an applicant start a case on this scope?".

The rule used to live twice: once as a pair of SQL filters in the geo listing endpoints,
once as a boolean in ``scope_case``. They disagreed, and the disagreement was invisible
until the last click — a route listed on the visa-type step could be refused when the
applicant finally pressed Start application. Both callers now come here.

A scope is offerable when every part of it is switched on **and** the whole scope is
sourced the same way: either all three rows carry a live content pack, or the route and
the procedure are both research-enabled and requirements are produced on demand (NF-2).
A route with a pack paired with a procedure without one is not a scope we can serve.
"""

from __future__ import annotations

from torii_api.db.models import CaseAction, Jurisdiction, VisaCategory


def scope_is_enabled(
    jurisdiction: Jurisdiction,
    visa_category: VisaCategory,
    case_action: CaseAction,
) -> bool:
    """True when ops has not switched off any part of this scope."""
    return jurisdiction.is_enabled and visa_category.is_enabled and case_action.is_enabled


def scope_is_live(
    jurisdiction: Jurisdiction,
    visa_category: VisaCategory,
    case_action: CaseAction,
) -> bool:
    """True when every part of this scope is served from a reviewed content pack."""
    return jurisdiction.is_live and visa_category.is_live and case_action.is_live


def scope_is_research(visa_category: VisaCategory, case_action: CaseAction) -> bool:
    """True when this scope is served by the live-research pipeline instead of a pack."""
    return visa_category.research_enabled and case_action.research_enabled


def scope_is_available(
    jurisdiction: Jurisdiction,
    visa_category: VisaCategory,
    case_action: CaseAction,
) -> bool:
    """The single test both the listing endpoints and ``scope_case`` apply."""
    if not scope_is_enabled(jurisdiction, visa_category, case_action):
        return False
    return scope_is_live(jurisdiction, visa_category, case_action) or scope_is_research(
        visa_category, case_action
    )


def available_actions(
    jurisdiction: Jurisdiction,
    visa_category: VisaCategory,
    actions: list[CaseAction],
) -> list[CaseAction]:
    """The procedures that form an offerable scope with this route."""
    return [a for a in actions if scope_is_available(jurisdiction, visa_category, a)]


def category_is_offerable(
    jurisdiction: Jurisdiction,
    visa_category: VisaCategory,
    actions: list[CaseAction],
) -> bool:
    """True when at least one procedure pairs with this route.

    Listing a route whose every procedure is refused walks the applicant into an empty
    application step, so the visa-type list asks this before showing one.
    """
    return any(scope_is_available(jurisdiction, visa_category, a) for a in actions)


def category_is_research_only(
    jurisdiction: Jurisdiction,
    visa_category: VisaCategory,
    actions: list[CaseAction],
) -> bool:
    """True when this route is offerable, but never from a reviewed pack.

    Surfaced to the applicant: requirements on a research-only route are read off the
    government's pages on demand rather than from content ops has reviewed.
    """
    offerable = [a for a in actions if scope_is_available(jurisdiction, visa_category, a)]
    if not offerable:
        return False
    return not any(scope_is_live(jurisdiction, visa_category, a) for a in offerable)
