"""Proposed changes to a jurisdiction pack, for ops to accept or reject.

Research either went live automatically (``validated_for_promote``) or not at all. That is
right for tier-A content — a fee, a filing channel, a processing time — where the citation
gate is the whole review. It is wrong for the content a human has to judge: the wording an
applicant reads, which documents a scope demands, what an eligibility rule actually says.

This is the missing middle. The agent writes what it found as a *diff* against the pack in
``docs/jurisdictions/**``, one entry per changed line with the source it read that line
from. Ops accept or reject. Accepting rewrites the pack file, which is versioned content,
so a bad proposal is a rejected diff or a revertable commit rather than a live regression.

Two rules the store enforces rather than trusts:

* Every change carries a citation with an ``http`` URL. A proposal with an uncited change
  is refused at write time, not at review time (NF-2).
* Applying a proposal touches only the pack file for its own scope, and only the paths the
  proposal listed. It cannot reach another scope, and it cannot add a change that was not
  reviewed.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
import yaml

from torii_api.services.content_packs import resolve_packs_dir

log = structlog.get_logger(__name__)

PROPOSALS_DIRNAME = "_proposals"

STATUS_PENDING = "pending"
STATUS_ACCEPTED = "accepted"
STATUS_REJECTED = "rejected"

# A path into a pack: dotted keys, with ``[key=value]`` to pick one item out of a list by
# its own key. `intake.questions[key=full_name].prompt`, `documents[code=passport].name`.
_SEGMENT = re.compile(r"^([A-Za-z0-9_]+)(?:\[([A-Za-z0-9_]+)=([^\]]+)\])?$")


class ProposalError(ValueError):
    """A proposal that cannot be stored or applied as written."""


@dataclass(frozen=True)
class Change:
    """One line of a pack, and what the agent found it should say."""

    path: str
    to: Any
    citation: dict[str, str]
    from_: Any = None
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "path": self.path,
            "from": self.from_,
            "to": self.to,
            "citation": dict(self.citation),
        }
        if self.reason:
            entry["reason"] = self.reason
        return entry


@dataclass(frozen=True)
class Proposal:
    """A set of changes to one scope's pack, awaiting a decision."""

    id: str
    scope: str
    source: str
    summary: str
    proposed_at: str
    changes: tuple[Change, ...]
    status: str = STATUS_PENDING
    decided_at: str | None = None
    decided_by: str | None = None
    decision_note: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "id": self.id,
            "scope": self.scope,
            "source": self.source,
            "summary": self.summary,
            "proposed_at": self.proposed_at,
            "status": self.status,
            "changes": [change.as_dict() for change in self.changes],
        }
        if self.decided_at:
            entry["decided_at"] = self.decided_at
            entry["decided_by"] = self.decided_by
            if self.decision_note:
                entry["decision_note"] = self.decision_note
        return entry


# ── Where proposals live ───────────────────────────────────────────────────────────


def proposals_dir() -> Path:
    return resolve_packs_dir() / PROPOSALS_DIRNAME


