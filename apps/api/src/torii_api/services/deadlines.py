"""Deterministic deadline computation, per jurisdiction (rule corpus).

Every number here is a statute, and a statute belongs to one country. These rules were
written from the Japan research spec and were applied to whatever case reached them, so a
jurisdiction whose law nobody has encoded would have been handed Japan's — a wrong date
presented with the same confidence as a right one, on the one screen an applicant uses to
decide when to file. A jurisdiction with no rules now gets **no** derived deadlines.

Japan (:data:`JP_RULES`), from the research spec:

* **Filing window** opens three months before the residence period expires (for statuses
  granted six months or more).
* **Online cut-off** is at least two business days before expiry: the ISA online system will
  not accept a filing on the final day of the residence period, so trusting a countdown to
  expiry minus one day risks falling out of status.
* **Grace period** (特例期間): filing on or before the expiry date lets the applicant remain
  lawfully in Japan while the application is pending — up to two months past expiry or until
  a decision. Work authorization continues during the window. Applies to EXTEND and CHANGE
  only; COE and Temporary Visitor do not get it.
* **My Number card** expiry is tied to the residence period and no reminder is sent.

All functions are pure date math — the engine never infers anything about the application's
merits (NF-1) — and deadlines only surface when the user's residence-card expiry is known.

To add a country, write its rules as a :class:`DeadlineRules` and register it in
:data:`RULES_BY_JURISDICTION`. Do not reuse another country's numbers as an approximation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta


@dataclass(frozen=True)
class DeadlineRules:
    """One jurisdiction's filing-deadline statute, as pure numbers."""

    # Days before expiry that the filing window opens.
    filing_window_open_days: int
    # Business days before expiry after which the online system stops accepting a filing.
    online_cutoff_buffer_days: int
    # Days past expiry the applicant may remain lawfully while a filing is pending, and the
    # procedures that earn it. ``None`` means this jurisdiction grants no such period.
    grace_period_days: int | None = None
    grace_procedures: tuple[str, ...] = ()
    # True where the national ID card's validity is tied to the residence period, so its
    # expiry is worth surfacing alongside the filing dates.
    id_card_expiry_tracks_residence: bool = False


JP_RULES = DeadlineRules(
    filing_window_open_days=90,  # three months before expiry (statuses granted 6+ months)
    online_cutoff_buffer_days=2,  # at least two business days before expiry
    grace_period_days=61,  # 特例期間 — up to two months past expiry
    grace_procedures=("extend", "change"),
    id_card_expiry_tracks_residence=True,  # My Number card
)

# Only jurisdictions whose rules someone has actually read off the statute belong here.
RULES_BY_JURISDICTION: dict[str, DeadlineRules] = {"JP": JP_RULES}

# Retained for callers that read the Japanese figures directly. New code should reach for
# the rules of the jurisdiction it is working in, not for these.
GRACE_PERIOD_DAYS = JP_RULES.grace_period_days
FILING_WINDOW_OPEN_DAYS = JP_RULES.filing_window_open_days
ONLINE_CUTOFF_BUFFER_DAYS = JP_RULES.online_cutoff_buffer_days
GRACE_PROCEDURES = JP_RULES.grace_procedures


def rules_for(jurisdiction: str | None) -> DeadlineRules | None:
    """The encoded rules for a jurisdiction code, or ``None`` when nobody has written them."""
    if not jurisdiction:
        return None
    return RULES_BY_JURISDICTION.get(jurisdiction.strip().upper())


def _is_weekend(day: date) -> bool:
    return day.weekday() >= 5


def add_business_days(start: date, days: int) -> date:
    """Return ``start`` shifted by ``days`` business days (weekends only).

    Japan public holidays are not modeled here; a weekend-only approximation is the
    deterministic, testable contract. Authorities use business calendars that vary by
    bureau, so this is surfaced as "at least N business days" rather than a hard date.
    """
    day = start
    step = 1 if days >= 0 else -1
    remaining = abs(days)
    while remaining > 0:
        day += timedelta(days=step)
        if not _is_weekend(day):
            remaining -= 1
    return day


@dataclass
class DeadlineProfile:
    """Computed deadlines for one case, derived solely from the residence-card expiry."""

    residence_expiry: date | None
    procedure: str
    # The country whose statute produced the dates below. Empty when none was encoded, in
    # which case every derived date stays ``None`` rather than borrowing another country's.
    jurisdiction: str = ""
    filing_window_opens: date | None = field(default=None)
    online_cutoff: date | None = field(default=None)
    grace_period_end: date | None = field(default=None)
    my_number_expiry: date | None = field(default=None)
    has_grace_period: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "residence_expiry": self.residence_expiry.isoformat()
            if self.residence_expiry
            else None,
            "procedure": self.procedure,
            "jurisdiction": self.jurisdiction,
            "filing_window_opens": (
                self.filing_window_opens.isoformat() if self.filing_window_opens else None
            ),
            "online_cutoff": self.online_cutoff.isoformat() if self.online_cutoff else None,
            "grace_period_end": (
                self.grace_period_end.isoformat() if self.grace_period_end else None
            ),
            "my_number_expiry": self.my_number_expiry.isoformat()
            if self.my_number_expiry
            else None,
            "has_grace_period": self.has_grace_period,
        }


def compute_deadlines(
    residence_expiry: str | None,
    procedure: str,
    *,
    jurisdiction: str | None,
) -> DeadlineProfile:
    """Compute the deadline profile for a case under its own jurisdiction's rules.

    ``procedure`` is the normalized action code (``"extend"`` / ``"change"`` / ``"coe"`` /
    ``"new_application"`` / ...). Without a residence expiry, no deadlines can be derived.

    ``jurisdiction`` is required and has no default: a caller that does not know which
    country's law applies cannot be given dates, and silently falling back to Japan's is
    the failure this argument exists to prevent. A jurisdiction with no encoded rules gets
    a profile carrying the expiry the applicant gave and nothing derived from it.
    """
    rules = rules_for(jurisdiction)
    code = (jurisdiction or "").strip().upper()

    if not residence_expiry:
        return DeadlineProfile(residence_expiry=None, procedure=procedure, jurisdiction=code)

    try:
        expiry = date.fromisoformat(residence_expiry)
    except (TypeError, ValueError):
        return DeadlineProfile(residence_expiry=None, procedure=procedure, jurisdiction=code)

    profile = DeadlineProfile(residence_expiry=expiry, procedure=procedure, jurisdiction=code)
    if rules is None:
        # The expiry is a fact the applicant gave us. Every other date on this profile
        # would be a guess dressed as a statute.
        return profile

    profile.filing_window_opens = expiry - timedelta(days=rules.filing_window_open_days)
    profile.online_cutoff = add_business_days(expiry, -rules.online_cutoff_buffer_days)
    if rules.id_card_expiry_tracks_residence:
        profile.my_number_expiry = expiry

    is_grace_eligible = (
        rules.grace_period_days is not None and procedure.lower() in rules.grace_procedures
    )
    profile.has_grace_period = is_grace_eligible
    if is_grace_eligible:
        assert rules.grace_period_days is not None  # narrowed by is_grace_eligible
        profile.grace_period_end = expiry + timedelta(days=rules.grace_period_days)

    return profile
