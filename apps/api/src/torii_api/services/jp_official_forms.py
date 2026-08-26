"""The catalogue of official Japanese forms, resolved per application type.

One published PDF is not enough: the Immigration Services Agency issues a *different*
sheet for every (residence status, procedure) pair — the Student extension form is not
the Engineer extension form even though both are 別記第三十号の二様式 — and the Ministry
of Foreign Affairs issues its own consular form on top. This module records, for each
scope the product supports, which forms are statutorily correct, where the ministry
publishes them, and which authored layout fills them.

Two things read this catalogue:

* :mod:`torii_api.services.official_form_store` — fetches and caches the exact PDF.
* :func:`intake_questions_for_scope` — derives the intake questionnaire from the form's
  own items, so every box the applicant has to sign for is actually asked about.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from torii_api.services.jp_form_layouts import (
    CHANGE_LAYOUT,
    COE_LAYOUT,
    DEPENDENT_PART2_LAYOUT,
    EXTENSION_LAYOUT,
    PERMANENT_RESIDENCE_LAYOUT,
    PROCEDURE_CONSULAR_VISA,
    SPOUSE_PART2_LAYOUT,
    SPOUSE_PART3_LAYOUT,
    STUDENT_PART2_LAYOUT,
    STUDENT_PART3_EXTENSION_LAYOUT,
    WORK_PART2_COE_LAYOUT,
    WORK_PART2_LAYOUT,
    FormLayout,
    Mark,
)

ISA_CONTENT_BASE = "https://www.moj.go.jp/isa/content"
ISA_AUTHORITY = "Immigration Services Agency of Japan (出入国在留管理庁)"
MOFA_AUTHORITY = "Ministry of Foreign Affairs of Japan (外務省)"


@dataclass(frozen=True)
class OfficialForm:
    """One official form the applicant has to file, and how to produce it."""

    code: str
    title_en: str
    title_ja: str
    procedure: str
    authority: str
    source_page_url: str
    # ``None`` for forms the ministry does not serve to automated clients (MOFA blocks
    # direct downloads); those ship as a bundled template instead.
    pdf_url: str | None
    layout: FormLayout | None
    pages: int
    # The applicant's later sheets (申請人等作成用 2 onwards), which are specific to the
    # residence status rather than shared like page 1.
    extra_layouts: tuple[FormLayout, ...] = ()
    # Digest of the published PDF the layout was authored against. A mismatch does not
    # block the download — it downgrades the fill to "layout unverified" so a revised
    # form is never written into blind coordinates.
    sha256: str | None = None
    bundled_template: str | None = None
    purpose_checkbox: Mark | None = None
    note: str | None = None
    # Items of a form filled through its AcroForm fields rather than a drawn layout,
    # as (printed item label, intake answer key). Used only to derive intake questions.
    acroform_items: tuple[tuple[str, str], ...] = ()

    @property
    def citation(self) -> dict[str, str]:
        return {
            "authority": self.authority,
            "title": f"{self.title_ja} / {self.title_en}",
            "url": self.source_page_url,
        }

    @property
    def series(self) -> str:
        return self.layout.series if self.layout is not None else ""


# ── Per-status source pages ────────────────────────────────────────────────────────
# Each page carries the three procedure forms for that residence status.
_STATUS_PAGES: dict[str, str] = {
    "work": "https://www.moj.go.jp/isa/applications/status/gijinkoku.html",
    "student": "https://www.moj.go.jp/isa/applications/status/student.html",
    "dependent": "https://www.moj.go.jp/isa/applications/status/dependent.html",
    "spouse": "https://www.moj.go.jp/isa/applications/status/spouseorchildofjapanese01.html",
    "hsp": "https://www.moj.go.jp/isa/applications/status/designatedactivities02_00004.html",
    "designated_activities": "https://www.moj.go.jp/isa/applications/status/designatedactivities02.html",
}

_STATUS_TITLES_JA: dict[str, str] = {
    "work": "技術・人文知識・国際業務",
    "student": "留学",
    "dependent": "家族滞在",
    "spouse": "日本人の配偶者等",
    "hsp": "高度専門職１号ロ",
    "designated_activities": "特定活動",
}

_STATUS_TITLES_EN: dict[str, str] = {
    "work": "Engineer / Specialist in Humanities / International Services",
    "student": "Student",
    "dependent": "Dependent",
    "spouse": "Spouse or Child of Japanese National",
    "hsp": "Highly Skilled Professional (i)(b)",
    "designated_activities": "Designated Activities",
}

# ISA content ids, per (status, procedure). Verified against the published pages; the
# store re-discovers them from the source page if a pinned id stops resolving.
_ISA_CONTENT_IDS: dict[tuple[str, str], tuple[str, str, int]] = {
    # (status, procedure): (content id, sha256 of that PDF, page count)
    ("work", "coe"): (
        "930004029",
        "62384b4f04ac715c59a798d766cd8d92ba8b3c7bd895ba2c0a20d1d3dd939e81",
        7,
    ),
    ("work", "change_of_status"): (
        "930004064",
        "c27a6c3b3e3aa4e39905a660af455abcc14e41326b13bc9537c950d6b5dd3529",
        7,
    ),
    ("work", "extension"): (
        "930004094",
        "f4a84e52db12074d9e007d0228fc8116c9f522dd6d4ad3dde920c6ee2bbecab3",
        7,
    ),
    ("student", "coe"): (
        "930004044",
        "26d918bb9957527abe0f51fe0bba8c2b7000f89cb102985242475de8a22c5cd6",
        6,
    ),
    ("student", "change_of_status"): (
        "930004076",
        "ae97f5e810444b43f8c74c0100bcc1d55ba7d7c3da6861e0ca502fc931f962af",
        6,
    ),
    ("student", "extension"): (
        "930004106",
        "bb3bc66715506e1dcd209707d44f812a0230b928ebe097e2fd58101c8b8109ce",
        6,
    ),
    ("dependent", "coe"): (
        "930004048",
        "8ea1915c90a4998767669dfac72f86eb1d78aefa7e8592940cc9aff4c767fef8",
        4,
    ),
    ("dependent", "change_of_status"): (
        "930004080",
        "250ed51e349997009ba07c400bbb5aeefdec41e1c34ce88205adbd4b354e9e28",
        4,
    ),
    ("dependent", "extension"): (
        "930004110",
        "d9e555e70774f8295403b76e0773309d92a69519a3f9ec0e1c9e5c737ab19276",
        4,
    ),
    ("spouse", "coe"): (
        "930004054",
        "d690116928bcaf345d3a93966617c85b253c4f4d7f9a7c4edd7b35129ed222fe",
        4,
    ),
    ("spouse", "change_of_status"): (
        "930004084",
        "b0d5278410f2d10d1f090cdade0c86fbf91e51cb88f1735f6f32d5a262b62338",
        4,
    ),
    ("spouse", "extension"): (
        "930004114",
        "8cce68867efbb2b915510efbca49ec4ee1917bbbb47013b57e566e45b2fac601",
        4,
    ),
    ("hsp", "coe"): (
        "930004031",
        "aa4a587dd8c40eb7f83839d991194b97e456a823b198d5fdc3ba0b926dd337f6",
        6,
    ),
    ("hsp", "change_of_status"): (
        "930004066",
        "202f59ad3c0460c6d8234db7bad0b4de1fd9e052b21a7e01036d6ae1739d3124",
        6,
    ),
    ("hsp", "extension"): (
        "930004096",
        "7310fb523b55b7871f1d5636733b7804bca1a81e83abaeb5155f51a799228197",
        6,
    ),
    ("designated_activities", "coe"): (
        "930004058",
        "90d14c4010c4fc252e261dae85c6f0eacff83be89256eee2f48a9ceca03ea372",
        6,
    ),
    ("designated_activities", "change_of_status"): (
        "930004088",
        "69e5b995a058aa7335b58636a1301f16497558e201e1ed87c94ac2aa573545c3",
        6,
    ),
    ("designated_activities", "extension"): (
        "930004118",
        "e551aa918f4329480a53974a951aa31eac05296d0a50dbbcefae68faf4a05789",
        6,
    ),
}

_PROCEDURE_TITLES: dict[str, tuple[str, str]] = {
    "coe": ("在留資格認定証明書交付申請書", "Application for Certificate of Eligibility"),
    "change_of_status": (
        "在留資格変更許可申請書",
        "Application for Change of Status of Residence",
    ),
    "extension": ("在留期間更新許可申請書", "Application for Extension of Period of Stay"),
}

# Applicant sheets beyond page 1, per (status, procedure). The extension and
# change-of-status packets carry the same 申請人等作成用 ２ sheet
# (在留期間更新・在留資格変更用); the Certificate of Eligibility packet has its own.
_EXTRA_LAYOUTS: dict[tuple[str, str], tuple[FormLayout, ...]] = {
    ("work", "coe"): (WORK_PART2_COE_LAYOUT,),
    ("work", "extension"): (WORK_PART2_LAYOUT,),
    ("work", "change_of_status"): (WORK_PART2_LAYOUT,),
    ("student", "extension"): (STUDENT_PART2_LAYOUT, STUDENT_PART3_EXTENSION_LAYOUT),
    ("student", "change_of_status"): (STUDENT_PART2_LAYOUT,),
    ("dependent", "extension"): (DEPENDENT_PART2_LAYOUT,),
    ("dependent", "change_of_status"): (DEPENDENT_PART2_LAYOUT,),
    ("spouse", "coe"): (SPOUSE_PART2_LAYOUT,),
    ("spouse", "extension"): (SPOUSE_PART2_LAYOUT, SPOUSE_PART3_LAYOUT),
    ("spouse", "change_of_status"): (SPOUSE_PART2_LAYOUT, SPOUSE_PART3_LAYOUT),
}


_PROCEDURE_LAYOUTS: dict[str, FormLayout] = {
    "coe": COE_LAYOUT,
    "change_of_status": CHANGE_LAYOUT,
    "extension": EXTENSION_LAYOUT,
}


def _isa_form(status: str, procedure: str) -> OfficialForm | None:
    entry = _ISA_CONTENT_IDS.get((status, procedure))
    if entry is None:
        return None
    content_id, digest, pages = entry
    title_ja, title_en = _PROCEDURE_TITLES[procedure]
    layout = _PROCEDURE_LAYOUTS[procedure]
    extra = _EXTRA_LAYOUTS.get((status, procedure), ())
    return OfficialForm(
        code=f"jp_{status}_{procedure}",
        title_en=f"{title_en} — {_STATUS_TITLES_EN[status]}",
        title_ja=f"{title_ja}（{_STATUS_TITLES_JA[status]}）",
        procedure=procedure,
        authority=ISA_AUTHORITY,
        source_page_url=_STATUS_PAGES[status],
        pdf_url=f"{ISA_CONTENT_BASE}/{content_id}.pdf",
        layout=layout,
        pages=pages,
        sha256=digest,
        extra_layouts=extra,
        purpose_checkbox=layout.purpose_checkboxes.get(status) if procedure == "coe" else None,
        note=(
            "The 特定活動 series covers several designations. The applicant part is "
            "identical across them, but the organisation part behind it is not, and the "
            "purpose-of-entry box is left for you to tick with your own designation."
            if status == "designated_activities"
            else None
        ),
    )


PERMANENT_RESIDENCE_FORM = OfficialForm(
    code="jp_permanent_residence",
    title_en="Application for Permanent Residence",
    title_ja="永住許可申請書",
    procedure="permanent_residence",
    authority=ISA_AUTHORITY,
    source_page_url="https://www.moj.go.jp/isa/applications/procedures/16-4.html",
    pdf_url=f"{ISA_CONTENT_BASE}/930002835.pdf",
    layout=PERMANENT_RESIDENCE_LAYOUT,
    pages=2,
    sha256="5129c9636092d13538f25fab681d6730e7d5d871561ae34fab0542083b85da1f",
)

CONSULAR_VISA_FORM = OfficialForm(
    code="jp_consular_visa",
    title_en="Visa Application Form to Enter Japan",
    title_ja="日本国査証申請書",
    procedure=PROCEDURE_CONSULAR_VISA,
    authority=MOFA_AUTHORITY,
    source_page_url="https://www.mofa.go.jp/j_info/visit/visa/index.html",
    # MOFA rejects automated downloads (HTTP 403), so this one ships with the service.
    pdf_url=None,
    layout=None,
    pages=2,
    bundled_template="japan_visa_application_form_template.pdf",
    note="Filed at a Japanese embassy or consulate; this template carries fillable fields.",
    acroform_items=(
        ("Surname / given names", "full_name"),
        ("Date of birth", "date_of_birth"),
        ("Place of birth", "place_of_birth"),
        ("Sex", "sex"),
        ("Marital status", "marital_status"),
        ("Nationality or citizenship", "nationality"),
        ("Passport type", "passport_type"),
        ("Passport No.", "passport_number"),
        ("Date of issue", "passport_issue_date"),
        ("Place of issue", "passport_issue_place"),
        ("Issuing authority", "passport_issuing_authority"),
        ("Date of expiry", "passport_expiry_date"),
        ("Purpose of visit to Japan", "purpose_of_visit"),
        ("Intended length of stay in Japan", "intended_length_of_stay"),
        ("Date of arrival in Japan", "planned_arrival_date"),
        ("Port of entry into Japan", "port_of_entry"),
        ("Name of ship or airline", "airline_flight_no"),
        ("Name of hotel or person you will stay with", "accommodation_name"),
        ("Tel. of hotel or person you will stay with", "accommodation_tel"),
        ("Address of hotel or person you will stay with", "accommodation_address"),
        ("Your current residential address", "current_address"),
        ("Tel.", "telephone_japan"),
        ("Mobile No.", "mobile_phone"),
        ("Current profession or occupation and position", "occupation"),
        ("Name of employer", "employer_name"),
        ("Tel. of employer", "employer_tel"),
        ("Address of employer", "employer_address"),
        ("Guarantor or reference in Japan — name", "resident_guarantor_name"),
        ("Guarantor or reference in Japan — tel.", "guarantor_telephone"),
        ("Guarantor or reference in Japan — address", "guarantor_address"),
        ("Guarantor or reference in Japan — relationship", "relationship_to_supporter"),
        ("Inviter in Japan — name", "inviter_name"),
        ("Inviter in Japan — tel.", "inviter_tel"),
        ("Inviter in Japan — address", "inviter_address"),
        ("Have you ever been convicted of a crime or offence in any country?", "criminal_record"),
        (
            "Have you ever been sentenced to imprisonment for 1 year or more?",
            "imprisoned_one_year_or_more",
        ),
        (
            "Have you ever been deported or removed from Japan or any country?",
            "prior_deportation",
        ),
        (
            "Have you ever been convicted and sentenced for a drug offence?",
            "drug_offence_conviction",
        ),
        ("Have you ever engaged in or facilitated prostitution?", "prostitution_involvement"),
        (
            "Have you ever committed, incited or aided trafficking in persons?",
            "human_trafficking_involvement",
        ),
    ),
)


def _scope_forms(visa_category: str, action: str) -> tuple[OfficialForm, ...]:
    category = (visa_category or "").lower()
    act = (action or "").lower()
    if act == "new":
        act = "new_application"

    if category == "permanent_resident":
        return (PERMANENT_RESIDENCE_FORM,)

    # Categories this catalogue does not cover get nothing rather than a near-miss.
    if category not in _STATUS_PAGES and category != "tourist":
        return ()

    if category == "tourist":
        # A short stay is granted at the border on a consular visa; the ISA residence
        # forms do not apply to it.
        return (CONSULAR_VISA_FORM,) if act == "new_application" else ()

    if act == "new_application":
        # Filing from abroad is two steps: the ISA certificate first, then the consular
        # visa that the certificate unlocks. Both forms belong to the packet.
        coe = _isa_form(category, "coe")
        return tuple(form for form in (coe, CONSULAR_VISA_FORM) if form is not None)
    if act == "change_of_status":
        form = _isa_form(category, "change_of_status")
        return (form,) if form is not None else ()
    if act == "renewal":
        form = _isa_form(category, "extension")
        return (form,) if form is not None else ()
    return ()


def forms_for_scope(visa_category: str, action: str) -> tuple[OfficialForm, ...]:
    """Official forms for a (visa category, action) scope, most important first."""
    return _scope_forms(visa_category, action)


def primary_form_for_scope(visa_category: str, action: str) -> OfficialForm | None:
    forms = forms_for_scope(visa_category, action)
    return forms[0] if forms else None


# ── Intake questions derived from the official forms ───────────────────────────────
# Every field the layouts can fill needs an answer. These specs are the questions the
# applicant is asked for them; keys already used by docs/jurisdictions/jp/*.yml are
# reused verbatim so a pack-authored question and its form field stay one question.

# Plain-language section titles. These are what the applicant reads, so they never
# mention "the official form" — every question in intake is for the official form, and
# saying so in a heading only makes the block look like an optional appendix. Where a
# scope's own pack already has a section covering the same ground, `merge_form_questions`
# folds these into it so intake stays one flow instead of two.
# Answer keys a form field may be filled from when its own key is unanswered.
#
# Every entry must be a *different name for the same fact*, never a related one. The
# applicant signs this form, so a near-enough substitution is a false statement: a
# guarantor's telephone is not theirs, a hotel is not their residence, a country of
# citizenship is not a city of birth, and the status they are applying for is not their
# reason for applying. Anything not the same fact stays blank and gets asked in intake.
#
# This table does double duty. The filler reads it to resolve a value, and
# `merge_form_questions` reads it to avoid asking a question the pack already asks under
# another name — without it, a pack asking `passport_expiry` still got a second question
# for `passport_expiry_date`.
ANSWER_ALIASES: dict[str, tuple[str, ...]] = {
    "nationality": ("visitor_nationality", "country_of_citizenship"),
    "full_name": ("applicant_name", "visitor_full_name"),
    "passport_expiry_date": ("passport_expiry",),
    "current_japan_address": ("registered_address_japan",),
    "telephone_japan": ("phone_number",),
    "mobile_phone": ("phone_number",),
    "current_status_of_residence": ("current_visa_status",),
    "current_status_expiry_date": ("current_stay_expiry_date", "residence_card_expiry"),
    "current_period_of_stay": ("current_period_of_stay_years",),
    "intended_entry_date": ("planned_arrival_date",),
    "intended_length_of_stay": ("intended_length_of_stay_days", "stay_duration_days"),
    "occupation": ("job_title",),
    "reason_for_extension": ("extension_explanation_details",),
    "criminal_record": ("criminal_record_any", "criminal_disclosures"),
    "desired_period_of_stay": ("desired_extension_days",),
}


_SECTION_IDENTITY = "Your details"
_SECTION_CONTACT = "Address & contact"
_SECTION_EMPLOYMENT = "Work & employer"
_SECTION_EDUCATION = "Education & qualifications"
_SECTION_FUNDING = "How your stay is paid for"
_SECTION_SPONSOR = "Guarantor or inviter in Japan"
_SECTION_STATUS = "Your current status in Japan"
_SECTION_REQUEST = "What you are applying for"
_SECTION_HISTORY = "Declarations & history"

# A pack section absorbs one of the groups above when its title contains one of these
# tokens. Tokens are chosen to be distinctive: "travel" would match both a pack's
# "Travel & Itinerary" and its "Travel & Disclosures", so neither group claims it.
_SECTION_ABSORPTION: tuple[tuple[str, tuple[str, ...]], ...] = (
    (_SECTION_IDENTITY, ("identity", "personal", "biographic", "about you")),
    (_SECTION_CONTACT, ("address", "contact")),
    (_SECTION_EMPLOYMENT, ("employer", "employment", "income", "salary")),
    (_SECTION_EDUCATION, ("education", "school", "study", "qualification")),
    (_SECTION_FUNDING, ("funding", "financial", "solvency", "money", "expenses")),
    (_SECTION_SPONSOR, ("guarantor", "sponsor", "inviter", "supporter")),
    (_SECTION_STATUS, ("residence card", "status of residence", "current status")),
    (_SECTION_REQUEST, ("itinerary", "purpose", "applying")),
    (_SECTION_HISTORY, ("disclosure", "declaration", "security", "criminal")),
)

# Order the groups appear in when a scope's pack has no section to fold them into.
_SECTION_FALLBACK_ORDER: tuple[str, ...] = (
    _SECTION_IDENTITY,
    _SECTION_CONTACT,
    _SECTION_EMPLOYMENT,
    _SECTION_EDUCATION,
    _SECTION_FUNDING,
    _SECTION_SPONSOR,
    _SECTION_STATUS,
    _SECTION_REQUEST,
    _SECTION_HISTORY,
)


@dataclass(frozen=True)
class QuestionSpec:
    prompt: str
    type: str
    section: str
    options: tuple[str, ...] = ()
    max_length: int | None = None
    min_length: int | None = None
    # Nothing derived from a form is intake-blocking: the packs decide what gates
    # completion, and a half-answered official form is still worth producing.
    required: bool = False


QUESTION_SPECS: dict[str, QuestionSpec] = {
    "nationality": QuestionSpec(
        "What is your nationality or region, exactly as printed in your passport?",
        "string",
        _SECTION_IDENTITY,
        min_length=2,
        max_length=64,
    ),
    "date_of_birth": QuestionSpec(
        "What is your date of birth (YYYY-MM-DD)?", "date", _SECTION_IDENTITY
    ),
    "full_name": QuestionSpec(
        "What is your full name as shown in your passport (family name first)?",
        "string",
        _SECTION_IDENTITY,
        min_length=2,
        max_length=200,
    ),
    "sex": QuestionSpec(
        "What sex is recorded on your passport?",
        "enum",
        _SECTION_IDENTITY,
        options=("male", "female"),
    ),
    "place_of_birth": QuestionSpec(
        "Where were you born (city and country)?",
        "string",
        _SECTION_IDENTITY,
        min_length=2,
        max_length=120,
    ),
    "marital_status": QuestionSpec(
        "What is your marital status?",
        "enum",
        _SECTION_IDENTITY,
        options=("single", "married"),
    ),
    "occupation": QuestionSpec(
        "What is your occupation or position?",
        "string",
        _SECTION_IDENTITY,
        min_length=2,
        max_length=100,
    ),
    "home_town_city": QuestionSpec(
        "What is your home town or city in your country of nationality?",
        "string",
        _SECTION_CONTACT,
        min_length=2,
        max_length=160,
    ),
    "current_japan_address": QuestionSpec(
        "What is your address in Japan (or your contact address in Japan if you are abroad)?",
        "string",
        _SECTION_CONTACT,
        min_length=2,
        max_length=200,
    ),
    "telephone_japan": QuestionSpec(
        "What telephone number should the immigration office use?",
        "string",
        _SECTION_CONTACT,
        max_length=40,
    ),
    "mobile_phone": QuestionSpec(
        "What is your cellular phone number?", "string", _SECTION_CONTACT, max_length=40
    ),
    "passport_number": QuestionSpec(
        "What is your passport number?",
        "string",
        _SECTION_IDENTITY,
        min_length=4,
        max_length=32,
    ),
    "passport_expiry_date": QuestionSpec(
        "When does your passport expire (YYYY-MM-DD)?", "date", _SECTION_IDENTITY
    ),
    "current_status_of_residence": QuestionSpec(
        "What status of residence do you currently hold?",
        "string",
        _SECTION_STATUS,
        max_length=80,
    ),
    "current_period_of_stay": QuestionSpec(
        "What period of stay was granted (for example 1 year, 3 years)?",
        "string",
        _SECTION_STATUS,
        max_length=40,
    ),
    "current_status_expiry_date": QuestionSpec(
        "When does your current period of stay expire (YYYY-MM-DD)?", "date", _SECTION_STATUS
    ),
    "residence_card_number": QuestionSpec(
        "What is your residence card number?", "string", _SECTION_STATUS, max_length=24
    ),
    "desired_status_of_residence": QuestionSpec(
        "Which status of residence are you applying to change to?",
        "string",
        _SECTION_REQUEST,
        max_length=80,
    ),
    "desired_period_of_stay": QuestionSpec(
        "What period of stay are you requesting (for example 1 year, 3 years, 5 years)?",
        "string",
        _SECTION_REQUEST,
        max_length=40,
    ),
    "reason_for_extension": QuestionSpec(
        "Why do you need to extend your stay?", "string", _SECTION_REQUEST, max_length=200
    ),
    "change_reason": QuestionSpec(
        "Why are you changing your status of residence?",
        "string",
        _SECTION_REQUEST,
        max_length=200,
    ),
    "pr_reason": QuestionSpec(
        "Why are you applying for permanent residence?",
        "string",
        _SECTION_REQUEST,
        max_length=200,
    ),
    "intended_entry_date": QuestionSpec(
        "On what date do you plan to enter Japan (YYYY-MM-DD)?", "date", _SECTION_REQUEST
    ),
    "port_of_entry": QuestionSpec(
        "Through which port do you plan to enter Japan (for example Narita, Haneda, Kansai)?",
        "string",
        _SECTION_REQUEST,
        max_length=80,
    ),
    "intended_length_of_stay": QuestionSpec(
        "How long do you intend to stay in Japan (for example 90 days, 1 year, 3 years)?",
        "string",
        _SECTION_REQUEST,
        max_length=40,
    ),
    "intended_visa_application_place": QuestionSpec(
        "At which Japanese embassy or consulate will you apply for the visa?",
        "string",
        _SECTION_REQUEST,
        max_length=120,
    ),
    "has_accompanying_persons": QuestionSpec(
        "Will anyone travel with you as an accompanying person?", "boolean", _SECTION_REQUEST
    ),
    "previous_japan_visits": QuestionSpec(
        "Have you entered or departed Japan before?", "boolean", _SECTION_HISTORY
    ),
    "prior_coe_applications": QuestionSpec(
        "Have you applied for a Certificate of Eligibility before?", "boolean", _SECTION_HISTORY
    ),
    "criminal_record": QuestionSpec(
        "Have you ever been subject to a criminal disposition, in Japan or overseas "
        "(including traffic offences)?",
        "boolean",
        _SECTION_HISTORY,
    ),
    "criminal_record_detail": QuestionSpec(
        "If you answered yes above, describe the disposition.",
        "string",
        _SECTION_HISTORY,
        max_length=200,
    ),
    "prior_deportation": QuestionSpec(
        "Have you ever been deported from Japan or left under a departure order?",
        "boolean",
        _SECTION_HISTORY,
    ),
    "has_family_in_japan": QuestionSpec(
        "Do you have family in Japan, or anyone you currently live with there?",
        "boolean",
        _SECTION_HISTORY,
    ),
    # Consular visa form (MOFA) items beyond the residence forms.
    "passport_type": QuestionSpec(
        "What type of passport do you hold?",
        "enum",
        _SECTION_IDENTITY,
        options=("ordinary", "official", "diplomatic", "other"),
    ),
    "passport_issue_date": QuestionSpec(
        "When was your passport issued (YYYY-MM-DD)?", "date", _SECTION_IDENTITY
    ),
    "passport_issue_place": QuestionSpec(
        "Where was your passport issued?", "string", _SECTION_IDENTITY, max_length=120
    ),
    "passport_issuing_authority": QuestionSpec(
        "Which authority issued your passport?", "string", _SECTION_IDENTITY, max_length=120
    ),
    "purpose_of_visit": QuestionSpec(
        "What is the purpose of your visit to Japan?",
        "string",
        _SECTION_REQUEST,
        max_length=120,
    ),
    "planned_arrival_date": QuestionSpec(
        "On what date do you plan to arrive in Japan (YYYY-MM-DD)?", "date", _SECTION_REQUEST
    ),
    "airline_flight_no": QuestionSpec(
        "Which ship or airline will you arrive on?", "string", _SECTION_REQUEST, max_length=80
    ),
    "accommodation_name": QuestionSpec(
        "What is the name of the hotel or the person you will stay with in Japan?",
        "string",
        _SECTION_CONTACT,
        max_length=160,
    ),
    "accommodation_tel": QuestionSpec(
        "What is their telephone number in Japan?", "string", _SECTION_CONTACT, max_length=40
    ),
    "accommodation_address": QuestionSpec(
        "What is their address in Japan?", "string", _SECTION_CONTACT, max_length=200
    ),
    "current_address": QuestionSpec(
        "What is your current residential address?",
        "string",
        _SECTION_CONTACT,
        max_length=200,
    ),
    "employer_name": QuestionSpec(
        "What is the name of your employer?", "string", _SECTION_EMPLOYMENT, max_length=160
    ),
    "employer_tel": QuestionSpec(
        "What is your employer's telephone number?", "string", _SECTION_EMPLOYMENT, max_length=40
    ),
    "employer_address": QuestionSpec(
        "What is your employer's address?", "string", _SECTION_EMPLOYMENT, max_length=200
    ),
    "resident_guarantor_name": QuestionSpec(
        "Who is your guarantor or reference in Japan?",
        "string",
        _SECTION_SPONSOR,
        max_length=160,
    ),
    "guarantor_telephone": QuestionSpec(
        "What is your guarantor's telephone number?", "string", _SECTION_SPONSOR, max_length=40
    ),
    "guarantor_address": QuestionSpec(
        "What is your guarantor's address in Japan?", "string", _SECTION_SPONSOR, max_length=200
    ),
    "relationship_to_supporter": QuestionSpec(
        "What is your guarantor's relationship to you?",
        "string",
        _SECTION_SPONSOR,
        max_length=80,
    ),
    "inviter_name": QuestionSpec(
        "Who is inviting you to Japan, if anyone (write the same name if it is your guarantor)?",
        "string",
        _SECTION_SPONSOR,
        max_length=160,
    ),
    "inviter_tel": QuestionSpec(
        "What is the inviter's telephone number?", "string", _SECTION_SPONSOR, max_length=40
    ),
    "inviter_address": QuestionSpec(
        "What is the inviter's address in Japan?", "string", _SECTION_SPONSOR, max_length=200
    ),
    # The consular form's six sworn declarations. Each is a separate question because
    # each is a separate box the applicant signs under.
    "imprisoned_one_year_or_more": QuestionSpec(
        "Have you ever been sentenced to imprisonment for one year or more in any country?",
        "boolean",
        _SECTION_HISTORY,
    ),
    "drug_offence_conviction": QuestionSpec(
        "Have you ever been convicted and sentenced for a drug offence in any country?",
        "boolean",
        _SECTION_HISTORY,
    ),
    "prostitution_involvement": QuestionSpec(
        "Have you ever engaged in, solicited or facilitated prostitution?",
        "boolean",
        _SECTION_HISTORY,
    ),
    "human_trafficking_involvement": QuestionSpec(
        "Have you ever committed, incited or aided trafficking in persons?",
        "boolean",
        _SECTION_HISTORY,
    ),
    # Applicant part 2 (申請人等作成用 ２) — the residence-status-specific sheet behind
    # page 1, which asks about the workplace, education and qualifications in detail.
    "employer_branch_name": QuestionSpec(
        "Which branch or office do you work at, if not the head office?",
        "string",
        _SECTION_EMPLOYMENT,
        max_length=160,
    ),
    "final_school_name": QuestionSpec(
        "What is the name of the last school you attended (or attend now)?",
        "string",
        _SECTION_EDUCATION,
        max_length=160,
    ),
    "graduation_date": QuestionSpec(
        "When did you graduate (YYYY-MM-DD)?", "date", _SECTION_EDUCATION
    ),
    "has_it_qualification": QuestionSpec(
        "Do you hold an information-technology qualification, or have you passed a "
        "certifying examination? (only asked of applicants working in IT)",
        "boolean",
        _SECTION_EDUCATION,
    ),
    "it_qualification_name": QuestionSpec(
        "What is the name of that qualification or examination?",
        "string",
        _SECTION_EDUCATION,
        max_length=160,
    ),
    "school_name": QuestionSpec(
        "What is the name of the school you attend in Japan?",
        "string",
        _SECTION_EDUCATION,
        max_length=160,
    ),
    "supporter_name": QuestionSpec(
        "Who pays for your living costs in Japan?", "string", _SECTION_FUNDING, max_length=160
    ),
    "school_address": QuestionSpec(
        "What is the address of the school you attend?",
        "string",
        _SECTION_EDUCATION,
        max_length=200,
    ),
    "school_tel": QuestionSpec(
        "What is the school's telephone number?", "string", _SECTION_EDUCATION, max_length=40
    ),
    "total_years_of_education": QuestionSpec(
        "How many years of education have you completed in total, from primary school to "
        "your last institution?",
        "integer",
        _SECTION_EDUCATION,
    ),
    "japanese_test_name": QuestionSpec(
        "Which Japanese language test have you taken, if any (for example JLPT)?",
        "string",
        _SECTION_EDUCATION,
        max_length=80,
    ),
    "japanese_test_score": QuestionSpec(
        "What level or score did you attain?", "string", _SECTION_EDUCATION, max_length=40
    ),
    "japanese_school_name": QuestionSpec(
        "Which institution gave you Japanese language education, if any?",
        "string",
        _SECTION_EDUCATION,
        max_length=160,
    ),
    "japanese_study_from": QuestionSpec(
        "When did that Japanese language education start (YYYY-MM-DD)?",
        "date",
        _SECTION_EDUCATION,
    ),
    "japanese_study_to": QuestionSpec("When did it end (YYYY-MM-DD)?", "date", _SECTION_EDUCATION),
    "support_self_monthly_jpy": QuestionSpec(
        "How much of your monthly costs in Japan do you pay yourself (yen)?",
        "integer",
        _SECTION_FUNDING,
    ),
    "support_overseas_supporter_monthly_jpy": QuestionSpec(
        "How much does a supporter living outside Japan pay each month (yen)?",
        "integer",
        _SECTION_FUNDING,
    ),
    "support_japan_supporter_monthly_jpy": QuestionSpec(
        "How much does a supporter in Japan pay each month (yen)?",
        "integer",
        _SECTION_FUNDING,
    ),
    "scholarship_monthly_jpy": QuestionSpec(
        "How much scholarship do you receive each month (yen)?", "integer", _SECTION_FUNDING
    ),
    "funds_carried_jpy": QuestionSpec(
        "How much money will you carry into Japan yourself (yen)?", "integer", _SECTION_FUNDING
    ),
    "funds_remitted_jpy": QuestionSpec(
        "How much will be remitted to you from abroad (yen)?", "integer", _SECTION_FUNDING
    ),
    "supporter_address": QuestionSpec(
        "What is your supporter's address?", "string", _SECTION_FUNDING, max_length=200
    ),
    "supporter_tel": QuestionSpec(
        "What is your supporter's telephone number?", "string", _SECTION_FUNDING, max_length=40
    ),
    "supporter_occupation": QuestionSpec(
        "What is your supporter's occupation and place of employment?",
        "string",
        _SECTION_FUNDING,
        max_length=160,
    ),
    "supporter_employer_tel": QuestionSpec(
        "What is their employer's telephone number?", "string", _SECTION_FUNDING, max_length=40
    ),
    "supporter_annual_income_jpy": QuestionSpec(
        "What is your supporter's annual income (yen)?", "integer", _SECTION_FUNDING
    ),
    "works_outside_status": QuestionSpec(
        "Are you working, or planning to work, outside what your current status permits "
        "(for example a part-time job on a Student status)?",
        "boolean",
        _SECTION_EMPLOYMENT,
    ),
    "part_time_work_type": QuestionSpec(
        "What kind of work is it?", "string", _SECTION_EMPLOYMENT, max_length=160
    ),
    "part_time_employer_name": QuestionSpec(
        "Where do you work?", "string", _SECTION_EMPLOYMENT, max_length=160
    ),
    "part_time_employer_tel": QuestionSpec(
        "What is that employer's telephone number?", "string", _SECTION_EMPLOYMENT, max_length=40
    ),
    "part_time_weekly_hours": QuestionSpec(
        "How many hours a week do you work?", "integer", _SECTION_EMPLOYMENT
    ),
    "part_time_salary_jpy": QuestionSpec("What is the pay (yen)?", "integer", _SECTION_EMPLOYMENT),
    "guardian_name": QuestionSpec(
        "If you are at primary or junior high school, who is your guardian in Japan?",
        "string",
        _SECTION_SPONSOR,
        max_length=160,
    ),
    "guardian_relationship": QuestionSpec(
        "What is their relationship to you?", "string", _SECTION_SPONSOR, max_length=80
    ),
    "guardian_address": QuestionSpec(
        "What is their address in Japan?", "string", _SECTION_SPONSOR, max_length=200
    ),
    "guardian_tel": QuestionSpec(
        "What is their telephone number?", "string", _SECTION_SPONSOR, max_length=40
    ),
    "guardian_mobile": QuestionSpec(
        "What is their mobile number?", "string", _SECTION_SPONSOR, max_length=40
    ),
    "legal_representative_mobile": QuestionSpec(
        "What is the legal representative's mobile number?",
        "string",
        _SECTION_SPONSOR,
        max_length=40,
    ),
    "family_notification_place_japan": QuestionSpec(
        "Where in Japan was your marriage, birth or adoption registered?",
        "string",
        _SECTION_SPONSOR,
        max_length=160,
    ),
    "family_notification_date_japan": QuestionSpec(
        "On what date was it registered in Japan (YYYY-MM-DD)?", "date", _SECTION_SPONSOR
    ),
    "family_notification_place_home": QuestionSpec(
        "Where in your home country was it registered?",
        "string",
        _SECTION_SPONSOR,
        max_length=160,
    ),
    "family_notification_date_home": QuestionSpec(
        "On what date was it registered there (YYYY-MM-DD)?", "date", _SECTION_SPONSOR
    ),
    "part_time_employer_branch": QuestionSpec(
        "Which branch or office of that employer?", "string", _SECTION_EMPLOYMENT, max_length=160
    ),
    "annual_income_jpy": QuestionSpec(
        "What is your own annual income (yen)?", "integer", _SECTION_FUNDING
    ),
    "support_guarantor_monthly_jpy": QuestionSpec(
        "How much does a guarantor pay each month (yen)?", "integer", _SECTION_FUNDING
    ),
    "support_other_monthly_jpy": QuestionSpec(
        "How much comes from any other source each month (yen)?", "integer", _SECTION_FUNDING
    ),
    "funds_carrier_name": QuestionSpec(
        "Who will carry that money into Japan?", "string", _SECTION_FUNDING, max_length=160
    ),
    "funds_carry_date": QuestionSpec(
        "When will they carry it (YYYY-MM-DD)?", "date", _SECTION_FUNDING
    ),
    "funds_other_jpy": QuestionSpec(
        "How much comes from any other source (yen)?", "integer", _SECTION_FUNDING
    ),
    "supporter_date_of_birth": QuestionSpec(
        "What is your supporter's date of birth (YYYY-MM-DD)?", "date", _SECTION_FUNDING
    ),
    "supporter_nationality": QuestionSpec(
        "What is your supporter's nationality?", "string", _SECTION_FUNDING, max_length=64
    ),
    "supporter_residence_card_number": QuestionSpec(
        "What is your supporter's residence card number?",
        "string",
        _SECTION_FUNDING,
        max_length=24,
    ),
    "supporter_status_of_residence": QuestionSpec(
        "What status of residence does your supporter hold?",
        "string",
        _SECTION_FUNDING,
        max_length=80,
    ),
    "supporter_period_of_stay": QuestionSpec(
        "What period of stay were they granted?", "string", _SECTION_FUNDING, max_length=40
    ),
    "supporter_status_expiry_date": QuestionSpec(
        "When does their period of stay expire (YYYY-MM-DD)?", "date", _SECTION_FUNDING
    ),
    "supporter_employer_name": QuestionSpec(
        "Where does your supporter work?", "string", _SECTION_FUNDING, max_length=160
    ),
    "supporter_employer_branch": QuestionSpec(
        "Which branch or office?", "string", _SECTION_FUNDING, max_length=160
    ),
    "supporter_employer_address": QuestionSpec(
        "What is their employer's address?", "string", _SECTION_FUNDING, max_length=200
    ),
    "guarantor_occupation": QuestionSpec(
        "What is your guarantor's occupation?", "string", _SECTION_SPONSOR, max_length=160
    ),
    "guarantor_mobile": QuestionSpec(
        "What is your guarantor's mobile number?", "string", _SECTION_SPONSOR, max_length=40
    ),
    "has_legal_representative": QuestionSpec(
        "Is a legal representative filing this application on your behalf?",
        "boolean",
        _SECTION_SPONSOR,
    ),
    "legal_representative_name": QuestionSpec(
        "If a legal representative is filing for you, what is their name?",
        "string",
        _SECTION_SPONSOR,
        max_length=160,
    ),
    "legal_representative_relationship": QuestionSpec(
        "What is their relationship to you?", "string", _SECTION_SPONSOR, max_length=80
    ),
    "legal_representative_address": QuestionSpec(
        "What is their address?", "string", _SECTION_SPONSOR, max_length=200
    ),
    "legal_representative_tel": QuestionSpec(
        "What is their telephone number?", "string", _SECTION_SPONSOR, max_length=40
    ),
}


def _question_dict(
    key: str,
    form: OfficialForm,
    item: str,
    label: str,
    depends_on: str | None = None,
) -> dict[str, Any] | None:
    spec = QUESTION_SPECS.get(key)
    if spec is None:
        return None
    reference = f"item {item} ({label})" if item else label
    # Says why the question exists and what skipping it costs. Without this an
    # unanswered question reads as merely optional, and the box prints blank on a sheet
    # the applicant then signs.
    where = f"Item {item} of your {form.title_ja}" if item else f"Asked on your {form.title_ja}"
    question: dict[str, Any] = {
        "key": key,
        "prompt": spec.prompt,
        "type": spec.type,
        "required": spec.required,
        "section": spec.section,
        "hint": f"{where}. Leave it blank and that box prints empty.",
        "citation": {
            "authority": form.authority,
            "title": f"{form.title_ja} — {reference}",
            "url": form.source_page_url,
        },
    }
    if spec.options:
        question["options"] = list(spec.options)
    if spec.min_length is not None:
        question["min_length"] = spec.min_length
    if spec.max_length is not None:
        question["max_length"] = spec.max_length
    if depends_on:
        # Carried raw; `merge_form_questions` turns it into a `show_when` pointing at the
        # key the scope's intake actually uses for that fact.
        question["_depends_on"] = depends_on
    return question


def intake_questions_for_form(form: OfficialForm) -> list[dict[str, Any]]:
    """The intake questions needed to fill every item of ``form``, in form order."""
    questions: list[dict[str, Any]] = []
    seen: set[str] = set()
    ordered: list[tuple[str, str, str, str | None]] = []
    if form.layout is not None:
        for layout in (form.layout, *form.extra_layouts):
            ordered.extend(
                (line.key, line.item, line.label, line.depends_on) for line in layout.lines
            )
            ordered.extend((c.key, c.item, c.label, None) for c in layout.choices)
    else:
        ordered = [(key, "", label, None) for label, key in form.acroform_items]
    for key, item, label, depends_on in ordered:
        if key in seen:
            continue
        seen.add(key)
        question = _question_dict(key, form, item, label, depends_on)
        if question is not None:
            questions.append(question)
    return questions


def intake_questions_for_scope(visa_category: str, action: str) -> list[dict[str, Any]]:
    """Form-derived intake questions for a scope, deduplicated across its forms."""
    questions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for form in forms_for_scope(visa_category, action):
        for question in intake_questions_for_form(form):
            if question["key"] in seen:
                continue
            seen.add(question["key"])
            questions.append(question)
    return questions


def already_asked(form_key: str, pack_keys: set[str]) -> bool:
    """Whether the pack already asks for the fact behind ``form_key``.

    Matching on the key alone is not enough: a pack asking ``passport_expiry`` covers the
    form's ``passport_expiry_date``, and one asking ``criminal_disclosures`` covers
    ``criminal_record``. Those are the same question under another name, and asking twice
    is what made the merged intake look duplicated. Only the aliases the filler would
    actually resolve from count — one hop, no transitive closure, so ``telephone_japan``
    and ``mobile_phone`` never collapse into each other just because both can fall back
    to ``phone_number``.
    """
    if form_key in pack_keys:
        return True
    return any(alias in pack_keys for alias in ANSWER_ALIASES.get(form_key, ()))


def _asked_as(form_key: str, pack_keys: set[str]) -> str:
    """The key this scope's intake actually uses for the fact behind ``form_key``.

    ``jp/work.renewal`` asks ``criminal_disclosures`` where the form calls it
    ``criminal_record``, so a follow-up conditional on the disclosure has to point at the
    pack's key or it would never fire.
    """
    if form_key in pack_keys:
        return form_key
    for alias in ANSWER_ALIASES.get(form_key, ()):
        if alias in pack_keys:
            return alias
    return form_key


def _absorbing_section(pack_section_titles: list[str], group: str) -> str:
    """The pack's own section covering ``group``, or ``group`` itself if it has none."""
    tokens = next((t for section, t in _SECTION_ABSORPTION if section == group), ())
    for title in pack_section_titles:
        lowered = title.lower()
        if any(token in lowered for token in tokens):
            return title
    return group


