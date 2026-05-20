#!/usr/bin/env bash
# verify.sh — End-to-end smoke test for the ACI System portfolio build.
#
# Bundles every mechanical check this project relies on into one runnable
# artifact. Fast (~5s), deterministic, and exits non-zero on any failure.
#
# What it covers:
#   1. Calc library golden tests
#   2. Skills MANIFEST is in sync with the .skills/ directory
#   3. Simulator round-trips deterministically (same seed → same bytes)
#   4. Validators reject bad rows (the discipline guarantee)
#   5. Embedded scenarios surface in the calcs they should
#   6. dal-02 close-loop artifacts cross-reference correctly
#   7. Descriptive calcs against the live dal-02 dataset
#   8. Exceptions-family calcs + chr-03 damage close-loop
#
# Usage: bash verify.sh
# Exit:  0 all checks pass; 1 any check failed.

set -uo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

pass=0
fail=0
failures=()

ok() {
    echo "  PASS: $1"
    pass=$((pass + 1))
}

ko() {
    echo "  FAIL: $1"
    echo "        $2"
    fail=$((fail + 1))
    failures+=("$1")
}

section() {
    echo
    echo "== $1 =="
}

assert_eq() {
    local label="$1" actual="$2" expected="$3"
    if [[ "$actual" == "$expected" ]]; then
        ok "$label"
    else
        ko "$label" "expected '$expected', got '$actual'"
    fi
}

assert_contains() {
    local label="$1" haystack="$2" needle="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        ok "$label"
    else
        ko "$label" "expected output to contain '$needle'"
    fi
}

# 1. Calc library golden tests --------------------------------------------------
section "1. Calc library golden tests"
if bash calc/tests/run.sh >/dev/null 2>&1; then
    ok "calc/tests/run.sh"
else
    ko "calc/tests/run.sh" "see: bash calc/tests/run.sh"
fi

# 2. Skills manifest reconcile --------------------------------------------------
section "2. Skills manifest in sync"
out=$(python .skills/.meta/reconcile.py 2>&1)
if [[ "$out" == *"No changes detected"* ]]; then
    ok "reconcile shows no drift"
else
    ko "reconcile shows no drift" "$out"
fi

# 3. Simulator determinism ------------------------------------------------------
section "3. Simulator determinism (same seed → same bytes)"
snapshot=$(mktemp -d)
cp data/metrics/operational/dal-02.csv "$snapshot/before.csv"
cp data/events/dal-02.csv "$snapshot/events_before.csv"
if python conversion/scripts/simulate_facility_data.py >/dev/null 2>&1; then
    if diff -q "$snapshot/before.csv" data/metrics/operational/dal-02.csv >/dev/null 2>&1; then
        ok "operational/dal-02.csv reproduces byte-for-byte"
    else
        ko "operational/dal-02.csv reproduces byte-for-byte" "simulator output drifted"
    fi
    if diff -q "$snapshot/events_before.csv" data/events/dal-02.csv >/dev/null 2>&1; then
        ok "events/dal-02.csv reproduces byte-for-byte"
    else
        ko "events/dal-02.csv reproduces byte-for-byte" "events output drifted"
    fi
else
    ko "simulator re-run" "simulator script failed"
fi
rm -rf "$snapshot"

