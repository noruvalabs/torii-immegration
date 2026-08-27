"""Fallback official citation for a pack item that does not carry one of its own.

Every rule, document and form the research agent discovers arrives with the citation it
was discovered from, and the packs author one per item. That citation is the accurate one
and it always wins here.

This module used to do the opposite. It derived a citation by sniffing substrings out of
an answer key -- ``"tax" in key``, ``"pension" in key``, thirty-odd branches -- against a
table of thirty-six URLs, and then *overrode* the item's own citation whenever the
authored URL looked "generic" to a heuristic. So a pack that cited
``procedures/16-3.html`` for an extension item had that citation replaced by a guess from
the key, and the applicant was shown a source the item was never checked against.

What is left is a fallback of last resort, keyed on the scope the case is actually in
rather than on words that happen to appear in an item's key. A work-renewal item with no
citation of its own cites the work-renewal procedure page; it does not cite the National
Tax Agency because its key contains "tax". An unmatched item resolves to nothing, and
callers render an uncited item as uncited -- a synthesised URL reads as an official source
and is not one, which is what NF-2 exists to prevent.
"""

from __future__ import annotations

from typing import Any

# The official page for a residence status or visa category, per jurisdiction. Ops extend
# this when a pack gains a category; it is a starting point for an item nobody has
# researched yet, not a substitute for the item's own source.
_SCOPE_CITATIONS: dict[str, dict[str, dict[str, str]]] = {
    "JP": {
        "": {
            "authority": "Immigration Services Agency of Japan (出入国在留管理庁)",
            "title": "Procedures for residence applications",
            "url": "https://www.moj.go.jp/isa/applications/procedures/index.html",
        },
        "work": {
            "authority": "Immigration Services Agency of Japan (出入国在留管理庁)",
            "title": "Engineer / Specialist in Humanities / International Services (技術・人文知識・国際業務)",
            "url": "https://www.moj.go.jp/isa/applications/status/gijinkoku.html",
        },
        "hsp": {
            "authority": "Immigration Services Agency of Japan (出入国在留管理庁)",
            "title": "Highly Skilled Professional (高度専門職)",
            "url": "https://www.moj.go.jp/isa/applications/status/designatedactivities02_00004.html",
        },
        "student": {
            "authority": "Immigration Services Agency of Japan (出入国在留管理庁)",
            "title": "Student (留学)",
            "url": "https://www.moj.go.jp/isa/applications/status/student.html",
        },
        "dependent": {
            "authority": "Immigration Services Agency of Japan (出入国在留管理庁)",
            "title": "Dependent (家族滞在)",
            "url": "https://www.moj.go.jp/isa/applications/status/dependent.html",
        },
        "spouse": {
            "authority": "Immigration Services Agency of Japan (出入国在留管理庁)",
            "title": "Spouse or Child of Japanese National (日本人の配偶者等)",
            "url": "https://www.moj.go.jp/isa/applications/status/spouseorchildofjapanese01.html",
        },
        "designated_activities": {
            "authority": "Immigration Services Agency of Japan (出入国在留管理庁)",
            "title": "Designated Activities (特定活動)",
            "url": "https://www.moj.go.jp/isa/applications/status/designatedactivities02.html",
        },
        "permanent_resident": {
            "authority": "Immigration Services Agency of Japan (出入国在留管理庁)",
            "title": "Permission for permanent residence (永住許可)",
            "url": "https://www.moj.go.jp/isa/applications/procedures/16-4.html",
        },
        "tourist": {
            "authority": "Ministry of Foreign Affairs of Japan (外務省)",
            "title": "Short-stay visa (短期滞在)",
            "url": "https://www.mofa.go.jp/j_info/visit/visa/short/index.html",
        },
    },
    "UK": {
        "": {
            "authority": "UK Visas and Immigration",
            "title": "Visas and immigration",
            "url": "https://www.gov.uk/browse/visas-immigration",
        },
        "work": {
            "authority": "UK Visas and Immigration",
            "title": "Skilled Worker visa",
            "url": "https://www.gov.uk/skilled-worker-visa",
        },
        "student": {
            "authority": "UK Visas and Immigration",
            "title": "Student visa",
            "url": "https://www.gov.uk/student-visa",
        },
        "tourist": {
            "authority": "UK Visas and Immigration",
            "title": "Standard Visitor visa",
            "url": "https://www.gov.uk/standard-visitor",
        },
    },
}

# The UK is published under both codes.
_SCOPE_CITATIONS["GB"] = _SCOPE_CITATIONS["UK"]


def _is_complete(citation: Any) -> bool:
    """Whether a citation says who published it, what it is, and where to read it."""
    if not isinstance(citation, dict):
        return False
    url = str(citation.get("url") or "")
    return bool(
        citation.get("authority") and citation.get("title") and url.startswith("http")
    )


def resolve_official_citation(
    jurisdiction_code: str,
    visa_category: str = "",
    existing_citation: dict[str, Any] | None = None,
    default_version: str = "2026-04",
) -> dict[str, Any]:
    """The citation to show for one item.

    The item's own citation wins whenever it is complete. There is deliberately no way to
    pass an item key: deriving a source from words in a key is what this module was
    rewritten to stop doing.
    """
    if _is_complete(existing_citation):
        assert existing_citation is not None  # narrowed by _is_complete
        return {
            "authority": str(existing_citation["authority"]),
            "title": str(existing_citation["title"]),
            "url": str(existing_citation["url"]),
            "source_version": existing_citation.get("source_version") or default_version,
        }

    jurisdiction = _SCOPE_CITATIONS.get((jurisdiction_code or "").upper())
    if jurisdiction is None:
        return {"authority": "", "title": "", "url": "", "source_version": default_version}

    fallback = jurisdiction.get((visa_category or "").lower()) or jurisdiction.get("")
    if fallback is None:
        return {"authority": "", "title": "", "url": "", "source_version": default_version}
    return {**fallback, "source_version": default_version}
