"""Citation engine — drop customer-facing instructions without sources (NF-2, US-11)."""

from __future__ import annotations

from torii_ai.citations.models import Instruction


def filter_instructions(instructions: list[Instruction]) -> list[Instruction]:
    """Keep only instructions that carry at least one resolvable source."""
    return [i for i in instructions if i.sources]


def sanitize_bubble(
    *,
    text: str,
    instructions: list[Instruction],
    claims_requirement: bool,
) -> tuple[str, list[Instruction]] | None:
    """Return (text, instructions) for the wire, or ``None`` to drop the bubble.

    If ``claims_requirement`` is true and no sourced instructions survive, drop the bubble.
    Otherwise attach only sourced instructions.
    """
    kept = filter_instructions(instructions)
    if claims_requirement and not kept:
        return None
    return text, kept