# 4. Validators reject bad rows -------------------------------------------------
section "4. Validators reject bad rows"
out=$(python - <<'PY' 2>&1
import sys
from pathlib import Path
sys.path.insert(0, str(Path("conversion") / "validation"))
import common

failures = []

# Case A: malformed date.
rows = [list(common.SCHEMAS["operational"])]
rows.append(["2026-13-99", "dal-02", "1000", "140.0", "0.005", "8.0"])
report = common.ValidationReport(script="verify", target="bad_date_test")
common.validate_metric_family("operational", rows, "dal-02", 0, report)
if report.passed:
    failures.append("malformed-date row was accepted")

# Case B: mismatched facility_id.
rows = [list(common.SCHEMAS["operational"])]
rows.append(["2026-03-15", "hou-01", "1000", "140.0", "0.005", "8.0"])
report = common.ValidationReport(script="verify", target="bad_facility_test")
common.validate_metric_family("operational", rows, "dal-02", 0, report)
if report.passed:
    failures.append("cross-facility row was accepted")

# Case C: out-of-range CPH.
rows = [list(common.SCHEMAS["operational"])]
rows.append(["2026-03-15", "dal-02", "1000", "999999", "0.005", "8.0"])
report = common.ValidationReport(script="verify", target="bad_range_test")
common.validate_metric_family("operational", rows, "dal-02", 0, report)
if report.passed:
    failures.append("out-of-range CPH was accepted")

# Case D: unknown event_type.
rows = [list(common.SCHEMAS["events"])]
rows.append(["2026-03-15", "dal-02", "nuclear_meltdown", "boom", "verify"])
report = common.ValidationReport(script="verify", target="bad_event_test")
common.validate_events_file(rows, "dal-02", report)
if report.passed:
    failures.append("unknown event_type was accepted")

if failures:
    print("FAILED: " + " | ".join(failures))
    sys.exit(1)
print("OK")
PY
)
if [[ "$out" == "OK" ]]; then
    ok "malformed date rejected"
    ok "cross-facility row rejected"
    ok "out-of-range CPH rejected"
    ok "unknown event_type rejected"
else
    ko "bad-row test suite" "$out"
fi

# 5. Scenario detection ---------------------------------------------------------
section "5. Embedded scenarios surface in calcs"

# 5a. dal-02 cohort dip: baseline → dip → recovery, with hou-01 peer unaffected.
baseline=$(bash calc/descriptive/avg_cph.sh dal-02 --start 2026-02-01 --end 2026-02-28)
dip=$(bash calc/descriptive/avg_cph.sh dal-02 --start 2026-03-08 --end 2026-03-22)
recovery=$(bash calc/descriptive/avg_cph.sh dal-02 --start 2026-04-01 --end 2026-04-30)
peer=$(bash calc/descriptive/avg_cph.sh hou-01 --start 2026-03-08 --end 2026-03-22)

assert_eq "dal-02 Feb baseline ≈ 141.82"   "$baseline" "141.82"
assert_eq "dal-02 Mar 8-22 dip ≈ 128.10"   "$dip"      "128.10"
assert_eq "dal-02 Apr recovery ≈ 141.56"   "$recovery" "141.56"
assert_eq "hou-01 Mar 8-22 unaffected ≈ 135.48" "$peer" "135.48"

# 5b. Cooccurrence finds the cohort training event near the dip.
cohort_events=$(bash calc/diagnostic/cooccurrence.sh dal-02 2026-03-15 --window 14)
assert_contains "dal-02 ±14 finds cohort training" "$cohort_events" "Cohort of 6 new hires"
assert_contains "dal-02 ±14 finds pick certification" "$cohort_events" "Pick certification"

# 5c. Cooccurrence finds bin relocation near chr-03 damage spike.
chr_events=$(bash calc/diagnostic/cooccurrence.sh chr-03 2026-04-15 --window 10)
assert_contains "chr-03 ±10 finds bin relocation sop_change" "$chr_events" "Bin relocation"
assert_contains "chr-03 event has sop_change type"           "$chr_events" "sop_change"

# 5d. change_drivers surfaces the cohort story without inline analysis.
drivers=$(bash calc/diagnostic/change_drivers.sh dal-02 \
    --baseline 2026-02-01:2026-02-28 \
    --comparison 2026-03-08:2026-03-22 --top 3 2>/dev/null)
assert_contains "change_drivers top row is mispick (+74%)"    "$drivers" "mispick"
assert_contains "change_drivers surfaces headcount_new spike" "$drivers" "headcount_new"

