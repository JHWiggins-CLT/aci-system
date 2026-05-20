#!/usr/bin/env bash
# avg.sh — Average any metric for a facility over an optional date range.
#
# Family: descriptive
# Question answered: what is the average of metric M at facility F between dates
#                    S and E? The family-aware generalization of avg_cph.sh, so
#                    a damage/mispick/downtime signal can be confirmed with the
#                    same clean three-number (baseline / dip / recovery) magnitude
#                    check that throughput investigations use for cph.
# Schema: requires v1 (any family — operational, inputs, exceptions, equipment).
#
# Metric family defaults to operational; use --family for another family:
#   --family exceptions   (damage, missort, mispick, lost, late_pick)
#   --family inputs       (headcount_new, inbound_units, order_mix_complex, ...)
#   --family equipment    (conveyor_down_m, mhe_down_m, wms_incidents, ...)
#
# Usage:
#   ./avg.sh <facility_id> <metric> [--family F] [--start YYYY-MM-DD] [--end YYYY-MM-DD]
#   ./avg.sh dal-02 cph --start 2026-02-01 --end 2026-02-28
#   ./avg.sh chr-03 damage --family exceptions --start 2026-04-12 --end 2026-04-24
#
# Output: single decimal number, 2 decimal places, or "NA" if no rows match.
# Exit codes: 0 success; 1 bad arguments; 2 data file not found.

set -euo pipefail
source "$(dirname "$0")/../lib/_schema_v1.sh"

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <facility_id> <metric> [--family F] [--start YYYY-MM-DD] [--end YYYY-MM-DD]" >&2
    exit 1
fi

FACILITY="$1"
METRIC="$2"
shift 2

START=""
END=""
FAMILY="operational"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --start)  START="$2"; shift 2 ;;
        --end)    END="$2"; shift 2 ;;
        --family) FAMILY="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

COL=$(col_for "$FAMILY" "$METRIC") || {
    echo "Unknown metric '$METRIC' in family '$FAMILY'" >&2; exit 1; }

DATA_ROOT="${DATA_ROOT:-data/metrics/${FAMILY}}"
FILE="${DATA_ROOT}/${FACILITY}.csv"
[[ -f "$FILE" ]] || { echo "Data file not found: $FILE" >&2; exit 2; }

awk -F',' -v start="$START" -v end="$END" -v col="$COL" '
    NR == 1 { next }                                          # skip header
    $col !~ /^-?[0-9]+(\.[0-9]+)?$/ { next }                  # skip blank/non-numeric (zeros are valid)
    start != "" && $1 < start { next }
    end   != "" && $1 > end   { next }
    { sum += $col; n++ }
    END { if (n > 0) printf "%.2f\n", sum / n; else print "NA" }
' "$FILE"
