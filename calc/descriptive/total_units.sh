#!/usr/bin/env bash
# total_units.sh — Total units shipped for a facility over an optional date range.
#
# Family: descriptive
# Question answered: how many units did facility F ship between dates S and E?
# Schema: requires v1 operational schema
#
# Usage:
#   ./total_units.sh <facility_id> [--start YYYY-MM-DD] [--end YYYY-MM-DD]
#   ./total_units.sh dal-02 --start 2026-02-01 --end 2026-02-28
#
# Output: single integer (total units), or "NA" if no rows match.
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

awk -F',' -v start="$START" -v end="$END" -v col="$COL_UNITS" '
    NR == 1 { next }
    $col == "" { next }
    start != "" && $1 < start { next }
    end   != "" && $1 > end   { next }
    { sum += $col; n++ }
    END { if (n > 0) printf "%d\n", sum; else print "NA" }
' "$FILE"
