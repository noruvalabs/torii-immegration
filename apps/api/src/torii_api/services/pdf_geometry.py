"""Geometry extraction for flat (non-fillable) official PDF forms.

The Japanese government publishes its residence-application forms as *flat* PDFs —
they carry no AcroForm fields, so values cannot be written into named boxes. What
they do carry is the ruled lines the applicant writes on. This module recovers those
rules from the page content stream, which gives a deterministic, self-describing
coordinate system to fill against.

Only :mod:`pypdf` is used (already a dependency); no rasterisation and no new native
libraries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pypdf.generic import ContentStream

# A rule is "horizontal" when it is at most this tall, and only counts as a writable
# field line when it is at least this wide.
MAX_RULE_HEIGHT = 2.0
MIN_RULE_WIDTH = 25.0
# Rules whose baselines are within this many points belong to the same visual row.
ROW_TOLERANCE = 1.5

Matrix = tuple[float, float, float, float, float, float]
IDENTITY: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _multiply(a: Matrix, b: Matrix) -> Matrix:
    return (
        a[0] * b[0] + a[1] * b[2],
        a[0] * b[1] + a[1] * b[3],
        a[2] * b[0] + a[3] * b[2],
        a[2] * b[1] + a[3] * b[3],
        a[4] * b[0] + a[5] * b[2] + b[4],
        a[4] * b[1] + a[5] * b[3] + b[5],
    )


def _apply(m: Matrix, x: float, y: float) -> tuple[float, float]:
    return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


@dataclass(frozen=True)
class Rule:
    """One horizontal ruled line in page (device) space."""

    y: float
    x0: float
    x1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0


@dataclass(frozen=True)
class Row:
    """The rules sharing one baseline, left to right."""

    y: float
    columns: tuple[Rule, ...]

    def column(self, index: int) -> Rule | None:
        if 0 <= index < len(self.columns):
            return self.columns[index]
        return None


def _path_boxes(page: Any, reader: Any) -> list[tuple[float, float, float, float]]:
    """Bounding boxes of every subpath on ``page``, in device space."""
    contents = page.get_contents()
    if contents is None:
        return []
    stream = ContentStream(contents, reader)

    ctm: Matrix = IDENTITY
    stack: list[Matrix] = []
    points: list[tuple[float, float]] = []
    boxes: list[tuple[float, float, float, float]] = []

    def flush() -> None:
        nonlocal points
        if len(points) >= 2:
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            boxes.append((min(xs), min(ys), max(xs), max(ys)))
        points = []

    for operands, operator in stream.operations:
        op = operator.decode("latin-1") if isinstance(operator, bytes) else str(operator)
        try:
            if op == "q":
                stack.append(ctm)
            elif op == "Q":
                ctm = stack.pop() if stack else IDENTITY
            elif op == "cm":
                values = tuple(float(v) for v in operands)
                if len(values) == 6:
                    ctm = _multiply(values, ctm)  # type: ignore[arg-type]
            elif op == "re":
                x, y, w, h = (float(v) for v in operands)
                points.extend(
                    [
                        _apply(ctm, x, y),
                        _apply(ctm, x + w, y),
                        _apply(ctm, x + w, y + h),
                        _apply(ctm, x, y + h),
                    ]
                )
                flush()
            elif op == "m":
                flush()
                points.append(_apply(ctm, float(operands[0]), float(operands[1])))
            elif op == "l":
                points.append(_apply(ctm, float(operands[0]), float(operands[1])))
            elif op in ("c", "v", "y"):
                numbers = [float(v) for v in operands]
                for index in range(0, len(numbers) - 1, 2):
                    points.append(_apply(ctm, numbers[index], numbers[index + 1]))
            elif op in ("S", "s", "f", "F", "f*", "B", "B*", "b", "b*", "n"):
                flush()
        except (TypeError, ValueError):
            points = []
    flush()
    return boxes


def extract_horizontal_rules(page: Any, reader: Any) -> list[Rule]:
    """Every horizontal ruled line on ``page``, top-to-bottom then left-to-right."""
    seen: set[tuple[float, float, float]] = set()
    rules: list[Rule] = []
    for x0, y0, x1, y1 in _path_boxes(page, reader):
        if (y1 - y0) > MAX_RULE_HEIGHT or (x1 - x0) < MIN_RULE_WIDTH:
            continue
        key = (round(y0, 1), round(x0, 1), round(x1, 1))
        if key in seen:
            continue
        seen.add(key)
        rules.append(Rule(y=key[0], x0=key[1], x1=key[2]))
    rules.sort(key=lambda rule: (-rule.y, rule.x0))
    return rules


def group_rows(rules: list[Rule]) -> list[Row]:
    """Collapse rules onto shared baselines so a field is addressable as (row, column)."""
    rows: list[Row] = []
    bucket: list[Rule] = []
    for rule in rules:
        if bucket and abs(bucket[0].y - rule.y) > ROW_TOLERANCE:
            rows.append(Row(y=bucket[0].y, columns=tuple(bucket)))
            bucket = []
        bucket.append(rule)
    if bucket:
        rows.append(Row(y=bucket[0].y, columns=tuple(bucket)))
    return rows


def page_rows(page: Any, reader: Any) -> list[Row]:
    return group_rows(extract_horizontal_rules(page, reader))


def _linear_fit(pairs: list[tuple[float, float]]) -> tuple[float, float, float]:
    """Least-squares ``scale, offset, max_error`` mapping the first value to the second."""
    count = len(pairs)
    sum_x = sum(pair[0] for pair in pairs)
    sum_y = sum(pair[1] for pair in pairs)
    sum_xx = sum(pair[0] * pair[0] for pair in pairs)
    sum_xy = sum(pair[0] * pair[1] for pair in pairs)
    denominator = count * sum_xx - sum_x * sum_x
    if abs(denominator) < 1e-9:
        return 1.0, 0.0, float("inf")
    scale = (count * sum_xy - sum_x * sum_y) / denominator
    offset = (sum_y - scale * sum_x) / count
    error = max(abs(scale * pair[0] + offset - pair[1]) for pair in pairs)
    return scale, offset, error


@dataclass(frozen=True)
class LayoutFit:
    """Maps authored (nominal) coordinates onto one concrete rendering of a form.

    The ministry publishes the same form template at slightly different scales and
    offsets per residence-status variant. Nominal coordinates are authored once against
    a reference PDF; this fit carries them onto whichever variant was actually fetched,
    so a mark is never placed blind.
    """

    rows: tuple[Row, ...]
    nominal_row_y: tuple[float, ...]
    x_scale: float
    x_offset: float
    y_scale: float
    max_error: float

    def row(self, index: int) -> Row | None:
        if 0 <= index < len(self.rows):
            return self.rows[index]
        return None

    def column(self, row_index: int, column_index: int) -> Rule | None:
        row = self.row(row_index)
        return row.column(column_index) if row is not None else None

    def map_x(self, x: float) -> float:
        return self.x_scale * x + self.x_offset

    def map_y(self, y: float) -> float:
        """Map a nominal y relative to the nearest authored row.

        A single global y fit leaves a few points of residual because row heights are
        not perfectly proportional between variants. Anchoring locally removes it, which
        matters for a mark that has to land inside a printed glyph.
        """
        if not self.nominal_row_y:
            return y
        nearest = min(
            range(len(self.nominal_row_y)),
            key=lambda index: abs(self.nominal_row_y[index] - y),
        )
        return self.rows[nearest].y + (y - self.nominal_row_y[nearest]) * self.y_scale


def fit_layout(
    rows: list[Row],
    nominal_rows: tuple[tuple[float, tuple[float, ...]], ...],
    *,
    tolerance: float = 2.5,
) -> LayoutFit | None:
    """Align extracted ``rows`` with the authored ``nominal_rows``.

    Returns ``None`` when the page does not have the authored shape — a revised form, a
    different document, or a parse failure. Callers must treat that as "layout not
    verified" and fall back rather than guess at coordinates.
    """
    if len(rows) != len(nominal_rows):
        return None
    for row, (_nominal_y, nominal_columns) in zip(rows, nominal_rows, strict=True):
        if len(row.columns) * 2 != len(nominal_columns):
            return None

    x_pairs: list[tuple[float, float]] = []
    y_pairs: list[tuple[float, float]] = []
    for row, (nominal_y, nominal_columns) in zip(rows, nominal_rows, strict=True):
        y_pairs.append((nominal_y, row.y))
        for index, rule in enumerate(row.columns):
            x_pairs.append((nominal_columns[index * 2], rule.x0))
            x_pairs.append((nominal_columns[index * 2 + 1], rule.x1))
    if len(x_pairs) < 4 or len(y_pairs) < 2:
        return None

    x_scale, x_offset, x_error = _linear_fit(x_pairs)
    y_scale, _offset, _error = _linear_fit(y_pairs)
    if x_error > tolerance:
        return None
    return LayoutFit(
        rows=tuple(rows),
        nominal_row_y=tuple(nominal_y for nominal_y, _ in nominal_rows),
        x_scale=x_scale,
        x_offset=x_offset,
        y_scale=y_scale,
        max_error=x_error,
    )
