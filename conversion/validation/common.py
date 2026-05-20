"""Shared validation routines for the conversion boundary.

Every conversion script (including the deterministic simulator) calls these
before writing a CSV into `data/metrics/` or `data/events/`. If any check
fails, the run aborts non-zero and a failure log is written to
`conversion/logs/`. The script does NOT write a partial or invalid CSV.

The validators are intentionally strict. Weakening a validator to make a
stubborn source pass is the most dangerous slow-corruption failure mode for
this architecture; fix the source or the script instead.

Schema column orders match `data/metrics/MANIFEST.md` (schema v1).
"""

from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = REPO_ROOT / "conversion" / "logs"


class ValidationError(Exception):
    """Raised when a validator fails. Causes the run to abort."""


@dataclass
class ValidationReport:
    script: str
    target: str
    checks_run: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    row_count: int = 0

    @property
    def passed(self) -> bool:
        return not self.failures

    def write_log(self, run_date: str | None = None) -> Path:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        stamp = run_date or dt.date.today().isoformat()
        safe_target = self.target.replace("/", "_").replace("\\", "_")
        log_path = LOG_DIR / f"{stamp}_{self.script}_{safe_target}.log"
        status = "PASS" if self.passed else "FAIL"
        lines = [
            f"script:     {self.script}",
            f"target:     {self.target}",
            f"row_count:  {self.row_count}",
            f"status:     {status}",
            "checks_run:",
            *(f"  - {c}" for c in self.checks_run),
        ]
        if self.failures:
            lines.append("failures:")
            lines.extend(f"  - {f}" for f in self.failures)
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return log_path


# --- Schemas (column order per data/metrics/MANIFEST.md, v1) -----------------

SCHEMAS: dict[str, list[str]] = {
    "operational": [
        "date", "facility_id", "units", "cph", "error_rate", "hours_run",
    ],
    "inputs": [
        "date", "facility_id", "headcount_total", "headcount_new",
        "headcount_shift1", "headcount_shift2", "headcount_shift3",
        "inbound_units", "order_mix_complex",
    ],
    "exceptions": [
        "date", "facility_id", "damage", "missort", "mispick", "lost",
        "late_pick",
    ],
    "equipment": [
        "date", "facility_id", "conveyor_down_m", "mhe_down_m",
        "wms_incidents", "scanner_faults",
    ],
    "events": [
        "date", "facility_id", "event_type", "description", "source",
    ],
    "events_network": [
        "date", "event_type", "description", "source",
    ],
}

# Numeric column sanity ranges (min, max) per family.
NUMERIC_RANGES: dict[str, dict[str, tuple[float, float]]] = {
    "operational": {
        "units":      (0, 200_000),
        "cph":        (0, 500),
        "error_rate": (0, 50),
        "hours_run":  (0, 100),
    },
    "inputs": {
        "headcount_total":    (0, 2_000),
        "headcount_new":      (0, 500),
        "headcount_shift1":   (0, 1_000),
        "headcount_shift2":   (0, 1_000),
        "headcount_shift3":   (0, 1_000),
        "inbound_units":      (0, 250_000),
        "order_mix_complex":  (0.0, 1.0),
    },
    "exceptions": {
        "damage":    (0, 5_000),
        "missort":   (0, 5_000),
        "mispick":   (0, 5_000),
        "lost":      (0, 5_000),
        "late_pick": (0, 5_000),
    },
    "equipment": {
        "conveyor_down_m": (0, 1_440),  # minutes in a day
        "mhe_down_m":      (0, 1_440),
        "wms_incidents":   (0, 100),
        "scanner_faults":  (0, 500),
    },
}

EVENT_TYPES = {
    "system_change", "deployment", "training", "incident",
    "leadership_change", "sop_change", "weather", "holiday", "audit",
    "equipment_install", "volume_shock",
}


# --- Individual validators ---------------------------------------------------

def validate_header(rows: Sequence[Sequence[str]], expected: Sequence[str],
                    report: ValidationReport) -> None:
    report.checks_run.append("header matches schema")
    if not rows:
        report.failures.append("empty file (no header row)")
        return
    if list(rows[0]) != list(expected):
        report.failures.append(
            f"header mismatch: got {rows[0]!r}, expected {list(expected)!r}"
        )


def validate_date_column(rows: Sequence[Sequence[str]], col: int,
                         report: ValidationReport) -> None:
    report.checks_run.append(f"date column ({col}) is YYYY-MM-DD")
    bad = []
    for i, row in enumerate(rows[1:], start=2):
        val = row[col] if col < len(row) else ""
        try:
            dt.date.fromisoformat(val)
        except ValueError:
            bad.append((i, val))
    if bad:
        sample = ", ".join(f"row {i}: {v!r}" for i, v in bad[:3])
        report.failures.append(
            f"{len(bad)} rows have malformed date in column {col} ({sample})"
        )


def validate_facility_match(rows: Sequence[Sequence[str]], col: int,
                            expected_id: str,
                            report: ValidationReport) -> None:
    report.checks_run.append(f"facility_id column ({col}) == {expected_id!r}")
    bad = []
    for i, row in enumerate(rows[1:], start=2):
        val = row[col] if col < len(row) else ""
        if val != expected_id:
            bad.append((i, val))
    if bad:
        sample = ", ".join(f"row {i}: {v!r}" for i, v in bad[:3])
        report.failures.append(
            f"{len(bad)} rows have non-matching facility_id ({sample})"
        )


