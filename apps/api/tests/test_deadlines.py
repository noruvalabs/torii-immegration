"""Deadlines belong to the country whose statute produced them.

``compute_deadlines`` encoded Japan's 特例期間 as bare module constants and applied them to
whatever case reached it. No non-JP pack asks ``residence_card_expiry`` today, so nothing
had gone wrong yet — but a UK route adding a BRP-expiry question, or a research-driven
scope generating one, would have been handed Japan's 61-day grace period and told an
applicant they were lawfully in the country when they were not.

These tests hold the line: Japan's numbers apply to Japan, and a jurisdiction nobody has
written rules for gets no derived dates rather than someone else's.
"""

from __future__ import annotations

from datetime import date

import pytest

from torii_api.services.deadlines import (
    JP_RULES,
    RULES_BY_JURISDICTION,
    compute_deadlines,
    rules_for,
)

EXPIRY = "2026-11-30"


# ── Japan, whose statute this is ───────────────────────────────────────────────


def test_japan_gets_the_filing_window_cutoff_and_grace_period() -> None:
    profile = compute_deadlines(EXPIRY, "extend", jurisdiction="JP")

    assert profile.residence_expiry == date(2026, 11, 30)
    assert profile.jurisdiction == "JP"
    # Three months before expiry.
    assert profile.filing_window_opens == date(2026, 9, 1)
    # Two business days before a Monday expiry is the Thursday before.
    assert profile.online_cutoff == date(2026, 11, 26)
    # 特例期間: up to two months past expiry.
    assert profile.has_grace_period is True
    assert profile.grace_period_end == date(2027, 1, 30)
    # The My Number card's validity is tied to the residence period.
    assert profile.my_number_expiry == date(2026, 11, 30)


@pytest.mark.parametrize("procedure", ["extend", "change"])
def test_japan_grants_the_grace_period_only_to_extend_and_change(procedure: str) -> None:
    assert compute_deadlines(EXPIRY, procedure, jurisdiction="JP").has_grace_period is True


@pytest.mark.parametrize("procedure", ["coe", "newapplication", "new_application", ""])
def test_a_first_filing_earns_no_grace_period(procedure: str) -> None:
    profile = compute_deadlines(EXPIRY, procedure, jurisdiction="JP")
    assert profile.has_grace_period is False
    assert profile.grace_period_end is None


def test_the_jurisdiction_code_is_matched_case_insensitively() -> None:
    assert compute_deadlines(EXPIRY, "extend", jurisdiction="jp").grace_period_end == date(
        2027, 1, 30
    )
    assert compute_deadlines(EXPIRY, "extend", jurisdiction=" Jp ").has_grace_period is True


# ── Everyone else ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize("jurisdiction", ["UK", "GB", "US", "CA", "", None])
def test_a_jurisdiction_with_no_encoded_rules_gets_no_derived_dates(
    jurisdiction: str | None,
) -> None:
    """The regression this module exists for: no borrowing another country's statute."""
    profile = compute_deadlines(EXPIRY, "extend", jurisdiction=jurisdiction)

    # The expiry is a fact the applicant gave; everything else would be a guess.
    assert profile.residence_expiry == date(2026, 11, 30)
    assert profile.filing_window_opens is None
    assert profile.online_cutoff is None
    assert profile.grace_period_end is None
    assert profile.my_number_expiry is None
    assert profile.has_grace_period is False


def test_the_uk_never_silently_inherits_japans_grace_period() -> None:
    uk = compute_deadlines(EXPIRY, "extend", jurisdiction="UK")
    jp = compute_deadlines(EXPIRY, "extend", jurisdiction="JP")

    assert jp.grace_period_end is not None
    assert uk.grace_period_end is None
    assert uk.to_dict()["jurisdiction"] == "UK"


def test_only_jurisdictions_someone_actually_wrote_rules_for_are_registered() -> None:
    assert set(RULES_BY_JURISDICTION) == {"JP"}
    assert rules_for("JP") is JP_RULES
    assert rules_for("UK") is None
    assert rules_for(None) is None


# ── No expiry, bad expiry ──────────────────────────────────────────────────────


@pytest.mark.parametrize("bad", [None, "", "not-a-date", "2026-13-45"])
def test_without_a_usable_expiry_there_is_nothing_to_derive(bad: str | None) -> None:
    profile = compute_deadlines(bad, "extend", jurisdiction="JP")
    assert profile.residence_expiry is None
    assert profile.filing_window_opens is None
    assert profile.grace_period_end is None


def test_the_dict_form_names_the_jurisdiction_it_used() -> None:
    payload = compute_deadlines(EXPIRY, "extend", jurisdiction="JP").to_dict()
    assert payload["jurisdiction"] == "JP"
    assert payload["residence_expiry"] == "2026-11-30"
    assert payload["grace_period_end"] == "2027-01-30"


# ── The caller cannot forget ───────────────────────────────────────────────────


def test_jurisdiction_is_required_so_no_caller_can_default_into_japan() -> None:
    with pytest.raises(TypeError):
        compute_deadlines(EXPIRY, "extend")  # type: ignore[call-arg]
