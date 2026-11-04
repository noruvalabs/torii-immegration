"""Unit tests for submission track resolution and route clarity."""

from __future__ import annotations

from torii_api.services.content_packs import load_jurisdiction_meta
from torii_api.services.submission_track import (
    SubmissionTrack,
    resolve_submission_track,
)


def test_india_medical_resolves_to_hybrid() -> None:
    track = resolve_submission_track(
        jurisdiction_code="IN",
        visa_category_code="medical",
    )
    assert track.track == SubmissionTrack.HYBRID
    assert "IVAC" in track.applicant_role
    assert track.requires_in_person is True
    assert "Hybrid" in track.badge_label


def test_india_tourist_evisa_resolves_to_digital() -> None:
    track = resolve_submission_track(
        jurisdiction_code="IN",
        visa_category_code="tourist",
    )
    assert track.track == SubmissionTrack.DIGITAL
    assert track.requires_in_person is False
    assert "100% Online" in track.badge_label


def test_japan_resolves_to_consular() -> None:
    track = resolve_submission_track(
        jurisdiction_code="JP",
        visa_category_code="tourist",
    )
    assert track.track == SubmissionTrack.CONSULAR
    assert track.requires_in_person is True
    assert "VFS" in track.applicant_role or "Embassy" in track.applicant_role


def test_digital_countries_resolve_properly() -> None:
    for code in ["SA", "VN", "EG", "BH", "KH", "JO", "QA", "LK", "TR", "MY"]:
        track = resolve_submission_track(jurisdiction_code=code)
        assert track.track == SubmissionTrack.DIGITAL, f"Expected {code} to be digital"
        assert track.requires_in_person is False


def test_research_evisa_route_infers_digital() -> None:
    track = resolve_submission_track(
        jurisdiction_code="BR",
        research_route="evisa",
    )
    assert track.track == SubmissionTrack.DIGITAL


def test_jurisdiction_meta_loads_submission_track() -> None:
    meta_in = load_jurisdiction_meta("IN")
    assert meta_in is not None
    assert meta_in.submission_track == "hybrid"

    meta_jp = load_jurisdiction_meta("JP")
    assert meta_jp is not None
    assert meta_jp.submission_track == "consular"
