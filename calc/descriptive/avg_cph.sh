#!/usr/bin/env bash
# avg_cph.sh — Average CPH for a facility over an optional date range.
#
# Family: descriptive
# Question answered: what is the average CPH at facility F between dates S and E?
# Schema: requires v1 operational schema
#
# Usage:
#   ./avg_cph.sh <facility_id> [--start YYYY-MM-DD] [--end YYYY-MM-DD]
#   ./avg_cph.sh dal-02 --start 2026-02-01 --end 2026-03-01
#
# Output: single decimal number, 2 decimal places, or "NA" if no rows match.
# Exit codes: 0 success; 1 bad arguments; 2 data file not found.

set -euo pipefail
source "$(dirname "$0")/../lib/_schema_v1.sh"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <facility_id> [--start YYYY-MM-DD] [--end YYYY-MM-DD]" >&2
    exit 1
fi

FACILITY="$1"; shift
DATA_ROOT="${DATA_ROOT:-data/metrics/operational}"
FILE="${DATA_ROOT}/${FACILITY}.csv"
START=""
END=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --start) START="$2"; shift 2 ;;
        --end)   END="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

if [[ ! -f "$FILE" ]]; then
    echo "Data file not found: $FILE" >&2
    exit 2
fi

awk -F',' -v start="$START" -v end="$END" -v col="$COL_CPH" '
    NR == 1 { next }                                          # skip header
    $col !~ /^-?[0-9]+(\.[0-9]+)?$/ { next }                  # skip blank/non-numeric (zeros are valid)
    start != "" && $1 < start { next }
    end   != "" && $1 > end   { next }
    { sum += $col; n++ }
    END { if (n > 0) printf "%.2f\n", sum / n; else print "NA" }
' "$FILE"