def _proposal_path(proposal_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", proposal_id):
        raise ProposalError(f"not a proposal id: {proposal_id!r}")
    return proposals_dir() / f"{proposal_id}.yml"


def _pack_path(scope: str) -> Path:
    """``jp/work.renewal`` → the pack file, refusing anything that escapes the packs dir."""
    if not re.fullmatch(r"[a-z]{2}/[a-z0-9_]+\.[a-z0-9_]+", scope):
        raise ProposalError(f"not a scope id: {scope!r}")
    root = resolve_packs_dir().resolve()
    path = (root / f"{scope}.yml").resolve()
    if root not in path.parents:
        raise ProposalError(f"scope escapes the packs directory: {scope!r}")
    return path


# ── Reading and writing a pack path ────────────────────────────────────────────────


def _walk(document: Any, path: str, *, create: bool = False) -> tuple[Any, str]:
    """Resolve all but the last segment of ``path``, returning (container, final key)."""
    segments = path.split(".")
    node: Any = document
    for raw in segments[:-1]:
        match = _SEGMENT.match(raw)
        if match is None:
            raise ProposalError(f"not a pack path: {path!r}")
        key, selector_key, selector_value = match.groups()
        if not isinstance(node, dict) or key not in node:
            if not create:
                raise ProposalError(f"{path!r}: no '{key}' here")
            node[key] = {} if selector_key is None else []
        node = node[key]
        if selector_key is not None:
            if not isinstance(node, list):
                raise ProposalError(f"{path!r}: '{key}' is not a list")
            matches = [
                item
                for item in node
                if isinstance(item, dict) and str(item.get(selector_key)) == selector_value
            ]
            if len(matches) != 1:
                raise ProposalError(
                    f"{path!r}: {len(matches)} items match {selector_key}={selector_value}"
                )
            node = matches[0]
    final = _SEGMENT.match(segments[-1])
    if final is None or final.group(2) is not None:
        raise ProposalError(f"not a pack path: {path!r}")
    return node, final.group(1)


def read_path(document: Any, path: str) -> Any:
    """The current value at ``path``, or ``None`` where the pack has none."""
    try:
        container, key = _walk(document, path)
    except ProposalError:
        return None
    if not isinstance(container, dict):
        return None
    return container.get(key)


def _write_path(document: Any, path: str, value: Any) -> None:
    container, key = _walk(document, path, create=True)
    if not isinstance(container, dict):
        raise ProposalError(f"{path!r}: cannot set a key on a {type(container).__name__}")
    container[key] = value


# ── Proposing ──────────────────────────────────────────────────────────────────────


def _cited(citation: Any) -> bool:
    return (
        isinstance(citation, dict)
        and isinstance(citation.get("url"), str)
        and citation["url"].startswith("http")
        and bool(citation.get("authority"))
    )


def _proposal_id(scope: str, changes: tuple[Change, ...], proposed_at: str) -> str:
    """Stable per (scope, content, timestamp), so a retry does not duplicate a proposal."""
    payload = "|".join(f"{change.path}={change.to!r}" for change in changes)
    digest = hashlib.sha256(f"{scope}|{payload}".encode()).hexdigest()[:8]
    return f"{proposed_at[:10]}-{scope.replace('/', '-').replace('.', '-')}-{digest}"


def propose(
    *,
    scope: str,
    changes: list[Change],
    source: str,
    summary: str = "",
    proposed_at: datetime | None = None,
) -> Proposal:
    """Store a proposal. Refuses an uncited change rather than queuing one for review."""
    if not changes:
        raise ProposalError("a proposal with no changes is not a proposal")
    pack_path = _pack_path(scope)
    if not pack_path.exists():
        raise ProposalError(f"no pack for scope {scope!r}")

    uncited = [change.path for change in changes if not _cited(change.citation)]
    if uncited:
        raise ProposalError(
            "every changed line needs an official source; these have none: "
            + ", ".join(sorted(uncited))
        )

    document = yaml.safe_load(pack_path.read_text(encoding="utf-8")) or {}
    resolved = tuple(
        Change(
            path=change.path,
            to=change.to,
            citation=dict(change.citation),
            from_=read_path(document, change.path),
            reason=change.reason,
        )
        for change in changes
    )
    # A change that changes nothing is noise in a review queue.
    resolved = tuple(change for change in resolved if change.from_ != change.to)
    if not resolved:
        raise ProposalError("every proposed change already matches the pack")

    stamp = (proposed_at or datetime.now(UTC)).isoformat()
    proposal = Proposal(
        id=_proposal_id(scope, resolved, stamp),
        scope=scope,
        source=source,
        summary=summary,
        proposed_at=stamp,
        changes=resolved,
    )
    _save(proposal)
    log.info(
        "pack_proposal.stored",
        proposal=proposal.id,
        scope=scope,
        changes=len(resolved),
        source=source,
    )
    return proposal


def diff_against_pack(scope: str, proposed: dict[str, Any]) -> list[Change]:
    """Turn a researched pack into the lines it would change.

    The agent returns a whole pack; ops review lines. Only the fields a human judges are
    compared -- question wording and sections, document names and why they are required,
    rule descriptions -- because those are the ones this loop exists for. Everything else
    the agent produces is tier A and already goes live behind its own citation gate.
    """
    current = yaml.safe_load(_pack_path(scope).read_text(encoding="utf-8")) or {}
    changes: list[Change] = []

    for section, selector, fields in (
        ("intake.questions", "key", ("prompt", "section", "hint")),
        ("documents", "code", ("name", "why_required", "how_to_obtain")),
        ("eligibility.rules", "key", ("description", "operator", "value")),
    ):
        for item in _items(proposed, section):
            identifier = item.get(selector)
            if identifier is None:
                continue
            for name in fields:
                if name not in item:
                    continue
                path = f"{section}[{selector}={identifier}].{name}"
                if read_path(current, path) == item[name]:
                    continue
                changes.append(
                    Change(
                        path=path,
                        to=item[name],
                        citation=item.get("citation") or {},
                        from_=read_path(current, path),
                    )
                )
    return changes


def _items(document: Any, section: str) -> list[dict[str, Any]]:
    node: Any = document
    for key in section.split("."):
        if not isinstance(node, dict):
            return []
        node = node.get(key)
    return [item for item in node] if isinstance(node, list) else []


# ── Reviewing ──────────────────────────────────────────────────────────────────────


def _save(proposal: Proposal) -> Path:
    directory = proposals_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = _proposal_path(proposal.id)
    header = (
        "# A proposed change to a jurisdiction pack, awaiting an ops decision.\n"
        "# Written by the research agent; accepted or rejected through\n"
        "# POST /v1/admin/ops/pack-proposals/{id}/decision. Accepting rewrites the pack,\n"
        "# which is versioned content -- so a bad proposal is a revertable commit.\n"
    )
    path.write_text(
        header + yaml.safe_dump(proposal.as_dict(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path


def _load(path: Path) -> Proposal:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Proposal(
        id=str(raw.get("id") or path.stem),
        scope=str(raw.get("scope") or ""),
        source=str(raw.get("source") or ""),
        summary=str(raw.get("summary") or ""),
        proposed_at=str(raw.get("proposed_at") or ""),
        status=str(raw.get("status") or STATUS_PENDING),
        decided_at=raw.get("decided_at"),
        decided_by=raw.get("decided_by"),
        decision_note=str(raw.get("decision_note") or ""),
        changes=tuple(
            Change(
                path=str(entry.get("path") or ""),
                to=entry.get("to"),
                citation=entry.get("citation") or {},
                from_=entry.get("from"),
                reason=str(entry.get("reason") or ""),
            )
            for entry in (raw.get("changes") or [])
            if isinstance(entry, dict)
        ),
    )


def load_proposal(proposal_id: str) -> Proposal | None:
    path = _proposal_path(proposal_id)
    return _load(path) if path.exists() else None


def list_proposals(*, status: str | None = None, scope: str | None = None) -> list[Proposal]:
    directory = proposals_dir()
    if not directory.exists():
        return []
    proposals = [_load(path) for path in sorted(directory.glob("*.yml"))]
    if status is not None:
        proposals = [item for item in proposals if item.status == status]
    if scope is not None:
        proposals = [item for item in proposals if item.scope == scope]
    return proposals


def decide(
    proposal_id: str,
    *,
    accept: bool,
    reviewer: str,
    note: str = "",
    decided_at: datetime | None = None,
) -> Proposal:
    """Accept a proposal (rewriting its pack) or reject it. Idempotent per decision."""
    proposal = load_proposal(proposal_id)
    if proposal is None:
        raise ProposalError(f"no such proposal: {proposal_id}")
    if proposal.status != STATUS_PENDING:
        raise ProposalError(f"{proposal_id} was already {proposal.status}")

    if accept:
        _apply(proposal)

    decided = Proposal(
        id=proposal.id,
        scope=proposal.scope,
        source=proposal.source,
        summary=proposal.summary,
        proposed_at=proposal.proposed_at,
        changes=proposal.changes,
        status=STATUS_ACCEPTED if accept else STATUS_REJECTED,
        decided_at=(decided_at or datetime.now(UTC)).isoformat(),
        decided_by=reviewer,
        decision_note=note,
    )
    _save(decided)
    log.info(
        "pack_proposal.decided",
        proposal=proposal.id,
        scope=proposal.scope,
        accepted=accept,
        reviewer=reviewer,
    )
    return decided


def _apply(proposal: Proposal) -> Path:
    """Write the accepted changes into the pack, and nothing else."""
    path = _pack_path(proposal.scope)
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for change in proposal.changes:
        _write_path(document, change.path, change.to)
    path.write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    return path
