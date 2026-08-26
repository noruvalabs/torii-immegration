"""``torii-fetch-forms`` — download every official form template into the local cache.

Run it at deploy time (or on a schedule) so the request path never waits on the
ministry, and so a form the ministry has revised is noticed here rather than by an
applicant holding a sheet that no longer matches the one they must file.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from torii_api.services.jp_official_forms import (
    CONSULAR_VISA_FORM,
    PERMANENT_RESIDENCE_FORM,
    OfficialForm,
    forms_for_scope,
)
from torii_api.services.official_form_store import cache_dir, ensure_template, refresh_template

_SCOPES: tuple[tuple[str, str], ...] = tuple(
    (category, action)
    for category in (
        "work",
        "student",
        "dependent",
        "spouse",
        "hsp",
        "designated_activities",
        "permanent_resident",
        "tourist",
    )
    for action in ("new_application", "change_of_status", "renewal")
)


def catalogue() -> list[OfficialForm]:
    """Every distinct official form the product can produce, deduplicated by code."""
    seen: dict[str, OfficialForm] = {}
    for category, action in _SCOPES:
        for form in forms_for_scope(category, action):
            seen.setdefault(form.code, form)
    seen.setdefault(PERMANENT_RESIDENCE_FORM.code, PERMANENT_RESIDENCE_FORM)
    seen.setdefault(CONSULAR_VISA_FORM.code, CONSULAR_VISA_FORM)
    return sorted(seen.values(), key=lambda form: form.code)


async def _fetch_all(force: bool) -> int:
    forms = catalogue()
    print(f"Caching {len(forms)} official form templates into {cache_dir()}\n")
    failures = 0
    for form in forms:
        if form.pdf_url is None:
            print(f"  {form.code:34} bundled with the service ({form.bundled_template})")
            continue
        template = await (refresh_template(form) if force else ensure_template(form))
        if template is None:
            failures += 1
            print(f"  {form.code:34} FAILED — {form.pdf_url}")
            continue
        if form.sha256 is None:
            revision = "no pinned revision"
        elif form.sha256 == template.sha256:
            revision = "matches pinned revision"
        else:
            revision = "REVISED since the layout was verified"
        print(f"  {form.code:34} {len(template.content):>8} bytes  {revision}")
    if failures:
        print(f"\n{failures} form(s) could not be downloaded.")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-download even when a cached copy exists",
    )
    args = parser.parse_args()
    sys.exit(1 if asyncio.run(_fetch_all(args.force)) else 0)


if __name__ == "__main__":
    main()
