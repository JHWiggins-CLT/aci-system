#!/usr/bin/env bash
# cooccurrence.sh — Events occurring within a date window of a signal date.
#
# Family: diagnostic
# Question answered: what events occurred near this date at this facility?
# Schema: reads events log (date, facility_id, event_type, description, source)
#
# Reads both data/events/{facility}.csv (per-facility log) and
# data/events/network.csv (network-wide events) if either exists. Returns
# all events whose date is within ±window days of the signal date.
#
# Usage:
#   ./cooccurrence.sh <facility_id> <signal_date> [--window N]
#   ./cooccurrence.sh dal-02 2026-03-08 --window 14
#
# Window defaults to 7 days. Output is one event per line:
#   YYYY-MM-DD | event_type | description | source
#
# Exit codes: 0 success (even if zero events found); 1 bad arguments;
#             2 facility log not found AND network log not found.

set -euo pipefail

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <facility_id> <signal_date> [--window N]" >&2
    exit 1
fi

FACILITY="$1"
SIGNAL_DATE="$2"
shift 2

WINDOW=7
while [[ $# -gt 0 ]]; do
    case "$1" in
        --window) WINDOW="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

EVENTS_ROOT="${EVENTS_ROOT:-data/events}"
FACILITY_FILE="${EVENTS_ROOT}/${FACILITY}.csv"
NETWORK_FILE="${EVENTS_ROOT}/network.csv"

if [[ ! -f "$FACILITY_FILE" && ! -f "$NETWORK_FILE" ]]; then
    echo "No events files found in $EVENTS_ROOT" >&2
    exit 2
fi

# Compute window bounds in YYYY-MM-DD using date arithmetic.
# Uses GNU date syntax; on macOS this needs `gdate` from coreutils.
if date --version >/dev/null 2>&1; then
    START_DATE=$(date -d "${SIGNAL_DATE} -${WINDOW} days" +%Y-%m-%d)
    END_DATE=$(date -d "${SIGNAL_DATE} +${WINDOW} days" +%Y-%m-%d)
else
    # BSD date (macOS)
    START_DATE=$(date -j -v-${WINDOW}d -f "%Y-%m-%d" "${SIGNAL_DATE}" +%Y-%m-%d)
    END_DATE=$(date -j -v+${WINDOW}d -f "%Y-%m-%d" "${SIGNAL_DATE}" +%Y-%m-%d)
fi

filter_events() {
    local file="$1"
    local has_facility_col="$2"  # "yes" or "no"
    [[ -f "$file" ]] || return 0

    if [[ "$has_facility_col" == "yes" ]]; then
        awk -F',' -v start="$START_DATE" -v end="$END_DATE" -v fac="$FACILITY" '
            NR == 1 { next }
            $1 >= start && $1 <= end && $2 == fac {
                # Strip surrounding quotes from description if present.
                desc = $4
                gsub(/^"|"$/, "", desc)
                printf "%s | %s | %s | %s\n", $1, $3, desc, $5
            }
        ' "$file"
    else
        awk -F',' -v start="$START_DATE" -v end="$END_DATE" '
            NR == 1 { next }
            $1 >= start && $1 <= end {
                desc = $3
                gsub(/^"|"$/, "", desc)
                printf "%s | %s | %s | %s | (network)\n", $1, $2, desc, $4
            }
        ' "$file"
    fi
}

filter_events "$FACILITY_FILE" "yes"
filter_events "$NETWORK_FILE" "no"