# 5e. segment_by produces day-of-week breakdown for the dip window.
seg=$(bash calc/diagnostic/segment_by.sh dal-02 operational cph --by dow \
    --start 2026-03-08 --end 2026-03-22)
assert_contains "segment_by dow output starts with Mon" "$seg" "Mon |"
assert_contains "segment_by dow output ends with Sat"   "$seg" "Sat |"

# 5f. correlate links the cohort story across families: cph falls as new-hire
# headcount rises (negative correlation) over the onboarding window.
corr=$(bash calc/diagnostic/correlate.sh dal-02 cph headcount_new \
    --start 2026-02-01 --end 2026-03-31)
assert_contains "correlate pairs cph with inputs:headcount_new" "$corr" "operational:cph | inputs:headcount_new"
assert_contains "correlate cph~headcount_new is negative"       "$corr" "negative"

# 6. Close-loop artifacts present and linked --------------------------------------
section "6. Close-loop artifacts (dal-02 cohort case)"

# 6a. The investigation moved from open/ to 2026-Q1/.
if [[ ! -e data/investigations/open/2026-03-15_dal-02_throughput_drop.md ]] \
&& [[ -e data/investigations/2026-Q1/2026-03-15_dal-02_throughput_drop.md ]]; then
    ok "investigation moved to 2026-Q1/"
else
    ko "investigation moved to 2026-Q1/" \
        "expected file under 2026-Q1/, not under open/"
fi

# 6b. The kaizen exists and references the investigation.
if [[ -f data/kaizens/open/k-2026-05-dal-02-trainer-ratio.md ]]; then
    kaizen_content=$(cat data/kaizens/open/k-2026-05-dal-02-trainer-ratio.md)
    assert_contains "kaizen references source investigation" "$kaizen_content" \
        "2026-03-15_dal-02_throughput_drop"
else
    ko "kaizen file exists" "data/kaizens/open/k-2026-05-dal-02-trainer-ratio.md missing"
fi

# 6c. The follow_ups INDEX contains at least one row tied to the Kaizen.
if [[ -f data/follow_ups/INDEX.md ]]; then
    fu_content=$(cat data/follow_ups/INDEX.md)
    assert_contains "follow_ups row exists for kaizen" "$fu_content" \
        "k-2026-05-dal-02-trainer-ratio"
else
    ko "follow_ups INDEX.md exists" "data/follow_ups/INDEX.md missing"
fi

# 6d. The simulator preserved floor-intake rows on its most recent run.
events_dal=$(cat data/events/dal-02.csv)
assert_contains "dal-02 events contains floor-intake leadership_change" \
    "$events_dal" "floor-intake-2026-05-18"
assert_contains "dal-02 events contains both simulator-seed and floor-intake sources" \
    "$events_dal" "simulator-seed"

# 6e. The scheduled baseline-maintenance follow-up still fires PASS.
fu_out=$(bash calc/outcome/follow_up_check.sh dal-02 cph --target 138 \
    --by 2026-05-15 --window-days 14 2>&1)
assert_contains "baseline-maintenance follow-up fires PASS" "$fu_out" "RESULT: PASS"

# 7. Descriptive calc integration (Phase 2.4) ------------------------------------
section "7. Descriptive calcs against the live dal-02 dataset"

# 7a. total_units for Feb baseline matches what we cited in the brief.
feb_units=$(bash calc/descriptive/total_units.sh dal-02 \
    --start 2026-02-01 --end 2026-02-28)
assert_eq "total_units dal-02 Feb = 625780" "$feb_units" "625780"

# 7b. worst_day picks the cohort-resignation date inside the dip window.
worst=$(bash calc/descriptive/worst_day.sh dal-02 cph \
    --start 2026-03-08 --end 2026-03-22)
assert_eq "worst_day dal-02 cph (dip window) = 2026-03-18 | 120.81" \
    "$worst" "2026-03-18 | 120.81"

