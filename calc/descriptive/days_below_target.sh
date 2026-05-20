#!/usr/bin/env bash
# days_below_target.sh — Count days where a metric fell below (or above) a target.
#
# Family: descriptive
# Question answered: how many days did facility F miss target T on metric M between
#                    dates S and E?
# Schema: requires v1 operational schema
#
# Two directions supported:
#   --target N   counts days where metric < N      (use for cph/units/hours_run)
#   --max N      counts days where metric > N      (use for error_rate, damage, etc.)
#
# Metric family defaults to operational; use --family to scan another family:
#   --family operational  (cph, units, error_rate, hours_run) [default]
#   --family exceptions   (damage, missort, mispick, lost, late_pick)
#   --family inputs       (headcount_new, inbound_units, ...)
#   --family equipment    (conveyor_down_m, mhe_down_m, ...)
#
# Usage:
#   ./days_below_target.sh <facility_id> <metric> --target N [--start S] [--end E]
#   ./days_below_target.sh <facility_id> <metric> --max N    [--family F] [--start S] [--end E]
#   ./days_below_target.sh dal-02 cph --target 138 --start 2026-03-08 --end 2026-03-22
#   ./days_below_target.sh chr-03 damage --max 20 --family exceptions --start 2026-04-12 --end 2026-04-24
#
# Output:
#   <count>/<total_days_in_window>
#   e.g.  9/15
#   If no rows match: NA
#
# Exit codes: 0 success; 1 bad arguments; 2 data file not found.

set -euo pipefail
source "$(dirname "$0")/../lib/_schema_v1.sh"

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <facility_id> <metric> --target N|--max N [--family F] [--start S] [--end E]" >&2
    exit 1
fi

FACILITY="$1"
METRIC="$2"
shift 2

TARGET_MIN=""
TARGET_MAX=""
START=""
END=""
FAMILY="operational"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target) TARGET_MIN="$2"; shift 2 ;;
        --max)    TARGET_MAX="$2"; shift 2 ;;
        --family) FAMILY="$2"; shift 2 ;;
        --start)  START="$2"; shift 2 ;;
        --end)    END="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "$TARGET_MIN" && -z "$TARGET_MAX" ]]; then
    echo "Required: --target N or --max N" >&2
    exit 1
fi

COL=$(col_for "$FAMILY" "$METRIC") || {
    echo "Unknown metric '$METRIC' in family '$FAMILY'" >&2; exit 1; }

DATA_ROOT="${DATA_ROOT:-data/metrics/${FAMILY}}"
FILE="${DATA_ROOT}/${FACILITY}.csv"
[[ -f "$FILE" ]] || { echo "Data file not found: $FILE" >&2; exit 2; }

awk -F',' \
    -v start="$START" -v end="$END" -v col="$COL" \
    -v tmin="$TARGET_MIN" -v tmax="$TARGET_MAX" '
    NR == 1 { next }
    $col == "" { next }
    start != "" && $1 < start { next }
    end   != "" && $1 > end   { next }
    {
        n++
        v = $col + 0
        if (tmin != "" && v < tmin + 0) below++
        if (tmax != "" && v > tmax + 0) below++
    }
    END {
        if (n == 0) { print "NA"; exit }
        printf "%d/%d\n", below + 0, n
    }
' "$FILE"
