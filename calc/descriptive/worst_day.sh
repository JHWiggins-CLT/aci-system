#!/usr/bin/env bash
# worst_day.sh — The single worst day for a metric in a window.
#
# Family: descriptive
# Question answered: which date had the worst value of metric M at facility F
#                    between dates S and E?
# Schema: requires v1 operational schema
#
# Direction is auto-detected from the metric/family — lower is worse for cph,
# units, and hours_run; higher is worse for error_rate and for every exceptions
# and equipment metric. Override with --direction:
#   --direction min   (lower is worse — default for cph/units/hours_run)
#   --direction max   (higher is worse — default for error_rate, damage, downtime)
#
# Metric family defaults to operational; use --family for another family:
#   --family exceptions   (damage, missort, mispick, lost, late_pick)
#   --family equipment    (conveyor_down_m, mhe_down_m, ...)
#
# Usage:
#   ./worst_day.sh <facility_id> <metric> [--family F] [--start S] [--end E] [--direction min|max]
#   ./worst_day.sh dal-02 cph --start 2026-03-08 --end 2026-03-22
#   ./worst_day.sh chr-03 damage --family exceptions --start 2026-04-12 --end 2026-04-24
#
# Output: one line "YYYY-MM-DD | <value>" or "NA" if no rows match.
# Exit codes: 0 success; 1 bad arguments; 2 data file not found.

set -euo pipefail
source "$(dirname "$0")/../lib/_schema_v1.sh"

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <facility_id> <metric> [--family F] [--start S] [--end E] [--direction min|max]" >&2
    exit 1
fi

FACILITY="$1"
METRIC="$2"
shift 2

START=""
END=""
DIRECTION=""
FAMILY="operational"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --start)     START="$2"; shift 2 ;;
        --end)       END="$2"; shift 2 ;;
        --direction) DIRECTION="$2"; shift 2 ;;
        --family)    FAMILY="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

COL=$(col_for "$FAMILY" "$METRIC") || {
    echo "Unknown metric '$METRIC' in family '$FAMILY'" >&2; exit 1; }

DIRECTION="${DIRECTION:-$(worse_direction "$FAMILY" "$METRIC")}"
case "$DIRECTION" in
    min|max) ;;
    *) echo "Unknown direction: $DIRECTION (use min or max)" >&2; exit 1 ;;
esac

DATA_ROOT="${DATA_ROOT:-data/metrics/${FAMILY}}"
FILE="${DATA_ROOT}/${FACILITY}.csv"
[[ -f "$FILE" ]] || { echo "Data file not found: $FILE" >&2; exit 2; }

awk -F',' -v start="$START" -v end="$END" -v col="$COL" -v dir="$DIRECTION" '
    NR == 1 { next }
    $col == "" { next }
    start != "" && $1 < start { next }
    end   != "" && $1 > end   { next }
    {
        v = $col + 0
        if (n == 0) {
            best_v = v; best_date = $1
        } else if (dir == "min" && v < best_v) {
            best_v = v; best_date = $1
        } else if (dir == "max" && v > best_v) {
            best_v = v; best_date = $1
        }
        n++
    }
    END {
        if (n == 0) { print "NA"; exit }
        printf "%s | %.2f\n", best_date, best_v
    }
' "$FILE"
