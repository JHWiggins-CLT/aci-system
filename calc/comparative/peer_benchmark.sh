#!/usr/bin/env bash
# peer_benchmark.sh — Compare a facility's metric to its peers.
#
# Family: comparative
# Question answered: how does facility F's metric M compare to its peer facilities?
# Schema: requires v1 operational schema
#
# Peer facilities are read from data/facilities/INDEX.md. The INDEX.md is
# expected to contain a Peer Pairings section formatted as one pair per line:
#   PEER: dal-02, hou-01
#   PEER: chr-03, atl-01
# If your INDEX.md uses a different format, set PEERS via the --peers flag.
#
# Usage:
#   ./peer_benchmark.sh <facility_id> <metric> [--start D] [--end D]
#   ./peer_benchmark.sh dal-02 cph --start 2026-03-01 --end 2026-03-31
#   ./peer_benchmark.sh dal-02 cph --peers hou-01,chr-03
#
# Metric can be: cph, units, error_rate, hours_run.
# Output: one line per facility with its average for the metric over the window:
#   FACILITY  AVG  DELTA-VS-FACILITY-OF-INTEREST
#
# The facility of interest is always the first row, with DELTA shown as 0.00.

set -euo pipefail
source "$(dirname "$0")/../lib/_schema_v1.sh"

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <facility_id> <metric> [--start D] [--end D] [--peers F1,F2]" >&2
    exit 1
fi

FACILITY="$1"
METRIC="$2"
shift 2

START=""
END=""
EXPLICIT_PEERS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --start)  START="$2"; shift 2 ;;
        --end)    END="$2"; shift 2 ;;
        --peers)  EXPLICIT_PEERS="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

case "$METRIC" in
    cph)        COL=$COL_CPH ;;
    units)      COL=$COL_UNITS ;;
    error_rate) COL=$COL_ERROR_RATE ;;
    hours_run)  COL=$COL_HOURS_RUN ;;
    *) echo "Unknown metric: $METRIC (expected: cph, units, error_rate, hours_run)" >&2; exit 1 ;;
esac

DATA_ROOT="${DATA_ROOT:-data/metrics/operational}"
INDEX_FILE="${INDEX_FILE:-data/facilities/INDEX.md}"

# Resolve peer list.
PEERS=""
if [[ -n "$EXPLICIT_PEERS" ]]; then
    PEERS=$(echo "$EXPLICIT_PEERS" | tr ',' ' ')
elif [[ -f "$INDEX_FILE" ]]; then
    # Pull peers from PEER: lines in INDEX.md.
    PEER_LINE=$(grep -E "^PEER:" "$INDEX_FILE" 2>/dev/null | \
                grep -E "\b${FACILITY}\b" | head -n1 || true)
    if [[ -n "$PEER_LINE" ]]; then
        # Extract facility IDs from the line, drop the focus facility.
        PEERS=$(echo "$PEER_LINE" | sed 's/PEER://' | tr -d ' ' | tr ',' '\n' | \
                grep -vx "$FACILITY" | tr '\n' ' ')
    fi
fi

# Helper: compute average of $METRIC for one facility over the window.
avg_for() {
    local fac="$1"
    local file="${DATA_ROOT}/${fac}.csv"
    [[ -f "$file" ]] || { echo "NA"; return 0; }
    awk -F',' -v start="$START" -v end="$END" -v col="$COL" '
        NR == 1 { next }
        $col !~ /^-?[0-9]+(\.[0-9]+)?$/ { next }                  # skip blank/non-numeric (zeros are valid)
        start != "" && $1 < start { next }
        end   != "" && $1 > end   { next }
        { sum += $col; n++ }
        END { if (n > 0) printf "%.2f", sum / n; else printf "NA" }
    ' "$file"
}

FOCUS_AVG=$(avg_for "$FACILITY")
printf "%-12s %8s   %s\n" "$FACILITY" "$FOCUS_AVG" "0.00 (focus)"

if [[ -z "$PEERS" ]]; then
    echo "(no peers found for $FACILITY in $INDEX_FILE; pass --peers explicitly)" >&2
    exit 0
fi

for peer in $PEERS; do
    PEER_AVG=$(avg_for "$peer")
    if [[ "$FOCUS_AVG" == "NA" || "$PEER_AVG" == "NA" ]]; then
        DELTA="NA"
    else
        DELTA=$(awk -v f="$FOCUS_AVG" -v p="$PEER_AVG" 'BEGIN { printf "%+.2f", f - p }')
    fi
    printf "%-12s %8s   %s\n" "$peer" "$PEER_AVG" "$DELTA"
done
