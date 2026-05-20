#!/usr/bin/env bash
# correlate.sh — Pearson correlation between two metric columns at one facility.
#
# Family: diagnostic
# Question answered: do metric A and metric B move together at facility F?
#                    (e.g. does CPH fall as new-hire headcount rises?)
# Schema: requires v1; the two metrics may live in different families.
#
# The two metrics are paired by date over the same window, so a missing day in
# either series drops that day from the pair (inner join on date). Correlation
# describes co-movement, not causation — a strong r is a lead worth a floor
# question, not a root cause.
#
# Usage:
#   ./correlate.sh <facility> <metric_a> <metric_b> [--start S] [--end E]
#
# Each metric is either a bare name (family auto-resolved, since metric names are
# unique across the v1 schema) or an explicit family:metric pair to disambiguate:
#   ./correlate.sh dal-02 cph headcount_new --start 2026-01-01 --end 2026-03-31
#   ./correlate.sh dal-02 operational:cph inputs:headcount_new
#
# Output (header + one row):
#   metric_a | metric_b | n | pearson_r | strength
#   operational:cph | inputs:headcount_new | 89 | -0.8234 | strong negative
#
# strength buckets |r|: >=0.7 strong, >=0.4 moderate, >=0.2 weak, else negligible
# (sign omitted for negligible). Prints "NA" when fewer than 2 paired points
# survive or either series has zero variance (correlation undefined).
#
# Exit codes: 0 success (including NA); 1 bad arguments; 2 data file not found.

set -euo pipefail
source "$(dirname "$0")/../lib/_schema_v1.sh"

usage() {
    echo "Usage: $0 <facility> <metric_a> <metric_b> [--start YYYY-MM-DD] [--end YYYY-MM-DD]" >&2
    exit 1
}

if [[ $# -lt 3 ]]; then usage; fi

FACILITY="$1"; METRIC_A="$2"; METRIC_B="$3"; shift 3
START=""
END=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --start) START="$2"; shift 2 ;;
        --end)   END="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; usage ;;
    esac
done

# resolve_metric <arg> — set REPLY_FAMILY, REPLY_METRIC, REPLY_COL for an arg
# that is either "family:metric" or a bare "metric" (auto-resolved). Returns 1
# if it can't be resolved or is ambiguous.
resolve_metric() {
    local arg="$1" fam metric col
    if [[ "$arg" == *:* ]]; then
        fam="${arg%%:*}"; metric="${arg##*:}"
        col=$(col_for "$fam" "$metric") || return 1
        REPLY_FAMILY="$fam"; REPLY_METRIC="$metric"; REPLY_COL="$col"
        return 0
    fi
    # Bare metric: search every family for a match. Names are unique in v1, so
    # the first hit is the only hit, but we keep scanning to catch ambiguity.
    local hits=0
    for fam in operational inputs exceptions equipment; do
        if col=$(col_for "$fam" "$arg" 2>/dev/null); then
            REPLY_FAMILY="$fam"; REPLY_METRIC="$arg"; REPLY_COL="$col"
            hits=$((hits + 1))
        fi
    done
    [[ $hits -eq 1 ]]
}

resolve_metric "$METRIC_A" || { echo "Unknown or ambiguous metric: '$METRIC_A'" >&2; exit 1; }
FAM_A="$REPLY_FAMILY"; COL_A="$REPLY_COL"; LABEL_A="${FAM_A}:${REPLY_METRIC}"
resolve_metric "$METRIC_B" || { echo "Unknown or ambiguous metric: '$METRIC_B'" >&2; exit 1; }
FAM_B="$REPLY_FAMILY"; COL_B="$REPLY_COL"; LABEL_B="${FAM_B}:${REPLY_METRIC}"

DATA_ROOT="${DATA_ROOT:-data/metrics}"
FILE_A="${DATA_ROOT}/${FAM_A}/${FACILITY}.csv"
FILE_B="${DATA_ROOT}/${FAM_B}/${FACILITY}.csv"
[[ -f "$FILE_A" ]] || { echo "Data file not found: $FILE_A" >&2; exit 2; }
[[ -f "$FILE_B" ]] || { echo "Data file not found: $FILE_B" >&2; exit 2; }

printf "metric_a | metric_b | n | pearson_r | strength\n"

# Read both files (FILE_A first, FILE_B second; the same path passed twice is
# fine — FNR resets per file). Pair on date, then compute Pearson r in one pass.
awk -F',' \
    -v start="$START" -v end="$END" \
    -v cola="$COL_A" -v colb="$COL_B" \
    -v labela="$LABEL_A" -v labelb="$LABEL_B" '
    function numeric(v) { return v ~ /^-?[0-9]+(\.[0-9]+)?$/ }
    FNR == 1 { fileidx++; next }
    {
        d = $1
        if (start != "" && d < start) next
        if (end   != "" && d > end)   next
        if (fileidx == 1) { if (numeric($cola)) xval[d] = $cola + 0 }
        else              { if (numeric($colb)) yval[d] = $colb + 0 }
    }
    END {
        n = 0
        for (d in xval) {
            if (d in yval) {
                x = xval[d]; y = yval[d]
                n++; sx += x; sy += y; sxx += x*x; syy += y*y; sxy += x*y
            }
        }
        if (n < 2) { print "NA"; exit }
        cov = sxy - sx*sy/n
        vx  = sxx - sx*sx/n
        vy  = syy - sy*sy/n
        if (vx <= 0 || vy <= 0) { print "NA"; exit }
        r = cov / sqrt(vx*vy)
        ar = (r < 0) ? -r : r
        sign = (r < 0) ? "negative" : "positive"
        if      (ar >= 0.7) strength = "strong " sign
        else if (ar >= 0.4) strength = "moderate " sign
        else if (ar >= 0.2) strength = "weak " sign
        else                strength = "negligible"
        printf "%s | %s | %d | %.4f | %s\n", labela, labelb, n, r, strength
    }
' "$FILE_A" "$FILE_B"
