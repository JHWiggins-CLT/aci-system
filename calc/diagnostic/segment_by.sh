#!/usr/bin/env bash
# segment_by.sh — Break a metric down by a dimension (day-of-week or month).
#
# Family: diagnostic
# Question answered: how does metric M at facility F vary across dimension D?
# Schema: requires v1 (any family — operational, inputs, exceptions, equipment).
#
# Usage:
#   ./segment_by.sh <facility> <family> <metric> --by <dow|month> [--start S] [--end E]
#
# Examples:
#   ./segment_by.sh dal-02 operational cph --by dow
#       → Mon | 17 | 138.42
#       → Tue | 17 | 140.05  (etc.)
#   ./segment_by.sh dal-02 inputs headcount_new --by month --start 2026-02-01 --end 2026-04-30
#
# <family> values: operational | inputs | exceptions | equipment
# <metric>: any column name from that family's schema (e.g. cph, units, mispick,
#           headcount_new, conveyor_down_m, etc.)
#
# Output: one row per segment value, sorted by segment (canonical order for dow,
# chronological for month). Format:
#   <segment> | <n> | <mean>
#
# Exit codes: 0 success; 1 bad arguments; 2 data file not found.
#
# Day-of-week is computed via Zeller's congruence inside awk so the calc has no
# dependency on GNU vs BSD `date`. Months are extracted from the ISO date string.

set -euo pipefail

usage() {
    echo "Usage: $0 <facility> <family> <metric> --by <dow|month> [--start YYYY-MM-DD] [--end YYYY-MM-DD]" >&2
    exit 1
}

if [[ $# -lt 5 ]]; then usage; fi

FACILITY="$1"; FAMILY="$2"; METRIC="$3"; shift 3
BY=""
START=""
END=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --by)    BY="$2"; shift 2 ;;
        --start) START="$2"; shift 2 ;;
        --end)   END="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; usage ;;
    esac
done

case "$BY" in
    dow|month) ;;
    *) echo "Invalid --by value: '$BY' (use dow or month)" >&2; exit 1 ;;
esac

# Map (family, metric) → column index (1-based). Schema v1.
column_of() {
    case "$1:$2" in
        operational:units)              echo 3 ;;
        operational:cph)                echo 4 ;;
        operational:error_rate)         echo 5 ;;
        operational:hours_run)          echo 6 ;;
        inputs:headcount_total)         echo 3 ;;
        inputs:headcount_new)           echo 4 ;;
        inputs:headcount_shift1)        echo 5 ;;
        inputs:headcount_shift2)        echo 6 ;;
        inputs:headcount_shift3)        echo 7 ;;
        inputs:inbound_units)           echo 8 ;;
        inputs:order_mix_complex)       echo 9 ;;
        exceptions:damage)              echo 3 ;;
        exceptions:missort)             echo 4 ;;
        exceptions:mispick)             echo 5 ;;
        exceptions:lost)                echo 6 ;;
        exceptions:late_pick)           echo 7 ;;
        equipment:conveyor_down_m)      echo 3 ;;
        equipment:mhe_down_m)           echo 4 ;;
        equipment:wms_incidents)        echo 5 ;;
        equipment:scanner_faults)       echo 6 ;;
        *) return 1 ;;
    esac
}

COL=$(column_of "$FAMILY" "$METRIC") || {
    echo "Unknown metric '$METRIC' in family '$FAMILY'" >&2
    exit 1
}

DATA_ROOT="${DATA_ROOT:-data/metrics/${FAMILY}}"
FILE="${DATA_ROOT}/${FACILITY}.csv"
if [[ ! -f "$FILE" ]]; then
    echo "Data file not found: $FILE" >&2
    exit 2
fi

awk -F',' -v start="$START" -v end="$END" -v col="$COL" -v by="$BY" '
function dow_label(d,    y, m, day, K, J, h, names, n) {
    y   = substr(d, 1, 4) + 0
    m   = substr(d, 6, 2) + 0
    day = substr(d, 9, 2) + 0
    if (m < 3) { m += 12; y -= 1 }
    K = y % 100
    J = int(y / 100)
    h = (day + int((13 * (m + 1)) / 5) + K + int(K / 4) + int(J / 4) + 5 * J) % 7
    # Zellers: 0=Sat 1=Sun 2=Mon 3=Tue 4=Wed 5=Thu 6=Fri
    names = "Sat Sun Mon Tue Wed Thu Fri"
    split(names, n, " ")
    return n[h + 1]
}
function dow_order(label) {
    if (label == "Mon") return 1
    if (label == "Tue") return 2
    if (label == "Wed") return 3
    if (label == "Thu") return 4
    if (label == "Fri") return 5
    if (label == "Sat") return 6
    if (label == "Sun") return 7
    return 8
}
NR == 1 { next }
$col == "" { next }
{
    if (start != "" && $1 < start) next
    if (end   != "" && $1 > end)   next
    if (by == "dow")   seg = dow_label($1)
    else               seg = substr($1, 1, 7)
    sum[seg] += $col + 0
    n[seg]   += 1
}
END {
    if (by == "dow") {
        for (s in n) keys[dow_order(s)] = s
        for (i = 1; i <= 7; i++) {
            s = keys[i]
            if (s == "") continue
            printf "%s | %d | %.2f\n", s, n[s], sum[s] / n[s]
        }
    } else {
        # Chronological by month string (already sortable).
        m = 0
        for (s in n) { months[++m] = s }
        # Simple insertion sort over months[1..m].
        for (i = 2; i <= m; i++) {
            k = months[i]; j = i - 1
            while (j >= 1 && months[j] > k) { months[j+1] = months[j]; j-- }
            months[j+1] = k
        }
        for (i = 1; i <= m; i++) {
            s = months[i]
            printf "%s | %d | %.2f\n", s, n[s], sum[s] / n[s]
        }
    }
}
' "$FILE"