# 7c. days_below_target counts all 12 dip-window days below 138.
below=$(bash calc/descriptive/days_below_target.sh dal-02 cph \
    --target 138 --start 2026-03-08 --end 2026-03-22)
assert_eq "days_below_target dal-02 cph<138 (dip window) = 12/12" \
    "$below" "12/12"

# 7d. month_summary Feb avg_cph matches the verified 141.82 baseline.
summary=$(bash calc/descriptive/month_summary.sh dal-02 --month 2026-02)
assert_contains "month_summary dal-02 Feb avg_cph = 141.82" \
    "$summary" "avg_cph | 141.82"
assert_contains "month_summary dal-02 Feb total_units = 625780" \
    "$summary" "total_units | 625780"

# 7e. avg.sh (generic) reproduces avg_cph.sh exactly on the live operational data.
avg_generic=$(bash calc/descriptive/avg.sh dal-02 cph --start 2026-02-01 --end 2026-02-28)
avg_cph=$(bash calc/descriptive/avg_cph.sh dal-02 --start 2026-02-01 --end 2026-02-28)
assert_eq "avg.sh cph == avg_cph.sh (Feb baseline = 141.82)" "$avg_generic" "$avg_cph"

# 8. Exceptions family is first-class (chr-03 damage spike) ----------------------
section "8. Exceptions-family calcs + chr-03 damage close-loop"

# 8a. worst_day reads the exceptions family and auto-selects max direction.
ex_worst=$(bash calc/descriptive/worst_day.sh chr-03 damage --family exceptions \
    --start 2026-04-12 --end 2026-04-24)
assert_eq "worst_day chr-03 damage (spike window) = 2026-04-22 | 43.00" \
    "$ex_worst" "2026-04-22 | 43.00"

# 8b. days_below_target --max counts spike-window days over the baseline ceiling
#     (10 of 11 days breach 18; one day sits at/below it).
ex_days=$(bash calc/descriptive/days_below_target.sh chr-03 damage --max 18 \
    --family exceptions --start 2026-04-12 --end 2026-04-24)
assert_eq "days_below_target chr-03 damage>18 (spike) = 10/11" "$ex_days" "10/11"

# 8b2. avg.sh gives the spike-window magnitude the damage_spike playbook now cites
#      (the exceptions mirror of throughput_drop's three avg_cph numbers).
ex_avg=$(bash calc/descriptive/avg.sh chr-03 damage --family exceptions \
    --start 2026-04-12 --end 2026-04-24)
assert_eq "avg.sh chr-03 damage (spike window) = 28.36" "$ex_avg" "28.36"

# 8c. follow_up_check tracks the metric that actually moved (damage), not a proxy,
#     and shows recovery to baseline after the floor's informal reversal.
ex_fu=$(bash calc/outcome/follow_up_check.sh chr-03 damage --max 18 \
    --by 2026-05-18 --family exceptions --window-days 14 2>&1)
assert_contains "chr-03 damage follow-up fires PASS (recovered)" "$ex_fu" "RESULT: PASS"

# 8d. The chr-03 close-loop artifacts exist and cross-reference correctly.
assert_eq "chr-03 investigation moved to 2026-Q2/" \
    "$([[ -f data/investigations/2026-Q2/2026-04-12_chr-03_damage_spike.md ]] && echo yes)" "yes"
kz=$(cat data/kaizens/open/k-2026-05-chr-03-bin-relocation.md 2>/dev/null)
assert_contains "chr-03 kaizen references source investigation" "$kz" \
    "2026-04-12_chr-03_damage_spike"
assert_contains "chr-03 kaizen tracks damage (exceptions), not error_rate proxy" "$kz" \
    "follow_up_check.sh chr-03 damage --max 18"
fu_idx=$(cat data/follow_ups/INDEX.md)
assert_contains "follow_ups index has chr-03 damage row" "$fu_idx" \
    "k-2026-05-chr-03-bin-relocation | 2026-06-19 | damage"

