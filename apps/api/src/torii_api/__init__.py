"""Torii API — the immigration form-preparation system of record.

Users and accounts, jurisdictions and their visa/eligibility/document rules, the canonical
case pipeline, form definitions and versioned field mappings, the document vault, payments,
and the immutable audit log. Rule evaluation is deterministic and lives here, never in a
model (docs/specs/03_architecture.md, NF-1).
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("torii-api")
except PackageNotFoundError:  # pragma: no cover - running from uninstalled source
    __version__ = "0.0.0+unknown"