def merge_form_questions(
    pack_questions: list[dict[str, Any]],
    visa_category: str,
    action: str,
) -> list[dict[str, Any]]:
    """Fold the official form's remaining questions into a scope's intake.

    Pack-authored questions are never reordered or reworded — they carry the scope's own
    citations and its ``required`` gating, and moving one could place it ahead of a
    question its ``show_when`` depends on, which would prune the answer. Form-derived
    questions are *inserted* after the last pack question of the section that covers the
    same ground, so intake reads as one flow rather than a form appendix bolted on the
    end. Questions with no matching pack section are grouped at the end in a fixed order.

    They stay non-blocking on purpose: a case already part-way through intake must not
    become incompletable. Each carries a ``hint`` naming the form item it fills so
    skipping one is an informed choice rather than an invisible blank.
    """
    pack_keys = {
        str(question.get("key"))
        for question in pack_questions
        if isinstance(question, dict) and question.get("key")
    }
    pack_section_titles: list[str] = []
    for question in pack_questions:
        title = str(question.get("section") or "")
        if title and title not in pack_section_titles:
            pack_section_titles.append(title)

    # Group the outstanding form questions under the section that will hold them.
    by_section: dict[str, list[dict[str, Any]]] = {}
    seen: set[str] = set()
    for question in intake_questions_for_scope(visa_category, action):
        key = question["key"]
        if key in seen or already_asked(key, pack_keys):
            continue
        seen.add(key)
        target = _absorbing_section(pack_section_titles, str(question["section"]))
        placed = dict(question)
        placed["section"] = target
        dependency = placed.pop("_depends_on", None)
        if dependency:
            # Show the follow-up only when the disclosure it belongs to is affirmative,
            # against whichever key this scope's intake uses for it. Without this the
            # "if you answered yes above" question appears even after a "no".
            placed["show_when"] = {"key": _asked_as(str(dependency), pack_keys), "equals": True}
        by_section.setdefault(target, []).append(placed)

    if not by_section:
        return list(pack_questions)

    # Where each pack section ends, so an insert lands after all of its questions.
    last_index_of: dict[str, int] = {}
    for index, question in enumerate(pack_questions):
        title = str(question.get("section") or "")
        if title:
            last_index_of[title] = index

    merged: list[dict[str, Any]] = []
    for index, question in enumerate(pack_questions):
        merged.append(question)
        title = str(question.get("section") or "")
        if title and last_index_of.get(title) == index and title in by_section:
            merged.extend(by_section.pop(title))

    for group in _SECTION_FALLBACK_ORDER:
        if group in by_section:
            merged.extend(by_section.pop(group))
    for remaining in by_section.values():  # any section title we did not anticipate
        merged.extend(remaining)
    return merged
