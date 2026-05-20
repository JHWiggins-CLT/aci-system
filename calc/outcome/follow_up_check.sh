#!/usr/bin/env bash
# follow_up_check.sh — Did metric M hit target T at facility F by date D?
#
# Family: outcome
# Question answered: did the intervention work, as measured by the metric
#                    reaching its target by the follow-up date?
# Schema: requires v1 operational schema
#
# The calc compares the metric's average over a recent window ending on the
# follow-up date against the target. Supports both directions:
#   --target N    pass condition: average >= N (use for metrics that should rise)
#   --max N       pass condition: average <= N (use for metrics like error_rate
#                 or any exceptions metric — damage, mispick — that should fall)
#
# Metric family defaults to operational; use --family to track another family.
# This is what lets an outcome check verify the metric that actually moved
# (e.g. exceptions/damage) rather than an operational proxy.
#
# Usage:
#   ./follow_up_check.sh <facility_id> <metric> --target N --by YYYY-MM-DD \
#       [--family F] [--baseline YYYY-MM] [--window-days N]
#   ./follow_up_check.sh dal-02 cph --target 138 --by 2026-04-08 --baseline 2026-02
#   ./follow_up_check.sh chr-03 damage --max 20 --by 2026-06-19 --family exceptions
#
# Defaults:
#   --window-days: 14 (averages the metric over the 14 days ending on --by)
#
# Output: a 5-line block:
#   FACILITY: dal-02
#   METRIC: cph
#   AS-OF DATE: 2026-04-08
#   ACTUAL: 139.21 (window: 2026-03-26 to 2026-04-08)
#   TARGET: >= 138.00  RESULT: PASS
#
# Exit codes: 0 PASS, 1 FAIL, 2 bad args, 3 data not found / window empty.

set -euo pipefail
source "$(dirname "$0")/../lib/_schema_v1.sh"

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <facility_id> <metric> --target N --by D [--max N] [--baseline YYYY-MM] [--window-days N]" >&2
    exit 2
fi

FACILITY="$1"
METRIC="$2"
shift 2

TARGET_MIN=""
TARGET_MAX=""
BY_DATE=""
BASELINE=""
WINDOW_DAYS=14
FAMILY="operational"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target)       TARGET_MIN="$2"; shift 2 ;;
        --max)          TARGET_MAX="$2"; shift 2 ;;
        --by)           BY_DATE="$2"; shift 2 ;;
        --baseline)     BASELINE="$2"; shift 2 ;;
        --window-days)  WINDOW_DAYS="$2"; shift 2 ;;
        --family)       FAMILY="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done

if [[ -z "$BY_DATE" ]]; then
    echo "Required: --by YYYY-MM-DD" >&2
    exit 2
fi
if [[ -z "$TARGET_MIN" && -z "$TARGET_MAX" ]]; then
    echo "Required: --target N or --max N" >&2
    exit 2
fi

COL=$(col_for "$FAMILY" "$METRIC") || {
    echo "Unknown metric '$METRIC' in family '$FAMILY'" >&2; exit 2; }

DATA_ROOT="${DATA_ROOT:-data/metrics/${FAMILY}}"
FILE="${DATA_ROOT}/${FACILITY}.csv"
[[ -f "$FILE" ]] || { echo "Data file not found: $FILE" >&2; exit 3; }

# Compute window start date.
if date --version >/dev/null 2>&1; then
    WIN_START=$(date -d "${BY_DATE} -$((WINDOW_DAYS - 1)) days" +%Y-%m-%d)
else
    WIN_START=$(date -j -v-$((WINDOW_DAYS - 1))d -f "%Y-%m-%d" "${BY_DATE}" +%Y-%m-%d)
fi

ACTUAL=$(awk -F',' -v start="$WIN_START" -v end="$BY_DATE" -v col="$COL" '
    NR == 1 { next }
    $col !~ /^-?[0-9]+(\.[0-9]+)?$/ { next }                  # skip blank/non-numeric (zeros are valid)
    $1 >= start && $1 <= end { sum += $col; n++ }
    END { if (n > 0) printf "%.2f", sum / n; else printf "NA" }
' "$FILE")

if [[ "$ACTUAL" == "NA" ]]; then
    echo "FACILITY: $FACILITY"
    echo "METRIC: $METRIC"
    echo "AS-OF DATE: $BY_DATE"
    echo "ACTUAL: NA (no data in window $WIN_START to $BY_DATE)"
    if [[ -n "$TARGET_MIN" ]]; then
        echo "TARGET: >= $TARGET_MIN  RESULT: NO DATA"
    else
        echo "TARGET: <= $TARGET_MAX  RESULT: NO DATA"
    fi
    exit 3
fi

if [[ -n "$TARGET_MIN" ]]; then
    RESULT=$(awk -v a="$ACTUAL" -v t="$TARGET_MIN" \
        'BEGIN { print (a + 0 >= t + 0) ? "PASS" : "FAIL" }')
    TARGET_LINE=">= $TARGET_MIN"
else
    RESULT=$(awk -v a="$ACTUAL" -v t="$TARGET_MAX" \
        'BEGIN { print (a + 0 <= t + 0) ? "PASS" : "FAIL" }')
    TARGET_LINE="<= $TARGET_MAX"
fi

echo "FACILITY: $FACILITY"
echo "METRIC: $METRIC"
echo "AS-OF DATE: $BY_DATE"
echo "ACTUAL: $ACTUAL (window: $WIN_START to $BY_DATE)"
echo "TARGET: $TARGET_LINE  RESULT: $RESULT"

[[ "$RESULT" == "PASS" ]] && exit 0 || exit 1
