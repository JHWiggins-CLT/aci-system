#!/usr/bin/env bash
# countermeasure_effectiveness.sh — Did metric M change between a pre-intervention
# and a post-intervention window?
#
# Family: outcome
# Question answered: after a countermeasure was put in place, did the metric move,
#                    and in the better or worse direction?
# Schema: requires v1; reads one metric family (default operational).
#
# Compares the metric's mean over a PRE window against its mean over a POST
# window, reports the delta and relative change, and renders a direction-aware
# verdict (IMPROVED / WORSENED / UNCHANGED) using worse_direction() so the same
# calc reads correctly for "higher is better" metrics (cph) and "lower is better"
# metrics (damage, error_rate, downtime).
#
# Metric family defaults to operational; use --family to track another family
# (e.g. the exceptions metric that actually moved, not an operational proxy).
#
# Usage:
#   ./countermeasure_effectiveness.sh <facility> <metric> \
#       --pre S:E --post S:E [--family F]
#   ./countermeasure_effectiveness.sh dal-02 cph \
#       --pre 2026-03-06:2026-03-09 --post 2026-03-11:2026-03-14
#   ./countermeasure_effectiveness.sh chr-03 damage \
#       --pre 2026-04-12:2026-04-24 --post 2026-05-05:2026-05-18 --family exceptions
#
# Output (labeled block):
#   FACILITY: dal-02
#   METRIC: cph (family: operational)
#   PRE:  127.00 (window: 2026-03-06 to 2026-03-09, n=4)
#   POST: 138.50 (window: 2026-03-11 to 2026-03-14, n=4)
#   DELTA: +11.50 (+9.06%)
#   DIRECTION: higher is better
#   RESULT: IMPROVED
#
# Exit codes: 0 IMPROVED, 1 WORSENED or UNCHANGED, 2 bad args, 3 data/window empty.

set -euo pipefail
source "$(dirname "$0")/../lib/_schema_v1.sh"

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <facility> <metric> --pre S:E --post S:E [--family F]" >&2
    exit 2
fi

FACILITY="$1"
METRIC="$2"
shift 2

PRE=""
POST=""
FAMILY="operational"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --pre)    PRE="$2"; shift 2 ;;
        --post)   POST="$2"; shift 2 ;;
        --family) FAMILY="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done

if [[ -z "$PRE" || -z "$POST" ]]; then
    echo "Required: --pre S:E and --post S:E" >&2
    exit 2
fi

COL=$(col_for "$FAMILY" "$METRIC") || {
    echo "Unknown metric '$METRIC' in family '$FAMILY'" >&2; exit 2; }

DATA_ROOT="${DATA_ROOT:-data/metrics/${FAMILY}}"
FILE="${DATA_ROOT}/${FACILITY}.csv"
[[ -f "$FILE" ]] || { echo "Data file not found: $FILE" >&2; exit 3; }

PRE_START="${PRE%%:*}";   PRE_END="${PRE##*:}"
POST_START="${POST%%:*}"; POST_END="${POST##*:}"

# mean_window <start> <end> -> "mean4 n" (mean to 4dp), or "NA 0" if empty.
mean_window() {
    awk -F',' -v start="$1" -v end="$2" -v col="$COL" '
        NR == 1 { next }
        $col !~ /^-?[0-9]+(\.[0-9]+)?$/ { next }     # skip blank/non-numeric, keep real zeros
        $1 >= start && $1 <= end { sum += $col; n++ }
        END { if (n > 0) printf "%.4f %d", sum / n, n; else printf "NA 0" }
    ' "$FILE"
}

read -r PRE_MEAN  PRE_N  <<<"$(mean_window "$PRE_START"  "$PRE_END")"
read -r POST_MEAN POST_N <<<"$(mean_window "$POST_START" "$POST_END")"

if [[ "$PRE_MEAN" == "NA" || "$POST_MEAN" == "NA" ]]; then
    echo "FACILITY: $FACILITY"
    echo "METRIC: $METRIC (family: $FAMILY)"
    [[ "$PRE_MEAN"  == "NA" ]] && echo "PRE:  NA (no data in window $PRE_START to $PRE_END)"
    [[ "$POST_MEAN" == "NA" ]] && echo "POST: NA (no data in window $POST_START to $POST_END)"
    echo "RESULT: NO DATA"
    exit 3
fi

DIR=$(worse_direction "$FAMILY" "$METRIC")   # min => lower is worse (higher better); max => higher is worse
if [[ "$DIR" == "min" ]]; then
    DIR_LABEL="higher is better"
else
    DIR_LABEL="lower is better"
fi

# Delta, relative change, and verdict. The verdict keys off the 2dp-rounded delta
# so a change that displays as +0.00 reads UNCHANGED rather than IMPROVED/WORSENED.
read -r DELTA REL RESULT <<<"$(awk -v pre="$PRE_MEAN" -v post="$POST_MEAN" -v dir="$DIR" 'BEGIN {
    d  = post - pre
    dr = sprintf("%.2f", d) + 0
    r  = (pre != 0) ? (d / pre) * 100 : 0
    verdict = "UNCHANGED"
    if      (dr > 0) verdict = (dir == "min") ? "IMPROVED" : "WORSENED"
    else if (dr < 0) verdict = (dir == "min") ? "WORSENED" : "IMPROVED"
    printf "%+.2f %+.2f %s", d, r, verdict
}')"

PRE_DISP=$(awk  -v m="$PRE_MEAN"  'BEGIN { printf "%.2f", m }')
POST_DISP=$(awk -v m="$POST_MEAN" 'BEGIN { printf "%.2f", m }')

echo "FACILITY: $FACILITY"
echo "METRIC: $METRIC (family: $FAMILY)"
echo "PRE:  $PRE_DISP (window: $PRE_START to $PRE_END, n=$PRE_N)"
echo "POST: $POST_DISP (window: $POST_START to $POST_END, n=$POST_N)"
echo "DELTA: $DELTA ($REL%)"
echo "DIRECTION: $DIR_LABEL"
echo "RESULT: $RESULT"

[[ "$RESULT" == "IMPROVED" ]] && exit 0 || exit 1
