#!/usr/bin/env bash
# intervention_attribution.sh — Is the change in metric M around an intervention
# attributable to the intervention, or did other variables move at the same time?
#
# Family: outcome
# Question answered: when a countermeasure landed on a date, did the target metric
#   move because of it — or did upstream variables (headcount, inbound volume,
#   downtime, ...) also shift in the same window and confound the attribution?
# Schema: requires v1; multi-family (resolves each variable's family via col_for).
#
# For the target metric and each --check-variable, the calc compares the mean over
# the PRE window (the `--window-days` days ending the day before the intervention)
# against the POST window (the `--window-days` days starting on the intervention
# date), reporting delta and relative change. A check-variable whose absolute
# relative change meets --threshold is flagged MOVED (a candidate confounder);
# otherwise STABLE. The verdict is CONFOUNDED when one or more checked variables
# moved, INCONCLUSIVE when none could be evaluated, and LIKELY otherwise. A
# variable that can't be evaluated (unknown metric, missing file, empty window) is
# surfaced as a caveat rather than silently counted as stable. A zero pre-mean
# makes relative change undefined: a real move (post != 0) is flagged MOVED with
# rel "n/a", never a silent STABLE.
#
# This calc never claims causation — it scopes attribution. A LIKELY verdict means
# "no checked confounder moved," not "proven caused by the intervention." The set
# of variables you pass is the set of alternative explanations you chose to rule
# out; choose them from the investigation's hypotheses.
#
# Variables may be a bare metric name (family auto-resolved by scanning
# operational, inputs, exceptions, equipment) or an explicit family:metric.
#
# Usage:
#   ./intervention_attribution.sh <facility> <target_metric> \
#       --intervention-date YYYY-MM-DD --check-variables m1,m2,... \
#       [--window-days N] [--threshold PCT]
#   ./intervention_attribution.sh dal-02 cph --intervention-date 2026-03-22 \
#       --check-variables headcount_new,inbound_units
#
# Defaults:
#   --window-days: 14   --threshold: 5.0 (percent relative change)
#
# Output: header block, a row per variable (target first), then a verdict line.
#
# Exit codes: 0 LIKELY, 1 CONFOUNDED, 2 bad args, 3 target data/window empty,
#             4 INCONCLUSIVE (no check variable could be evaluated).

set -euo pipefail
source "$(dirname "$0")/../lib/_schema_v1.sh"

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <facility> <target_metric> --intervention-date D --check-variables m1,m2,... [--window-days N] [--threshold PCT]" >&2
    exit 2
fi

FACILITY="$1"
TARGET="$2"
shift 2

INT_DATE=""
CHECK_VARS=""
WINDOW_DAYS=14
THRESHOLD=5.0

# need <args...> — guard that a flag actually has a value, so a trailing flag
# returns a clean exit 2 instead of tripping set -u on an unset $2.
need() { [[ $# -ge 2 ]] || { echo "Missing value for argument $1" >&2; exit 2; }; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --intervention-date) need "$@"; INT_DATE="$2"; shift 2 ;;
        --check-variables)   need "$@"; CHECK_VARS="$2"; shift 2 ;;
        --window-days)       need "$@"; WINDOW_DAYS="$2"; shift 2 ;;
        --threshold)         need "$@"; THRESHOLD="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done

if [[ -z "$INT_DATE" ]]; then echo "Required: --intervention-date YYYY-MM-DD" >&2; exit 2; fi
if [[ -z "$CHECK_VARS" ]]; then echo "Required: --check-variables m1,m2,..." >&2; exit 2; fi

DATA_ROOT="${DATA_ROOT:-data/metrics}"

# resolve_metric <arg> -> "family metric col" on stdout, return 0; nothing + return 1.
# <arg> is "family:metric" or a bare "metric" (family found by scanning families).
resolve_metric() {
    local arg="$1" fam metric col
    if [[ "$arg" == *:* ]]; then
        fam="${arg%%:*}"; metric="${arg##*:}"
        col=$(col_for "$fam" "$metric") || return 1
        printf "%s %s %s" "$fam" "$metric" "$col"; return 0
    fi
    metric="$arg"
    for fam in operational inputs exceptions equipment; do
        if col=$(col_for "$fam" "$metric" 2>/dev/null); then
            printf "%s %s %s" "$fam" "$metric" "$col"; return 0
        fi
    done
    return 1
}

# Window dates: PRE = [D - window_days, D - 1]; POST = [D, D + window_days - 1].
shift_date() {  # shift_date <YYYY-MM-DD> <signed-days>
    if date --version >/dev/null 2>&1; then
        date -d "$1 $2 days" +%Y-%m-%d
    else
        date -j -v"${2}"d -f "%Y-%m-%d" "$1" +%Y-%m-%d
    fi
}
PRE_START=$(shift_date "$INT_DATE" "-$WINDOW_DAYS")
PRE_END=$(shift_date "$INT_DATE" "-1")
POST_START="$INT_DATE"
POST_END=$(shift_date "$INT_DATE" "+$((WINDOW_DAYS - 1))")

# mean_window <file> <col> <start> <end> -> "mean4 n", or "NA 0" if empty.
mean_window() {
    awk -F',' -v start="$3" -v end="$4" -v col="$2" '
        NR == 1 { next }
        $col !~ /^-?[0-9]+(\.[0-9]+)?$/ { next }     # skip blank/non-numeric, keep real zeros
        $1 >= start && $1 <= end { sum += $col; n++ }
        END { if (n > 0) printf "%.4f %d", sum / n, n; else printf "NA 0" }
    ' "$1"
}

fmt2() { awk -v m="$1" 'BEGIN { printf "%.2f", m }'; }