# 8e. The damage_spike playbook now exists for cold-start of future damage signals.
assert_eq "damage_spike playbook exists" \
    "$([[ -f .skills/investigate/playbooks/damage_spike.md ]] && echo yes)" "yes"

# 9. A3 demonstration (network trainer-coverage, paired with dal-02 Kaizen) ------
section "9. A3 artifacts (network trainer-coverage)"

A3=data/a3s/open/a3-2026-05-network-trainer-coverage.md

# 9a. The A3 file and index exist.
assert_eq "A3 file exists in a3s/open/" \
    "$([[ -f $A3 ]] && echo yes)" "yes"
a3_idx=$(cat data/a3s/INDEX.md 2>/dev/null)
assert_contains "a3s INDEX lists the network trainer-coverage A3" "$a3_idx" \
    "a3-2026-05-network-trainer-coverage"

# 9b. The A3 cross-references its source investigation and companion Kaizen.
a3=$(cat "$A3" 2>/dev/null)
assert_contains "A3 cites source investigation" "$a3" \
    "2026-03-15_dal-02_throughput_drop"
assert_contains "A3 names companion Kaizen" "$a3" \
    "k-2026-05-dal-02-trainer-ratio"

# 9c. The follow-ups gate holds: the A3 has rows in the follow-ups index.
fu_a3=$(cat data/follow_ups/INDEX.md)
assert_contains "follow_ups index has the A3 proof-case row" "$fu_a3" \
    "a3-2026-05-network-trainer-coverage | 2026-06-15 | cph | 138"

# 9d. The dal-02 investigation links the companion A3 (paired disposition).
inv=$(cat data/investigations/2026-Q1/2026-03-15_dal-02_throughput_drop.md 2>/dev/null)
assert_contains "dal-02 investigation links the companion A3" "$inv" \
    "a3_id: a3-2026-05-network-trainer-coverage"

# 9e. The A3's peer-evidence gate is honest: a live correlate sweep confirms the
#     cohort-overload signature is single-facility today (only dal-02 negative;
#     the tracked peer ral-02 stays above the -0.35 gate floor).
ral_corr=$(bash calc/diagnostic/correlate.sh ral-02 cph headcount_new | tail -1)
assert_contains "A3 peer gate: ral-02 is negligible (not the signature)" \
    "$ral_corr" "negligible"

# 10. Pattern compounding (equipment-downtime throughput drag) -------------------
section "10. Pattern: equipment-downtime throughput drag"

# 10a. The pattern file and index exist and cross-reference.
assert_eq "patterns/INDEX.md exists" \
    "$([[ -f data/patterns/INDEX.md ]] && echo yes)" "yes"
pidx=$(cat data/patterns/INDEX.md 2>/dev/null)
assert_contains "patterns INDEX lists the equipment-downtime pattern" "$pidx" \
    "equipment_downtime_throughput_drag.md"

# 10b. The pattern's 3 historical instances all exist on disk (the threshold).
for inv in \
    data/investigations/2026-Q2/2026-04-22_ral-02_throughput_drop.md \
    data/investigations/2026-Q1/2026-03-11_sav-01_throughput_drop.md \
    data/investigations/2026-Q2/2026-04-07_atl-03_throughput_drop.md; do
    assert_eq "pattern instance exists: $(basename "$inv")" \
        "$([[ -f $inv ]] && echo yes)" "yes"
done

