"""Deterministic deadline computation for JP status-of-residence procedures (rule corpus).

Encodes the temporal rules from the Japan research spec:

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
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

GRACE_PERIOD_DAYS = 61  # up to two months past expiry
FILING_WINDOW_OPEN_DAYS = 90  # three months before expiry (statuses granted 6+ months)
ONLINE_CUTOFF_BUFFER_DAYS = 2  # at least two business days before expiry

# Procedures that qualify for the 特例期間 grace period.
GRACE_PROCEDURES = ("extend", "change")


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


def compute_deadlines(residence_expiry: str | None, procedure: str) -> DeadlineProfile:
    """Compute the deadline profile for a case.

    ``procedure`` is the normalized action code (``"extend"`` / ``"change"`` / ``"coe"`` /
    ``"new_application"`` / ...). Without a residence expiry, no deadlines can be derived.
    """
    if not residence_expiry:
        return DeadlineProfile(residence_expiry=None, procedure=procedure)

    try:
        expiry = date.fromisoformat(residence_expiry)
    except (TypeError, ValueError):
        return DeadlineProfile(residence_expiry=None, procedure=procedure)

    profile = DeadlineProfile(residence_expiry=expiry, procedure=procedure)
    profile.filing_window_opens = expiry - timedelta(days=FILING_WINDOW_OPEN_DAYS)
    profile.online_cutoff = add_business_days(expiry, -ONLINE_CUTOFF_BUFFER_DAYS)
    profile.my_number_expiry = expiry

    is_grace_eligible = procedure.lower() in GRACE_PROCEDURES
    profile.has_grace_period = is_grace_eligible
    if is_grace_eligible:
        profile.grace_period_end = expiry + timedelta(days=GRACE_PERIOD_DAYS)

    return profile