# --- Target metric -----------------------------------------------------------
T_RESOLVED="$(resolve_metric "$TARGET" || true)"
[[ -n "$T_RESOLVED" ]] || { echo "Unknown target metric '$TARGET'" >&2; exit 2; }
read -r T_FAM T_METRIC T_COL <<<"$T_RESOLVED"

T_FILE="${DATA_ROOT}/${T_FAM}/${FACILITY}.csv"
[[ -f "$T_FILE" ]] || { echo "Target data file not found: $T_FILE" >&2; exit 3; }

read -r T_PRE  T_PRE_N  <<<"$(mean_window "$T_FILE" "$T_COL" "$PRE_START"  "$PRE_END")"
read -r T_POST T_POST_N <<<"$(mean_window "$T_FILE" "$T_COL" "$POST_START" "$POST_END")"
if [[ "$T_PRE" == "NA" || "$T_POST" == "NA" ]]; then
    echo "Target metric '$T_FAM:$T_METRIC' has no data in one of the windows ($PRE_START..$PRE_END / $POST_START..$POST_END)" >&2
    exit 3
fi
read -r T_DELTA T_RELDISP <<<"$(awk -v p="$T_PRE" -v q="$T_POST" 'BEGIN {
    d = q - p
    if (p != 0)      reldisp = sprintf("%+.2f%%", (d / p) * 100)
    else if (q == 0) reldisp = "+0.00%"
    else             reldisp = "n/a"
    printf "%+.2f %s", d, reldisp }')"

# --- Check variables ---------------------------------------------------------
rows=()
moved=()
uncheckable=()
evaluated=0
IFS=',' read -ra VARS <<<"$CHECK_VARS"
for v in "${VARS[@]}"; do
    [[ -n "$v" ]] || continue
    r="$(resolve_metric "$v" || true)"
    if [[ -z "$r" ]]; then
        rows+=("$v | - | - | - | - | UNKNOWN")
        uncheckable+=("$v (unknown metric)")
        continue
    fi
    read -r f m c <<<"$r"
    file="${DATA_ROOT}/${f}/${FACILITY}.csv"
    if [[ ! -f "$file" ]]; then
        rows+=("$f:$m | - | - | - | - | NO FILE")
        uncheckable+=("$f:$m (no file)")
        continue
    fi
    read -r pre  pn <<<"$(mean_window "$file" "$c" "$PRE_START"  "$PRE_END")"
    read -r post qn <<<"$(mean_window "$file" "$c" "$POST_START" "$POST_END")"
    if [[ "$pre" == "NA" || "$post" == "NA" ]]; then
        rows+=("$f:$m | - | - | - | - | NO DATA")
        uncheckable+=("$f:$m (no data)")
        continue
    fi
    # delta, rel display, status. A zero pre-mean makes relative change undefined:
    # a real move (post != 0) is MOVED with rel "n/a", never a silent STABLE.
    read -r d reldisp status <<<"$(awk -v p="$pre" -v q="$post" -v th="$THRESHOLD" 'BEGIN {
        d = q - p
        if (p != 0) {
            r = (d / p) * 100; ar = (r < 0) ? -r : r
            reldisp = sprintf("%+.2f%%", r)
            st = (ar >= th + 0) ? "MOVED" : "STABLE"
        } else if (q == 0) {
            reldisp = "+0.00%"; st = "STABLE"
        } else {
            reldisp = "n/a"; st = "MOVED"
        }
        printf "%+.2f %s %s", d, reldisp, st }')"
    rows+=("$f:$m | $(fmt2 "$pre") | $(fmt2 "$post") | $d | $reldisp | $status")
    evaluated=$((evaluated + 1))
    [[ "$status" == "MOVED" ]] && moved+=("$f:$m")
done

# Verdict. CONFOUNDED if any checked variable moved; INCONCLUSIVE if NONE could be
# evaluated (so we must not claim LIKELY); LIKELY otherwise. Uncheckable variables
# are surfaced as a caveat so the verdict never silently overstates attribution.
unc_str=""
if [[ ${#uncheckable[@]} -gt 0 ]]; then
    unc_str=$(printf "%s, " "${uncheckable[@]}"); unc_str="${unc_str%, }"
fi
if [[ ${#moved[@]} -gt 0 ]]; then
    moved_str=$(printf "%s, " "${moved[@]}"); moved_str="${moved_str%, }"
    VERDICT="CONFOUNDED (also moved: $moved_str"
    [[ -n "$unc_str" ]] && VERDICT="$VERDICT; could not evaluate: $unc_str"
    VERDICT="$VERDICT)"
    RC=1
elif [[ $evaluated -eq 0 ]]; then
    VERDICT="INCONCLUSIVE (no check variables could be evaluated: $unc_str)"
    RC=4
else
    VERDICT="LIKELY (no checked variables moved"
    [[ -n "$unc_str" ]] && VERDICT="$VERDICT; could not evaluate: $unc_str"
    VERDICT="$VERDICT)"
    RC=0
fi

echo "FACILITY: $FACILITY"
echo "TARGET: $T_FAM:$T_METRIC"
echo "INTERVENTION DATE: $INT_DATE"
echo "PRE WINDOW:  $PRE_START to $PRE_END"
echo "POST WINDOW: $POST_START to $POST_END"
echo "THRESHOLD: $(fmt2 "$THRESHOLD")% relative change"
echo
echo "variable | pre_mean | post_mean | delta | rel_change_pct | status"
echo "$T_FAM:$T_METRIC | $(fmt2 "$T_PRE") | $(fmt2 "$T_POST") | $T_DELTA | $T_RELDISP | (target)"
for row in "${rows[@]}"; do echo "$row"; done
echo
echo "ATTRIBUTION: $VERDICT"

exit $RC
