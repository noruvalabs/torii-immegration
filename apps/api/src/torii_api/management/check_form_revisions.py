"""``torii-check-form-revisions`` — ask the ministry what it publishes today.

Run it nightly. It records, per official form, the URL and digest the Immigration Services
Agency serves right now and whether that is the revision the authored layout was verified
against, writing the answer to ``docs/jurisdictions/jp/_form_revisions.yml``.

It never adopts a revision. A revised sheet may have moved a field, so the layout has to be
re-verified by hand and the digest repinned in ``jp_official_forms.py``. Until then the fill
gate leaves that page blank rather than writing into coordinates that may have moved, which
is what makes a queued review the safe outcome rather than an outage.

Exit code 1 when anything needs review, so a scheduler can raise it.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime

from torii_api.management.fetch_forms import catalogue
from torii_api.services.form_revisions import (
    STATUS_CURRENT,
    check_all,
    pending_reviews,
    write_revisions,
)


async def _run() -> int:
    forms = catalogue()
    print(f"Checking {len(forms)} official forms against the ministry...\n")
    records = await check_all(forms)
    path = write_revisions(records, checked_at=datetime.now(UTC))

    for record in sorted(records, key=lambda item: item.code):
        marker = "ok " if record.status == STATUS_CURRENT else "!! "
        print(f"{marker}{record.code:<42} {record.status}")
        if record.note:
            print(f"     {record.note}")

    needs_review = [record for record in records if record.needs_review]
    print(f"\nWrote {path}")
    if needs_review:
        print(f"\n{len(needs_review)} form(s) need a human to look at them:")
        for record in needs_review:
            print(f"  - {record.code}: {record.status}")
        print(
            "\nRe-verify each layout against the new sheet, then repin its digest in\n"
            "jp_official_forms.py. Until you do, those pages are left blank rather than\n"
            "filled into coordinates that may have moved."
        )
        return 1
    print("\nEvery form matches the revision its layout was verified against.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--queue-only",
        action="store_true",
        help="print the queue from the last recorded check without going to the network",
    )
    args = parser.parse_args()

    if args.queue_only:
        queue = pending_reviews()
        if not queue:
            print("Nothing queued: the last check found every form current.")
            raise SystemExit(0)
        for record in queue:
            print(f"{record.code:<42} {record.status}  {record.pdf_url}")
        raise SystemExit(1)

    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())  # type: ignore[func-returns-value]