# 10c. Each of the three cases shows the equipment signature: an equipment-family
#      metric is the top change_drivers mover (not quality, not headcount_new).
ral_drv=$(bash calc/diagnostic/change_drivers.sh ral-02 --baseline 2026-03-01:2026-03-31 --comparison 2026-04-20:2026-04-27 --top 1 2>/dev/null | tail -1)
assert_contains "ral-02 top driver is equipment downtime" "$ral_drv" "equipment|"
sav_drv=$(bash calc/diagnostic/change_drivers.sh sav-01 --baseline 2026-02-01:2026-02-28 --comparison 2026-03-09:2026-03-16 --top 1 2>/dev/null | tail -1)
assert_contains "sav-01 top driver is equipment downtime" "$sav_drv" "equipment|mhe_down_m"
atl_drv=$(bash calc/diagnostic/change_drivers.sh atl-03 --baseline 2026-03-01:2026-03-31 --comparison 2026-04-06:2026-04-13 --top 1 2>/dev/null | tail -1)
assert_contains "atl-03 top driver is equipment downtime" "$atl_drv" "equipment|conveyor_down_m"

# 10d. The throughput_drop playbook now consults the pattern library.
pb=$(cat .skills/investigate/playbooks/throughput_drop.md 2>/dev/null)
assert_contains "throughput_drop playbook checks the pattern library" "$pb" \
    "Check the pattern library first"
assert_contains "throughput_drop playbook names the equipment pattern" "$pb" \
    "equipment_downtime_throughput_drag"

# 10e. The ral-02 preventive Kaizen's follow-up fires PASS (line healthy post-repair).
ral_fu=$(bash calc/outcome/follow_up_check.sh ral-02 conveyor_down_m --max 60 --by 2026-05-18 --family equipment --window-days 18 2>&1)
assert_contains "ral-02 conveyor PM follow-up fires PASS" "$ral_fu" "RESULT: PASS"

# 10f. Mechanism independence: seeding the equipment cases did NOT create a cohort
#      signature at those facilities, so the dal-02 A3's single-facility story holds.
sav_coh=$(bash calc/diagnostic/correlate.sh sav-01 cph headcount_new | tail -1)
assert_contains "equipment cases stay clear of the cohort signature (sav-01)" \
    "$sav_coh" "negligible"

# 11. Deployment-mode gate (onboarding slice 1) ---------------------------------
section "11. Deployment-mode gate"

# 11a. Committed template exists and reads as unset (first-run trigger).
assert_eq "config/deployment.yaml.example exists" \
    "$([[ -f config/deployment.yaml.example ]] && echo yes)" "yes"
assert_eq "example reads as unset" \
    "$(python config/deployment.py get --file config/deployment.yaml.example)" "unset"

# 11b. A missing live config reads as unset (so a fresh fork greets).
assert_eq "missing config reads as unset" \
    "$(python config/deployment.py get --file /nonexistent/deployment.yaml)" "unset"

# 11c. set/get round-trips, and the capabilities block survives a write.
MODE_TMP=$(mktemp)
python config/deployment.py set demo --file "$MODE_TMP" --by "verify" >/dev/null
assert_eq "set demo → get demo" "$(python config/deployment.py get --file "$MODE_TMP")" "demo"
python config/deployment.py set production --file "$MODE_TMP" --by "verify" >/dev/null
assert_eq "set production → get production" "$(python config/deployment.py get --file "$MODE_TMP")" "production"
assert_eq "capabilities block preserved through a write" \
    "$(grep -c '^capabilities:' "$MODE_TMP")" "1"
rm -f "$MODE_TMP"

# 11d. The live config is gitignored (deployment-local, not committed).
assert_contains "config/deployment.yaml is gitignored" \
    "$(git check-ignore config/deployment.yaml 2>/dev/null || echo MISS)" "config/deployment.yaml"

# 11e. The protocol entry point documents the mode gate.
readme=$(cat .skills/README.md)
assert_contains "skills README documents the deployment-mode gate" "$readme" "## Deployment mode"
assert_contains "skills protocol checks mode before the manifest" "$readme" "Check the deployment mode"

# Summary ----------------------------------------------------------------------
echo
echo "================================================================"
echo "Results: $pass passed, $fail failed"
if [[ $fail -gt 0 ]]; then
    echo "Failed checks: ${failures[*]}"
    exit 1
fi
echo "All checks passed."
exit 0
