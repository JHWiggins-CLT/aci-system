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

# avg (family-aware generalization of avg_cph) — must reproduce avg_cph on the
# operational fixture, and average any column in another family via --family.
run_test avg_cph "$CALC_ROOT/descriptive/avg.sh" dal-02 cph
DATA_ROOT="$TMPDIR/metrics/exceptions" \
    run_test avg_damage "$CALC_ROOT/descriptive/avg.sh" \
    chr-test damage --family exceptions

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

# correlate (diagnostic) — expects DATA_ROOT to be the metrics/ root. units is
# exactly 60*cph in the fixture (perfect positive); error_rate moves inversely
# to cph (strong negative). Both pairs are intra-operational so the single
# operational fixture covers them.
DATA_ROOT="$TMPDIR/metrics" \
    run_test correlate_cph_units "$CALC_ROOT/diagnostic/correlate.sh" \
    dal-02 cph units
DATA_ROOT="$TMPDIR/metrics" \
    run_test correlate_cph_error_rate "$CALC_ROOT/diagnostic/correlate.sh" \
    dal-02 cph error_rate

# outcome calcs ----------------------------------------------------------------
# follow_up_check (single-family, operational): 14-day window to 2026-03-14 means
# 1888/14 = 134.86 cph, below the 138 target -> FAIL.
run_test follow_up_check "$CALC_ROOT/outcome/follow_up_check.sh" \
    dal-02 cph --target 138 --by 2026-03-14 --window-days 14

# countermeasure_effectiveness (single-family): trough week (508/4=127.00) vs
# recovery week (554/4=138.50) -> +11.50 (+9.06%), cph higher-is-better -> IMPROVED.
run_test countermeasure_effectiveness "$CALC_ROOT/outcome/countermeasure_effectiveness.sh" \
    dal-02 cph --pre 2026-03-06:2026-03-09 --post 2026-03-11:2026-03-14

# intervention_attribution (multi-family; intra-operational here so one fixture
# covers it). cph and units both fall -3.55% (STABLE < 5%), error_rate rises
# +12.16% (MOVED) -> CONFOUNDED by error_rate. Needs the metrics/ root.
DATA_ROOT="$TMPDIR/metrics" \
    run_test intervention_attribution "$CALC_ROOT/outcome/intervention_attribution.sh" \
    dal-02 cph --intervention-date 2026-03-08 --check-variables units,error_rate \
    --window-days 3 --threshold 5

rm -rf "$TMPDIR"

echo
echo "Results: $pass passed, $fail failed"
if [[ $fail -gt 0 ]]; then
    echo "Failed: ${failed_tests[*]}"
    exit 1
fi
exit 0
