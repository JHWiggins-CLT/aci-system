#!/usr/bin/env bash
# month_summary.sh — Multi-metric monthly summary for a facility.
#
# Family: descriptive
# Question answered: how did facility F perform across all operational metrics
#                    in a given month?
# Schema: requires v1 operational schema
#
# Reports five numbers per month, computed from rows whose date is in YYYY-MM:
#   days          — number of days with data
#   total_units   — sum of units
#   avg_cph       — mean of cph
#   avg_error_rate — mean of error_rate (as a percent — same units as the column)
#   avg_hours_run — mean of hours_run
#
# Usage:
#   ./month_summary.sh <facility_id> --month YYYY-MM
#   ./month_summary.sh dal-02 --month 2026-02
#
# Output: 5 lines, one per metric, "label | value".
# Exit codes: 0 success; 1 bad arguments; 2 data file not found.

set -euo pipefail
source "$(dirname "$0")/../lib/_schema_v1.sh"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <facility_id> --month YYYY-MM" >&2
    exit 1
fi

FACILITY="$1"; shift
MONTH=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --month) MONTH="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "$MONTH" ]]; then
    echo "Required: --month YYYY-MM" >&2
    exit 1
fi

if [[ ! "$MONTH" =~ ^[0-9]{4}-[0-9]{2}$ ]]; then
    echo "Bad --month format: $MONTH (expected YYYY-MM)" >&2
    exit 1
fi

DATA_ROOT="${DATA_ROOT:-data/metrics/operational}"
FILE="${DATA_ROOT}/${FACILITY}.csv"
[[ -f "$FILE" ]] || { echo "Data file not found: $FILE" >&2; exit 2; }

awk -F',' \
    -v month="$MONTH" \
    -v c_units="$COL_UNITS" \
    -v c_cph="$COL_CPH" \
    -v c_err="$COL_ERROR_RATE" \
    -v c_hrs="$COL_HOURS_RUN" '
    NR == 1 { next }
    substr($1, 1, 7) != month { next }
    {
        n++
        if ($c_units ~ /^-?[0-9]+(\.[0-9]+)?$/) { u_sum   += $c_units }
        if ($c_cph   ~ /^-?[0-9]+(\.[0-9]+)?$/) { cph_sum += $c_cph; cph_n++ }
        if ($c_err   ~ /^-?[0-9]+(\.[0-9]+)?$/) { err_sum += $c_err; err_n++ }
        if ($c_hrs   ~ /^-?[0-9]+(\.[0-9]+)?$/) { hrs_sum += $c_hrs; hrs_n++ }
    }
    END {
        if (n == 0) {
            print "days | 0"
            print "total_units | NA"
            print "avg_cph | NA"
            print "avg_error_rate | NA"
            print "avg_hours_run | NA"
            exit
        }
        printf "days | %d\n", n
        printf "total_units | %d\n", u_sum
        if (cph_n > 0) printf "avg_cph | %.2f\n", cph_sum / cph_n; else print "avg_cph | NA"
        if (err_n > 0) printf "avg_error_rate | %.2f\n", err_sum / err_n; else print "avg_error_rate | NA"
        if (hrs_n > 0) printf "avg_hours_run | %.2f\n", hrs_sum / hrs_n; else print "avg_hours_run | NA"
    }
' "$FILE"