def validate_no_nulls(rows: Sequence[Sequence[str]], columns: Iterable[int],
                      report: ValidationReport) -> None:
    columns = list(columns)
    report.checks_run.append(f"no nulls in columns {columns}")
    for i, row in enumerate(rows[1:], start=2):
        for col in columns:
            if col >= len(row) or row[col] == "":
                report.failures.append(f"row {i} has null in column {col}")
                return


def validate_numeric_range(rows: Sequence[Sequence[str]], col: int,
                           col_name: str, lo: float, hi: float,
                           report: ValidationReport) -> None:
    report.checks_run.append(
        f"column {col} ({col_name}) in [{lo}, {hi}]"
    )
    bad = []
    for i, row in enumerate(rows[1:], start=2):
        try:
            v = float(row[col])
        except (ValueError, IndexError):
            bad.append((i, row[col] if col < len(row) else ""))
            continue
        if v < lo or v > hi:
            bad.append((i, v))
    if bad:
        sample = ", ".join(f"row {i}: {v!r}" for i, v in bad[:3])
        report.failures.append(
            f"{len(bad)} rows out of range for {col_name} ({sample})"
        )


def validate_row_count(rows: Sequence[Sequence[str]], min_expected: int,
                       report: ValidationReport) -> None:
    data_rows = max(0, len(rows) - 1)  # exclude header
    report.row_count = data_rows
    report.checks_run.append(f"row count >= {min_expected}")
    if data_rows < min_expected:
        report.failures.append(
            f"only {data_rows} data rows; expected >= {min_expected}"
        )


def validate_event_types(rows: Sequence[Sequence[str]], col: int,
                         report: ValidationReport) -> None:
    report.checks_run.append(f"event_type column ({col}) is in taxonomy")
    bad = []
    for i, row in enumerate(rows[1:], start=2):
        val = row[col] if col < len(row) else ""
        if val not in EVENT_TYPES:
            bad.append((i, val))
    if bad:
        sample = ", ".join(f"row {i}: {v!r}" for i, v in bad[:3])
        report.failures.append(
            f"{len(bad)} rows have unknown event_type ({sample})"
        )


def validate_dates_sorted_ascending(rows: Sequence[Sequence[str]], col: int,
                                    report: ValidationReport) -> None:
    report.checks_run.append(f"date column ({col}) is sorted ascending")
    prev = None
    for i, row in enumerate(rows[1:], start=2):
        val = row[col] if col < len(row) else ""
        if prev is not None and val < prev:
            report.failures.append(
                f"row {i}: date {val!r} precedes previous {prev!r}"
            )
            return
        prev = val


# --- Family-specific bundles -------------------------------------------------

def validate_metric_family(family: str, rows: Sequence[Sequence[str]],
                           expected_facility: str | None,
                           min_rows: int,
                           report: ValidationReport) -> None:
    """Run the full validation bundle for a metric family CSV."""
    schema = SCHEMAS[family]
    validate_header(rows, schema, report)
    if report.failures:
        return
    validate_row_count(rows, min_rows, report)
    validate_date_column(rows, schema.index("date"), report)
    validate_dates_sorted_ascending(rows, schema.index("date"), report)
    if expected_facility is not None and "facility_id" in schema:
        validate_facility_match(
            rows, schema.index("facility_id"), expected_facility, report,
        )
    validate_no_nulls(rows, range(len(schema)), report)
    for col_name, (lo, hi) in NUMERIC_RANGES.get(family, {}).items():
        validate_numeric_range(rows, schema.index(col_name), col_name,
                               lo, hi, report)


def validate_events_file(rows: Sequence[Sequence[str]],
                         expected_facility: str | None,
                         report: ValidationReport,
                         min_rows: int = 0) -> None:
    family = "events_network" if expected_facility is None else "events"
    schema = SCHEMAS[family]
    validate_header(rows, schema, report)
    if report.failures:
        return
    validate_row_count(rows, min_rows, report)
    validate_date_column(rows, schema.index("date"), report)
    validate_dates_sorted_ascending(rows, schema.index("date"), report)
    if expected_facility is not None:
        validate_facility_match(
            rows, schema.index("facility_id"), expected_facility, report,
        )
    validate_event_types(rows, schema.index("event_type"), report)
    validate_no_nulls(rows, range(len(schema)), report)


# --- File-level helpers ------------------------------------------------------

def read_csv(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


def write_csv_atomic(path: Path, header: Sequence[str],
                     rows: Iterable[Sequence[object]]) -> None:
    """Write a CSV via a temp-and-rename so a failed run never leaves a partial."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(header)
        for r in rows:
            writer.writerow(r)
    tmp.replace(path)


def assert_passed(report: ValidationReport) -> None:
    """Raise ValidationError if the report has any failures."""
    if not report.passed:
        raise ValidationError(
            f"{report.script} → {report.target}: "
            + "; ".join(report.failures)
        )
