"""Submission track resolution and route clarity models.

Categorizes corridors and visa procedures into three operational models:
1. DIGITAL: Full online submission & payment by Torii bots/concierge. User visits no embassy.
2. HYBRID: Torii completes online registration/portal submission; user visits VAC (e.g. IVAC)
   with the printed Torii dossier for biometrics and passport drop-off.
3. CONSULAR: Statutory in-person consular / VFS submission. Torii prepares a 100% compliant,
   print-ready dossier kit (official forms, itinerary, cover letter, solvency proofs).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class SubmissionTrack(StrEnum):
    DIGITAL = "digital"
    HYBRID = "hybrid"
    CONSULAR = "consular"


class TrackSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    track: SubmissionTrack
    badge_label: str
    title: str
    headline: str
    torii_role: str
    applicant_role: str
    submission_center: str
    requires_in_person: bool


# Well-known country defaults according to the Torii business plan and implementation roadmap
KNOWN_TRACKS: dict[str, SubmissionTrack] = {
    # Digital / eVisa (Sit back & relax track)
    "SA": SubmissionTrack.DIGITAL,  # Saudi Arabia
    "VN": SubmissionTrack.DIGITAL,  # Vietnam
    "EG": SubmissionTrack.DIGITAL,  # Egypt
    "BH": SubmissionTrack.DIGITAL,  # Bahrain
    "KH": SubmissionTrack.DIGITAL,  # Cambodia
    "JO": SubmissionTrack.DIGITAL,  # Jordan
    "QA": SubmissionTrack.DIGITAL,  # Qatar
    "LK": SubmissionTrack.DIGITAL,  # Sri Lanka
    "TR": SubmissionTrack.DIGITAL,  # Turkey
    "MY": SubmissionTrack.DIGITAL,  # Malaysia
    "AE": SubmissionTrack.DIGITAL,  # UAE
    "RW": SubmissionTrack.DIGITAL,  # Rwanda
    "KE": SubmissionTrack.DIGITAL,  # Kenya
    "OM": SubmissionTrack.DIGITAL,  # Oman
    # Hybrid (Online registration + Counter / IVAC drop-off)
    "IN": SubmissionTrack.HYBRID,  # India (Medical Visa MED-1 via IVAC)
    "CA": SubmissionTrack.HYBRID,  # Canada (IRCC portal submission + VFS biometrics)
    # Consular / VFS (Walk-in ready dossier kit)
    "JP": SubmissionTrack.CONSULAR,  # Japan (MOFA form + VFS submission)
    "US": SubmissionTrack.CONSULAR,  # USA (DS-160 + Consular interview)
    "GB": SubmissionTrack.CONSULAR,  # UK (gov.uk form + VFS biometrics)
    "UK": SubmissionTrack.CONSULAR,  # UK alias
    "FR": SubmissionTrack.CONSULAR,  # France (France-Visas + VFS)
    "DE": SubmissionTrack.CONSULAR,  # Germany (VIDEX + Embassy/VFS)
    "ES": SubmissionTrack.CONSULAR,  # Spain (BLS International)
    "KR": SubmissionTrack.CONSULAR,  # South Korea (Embassy counter)
    "IT": SubmissionTrack.CONSULAR,  # Italy (VFS)
    "CH": SubmissionTrack.CONSULAR,  # Switzerland (VFS)
    "AU": SubmissionTrack.CONSULAR,  # Australia biometrics / VFS
}


def build_track_summary(
    track: SubmissionTrack | str,
    *,
    jurisdiction_code: str | None = None,
    visa_category_code: str | None = None,
) -> TrackSummary:
    """Construct user-friendly 'What Torii Does vs What You Do' metadata."""
    t = SubmissionTrack(track)
    j_code = (jurisdiction_code or "").upper()
    v_code = (visa_category_code or "").lower()  # noqa: F841 — used below in build_track_summary calls

    if t == SubmissionTrack.DIGITAL:
        return TrackSummary(
            track=t,
            badge_label="Digital eVisa (100% Online)",
            title="Full-Service Automated Online Submission",
            headline="We handle the government portal and pay the visa fee for you.",
            torii_role="Torii enters your verified data into the official government portal, pays the statutory visa fee using virtual cards, and downloads your approved visa.",
            applicant_role="Sit back and relax. Zero embassy or consulate visits required. Your official approved eVisa will be delivered directly to your Torii dashboard.",
            submission_center="Official Government eVisa Portal",
            requires_in_person=False,
        )

    if t == SubmissionTrack.HYBRID:
        center = (
            "IVAC (Indian Visa Application Center)" if j_code == "IN" else "Visa Application Center"
        )
        return TrackSummary(
            track=t,
            badge_label="Hybrid (Online Filing + Center Drop-Off)",
            title="Online Portal Filing & Appointment Dossier",
            headline="We submit the official online registration; you drop off your packet at the visa center.",
            torii_role="Torii completes your official portal registration, pays any digital gateway fees, and generates your barcode-stamped, ready-to-print submission dossier.",
            applicant_role=f"Take your printed Torii appointment kit to {center} for biometric enrollment and passport submission.",
            submission_center=center,
            requires_in_person=True,
        )

    # Consular default
    center = "VFS Global / Embassy of Japan" if j_code == "JP" else "VFS Global / Consular Section"
    return TrackSummary(
        track=t,
        badge_label="Consular / VFS Dossier Preparation",
        title="Walk-In Ready Official Consular Dossier",
        headline="We prepare a flawless, rejection-proof packet for your in-person appointment.",
        torii_role="Torii generates your official typewritten government forms, custom day-by-day travel itinerary, financial solvency binder, and cover letters.",
        applicant_role=f"Print your prepared dossier kit, sign where indicated, and attend your appointment at {center}. Pay the consular fee only upon approval or submission.",
        submission_center=center,
        requires_in_person=True,
    )


def resolve_submission_track(
    *,
    jurisdiction_code: str | None,
    visa_category_code: str | None = None,
    explicit_category_track: str | None = None,
    explicit_jurisdiction_track: str | None = None,
    research_route: str | None = None,
    filing_channel: str | None = None,
) -> TrackSummary:
    """Resolve the effective submission track taking overrides, corridors, and research into account."""
    j_code = (jurisdiction_code or "").upper()
    v_code = (visa_category_code or "").lower()  # noqa: F841 — used below in build_track_summary calls

    # 1. Explicit category-level track override
    if explicit_category_track:
        try:
            return build_track_summary(
                SubmissionTrack(explicit_category_track),
                jurisdiction_code=j_code,
                visa_category_code=v_code,
            )
        except ValueError:
            pass

    # 2. Specific route exceptions (e.g. India tourist eVisa vs India medical)
    if j_code == "IN":
        if v_code in ("tourist", "evisa"):
            return build_track_summary(
                SubmissionTrack.DIGITAL, jurisdiction_code=j_code, visa_category_code=v_code
            )
        # Medical & other standard Indian visas are hybrid (IVAC)
        return build_track_summary(
            SubmissionTrack.HYBRID, jurisdiction_code=j_code, visa_category_code=v_code
        )

    # 3. Explicit jurisdiction-level track
    if explicit_jurisdiction_track:
        try:
            return build_track_summary(
                SubmissionTrack(explicit_jurisdiction_track),
                jurisdiction_code=j_code,
                visa_category_code=v_code,
            )
        except ValueError:
            pass

    # 4. Agentic research clues
    if research_route in ("evisa", "eta", "visa_free"):
        return build_track_summary(
            SubmissionTrack.DIGITAL, jurisdiction_code=j_code, visa_category_code=v_code
        )

    # 5. Known country mapping
    if j_code in KNOWN_TRACKS:
        return build_track_summary(
            KNOWN_TRACKS[j_code], jurisdiction_code=j_code, visa_category_code=v_code
        )

    # 6. Fallback to consular
    return build_track_summary(
        SubmissionTrack.CONSULAR, jurisdiction_code=j_code, visa_category_code=v_code
    )
