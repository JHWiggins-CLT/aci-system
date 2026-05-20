#!/usr/bin/env python3
"""adapter_template.py — scaffold for a PRODUCTION conversion adapter.

Copy this to e.g. conversion/scripts/convert_<source>.py and fill in the two
functions marked `FILL THIS IN`. Everything else — the canonical-CSV writers and
the validator calls — is wired for you, so a bad mapping fails loudly at the
conversion boundary instead of corrupting downstream calcs.

The contract this enforces (do not weaken it):
  - One CSV per (family, facility) at data/metrics/{family}/{facility}.csv
  - Columns in the EXACT schema order (see SCHEMAS, printed by --show-schema)
  - Rows sorted ascending by date, no nulls, values in range
  - Every write goes through write_csv_atomic + validate_metric_family

This file intentionally raises NotImplementedError until you implement the
mapping — it must never silently emit empty/placeholder data.

Usage (after you implement the FILL-THIS-IN parts):
  python conversion/scripts/convert_<source>.py            # convert all facilities
  python conversion/scripts/convert_<source>.py --show-schema
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "conversion"))
from validation.common import (  # noqa: E402
    SCHEMAS,
    ValidationReport,
    assert_passed,
    read_csv,
    validate_metric_family,
    write_csv_atomic,
)

DATA_DIR = REPO_ROOT / "data"
METRICS_DIR = DATA_DIR / "metrics"
FAMILIES = ("operational", "inputs", "exceptions", "equipment")


# --- FILL THIS IN (1/2): which facilities does your source cover? -------------
def facilities() -> list[str]:
    """Return the facility IDs this adapter produces (must match data/facilities/INDEX.md)."""
    raise NotImplementedError("List your facility IDs, e.g. return ['dal-02', 'hou-01']")


# --- FILL THIS IN (2/2): map your source → canonical rows for one family ------
def rows_for(facility_id: str, family: str) -> list[list]:
    """Read your source for this facility+family and return rows in SCHEMAS[family] order.

    Each row is a list whose values line up 1:1 with SCHEMAS[family]. For example,
    an `operational` row is [date, facility_id, units, cph, error_rate, hours_run]
    with date as 'YYYY-MM-DD'. Sort rows ascending by date.

    This is the only bespoke part: read your Excel/CSV/WMS export here and map its
    columns onto the canonical schema. Have the operator confirm each field mapping.
    The validators below will reject anything malformed before it lands.
    """
    raise NotImplementedError(
        f"Map your source rows for {facility_id}/{family} onto SCHEMAS['{family}']"
    )


def write_family(facility_id: str, family: str, min_rows: int = 1) -> Path:
    """Write + validate one canonical CSV. Mirrors the simulator's write path."""
    header = list(SCHEMAS[family])
    rows = rows_for(facility_id, family)
    target = METRICS_DIR / family / f"{facility_id}.csv"
    write_csv_atomic(target, header, rows)
    report = ValidationReport(
        script=Path(__file__).name,
        target=str(target.relative_to(REPO_ROOT)).replace("\\", "/"),
    )
    validate_metric_family(family, read_csv(target), facility_id, min_rows, report)
    report.write_log()
    assert_passed(report)  # raises ValidationError on any failure — the safety net
    return target


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Production conversion adapter (scaffold).")
    ap.add_argument("--show-schema", action="store_true",
                    help="print the canonical column order for each family and exit")
    ap.add_argument("--min-rows", type=int, default=1,
                    help="minimum rows required per CSV (set to your real data horizon)")
    args = ap.parse_args(argv)

    if args.show_schema:
        for fam in FAMILIES:
            print(f"{fam}: {', '.join(SCHEMAS[fam])}")
        return 0

    written = 0
    for fac in facilities():
        for fam in FAMILIES:
            path = write_family(fac, fam, args.min_rows)
            print(f"  wrote + validated: {path.relative_to(REPO_ROOT)}")
            written += 1
    print(f"\nConverted {written} CSV(s) across {len(facilities())} facilities. "
          f"All passed validation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
