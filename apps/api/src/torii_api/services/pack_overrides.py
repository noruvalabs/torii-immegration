"""Admin edits to seeded pack content, applied on top of it at read time.

The packs in ``docs/jurisdictions`` are the reviewed ground truth, and ``seed()`` rewrites
the seeded rows from them on every run — ``existing.questions = questions``, then
``is_live = True``. An edit written into those rows is therefore destroyed on the next
boot, silently, which is what happened to anything saved through the ``/admin/ops``
upserts.

So an edit lives beside the seeded row rather than inside it. Seed never touches this
table; the override is re-applied to whatever the pack now says. Three things follow that
are worth having on their own:

* A deploy cannot lose an ops edit.
* The pack and the live content stay legible as separate things — you can always answer
  "what does the ministry pack say, and what have we changed?"
* Reverting is deleting a row, not reconstructing from memory what the pack used to say.

An override addresses one value by the same path grammar ``pack_proposals`` uses, so the
two mechanisms describe a change the same way::

    intake.questions[key=full_name].prompt
    eligibility.rules[key=criminal_record].failure_status
    documents[code=passport_original].name

The leading segment routes the override to the seeded row that holds that section. A path
whose selector matches no item — because the pack moved on and the question it edited is
gone — is skipped rather than applied to the wrong item, and reported by
:func:`stale_overrides` so ops can see that the edit no longer lands anywhere.
"""

from __future__ import annotations

import copy
import re
from typing import Any

import structlog

log = structlog.get_logger(__name__)

# ``key`` / ``code`` picks one item out of a list; the tail names the field on it.
_SEGMENT = re.compile(r"^([A-Za-z0-9_]+)(?:\[([A-Za-z0-9_]+)=([^\]]+)\])?$")

# Which seeded row each path prefix belongs to. Ordered longest-first so
# ``intake.questions`` is matched before a hypothetical ``intake``.
SECTION_INTAKE = "intake.questions"
SECTION_RULES = "eligibility.rules"
SECTION_DOCUMENTS = "documents"

SECTIONS: tuple[str, ...] = (SECTION_INTAKE, SECTION_RULES, SECTION_DOCUMENTS)


class OverrideError(ValueError):
    """An override that cannot be stored or applied as written."""


def _split(path: str) -> tuple[str, tuple[str, str], list[str]]:
    """``intake.questions[key=full_name].prompt`` → section, selector, field path.

    The selector rides on the segment naming the list, exactly as in ``pack_proposals``:
    the section is every segment up to and including that one, with the selector removed.
    """
    segments = [segment for segment in path.split(".") if segment]
    if not segments:
        raise OverrideError("an empty path addresses nothing")

    names: list[str] = []
    for index, raw in enumerate(segments):
        match = _SEGMENT.match(raw)
        if match is None:
            raise OverrideError(f"not a pack path: {path!r}")
        name, selector_key, selector_value = match.groups()
        names.append(name)
        if selector_key is None:
            continue

        section = ".".join(names)
        if section not in SECTIONS:
            raise OverrideError(
                f"not an editable section: {section!r} — it has to be one of {', '.join(SECTIONS)}"
            )
        field_path = segments[index + 1 :]
        if not field_path:
            raise OverrideError(f"{path!r}: names an item but no field on it")
        for segment in field_path:
            tail = _SEGMENT.match(segment)
            if tail is None or tail.group(2) is not None:
                raise OverrideError(f"not a pack path: {path!r}")
        return section, (selector_key, selector_value), field_path

    # No selector anywhere: the path names a section, or a field of one, but not an item.
    section = ".".join(names)
    if section in SECTIONS or any(s.startswith(f"{section}.") for s in SECTIONS):
        raise OverrideError(
            f"{path!r}: pick one item with [key=...] or [code=...] before naming a field"
        )
    raise OverrideError(
        f"not an editable path: {path!r} — it has to start with one of {', '.join(SECTIONS)}"
    )


def section_of(path: str) -> str:
    """Which seeded section ``path`` edits.

    Raises rather than guessing: an override that cannot be routed is one that would
    silently never apply, and this is the write-time gate against storing one.
    """
    return _split(path)[0]


def parse_path(path: str) -> tuple[str, tuple[str, str], list[str]]:
    """``(section, selector, field_path)`` for ``path``, or raise ``OverrideError``.

    ``selector`` is the ``(key, value)`` that picks one item out of the section's list.
    ``field_path`` is the remaining keys to walk inside that item, so a nested field such
    as ``name.en`` or ``show_when.equals`` is addressable.
    """
    return _split(path)


def validate_path(path: str) -> str:
    """The path, having proved it is one an override can be applied through."""
    parse_path(path)
    return path


def _find(items: list[dict[str, Any]], selector: tuple[str, str]) -> dict[str, Any] | None:
    selector_key, selector_value = selector
    matches = [
        item
        for item in items
        if isinstance(item, dict) and str(item.get(selector_key)) == selector_value
    ]
    if len(matches) != 1:
        return None
    return matches[0]


def applies_to(items: list[dict[str, Any]], path: str) -> bool:
    """Whether ``path`` still addresses exactly one item in ``items``."""
    try:
        selector = parse_path(path)[1]
    except OverrideError:
        return False
    return _find(items, selector) is not None


def apply_overrides(
    items: list[dict[str, Any]],
    overrides: list[dict[str, Any]],
    *,
    section: str,
) -> list[dict[str, Any]]:
    """``items`` with every override for ``section`` written onto it.

    Never mutates the caller's list: the seeded rows are SQLAlchemy-attached JSON, and
    editing them in place would write the override back into the row it exists to avoid
    touching. An override whose selector no longer matches is skipped — the pack has
    moved and the safe reading of "edit this question" is not "edit whichever question
    is there now".
    """
    relevant = [o for o in overrides if o.get("path") and section_of(str(o["path"])) == section]
    if not relevant:
        return items

    result = copy.deepcopy(items)
    for override in relevant:
        path = str(override["path"])
        try:
            selector, field_path = parse_path(path)[1:]
        except OverrideError as exc:
            log.warning("pack_override.unroutable", path=path, error=str(exc))
            continue
        item = _find(result, selector)
        if item is None:
            log.info("pack_override.stale", path=path, section=section)
            continue
        node: Any = item
        for segment in field_path[:-1]:
            nxt = node.get(segment)
            if not isinstance(nxt, dict):
                nxt = {}
                node[segment] = nxt
            node = nxt
        node[field_path[-1]] = copy.deepcopy(override.get("value"))
    return result


def stale_overrides(
    items: list[dict[str, Any]], overrides: list[dict[str, Any]], *, section: str
) -> list[str]:
    """Paths that no longer address anything, so ops can see an edit stopped landing."""
    stale: list[str] = []
    for override in overrides:
        path = str(override.get("path") or "")
        try:
            if section_of(path) != section:
                continue
        except OverrideError:
            stale.append(path)
            continue
        if not applies_to(items, path):
            stale.append(path)
    return stale
