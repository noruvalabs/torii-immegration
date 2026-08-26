"""Field geometry for the four official Japanese application-form families.

The Ministry of Justice publishes one form template per procedure, reused across every
residence status: the applicant part (page 1) of the Certificate of Eligibility form is
the same sheet whether the status is Engineer, Student, Dependent or Spouse — only the
organisation part behind it and the ticked purpose-of-entry box differ. So geometry is
authored once per *family* here, and :mod:`torii_api.services.jp_official_forms` binds a
family to each (visa category, action) scope together with the exact published PDF.

Coordinates are nominal: they were measured against the reference PDF named in each
layout's ``reference`` field. At fill time
:func:`torii_api.services.pdf_geometry.fit_layout` aligns them with the ruled lines of
whichever variant was actually fetched, so the small per-status scale differences the
ministry ships do not move a value out of its box. If the shape does not match, nothing
is written — see :mod:`torii_api.services.official_form_filler`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

NominalRows = tuple[tuple[float, tuple[float, ...]], ...]

# Procedure codes. These name the statutory application, not the visa category.
PROCEDURE_COE = "coe"
PROCEDURE_CHANGE = "change_of_status"
PROCEDURE_EXTENSION = "extension"
PROCEDURE_PERMANENT_RESIDENCE = "permanent_residence"
PROCEDURE_CONSULAR_VISA = "consular_visa"


@dataclass(frozen=True)
class DateSlots:
    """Right edges of the year / month / day slots of a 年月日 line.

    ``day`` is ``None`` on the 年月 lines that ask only for a month — a graduation date
    or a study period — where writing a day would put a number outside any printed box.
    """

    year: float
    month: float
    day: float | None = None


@dataclass(frozen=True)
class NameSlots:
    """Left edges of the family-name and given-name halves of the 氏名 line."""

    family: float
    given: float


@dataclass(frozen=True)
class Mark:
    """A printed glyph to circle (有 / 無 / 男 / 女) or a checkbox to tick."""

    x0: float
    x1: float
    y: float


@dataclass(frozen=True)
class Box:
    """A rectangle on the form — currently only the 写真 photo panel."""

    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(frozen=True)
class LineField:
    """A value written onto one ruled line, addressed as (row, column)."""

    item: str
    key: str
    label: str
    row: int
    column: int = 0
    dates: DateSlots | None = None
    names: NameSlots | None = None
    # Only expected when this other answer is affirmative — the 具体的内容 detail line
    # under a 有 / 無 question stays blank when the answer is 無, and reporting it as an
    # unfilled item would be wrong.
    depends_on: str | None = None


@dataclass(frozen=True)
class ChoiceField:
    """A 有 / 無 style choice answered by circling one of the printed glyphs."""

    item: str
    key: str
    label: str
    options: tuple[tuple[str, Mark], ...]


@dataclass(frozen=True)
class FormLayout:
    code: str
    series: str
    procedure: str
    reference: str
    rows: NominalRows
    lines: tuple[LineField, ...]
    choices: tuple[ChoiceField, ...] = ()
    photo: Box | None = None
    # Which sheet of the packet this describes. A ministry form staples several forms
    # together: page 1 is 申請人等作成用 1 and shares one layout across every residence
    # status, while the applicant's later parts are status-specific.
    page: int = 0
    # Items on this sheet that are known to need filling but are not authored yet, so the
    # applicant is told what is still theirs instead of finding the gap at the counter.
    unsupported_items: tuple[str, ...] = ()
    # Purpose-of-entry checkbox column (Certificate of Eligibility item 11) keyed by
    # visa category; the ticked box is what makes a generic sheet a specific application.
    purpose_checkboxes: dict[str, Mark] = field(default_factory=dict)

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys([line.key for line in self.lines] + [c.key for c in self.choices])
        )


# ── Certificate of Eligibility — 別記第六号の三様式 ────────────────────────────────
# Reference: https://www.moj.go.jp/isa/content/930004029.pdf (Engineer / Specialist).

_COE_ROWS: NominalRows = (
    (803.5, (44.3, 550.8)),
    (669.8, (115.2, 293.5, 376.6, 539.2)),
    (652.0, (115.2, 539.2)),
    (628.3, (222.1, 388.6)),
    (611.9, (91.4, 210.4, 317.2, 539.2)),
    (594.6, (139.0, 539.2)),
    (576.8, (139.0, 281.6, 376.6, 527.8)),
    (559.0, (139.0, 281.6, 376.6, 527.8)),
    (403.8, (127.1, 281.6, 376.6, 539.2)),
    (386.0, (127.1, 281.6)),
    (368.2, (150.8, 305.4)),
    (327.2, (91.4, 127.2, 234.0, 376.7, 400.3, 539.2)),
    (285.7, (257.8, 293.5, 470.6, 505.0)),
    (250.3, (150.8, 482.2)),
    (216.2, (234.0, 269.8, 400.3, 539.2)),
    (181.3, (44.3, 550.8)),
    (153.2, (44.3, 550.8)),
    (137.8, (293.8, 341.3)),
    (122.5, (293.8, 341.3)),
    (107.1, (293.8, 341.3)),
    (91.8, (44.3, 550.8)),
    (52.3, (44.3, 550.8)),
)

COE_LAYOUT = FormLayout(
    code="moj_coe_applicant_p1",
    series="別記第六号の三様式（第六条の二関係）",
    procedure=PROCEDURE_COE,
    reference="930004029.pdf",
    rows=_COE_ROWS,
    lines=(
        LineField("1", "nationality", "Nationality / Region", row=1, column=0),
        LineField(
            "2",
            "date_of_birth",
            "Date of birth",
            row=1,
            column=1,
            dates=DateSlots(year=429.8, month=476.0, day=523.3),
        ),
        LineField(
            "3",
            "full_name",
            "Name (family / given)",
            row=2,
            names=NameSlots(family=131.0, given=273.4),
        ),
        LineField("5", "place_of_birth", "Place of birth", row=3),
        LineField("7", "occupation", "Occupation", row=4, column=0),
        LineField("8", "home_town_city", "Home town / city", row=4, column=1),
        LineField("9", "current_japan_address", "Address in Japan", row=5),
        LineField("9", "telephone_japan", "Telephone No.", row=6, column=0),
        LineField("9", "mobile_phone", "Cellular phone No.", row=6, column=1),
        LineField("10(1)", "passport_number", "Passport number", row=7, column=0),
        LineField(
            "10(2)",
            "passport_expiry_date",
            "Passport date of expiration",
            row=7,
            column=1,
            dates=DateSlots(year=429.8, month=476.0, day=516.7),
        ),
        LineField(
            "12",
            "intended_entry_date",
            "Date of entry",
            row=8,
            column=0,
            dates=DateSlots(year=180.3, month=228.0, day=271.3),
        ),
        LineField("13", "port_of_entry", "Port of entry", row=8, column=1),
        LineField("14", "intended_length_of_stay", "Intended length of stay", row=9),
        LineField(
            "16", "intended_visa_application_place", "Intended place to apply for visa", row=10
        ),
        LineField(
            "19",
            "criminal_record_detail",
            "Criminal record — detail",
            row=13,
            depends_on="criminal_record",
        ),
    ),
    choices=(
        ChoiceField(
            "4",
            "sex",
            "Sex",
            (
                ("male", Mark(100.3, 106.8, 637.9)),
                ("female", Mark(136.0, 142.9, 637.8)),
            ),
        ),
        ChoiceField(
            "6",
            "marital_status",
            "Marital status",
            (
                ("married", Mark(479.0, 486.0, 637.6)),
                ("single", Mark(513.3, 520.2, 638.0)),
            ),
        ),
        ChoiceField(
            "15",
            "has_accompanying_persons",
            "Accompanying persons",
            (
                ("yes", Mark(427.0, 434.1, 394.9)),
                ("no", Mark(450.7, 457.5, 395.2)),
            ),
        ),
        ChoiceField(
            "17",
            "previous_japan_visits",
            "Past entry into / departure from Japan",
            (
                ("yes", Mark(189.4, 196.5, 359.6)),
                ("no", Mark(213.3, 220.2, 360.0)),
            ),
        ),
        ChoiceField(
            "18",
            "prior_coe_applications",
            "Past history of applying for a certificate of eligibility",
            (
                ("yes", Mark(237.0, 244.0, 316.3)),
                ("no", Mark(260.8, 267.7, 316.6)),
            ),
        ),
        ChoiceField(
            "19",
            "criminal_record",
            "Criminal record (in Japan / overseas)",
            (
                ("yes", Mark(69.4, 76.5, 258.9)),
                ("no", Mark(507.7, 514.5, 259.3)),
            ),
        ),
        ChoiceField(
            "20",
            "prior_deportation",
            "Departure by deportation / departure order",
            (
                ("yes", Mark(248.8, 255.9, 241.4)),
                ("no", Mark(272.7, 279.6, 241.8)),
            ),
        ),
        ChoiceField(
            "21",
            "has_family_in_japan",
            "Family in Japan / anyone you reside with",
            (
                ("yes", Mark(69.4, 76.5, 189.9)),
                ("no", Mark(322.4, 329.3, 190.3)),
            ),
        ),
    ),
    photo=Box(456.6, 687.7, 544.0, 801.3),
    purpose_checkboxes={
        "work": Mark(390.9, 396.4, 526.0),
        "student": Mark(379.0, 384.6, 493.1),
        "dependent": Mark(473.1, 478.6, 477.0),
        "spouse": Mark(58.2, 63.8, 445.4),
        "hsp": Mark(188.9, 194.5, 429.5),
    },
)


# ── Change of Status of Residence — 別記第三十号様式 ───────────────────────────────
# Reference: https://www.moj.go.jp/isa/content/930004064.pdf (Engineer / Specialist).

_CHANGE_ROWS: NominalRows = (
    (791.7, (55.0, 540.4)),
    (644.7, (133.3, 263.0, 340.7, 512.9)),
    (619.5, (133.3, 526.4)),
    (589.4, (237.0, 379.7)),
    (567.1, (107.4, 211.2, 314.8, 526.4)),
    (544.8, (133.3, 526.4)),
    (521.4, (133.3, 289.0, 366.6, 526.4)),
    (498.4, (159.2, 276.0, 353.6, 526.4)),
    (474.8, (159.2, 301.9, 379.6, 526.4)),
    (451.2, (159.2, 327.8)),
    (427.5, (159.2, 340.8)),
    (403.9, (159.2, 340.8)),
    (380.2, (159.2, 276.0)),
    (356.6, (198.1, 526.4)),
    (311.1, (159.2, 472.2)),
    (264.0, (55.0, 540.4)),
    (226.5, (55.0, 540.4)),
    (206.1, (302.3, 354.1)),
    (185.7, (302.3, 354.1)),
    (165.3, (302.3, 354.1)),
    (144.9, (302.3, 354.1)),
    (124.5, (302.3, 354.1)),
    (104.1, (55.0, 540.4)),
    (58.4, (55.0, 540.4)),
)

CHANGE_LAYOUT = FormLayout(
    code="moj_change_applicant_p1",
    series="別記第三十号様式（第二十条関係）",
    procedure=PROCEDURE_CHANGE,
    reference="930004064.pdf",
    rows=_CHANGE_ROWS,
    lines=(
        LineField("1", "nationality", "Nationality / Region", row=1, column=0),
        LineField(
            "2",
            "date_of_birth",
            "Date of birth",
            row=1,
            column=1,
            dates=DateSlots(year=398.3, month=451.5, day=500.6),
        ),
        LineField(
            "3",
            "full_name",
            "Name (family / given)",
            row=2,
            names=NameSlots(family=150.5, given=305.8),
        ),
        LineField("5", "place_of_birth", "Place of birth", row=3),
        LineField("7", "occupation", "Occupation", row=4, column=0),
        LineField("8", "home_town_city", "Home town / city", row=4, column=1),
        LineField("9", "current_japan_address", "Address in Japan", row=5),
        LineField("9", "telephone_japan", "Telephone No.", row=6, column=0),
        LineField("9", "mobile_phone", "Cellular phone No.", row=6, column=1),
        LineField("10(1)", "passport_number", "Passport number", row=7, column=0),
        LineField(
            "10(2)",
            "passport_expiry_date",
            "Passport date of expiration",
            row=7,
            column=1,
            dates=DateSlots(year=411.3, month=465.1, day=514.2),
        ),
        LineField("11", "current_status_of_residence", "Status of residence", row=8, column=0),
        LineField("11", "current_period_of_stay", "Period of stay", row=8, column=1),
        LineField(
            "11",
            "current_status_expiry_date",
            "Date of expiration of period of stay",
            row=9,
            dates=DateSlots(year=216.9, month=268.9, day=316.2),
        ),
        LineField("12", "residence_card_number", "Residence card number", row=10),
        LineField("13", "desired_status_of_residence", "Desired status of residence", row=11),
        LineField("13", "desired_period_of_stay", "Desired period of stay", row=12),
        LineField("14", "change_reason", "Reason for change of status", row=13),
        LineField(
            "15",
            "criminal_record_detail",
            "Criminal record — detail",
            row=14,
            depends_on="criminal_record",
        ),
    ),
    choices=(
        ChoiceField(
            "4",
            "sex",
            "Sex",
            (
                ("male", Mark(109.9, 118.4, 600.5)),
                ("female", Mark(135.9, 144.9, 600.3)),
            ),
        ),
        ChoiceField(
            "6",
            "marital_status",
            "Marital status",
            (
                ("married", Mark(480.8, 489.9, 600.4)),
                ("single", Mark(509.0, 517.9, 600.9)),
            ),
        ),
        ChoiceField(
            "15",
            "criminal_record",
            "Criminal record (in Japan / overseas)",
            (
                ("yes", Mark(83.7, 92.9, 323.3)),
                ("no", Mark(502.0, 511.0, 323.8)),
            ),
        ),
        ChoiceField(
            "16",
            "has_family_in_japan",
            "Family in Japan / anyone you reside with",
            (
                ("yes", Mark(83.7, 92.9, 275.8)),
                ("no", Mark(409.6, 418.6, 276.3)),
            ),
        ),
    ),
    photo=Box(444.1, 671.1, 531.7, 788.9),
)


# ── Extension of Period of Stay — 別記第三十号の二様式 ─────────────────────────────
# Reference: https://www.moj.go.jp/isa/content/930004094.pdf (Engineer / Specialist).

_EXTENSION_ROWS: NominalRows = (
    (791.6, (43.9, 551.4)),
    (639.6, (124.6, 257.9, 337.7, 520.6)),
    (613.4, (124.6, 535.8)),
    (559.3, (97.9, 204.6, 311.0, 535.8)),
    (536.2, (124.6, 535.8)),
    (512.0, (124.6, 284.5, 364.3, 535.8)),
    (488.2, (151.2, 271.2, 351.0, 535.8)),
    (463.8, (151.2, 297.8, 377.6, 535.8)),
    (439.3, (151.2, 324.5)),
    (414.8, (151.2, 337.8)),
    (390.3, (151.2, 271.2)),
    (365.9, (151.2, 535.8)),
    (318.8, (151.2, 474.8)),
    (271.8, (43.9, 551.4)),
    (233.1, (43.9, 551.4)),
    (212.0, (298.2, 351.5)),
    (190.9, (298.2, 351.5)),
    (169.8, (298.2, 351.5)),
    (148.7, (298.2, 351.5)),
    (127.5, (298.2, 351.5)),
    (106.4, (43.9, 551.4)),
    (58.9, (43.9, 551.4)),
)

EXTENSION_LAYOUT = FormLayout(
    code="moj_extension_applicant_p1",
    series="別記第三十号の二様式（第二十一条関係）",
    procedure=PROCEDURE_EXTENSION,
    reference="930004094.pdf",
    rows=_EXTENSION_ROWS,
    lines=(
        LineField("1", "nationality", "Nationality / Region", row=1, column=0),
        LineField(
            "2",
            "date_of_birth",
            "Date of birth",
            row=1,
            column=1,
            dates=DateSlots(year=397.0, month=452.4, day=506.7),
        ),
        LineField(
            "3",
            "full_name",
            "Name (family / given)",
            row=2,
            names=NameSlots(family=142.0, given=302.0),
        ),
        LineField("6", "occupation", "Occupation", row=3, column=0),
        LineField("7", "home_town_city", "Home town / city", row=3, column=1),
        LineField("8", "current_japan_address", "Address in Japan", row=4),
        LineField("9", "telephone_japan", "Telephone No.", row=5, column=0),
        LineField("9", "mobile_phone", "Cellular phone No.", row=5, column=1),
        LineField("10(1)", "passport_number", "Passport number", row=6, column=0),
        LineField(
            "10(2)",
            "passport_expiry_date",
            "Passport date of expiration",
            row=6,
            column=1,
            dates=DateSlots(year=410.3, month=467.6, day=521.9),
        ),
        LineField("11", "current_status_of_residence", "Status of residence", row=7, column=0),
        LineField("11", "current_period_of_stay", "Period of stay", row=7, column=1),
        LineField(
            "11",
            "current_status_expiry_date",
            "Date of expiration of period of stay",
            row=8,
            dates=DateSlots(year=210.5, month=264.0, day=312.5),
        ),
        LineField("12", "residence_card_number", "Residence card number", row=9),
        LineField("13", "desired_period_of_stay", "Desired length of extension", row=10),
        LineField("14", "reason_for_extension", "Reason for extension", row=11),
        LineField(
            "15",
            "criminal_record_detail",
            "Criminal record — detail",
            row=12,
            depends_on="criminal_record",
        ),
    ),
    choices=(
        ChoiceField(
            "4",
            "sex",
            "Sex",
            (
                ("male", Mark(100.4, 109.1, 593.6)),
                ("female", Mark(127.1, 136.3, 593.4)),
            ),
        ),
        ChoiceField(
            "5",
            "marital_status",
            "Marital status",
            (
                ("married", Mark(372.7, 382.0, 593.5)),
                ("single", Mark(400.4, 409.6, 594.0)),
            ),
        ),
        ChoiceField(
            "15",
            "criminal_record",
            "Criminal record (in Japan / overseas)",
            (
                ("yes", Mark(73.5, 82.9, 331.3)),
                ("no", Mark(508.8, 517.9, 331.8)),
            ),
        ),
        ChoiceField(
            "16",
            "has_family_in_japan",
            "Family in Japan / anyone you reside with",
            (
                ("yes", Mark(73.5, 82.9, 284.3)),
                ("no", Mark(407.7, 416.9, 284.8)),
            ),
        ),
    ),
    photo=Box(448.4, 664.4, 542.4, 783.6),
)


# ── Permanent Residence — 別記第三十四号様式 その１ ────────────────────────────────
# Reference: https://www.moj.go.jp/isa/content/930002835.pdf.

_PR_ROWS: NominalRows = (
    (755.3, (60.5, 528.0)),
    (615.8, (149.4, 275.6, 351.1, 515.0)),
    (593.5, (124.2, 515.0)),
    (561.2, (250.2, 376.4)),
    (538.4, (124.2, 212.6, 325.9, 515.0)),
    (516.5, (149.4, 515.0)),
    (493.8, (136.8, 288.2, 363.7, 515.0)),
    (471.9, (162.0, 275.6, 351.1, 515.0)),
    (450.1, (174.6, 313.4, 388.9, 515.0)),
    (428.2, (174.6, 338.6)),
    (405.9, (174.6, 363.8)),
    (373.4, (162.0, 452.0)),
    (352.4, (225.1, 515.0)),
    (334.1, (86.4, 515.0)),
    (283.4, (174.6, 300.8)),
    (261.1, (136.8, 300.8, 363.7, 515.0)),
    (238.7, (174.6, 326.0)),
    (216.4, (174.6, 326.0)),
    (194.5, (60.5, 528.0)),
    (174.5, (60.5, 528.0)),
    (131.8, (288.5, 528.0)),
    (110.4, (288.5, 528.0)),
    (89.1, (60.5, 528.0)),
    (77.9, (60.5, 528.0)),
    (57.7, (60.5, 528.0)),
)

PERMANENT_RESIDENCE_LAYOUT = FormLayout(
    code="moj_permanent_residence_p1",
    series="別記第三十四号様式（第二十二条，第二十五条関係）その１",
    procedure=PROCEDURE_PERMANENT_RESIDENCE,
    reference="930002835.pdf",
    rows=_PR_ROWS,
    lines=(
        LineField("1", "nationality", "Nationality / Region", row=1, column=0),
        LineField(
            "2",
            "date_of_birth",
            "Date of birth",
            row=1,
            column=1,
            dates=DateSlots(year=400.4, month=451.0, day=503.5),
        ),
        LineField(
            "3",
            "full_name",
            "Name (family / given)",
            row=2,
            names=NameSlots(family=153.5, given=304.6),
        ),
        LineField("5", "place_of_birth", "Place of birth", row=3),
        LineField("7", "occupation", "Occupation", row=4, column=0),
        LineField("8", "home_town_city", "Home town / city", row=4, column=1),
        LineField("9", "current_japan_address", "Address in Japan", row=5),
        LineField("9", "telephone_japan", "Telephone No.", row=6, column=0),
        LineField("9", "mobile_phone", "Cellular phone No.", row=6, column=1),
        LineField("10(1)", "passport_number", "Passport number", row=7, column=0),
        LineField(
            "10(2)",
            "passport_expiry_date",
            "Passport date of expiration",
            row=7,
            column=1,
            dates=DateSlots(year=400.4, month=451.0, day=503.5),
        ),
        LineField("11", "current_status_of_residence", "Status of residence", row=8, column=0),
        LineField("11", "current_period_of_stay", "Period of stay", row=8, column=1),
        LineField(
            "11",
            "current_status_expiry_date",
            "Date of expiration of period of stay",
            row=9,
            dates=DateSlots(year=224.0, month=274.6, day=327.1),
        ),
        LineField("12", "residence_card_number", "Residence card number", row=10),
        LineField(
            "13",
            "criminal_record_detail",
            "Criminal record — detail",
            row=11,
            depends_on="criminal_record",
        ),
        LineField("14", "pr_reason", "Reason for applying for permanent residence", row=12),
    ),
    choices=(
        ChoiceField(
            "4",
            "sex",
            "Sex",
            (
                ("male", Mark(126.6, 134.8, 572.4)),
                ("female", Mark(151.8, 160.6, 572.2)),
            ),
        ),
        ChoiceField(
            "6",
            "marital_status",
            "Marital status",
            (
                ("married", Mark(472.4, 481.3, 572.3)),
                ("single", Mark(498.6, 507.4, 572.8)),
            ),
        ),
        ChoiceField(
            "13",
            "criminal_record",
            "Criminal record (in Japan / overseas)",
            (
                ("yes", Mark(88.5, 97.4, 383.9)),
                ("no", Mark(469.5, 478.2, 384.4)),
            ),
        ),
    ),
    photo=Box(438.1, 639.6, 523.9, 753.3),
)


# ── Applicant part 2, form N — 別記第三十号の二様式 申請人等作成用 ２ ─────────────────
# Reference: https://www.moj.go.jp/isa/content/930004094.pdf page 3 (Engineer / Specialist).
# The same sheet serves extension and change of status (在留期間更新・在留資格変更用); the
# Certificate of Eligibility packet carries its own variant.

_WORK_PART2_ROWS: NominalRows = (
    (779.1, (53.2, 533.9)),
    (732.8, (117.5, 260.2, 337.8, 520.6)),
    (711.7, (117.5, 299.0, 376.7, 520.6)),
    (617.5, (130.4, 273.1, 337.8, 481.7)),
    (393.4, (234.1, 494.6)),
    (382.5, (53.2, 533.9)),
    (360.9, (53.2, 156.8, 286.4, 390.1)),
    (339.3, (53.2, 533.9)),
    (281.7, (53.2, 533.9)),
    (250.5, (104.5, 273.1, 402.6, 520.6)),
    (230.7, (117.5, 520.6)),
    (210.9, (130.4, 273.1, 363.7, 520.6)),
    (163.8, (65.6, 520.6)),
    (162.1, (65.6, 520.6)),
    (69.9, (104.5, 221.3, 286.0, 520.6)),
    (29.6, (78.6, 350.9, 389.6, 520.6)),
    (23.0, (53.2, 533.9)),
)


# The Certificate of Eligibility packet asks the same items in the same order as the
# extension packet, at different coordinates, so the field map is shared and only the
# ruled-line geometry and the 有/無 glyph differ.
def _work_part2_unsupported(item_offset: int = 0) -> tuple[str, ...]:
    """Items on this sheet that still need filling by hand, numbered for the packet."""
    return tuple(
        f"{_renumber(item.split(' ', 1)[0], item_offset)} {item.split(' ', 1)[1]}"
        for item in (
            "18(1)(2) Final education — country and level (tick boxes)",
            "19 Major field of study (tick boxes)",
            "21 Work experience (table)",
        )
    )


def _renumber(item: str, offset: int) -> str:
    """Shift an item number, e.g. ``"17(1)"`` by 5 becomes ``"22(1)"``.

    The same sheet is numbered differently in each packet because page 1 of the
    Certificate of Eligibility carries more items than page 1 of the extension.
    """
    match = re.match(r"^(\d+)(.*)$", item)
    if not match or not offset:
        return item
    return f"{int(match.group(1)) + offset}{match.group(2)}"


def _work_part2_lines(graduation: DateSlots, item_offset: int = 0) -> tuple[LineField, ...]:
    """The item map for applicant part 2 form N.

    The extension and Certificate of Eligibility packets ask the same items in the same
    order, so this map is shared. Two things differ per sheet and are passed in: the
    年月日 slot positions, because each sheet is drawn in its own coordinate space, and
    the item numbering, because page 1 of the Certificate of Eligibility carries more
    items so everything behind it is numbered five higher.
    """
    lines = (
        LineField("17(1)", "employer_name", "Place of employment — name", row=1, column=0),
        LineField("17(1)", "employer_branch_name", "Name of branch", row=1, column=1),
        LineField("17(2)", "employer_address", "Place of employment — address", row=2, column=0),
        LineField("17(3)", "employer_tel", "Place of employment — telephone", row=2, column=1),
        LineField("18(3)", "final_school_name", "Name of school", row=3, column=0),
        LineField(
            "18(4)",
            "graduation_date",
            "Date of graduation",
            row=3,
            column=1,
            dates=graduation,
        ),
        LineField(
            "20",
            "it_qualification_name",
            "Name of the information-processing qualification",
            row=4,
            depends_on="has_it_qualification",
        ),
        # Item 22 is only completed when a legal representative files on the applicant's
        # behalf, so it is gated rather than reported as an unfilled box.
        LineField(
            "22(1)",
            "legal_representative_name",
            "Legal representative — name",
            row=9,
            column=0,
            depends_on="has_legal_representative",
        ),
        LineField(
            "22(2)",
            "legal_representative_relationship",
            "Legal representative — relationship",
            row=9,
            column=1,
            depends_on="has_legal_representative",
        ),
        LineField(
            "22(3)",
            "legal_representative_address",
            "Legal representative — address",
            row=10,
            depends_on="has_legal_representative",
        ),
        LineField(
            "22(3)",
            "legal_representative_tel",
            "Legal representative — telephone",
            row=11,
            column=0,
            depends_on="has_legal_representative",
        ),
    )
    if not item_offset:
        return lines
    return tuple(
        LineField(
            _renumber(line.item, item_offset),
            line.key,
            line.label,
            row=line.row,
            column=line.column,
            dates=line.dates,
            names=line.names,
            depends_on=line.depends_on,
        )
        for line in lines
    )


WORK_PART2_LAYOUT = FormLayout(
    code="moj_work_applicant_p2",
    series="別記第三十号の二様式 申請人等作成用 ２（Ｎ）",
    procedure=PROCEDURE_EXTENSION,
    reference="930004094.pdf p3",
    page=2,
    rows=_WORK_PART2_ROWS,
    lines=_work_part2_lines(DateSlots(year=369.5, month=422.4, day=470.0)),
    choices=(
        ChoiceField(
            "20",
            "has_it_qualification",
            "Information-processing qualification",
            (
                ("yes", Mark(434.6, 443.7, 434.1)),
                ("no", Mark(455.1, 464.1, 434.6)),
            ),
        ),
    ),
    unsupported_items=_work_part2_unsupported(),
)


# ── Applicant part 2, form N — Certificate of Eligibility variant ───────────────────
# Reference: https://www.moj.go.jp/isa/content/930004029.pdf page 3.

_WORK_PART2_COE_ROWS: NominalRows = (
    (790.3, (17.9, 568.1)),
    (748.5, (80.3, 253.3, 363.2, 552.0)),
    (726.5, (96.0, 300.5, 394.7, 552.0)),
    (625.6, (111.7, 284.8, 363.2, 536.3)),
    (406.8, (221.8, 552.0)),
    (394.5, (17.9, 568.1)),
    (374.9, (17.9, 143.6, 285.1, 410.9)),
    (355.2, (17.9, 568.1)),
    (296.1, (17.9, 568.1)),
    (254.4, (96.0, 269.0, 410.4, 552.0)),
    (232.3, (96.0, 552.0)),
    (210.2, (111.7, 269.0, 394.7, 552.0)),
    (147.6, (33.1, 552.0)),
    (145.8, (33.1, 552.0)),
    (55.2, (80.3, 206.2, 284.6, 552.0)),
    (23.2, (48.8, 347.6, 363.2, 552.0)),
    (13.4, (17.9, 568.1)),
)

WORK_PART2_COE_LAYOUT = FormLayout(
    code="moj_work_applicant_p2_coe",
    series="別記第六号の三様式 申請人等作成用 ２（Ｎ）",
    procedure=PROCEDURE_COE,
    reference="930004029.pdf p3",
    page=2,
    rows=_WORK_PART2_COE_ROWS,
    lines=_work_part2_lines(DateSlots(year=403.1, month=466.2, day=521.9), item_offset=5),
    choices=(
        ChoiceField(
            "20",
            "has_it_qualification",
            "Information-processing qualification",
            (
                ("yes", Mark(459.8, 469.1, 447.0)),
                ("no", Mark(525.2, 534.3, 447.5)),
            ),
        ),
    ),
    unsupported_items=_work_part2_unsupported(item_offset=5),
)


# ── Applicant part 2, form T (Spouse / Long-term resident) — 申請人等作成用 ２ ─────────
# Reference: https://www.moj.go.jp/isa/content/930004114.pdf page 3.
# One layout serves all three procedures for this status.

_SPOUSE_PART2_ROWS: NominalRows = (
    (771.1, (55.8, 530.0)),
    (490.1, (142.8, 305.2, 367.4, 517.3)),
    (468.4, (142.8, 305.2, 367.4, 517.3)),
    (405.8, (105.4, 255.2, 330.0, 517.3)),
    (384.2, (117.8, 342.6, 392.4, 517.3)),
    (362.6, (130.3, 205.3)),
    (321.6, (180.2, 280.2, 404.9, 504.8)),
    (300.0, (180.2, 280.2, 404.9, 504.8)),
    (278.4, (180.2, 280.2)),
    (242.4, (180.2, 280.2, 404.9, 504.8)),
    (220.8, (155.3, 230.3, 292.6, 342.6, 404.9, 504.8)),
    (177.6, (130.3, 342.6)),
    (156.0, (130.3, 342.6, 404.9, 517.3)),
    (134.4, (192.7, 342.6, 404.9, 517.3)),
    (111.7, (142.8, 217.8)),
    (104.1, (55.8, 530.0)),
    (57.1, (55.8, 530.0)),
)

_SPOUSE_PART2_DATE = DateSlots(year=411.5, month=461.6, day=506.8)

SPOUSE_PART2_LAYOUT = FormLayout(
    code="moj_spouse_applicant_p2",
    series="別記第三十号の二様式 申請人等作成用 ２（Ｔ 日本人の配偶者等）",
    procedure=PROCEDURE_EXTENSION,
    reference="930004114.pdf p3",
    page=2,
    rows=_SPOUSE_PART2_ROWS,
    lines=(
        LineField(
            "18(1)",
            "family_notification_place_japan",
            "Marriage or birth registered with — Japanese authorities",
            row=1,
            column=0,
        ),
        LineField(
            "18(1)",
            "family_notification_date_japan",
            "Date registered in Japan",
            row=1,
            column=1,
            dates=_SPOUSE_PART2_DATE,
        ),
        LineField(
            "18(2)",
            "family_notification_place_home",
            "Marriage or birth registered with — home-country authorities",
            row=2,
            column=0,
        ),
        LineField(
            "18(2)",
            "family_notification_date_home",
            "Date registered in your home country",
            row=2,
            column=1,
            dates=_SPOUSE_PART2_DATE,
        ),
        LineField("19(1)", "employer_name", "Place of employment — name", row=3, column=0),
        LineField("19(1)", "employer_branch_name", "Name of branch", row=3, column=1),
        LineField("19(2)", "employer_address", "Place of employment — address", row=4, column=0),
        LineField("19(2)", "employer_tel", "Place of employment — telephone", row=4, column=1),
        LineField("19(3)", "annual_income_jpy", "Your annual income (yen)", row=5),
        LineField(
            "20(1)", "support_self_monthly_jpy", "Support — self (yen/month)", row=6, column=0
        ),
        LineField(
            "20(1)",
            "support_overseas_supporter_monthly_jpy",
            "Support — supporter living abroad (yen/month)",
            row=6,
            column=1,
        ),
        LineField(
            "20(1)",
            "support_japan_supporter_monthly_jpy",
            "Support — supporter in Japan (yen/month)",
            row=7,
            column=0,
        ),
        LineField(
            "20(1)",
            "support_guarantor_monthly_jpy",
            "Support — guarantor (yen/month)",
            row=7,
            column=1,
        ),
        LineField("20(1)", "support_other_monthly_jpy", "Support — other (yen/month)", row=8),
        LineField("20(2)", "funds_carried_jpy", "Money carried from abroad (yen)", row=9, column=0),
        LineField(
            "20(2)", "funds_remitted_jpy", "Money remitted from abroad (yen)", row=9, column=1
        ),
        LineField("20(2)", "funds_carrier_name", "Who carries the money", row=10, column=0),
        LineField("20(2)", "funds_carry_date", "When it is carried", row=10, column=1),
        LineField("20(2)", "funds_other_jpy", "Other funds (yen)", row=10, column=2),
        LineField("20(3)", "supporter_name", "Supporter — name", row=11),
        LineField("20(3)", "supporter_address", "Supporter — address", row=12, column=0),
        LineField("20(3)", "supporter_tel", "Supporter — telephone", row=12, column=1),
        LineField("20(3)", "supporter_occupation", "Supporter — occupation", row=13, column=0),
        LineField(
            "20(3)", "supporter_employer_tel", "Supporter — employer telephone", row=13, column=1
        ),
        LineField(
            "20(3)", "supporter_annual_income_jpy", "Supporter — annual income (yen)", row=14
        ),
    ),
    unsupported_items=(
        "17 Personal relationship or status (tick boxes)",
        "20 Method-of-support tick boxes beside each amount",
    ),
)


# ── Applicant part 3, form T (Spouse / Long-term resident) — 申請人等作成用 ３ ─────────
# Reference: https://www.moj.go.jp/isa/content/930004114.pdf page 4.

_SPOUSE_PART3_ROWS: NominalRows = (
    (789.3, (42.5, 539.5)),
    (751.4, (120.5, 329.9)),
    (728.2, (120.5, 290.6, 395.2, 526.1)),
    (705.1, (303.6, 473.8)),
    (681.9, (133.6, 238.3, 303.6, 408.4)),
    (658.0, (159.7, 329.9)),
    (576.5, (146.6, 290.6, 355.9, 526.1)),
    (553.3, (133.6, 329.9, 395.2, 526.1)),
    (530.1, (133.6, 212.2)),
    (495.9, (107.4, 277.6, 329.8, 526.1)),
    (472.1, (120.5, 526.1)),
    (449.6, (133.6, 277.6, 369.0, 526.1)),
    (416.0, (94.3, 277.6, 408.2, 526.1)),
    (393.0, (120.5, 526.1)),
    (369.9, (133.6, 277.6, 369.0, 526.1)),
    (303.2, (68.2, 526.1)),
    (301.4, (68.2, 526.1)),
    (182.1, (94.3, 251.4, 316.7, 526.1)),
    (132.9, (81.2, 329.9, 382.1, 526.1)),
    (129.2, (42.5, 539.5)),
    (51.4, (42.5, 539.5)),
)

SPOUSE_PART3_LAYOUT = FormLayout(
    code="moj_spouse_applicant_p3",
    series="別記第三十号の二様式 申請人等作成用 ３（Ｔ 日本人の配偶者等）",
    procedure=PROCEDURE_EXTENSION,
    reference="930004114.pdf p4",
    page=3,
    rows=_SPOUSE_PART3_ROWS,
    lines=(
        LineField("21(1)", "supporter_name", "Supporter — name", row=1),
        LineField(
            "21(2)",
            "supporter_date_of_birth",
            "Supporter — date of birth",
            row=2,
            column=0,
            dates=DateSlots(year=178.6, month=231.1, day=279.1),
        ),
        LineField("21(3)", "supporter_nationality", "Supporter — nationality", row=2, column=1),
        LineField(
            "21(4)",
            "supporter_residence_card_number",
            "Supporter — residence card number",
            row=3,
        ),
        LineField(
            "21(5)",
            "supporter_status_of_residence",
            "Supporter — status of residence",
            row=4,
            column=0,
        ),
        LineField(
            "21(6)", "supporter_period_of_stay", "Supporter — period of stay", row=4, column=1
        ),
        LineField(
            "21(7)",
            "supporter_status_expiry_date",
            "Supporter — date of expiration",
            row=5,
            dates=DateSlots(year=217.8, month=270.3, day=318.4),
        ),
        LineField("21(9)", "supporter_employer_name", "Supporter — employer", row=6, column=0),
        LineField(
            "21(9)", "supporter_employer_branch", "Supporter — employer branch", row=6, column=1
        ),
        LineField(
            "21(10)", "supporter_employer_address", "Supporter — employer address", row=7, column=0
        ),
        LineField(
            "21(10)", "supporter_employer_tel", "Supporter — employer telephone", row=7, column=1
        ),
        LineField(
            "21(11)", "supporter_annual_income_jpy", "Supporter — annual income (yen)", row=8
        ),
        LineField("22(1)", "resident_guarantor_name", "Guarantor in Japan — name", row=9, column=0),
        LineField(
            "22(2)", "guarantor_occupation", "Guarantor in Japan — occupation", row=9, column=1
        ),
        LineField("22(3)", "guarantor_address", "Guarantor in Japan — address", row=10),
        LineField(
            "22(3)", "guarantor_telephone", "Guarantor in Japan — telephone", row=11, column=0
        ),
        LineField("22(3)", "guarantor_mobile", "Guarantor in Japan — mobile", row=11, column=1),
        LineField(
            "23(1)",
            "legal_representative_name",
            "Legal representative — name",
            row=12,
            column=0,
            depends_on="has_legal_representative",
        ),
        LineField(
            "23(2)",
            "legal_representative_relationship",
            "Legal representative — relationship",
            row=12,
            column=1,
            depends_on="has_legal_representative",
        ),
        LineField(
            "23(3)",
            "legal_representative_address",
            "Legal representative — address",
            row=13,
            depends_on="has_legal_representative",
        ),
        LineField(
            "23(3)",
            "legal_representative_tel",
            "Legal representative — telephone",
            row=14,
            column=0,
            depends_on="has_legal_representative",
        ),
        LineField(
            "23(3)",
            "legal_representative_mobile",
            "Legal representative — mobile",
            row=14,
            column=1,
            depends_on="has_legal_representative",
        ),
    ),
    unsupported_items=("21(8) Supporter's relationship to you (tick boxes)",),
)


# ── Applicant part 2, form R (Dependent) — 申請人等作成用 ２ ──────────────────────────
# Reference: https://www.moj.go.jp/isa/content/930004110.pdf page 3.
# Serves extension and change of status.

_DEPENDENT_PART2_ROWS: NominalRows = (
    (776.4, (56.6, 536.2)),
    (726.1, (162.7, 376.0)),
    (700.2, (162.7, 336.0)),
    (674.7, (162.7, 376.0)),
    (648.8, (162.7, 336.0)),
    (493.1, (136.1, 522.5)),
    (467.6, (109.4, 256.1, 335.9, 522.5)),
    (442.2, (149.4, 296.0)),
    (416.7, (149.4, 202.8, 282.6, 362.6)),
    (377.1, (122.8, 269.4, 389.2, 509.2)),
    (351.2, (122.8, 509.2)),
    (325.3, (136.1, 269.4, 362.5, 509.2)),
    (257.1, (69.5, 522.5)),
    (255.3, (69.5, 522.5)),
    (132.3, (109.4, 269.4, 322.6, 522.5)),
    (81.6, (82.8, 349.3, 389.2, 522.5)),
    (77.8, (56.6, 536.2)),
    (48.0, (56.6, 536.2)),
)

DEPENDENT_PART2_LAYOUT = FormLayout(
    code="moj_dependent_applicant_p2",
    series="別記第三十号の二様式 申請人等作成用 ２（Ｒ 家族滞在）",
    procedure=PROCEDURE_EXTENSION,
    reference="930004110.pdf p3",
    page=2,
    rows=_DEPENDENT_PART2_ROWS,
    lines=(
        LineField(
            "17(1)",
            "family_notification_place_japan",
            "Marriage or birth registered with — Japanese authorities",
            row=1,
        ),
        LineField(
            "17(1)",
            "family_notification_date_japan",
            "Date registered in Japan",
            row=2,
            dates=DateSlots(year=222.0, month=275.5, day=324.3),
        ),
        LineField(
            "17(2)",
            "family_notification_place_home",
            "Marriage or birth registered with — home-country authorities",
            row=3,
        ),
        LineField(
            "17(2)",
            "family_notification_date_home",
            "Date registered in your home country",
            row=4,
            dates=DateSlots(year=222.0, month=275.5, day=324.3),
        ),
        LineField(
            "19(1)",
            "part_time_work_type",
            "Work outside status — type of work",
            row=5,
            depends_on="works_outside_status",
        ),
        LineField(
            "19(2)",
            "part_time_employer_name",
            "Work outside status — employer",
            row=6,
            column=0,
            depends_on="works_outside_status",
        ),
        LineField(
            "19(2)",
            "part_time_employer_branch",
            "Work outside status — branch",
            row=6,
            column=1,
            depends_on="works_outside_status",
        ),
        LineField(
            "19(2)",
            "part_time_employer_tel",
            "Work outside status — telephone",
            row=7,
            depends_on="works_outside_status",
        ),
        LineField(
            "19(3)",
            "part_time_weekly_hours",
            "Work outside status — hours per week",
            row=8,
            column=0,
            depends_on="works_outside_status",
        ),
        LineField(
            "19(4)",
            "part_time_salary_jpy",
            "Work outside status — salary (yen)",
            row=8,
            column=1,
            depends_on="works_outside_status",
        ),
        LineField(
            "20(1)",
            "legal_representative_name",
            "Legal representative — name",
            row=9,
            column=0,
            depends_on="has_legal_representative",
        ),
        LineField(
            "20(2)",
            "legal_representative_relationship",
            "Legal representative — relationship",
            row=9,
            column=1,
            depends_on="has_legal_representative",
        ),
        LineField(
            "20(3)",
            "legal_representative_address",
            "Legal representative — address",
            row=10,
            depends_on="has_legal_representative",
        ),
        LineField(
            "20(3)",
            "legal_representative_tel",
            "Legal representative — telephone",
            row=11,
            column=0,
            depends_on="has_legal_representative",
        ),
        LineField(
            "20(3)",
            "legal_representative_mobile",
            "Legal representative — mobile",
            row=11,
            column=1,
            depends_on="has_legal_representative",
        ),
    ),
    choices=(
        ChoiceField(
            "19",
            "works_outside_status",
            "Activities other than those permitted",
            (
                ("yes", Mark(434.1, 443.5, 563.5)),
                ("no", Mark(455.2, 464.4, 564.0)),
            ),
        ),
    ),
    unsupported_items=("18 Method of support (tick boxes)",),
)


# ── Applicant part 2, form P (Student) — 申請人等作成用 ２ ────────────────────────────
# Reference: https://www.moj.go.jp/isa/content/930004106.pdf page 3.
# Serves extension and change of status; the Certificate of Eligibility has its own.

_STUDENT_PART2_ROWS: NominalRows = (
    (801.8, (65.3, 505.9)),
    (764.9, (142.6, 492.6)),
    (741.1, (129.6, 298.2, 375.8, 492.6)),
    (696.0, (324.0, 388.9)),
    (595.7, (155.5, 246.4, 362.9, 492.6)),
    (528.6, (116.6, 298.2, 337.0, 492.6)),
    (495.4, (142.6, 324.1)),
    (471.6, (142.6, 272.3, 298.1, 427.8)),
    (449.6, (129.6, 492.6)),
    (427.7, (129.6, 492.6)),
    (360.6, (142.6, 324.1)),
    (337.4, (142.6, 272.3, 298.1, 427.8)),
    (278.6, (142.6, 246.4, 401.8, 479.6)),
    (254.9, (181.4, 285.2, 401.8, 479.6)),
    (230.5, (129.6, 233.4)),
    (195.5, (168.5, 272.3, 401.8, 479.6)),
    (172.3, (142.6, 220.4, 285.1, 337.1, 401.8, 479.6)),
    (117.2, (129.6, 350.0)),
    (93.5, (129.6, 350.0, 401.8, 492.6)),
    (70.3, (207.4, 337.1, 401.8, 492.6)),
    (48.4, (155.5, 220.4)),
    (44.6, (65.3, 505.9)),
)

STUDENT_PART2_LAYOUT = FormLayout(
    code="moj_student_applicant_p2",
    series="別記第三十号の二様式 申請人等作成用 ２（Ｐ 留学）",
    procedure=PROCEDURE_EXTENSION,
    reference="930004106.pdf p3",
    page=2,
    rows=_STUDENT_PART2_ROWS,
    lines=(
        LineField("17(1)", "school_name", "Place of study — name", row=1),
        LineField("17(2)", "school_address", "Place of study — address", row=2, column=0),
        LineField("17(3)", "school_tel", "Place of study — telephone", row=2, column=1),
        LineField("18", "total_years_of_education", "Total period of education (years)", row=3),
        LineField("19(2)", "final_school_name", "Last school attended", row=4, column=0),
        LineField(
            "19(3)",
            "graduation_date",
            "Date of graduation or expected graduation",
            row=4,
            column=1,
            dates=DateSlots(year=407.0, month=470.0),
        ),
        LineField("20(1)", "japanese_test_name", "Japanese language test — name", row=5, column=0),
        LineField(
            "20(2)",
            "japanese_test_score",
            "Japanese language test — level or score",
            row=5,
            column=1,
        ),
        LineField("20", "japanese_school_name", "Japanese language school — name", row=6),
        LineField(
            "20",
            "japanese_study_from",
            "Japanese language study — from",
            row=7,
            column=0,
            dates=DateSlots(year=196.0, month=245.0),
        ),
        LineField(
            "20",
            "japanese_study_to",
            "Japanese language study — to",
            row=7,
            column=1,
            dates=DateSlots(year=352.0, month=401.0),
        ),
        LineField(
            "22(1)", "support_self_monthly_jpy", "Support — self (yen/month)", row=12, column=0
        ),
        LineField(
            "22(1)",
            "support_overseas_supporter_monthly_jpy",
            "Support — supporter living abroad (yen/month)",
            row=12,
            column=1,
        ),
        LineField(
            "22(1)",
            "support_japan_supporter_monthly_jpy",
            "Support — supporter in Japan (yen/month)",
            row=13,
            column=0,
        ),
        LineField(
            "22(1)",
            "scholarship_monthly_jpy",
            "Support — scholarship (yen/month)",
            row=13,
            column=1,
        ),
        LineField("22(1)", "support_other_monthly_jpy", "Support — other (yen/month)", row=14),
        LineField(
            "22(2)", "funds_carried_jpy", "Money carried from abroad (yen)", row=15, column=0
        ),
        LineField(
            "22(2)", "funds_remitted_jpy", "Money remitted from abroad (yen)", row=15, column=1
        ),
        LineField("22(2)", "funds_carrier_name", "Who carries the money", row=16, column=0),
        LineField("22(2)", "funds_carry_date", "When it is carried", row=16, column=1),
        LineField("22(2)", "funds_other_jpy", "Other funds (yen)", row=16, column=2),
        LineField("22(3)", "supporter_name", "Supporter — name", row=17),
        LineField("22(3)", "supporter_address", "Supporter — address", row=18, column=0),
        LineField("22(3)", "supporter_tel", "Supporter — telephone", row=18, column=1),
        LineField("22(3)", "supporter_occupation", "Supporter — occupation", row=19, column=0),
        LineField(
            "22(3)", "supporter_employer_tel", "Supporter — employer telephone", row=19, column=1
        ),
        LineField(
            "22(3)", "supporter_annual_income_jpy", "Supporter — annual income (yen)", row=20
        ),
    ),
    unsupported_items=(
        "19(1) Registered enrollment and school level (tick boxes)",
        "21 Japanese education history (high-school applicants only)",
        "22 Method-of-support tick boxes beside each amount",
    ),
)


# ── Applicant part 3, form P (Student) — 申請人等作成用 ３ ────────────────────────────
# Reference: https://www.moj.go.jp/isa/content/930004106.pdf page 4 (extension).

_STUDENT_PART3_EXT_ROWS: NominalRows = (
    (819.2, (75.5, 495.7)),
    (543.1, (161.5, 483.0)),
    (520.0, (161.5, 310.0, 371.6, 483.0)),
    (496.1, (161.5, 211.1, 285.1, 359.4)),
    (392.2, (136.8, 272.9, 396.4, 483.0)),
    (369.1, (136.8, 483.0)),
    (346.0, (149.2, 272.9, 359.3, 483.0)),
    (311.6, (136.8, 272.9, 396.4, 483.0)),
    (288.6, (136.8, 483.0)),
    (265.4, (149.2, 272.9, 359.3, 483.0)),
    (184.7, (87.4, 483.0)),
    (183.1, (87.4, 483.0)),
    (84.4, (124.4, 248.2, 297.5, 483.0)),
    (36.6, (99.7, 347.0, 371.6, 483.0)),
    (33.0, (75.5, 495.7)),
)

_STUDENT_PART3_LINES: tuple[LineField, ...] = (
    # Item 23 is only completed when the applicant works outside their status.
    LineField(
        "23(1)",
        "part_time_work_type",
        "Work outside status — type of work",
        row=1,
        depends_on="works_outside_status",
    ),
    LineField(
        "23(2)",
        "part_time_employer_name",
        "Work outside status — place of employment",
        row=2,
        column=0,
        depends_on="works_outside_status",
    ),
    LineField(
        "23(2)",
        "part_time_employer_tel",
        "Work outside status — telephone",
        row=2,
        column=1,
        depends_on="works_outside_status",
    ),
    LineField(
        "23(3)",
        "part_time_weekly_hours",
        "Work outside status — hours per week",
        row=3,
        column=0,
        depends_on="works_outside_status",
    ),
    LineField(
        "23(4)",
        "part_time_salary_jpy",
        "Work outside status — salary (yen)",
        row=3,
        column=1,
        depends_on="works_outside_status",
    ),
    # Item 25 applies only to primary and junior-high pupils.
    LineField("25(1)", "guardian_name", "Guardian in Japan — name", row=4, column=0),
    LineField(
        "25(2)", "guardian_relationship", "Guardian in Japan — relationship", row=4, column=1
    ),
    LineField("25(3)", "guardian_address", "Guardian in Japan — address", row=5),
    LineField("25(3)", "guardian_tel", "Guardian in Japan — telephone", row=6, column=0),
    LineField("25(3)", "guardian_mobile", "Guardian in Japan — mobile", row=6, column=1),
    LineField(
        "26(1)",
        "legal_representative_name",
        "Legal representative — name",
        row=7,
        column=0,
        depends_on="has_legal_representative",
    ),
    LineField(
        "26(2)",
        "legal_representative_relationship",
        "Legal representative — relationship",
        row=7,
        column=1,
        depends_on="has_legal_representative",
    ),
    LineField(
        "26(3)",
        "legal_representative_address",
        "Legal representative — address",
        row=8,
        depends_on="has_legal_representative",
    ),
    LineField(
        "26(3)",
        "legal_representative_tel",
        "Legal representative — telephone",
        row=9,
        column=0,
        depends_on="has_legal_representative",
    ),
    LineField(
        "26(3)",
        "legal_representative_mobile",
        "Legal representative — mobile",
        row=9,
        column=1,
        depends_on="has_legal_representative",
    ),
)

_STUDENT_PART3_CHOICES: tuple[ChoiceField, ...] = (
    ChoiceField(
        "23",
        "works_outside_status",
        "Activities other than those permitted",
        (
            ("yes", Mark(425.8, 434.5, 608.4)),
            ("no", Mark(445.5, 454.0, 608.9)),
        ),
    ),
)

_STUDENT_PART3_UNSUPPORTED = (
    "22(4)(5) Relationship of supporter and scholarship provider (tick boxes)",
    "24 Plan after graduation (tick boxes)",
)

STUDENT_PART3_EXTENSION_LAYOUT = FormLayout(
    code="moj_student_applicant_p3_extension",
    series="別記第三十号の二様式 申請人等作成用 ３（Ｐ 留学）",
    procedure=PROCEDURE_EXTENSION,
    reference="930004106.pdf p4",
    page=3,
    rows=_STUDENT_PART3_EXT_ROWS,
    lines=_STUDENT_PART3_LINES,
    choices=_STUDENT_PART3_CHOICES,
    unsupported_items=_STUDENT_PART3_UNSUPPORTED,
)


LAYOUTS: dict[str, FormLayout] = {
    layout.code: layout
    for layout in (
        COE_LAYOUT,
        CHANGE_LAYOUT,
        EXTENSION_LAYOUT,
        PERMANENT_RESIDENCE_LAYOUT,
        WORK_PART2_LAYOUT,
        WORK_PART2_COE_LAYOUT,
        STUDENT_PART2_LAYOUT,
        STUDENT_PART3_EXTENSION_LAYOUT,
        DEPENDENT_PART2_LAYOUT,
        SPOUSE_PART2_LAYOUT,
        SPOUSE_PART3_LAYOUT,
    )
}
