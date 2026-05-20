#!/usr/bin/env bash
# change_drivers.sh — Rank input/exception/equipment metrics by change between
# a baseline window and a comparison window.
#
# Family: diagnostic
# Question answered: when CPH changed between window A and window B, which
# upstream metrics moved most? This is the workhorse calc for root-cause work.
# Schema: requires v1; reads all four families if their CSVs exist.
#
# Usage:
#   ./change_drivers.sh <facility> --baseline S:E --comparison S:E [--top N] [--family F]
#
# Examples:
#   ./change_drivers.sh dal-02 \
#       --baseline   2026-02-01:2026-02-28 \
#       --comparison 2026-03-08:2026-03-22
#
#   ./change_drivers.sh dal-02 \
#       --baseline   2026-02-01:2026-02-28 \
#       --comparison 2026-03-08:2026-03-22 \
#       --family inputs --top 5
#
# Output (one row per metric, sorted by abs(rel_change_pct) descending):
#   family | metric | baseline_mean | comparison_mean | delta | rel_change_pct
#
# A metric is skipped if either window has zero rows or the baseline mean is
# zero (division by zero). Skipped metrics print to stderr.
#
# Exit codes: 0 success; 1 bad arguments; 2 no data files found for facility.

set -euo pipefail

usage() {
    echo "Usage: $0 <facility> --baseline S:E --comparison S:E [--top N] [--family F]" >&2
    exit 1
}

if [[ $# -lt 1 ]]; then usage; fi

FACILITY="$1"; shift
BASELINE=""
COMPARISON=""
TOP=0          # 0 = no limit
ONLY_FAMILY=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --baseline)   BASELINE="$2"; shift 2 ;;
        --comparison) COMPARISON="$2"; shift 2 ;;
        --top)        TOP="$2"; shift 2 ;;
        --family)     ONLY_FAMILY="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; usage ;;
    esac
done

[[ -n "$BASELINE" && -n "$COMPARISON" ]] || usage

# Parse "S:E" windows.
BL_START="${BASELINE%%:*}"; BL_END="${BASELINE##*:}"
CP_START="${COMPARISON%%:*}"; CP_END="${COMPARISON##*:}"

DATA_ROOT="${DATA_ROOT:-data/metrics}"

# (family, metric, column-index). Order here is the order metrics are scanned;
# the final output is re-sorted by abs(rel_change_pct).
METRICS=(
    "operational:units:3"
    "operational:cph:4"
    "operational:error_rate:5"
    "operational:hours_run:6"
    "inputs:headcount_total:3"
    "inputs:headcount_new:4"
    "inputs:headcount_shift1:5"
    "inputs:headcount_shift2:6"
    "inputs:headcount_shift3:7"
    "inputs:inbound_units:8"
    "inputs:order_mix_complex:9"
    "exceptions:damage:3"
    "exceptions:missort:4"
    "exceptions:mispick:5"
    "exceptions:lost:6"
    "exceptions:late_pick:7"
    "equipment:conveyor_down_m:3"
    "equipment:mhe_down_m:4"
    "equipment:wms_incidents:5"
    "equipment:scanner_faults:6"
)

# Per-family file existence check.
found_any=0
for fam in operational inputs exceptions equipment; do
    [[ -f "${DATA_ROOT}/${fam}/${FACILITY}.csv" ]] && found_any=1
done
if [[ $found_any -eq 0 ]]; then
    echo "No metric CSVs found for ${FACILITY} under ${DATA_ROOT}" >&2
    exit 2
fi

# Compute mean of one column over one window. Prints "NA" if no rows match.
mean_window() {
    local file="$1" col="$2" start="$3" end="$4"
    [[ -f "$file" ]] || { echo "NA"; return; }
    awk -F',' -v start="$start" -v end="$end" -v col="$col" '
        NR == 1 { next }
        $col == "" { next }
        $1 >= start && $1 <= end { sum += $col + 0; n++ }
        END { if (n > 0) printf "%.4f\n", sum / n; else print "NA" }
    ' "$file"
}

# Collect all rows, then sort by abs(rel_change_pct).
rows=()
skipped=()
for entry in "${METRICS[@]}"; do
    fam="${entry%%:*}"
    rest="${entry#*:}"
    metric="${rest%%:*}"
    col="${rest##*:}"
    if [[ -n "$ONLY_FAMILY" && "$ONLY_FAMILY" != "$fam" ]]; then continue; fi
    file="${DATA_ROOT}/${fam}/${FACILITY}.csv"
    [[ -f "$file" ]] || { skipped+=("$fam:$metric (no file)"); continue; }
    bl=$(mean_window "$file" "$col" "$BL_START" "$BL_END")
    cp=$(mean_window "$file" "$col" "$CP_START" "$CP_END")
    if [[ "$bl" == "NA" || "$cp" == "NA" ]]; then
        skipped+=("$fam:$metric (empty window)")
        continue
    fi
    # Compute delta + rel_change_pct in awk for precision.
    read -r delta rel abs_rel <<<"$(awk -v b="$bl" -v c="$cp" 'BEGIN {
        d = c - b
        if (b == 0) { print d, "NA", "0" }
        else        { r = (d / b) * 100; ar = (r < 0) ? -r : r; printf "%.4f %.2f %.4f\n", d, r, ar }
    }')"
    if [[ "$rel" == "NA" ]]; then
        skipped+=("$fam:$metric (baseline mean = 0)")
        continue
    fi
    # Sort key first so a stable sort works.
    rows+=("$(printf "%012.4f|%s|%s|%.2f|%.2f|%+.2f|%+.2f%%" \
        "$abs_rel" "$fam" "$metric" "$bl" "$cp" "$delta" "$rel")")
done

# Sort descending by leading numeric sort key, then strip it.
IFS=$'\n' sorted=($(printf "%s\n" "${rows[@]}" | sort -t'|' -k1,1 -r))
unset IFS

# Print header for readability.
printf "family | metric | baseline_mean | comparison_mean | delta | rel_change_pct\n"

count=0
for r in "${sorted[@]}"; do
    # Drop the leading "<sortkey>|"
    line="${r#*|}"
    echo "$line"
    count=$((count + 1))
    if [[ $TOP -gt 0 && $count -ge $TOP ]]; then break; fi
done

if [[ ${#skipped[@]} -gt 0 ]]; then
    echo "(skipped: ${skipped[*]})" >&2
fi
