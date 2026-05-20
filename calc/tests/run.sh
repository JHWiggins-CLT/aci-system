#!/usr/bin/env bash
# run.sh — Run all golden tests for the calc library.
#
# Usage: ./calc/tests/run.sh
# Exit codes: 0 all pass; 1 one or more failed.
#
# Each test:
#   1. Points the calc at a golden CSV in tests/golden/
#   2. Captures the calc's output
#   3. Diffs it against the expected output in tests/expected/
#
# Add new tests by appending more `run_test` invocations below.

set -euo pipefail

CALC_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GOLDEN="$CALC_ROOT/tests/golden"
EXPECTED="$CALC_ROOT/tests/expected"

pass=0
fail=0
failed_tests=()

run_test() {
    local name="$1"
    local expected_file="$EXPECTED/${name}.txt"
    shift
    local actual
    actual=$("$@" 2>&1) || true
    local expected
    expected=$(cat "$expected_file")
    if [[ "$actual" == "$expected" ]]; then
        echo "PASS: $name"
        pass=$((pass + 1))
    else
        echo "FAIL: $name"
        echo "  expected: $expected"
        echo "  actual:   $actual"
        fail=$((fail + 1))
        failed_tests+=("$name")
    fi
}

# Each test mounts the golden CSV at the location the calc expects.
# DATA_ROOT can be overridden to point at our fixtures dir.
TMPDIR=$(mktemp -d)
mkdir -p "$TMPDIR/metrics/operational" "$TMPDIR/metrics/exceptions"
cp "$GOLDEN/operational_dal-02.csv" "$TMPDIR/metrics/operational/dal-02.csv"
cp "$GOLDEN/exceptions_chr-test.csv" "$TMPDIR/metrics/exceptions/chr-test.csv"

# All descriptive calcs share a fixture at the column root.
export DATA_ROOT="$TMPDIR/metrics/operational"

# avg_cph
run_test avg_cph_all "$CALC_ROOT/descriptive/avg_cph.sh" dal-02
run_test avg_cph_windowed "$CALC_ROOT/descriptive/avg_cph.sh" dal-02 \
    --start 2026-03-06 --end 2026-03-10

# total_units
run_test total_units_all "$CALC_ROOT/descriptive/total_units.sh" dal-02
run_test total_units_windowed "$CALC_ROOT/descriptive/total_units.sh" dal-02 \
    --start 2026-03-06 --end 2026-03-10

# days_below_target
run_test days_below_target_all "$CALC_ROOT/descriptive/days_below_target.sh" \
    dal-02 cph --target 138
run_test days_below_target_windowed "$CALC_ROOT/descriptive/days_below_target.sh" \
    dal-02 cph --target 138 --start 2026-03-06 --end 2026-03-10

# worst_day (auto-direction by metric)
run_test worst_day_cph "$CALC_ROOT/descriptive/worst_day.sh" dal-02 cph
run_test worst_day_error_rate "$CALC_ROOT/descriptive/worst_day.sh" dal-02 error_rate

# month_summary
run_test month_summary "$CALC_ROOT/descriptive/month_summary.sh" dal-02 --month 2026-03

# Exceptions family (--family flag): locks family-aware column resolution and
# the exceptions/equipment "higher is worse" default direction.
DATA_ROOT="$TMPDIR/metrics/exceptions" \
    run_test worst_day_damage "$CALC_ROOT/descriptive/worst_day.sh" \
    chr-test damage --family exceptions
DATA_ROOT="$TMPDIR/metrics/exceptions" \
    run_test days_below_target_damage "$CALC_ROOT/descriptive/days_below_target.sh" \
    chr-test damage --max 20 --family exceptions

# segment_by (diagnostic) — expects DATA_ROOT to be the {family} dir.
run_test segment_by_dow "$CALC_ROOT/diagnostic/segment_by.sh" \
    dal-02 operational cph --by dow

# change_drivers (diagnostic) — expects DATA_ROOT to be the metrics/ root
# so it can find {family}/{facility}.csv. We restrict to --family operational
# since the golden fixture only contains the operational family.
DATA_ROOT="$TMPDIR/metrics" \
    run_test change_drivers_operational "$CALC_ROOT/diagnostic/change_drivers.sh" \
    dal-02 --baseline 2026-03-01:2026-03-07 --comparison 2026-03-08:2026-03-14 \
    --family operational

rm -rf "$TMPDIR"

echo
echo "Results: $pass passed, $fail failed"
if [[ $fail -gt 0 ]]; then
    echo "Failed: ${failed_tests[*]}"
    exit 1
fi
exit 0
