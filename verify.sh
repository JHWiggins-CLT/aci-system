#!/usr/bin/env bash
# verify.sh — End-to-end smoke test for the ACI System portfolio build.
#
# Bundles every mechanical check this project relies on into one runnable
# artifact. Fast (~5s), deterministic, and exits non-zero on any failure.
#
# What it covers, in two tiers:
#   STRUCTURAL (run in every mode): golden tests (1), manifest sync (2),
#     validator discipline (4), deployment-mode gate (11), onboard tooling (12).
#   DEMO-SCENARIO (run only in demo/unset mode): simulator determinism (3) and
#     the embedded-scenario / close-loop / A3 / pattern checks (5-10). These
#     assert the built-in simulated dataset, so they are skipped in production
#     (where Section 3 would also overwrite real data by re-running the simulator).
#
# The tier is chosen automatically from `config/deployment.py get`:
#   - demo / unset → all checks
#   - production   → structural only
#
# Usage:
#   bash verify.sh               # auto by deployment mode
#   bash verify.sh --structural  # force structural-only (any mode)
#   bash verify.sh --all         # force all checks (even in production)
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

# --- Mode awareness (onboarding slice 6) --------------------------------------
# Structural checks (golden tests, manifest, validators, onboarding plumbing) run
# in every mode. Demo-scenario checks (Sections 3 and 5-10) assert the built-in
# simulated dataset and only run in demo/unset mode: in production they would be
# meaningless, and Section 3 in particular re-runs the simulator, which would
# OVERWRITE real data. Override with --all (force demo checks too) or
# --structural (skip them).
FORCE=""
for arg in "$@"; do
    case "$arg" in
        --all) FORCE=all ;;
        --structural) FORCE=structural ;;
        *) echo "unknown arg: $arg (use --all or --structural)" >&2; exit 2 ;;
    esac
done
MODE=$(python config/deployment.py get 2>/dev/null || echo unset)
if [[ "$FORCE" == "all" ]]; then RUN_DEMO=1
elif [[ "$FORCE" == "structural" ]]; then RUN_DEMO=0
elif [[ "$MODE" == "production" ]]; then RUN_DEMO=0
else RUN_DEMO=1; fi

if [[ "$RUN_DEMO" == 1 ]]; then
    echo "verify.sh — mode=$MODE — running ALL checks (structural + demo-scenario)"
else
    echo "verify.sh — mode=$MODE — STRUCTURAL checks only (demo-scenario sections skipped)"
fi

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
# DEMO-ONLY: re-runs the simulator, which writes data/metrics — must never run in
# production (it would overwrite real data).
if [[ "$RUN_DEMO" == 1 ]]; then
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
fi  # RUN_DEMO (Section 3)

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

# --- DEMO-SCENARIO checks (Sections 5-10): assert the built-in simulated dataset
# --- and its demo investigations/Kaizens/A3/pattern. Skipped in production mode.
if [[ "$RUN_DEMO" == 1 ]]; then

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

# 6f. countermeasure_effectiveness captures the dal-02 cph recovery after the
# trainer-ratio fix: the dip window (~128 cph) vs the post-recovery window
# (~142 cph) reads IMPROVED for a higher-is-better metric.
ce_out=$(bash calc/outcome/countermeasure_effectiveness.sh dal-02 cph \
    --pre 2026-03-08:2026-03-22 --post 2026-04-01:2026-04-15 2>&1)
assert_contains "countermeasure_effectiveness dal-02 cph recovered = IMPROVED" \
    "$ce_out" "RESULT: IMPROVED"

# 6g. intervention_attribution scopes the dal-02 cph drop to the new-hire cohort:
# headcount_new MOVED over the onboarding window while inbound_units stayed STABLE,
# so the drop is CONFOUNDED by headcount_new (the cohort signal) — not volume.
ia_out=$(bash calc/outcome/intervention_attribution.sh dal-02 cph \
    --intervention-date 2026-03-08 --check-variables headcount_new,inbound_units \
    --window-days 10 2>&1)
assert_contains "intervention_attribution flags the cohort as the confounder" \
    "$ia_out" "ATTRIBUTION: CONFOUNDED (also moved: inputs:headcount_new)"

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

fi  # RUN_DEMO (Sections 5-10)

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

# 12. Onboarding skill + setup tooling (onboarding slices 2-5) ------------------
section "12. Onboarding skill + setup tooling"

# 12a. The onboard skill exists and is registered in the manifest.
assert_eq "onboard SKILL exists" \
    "$([[ -f .skills/onboard/SKILL.md ]] && echo yes)" "yes"
assert_contains "onboard registered in MANIFEST" "$(cat .skills/MANIFEST.yaml)" "name: onboard"

# 12b. The human-readable SETUP.md mirror exists.
assert_eq "SETUP.md exists" "$([[ -f SETUP.md ]] && echo yes)" "yes"

# 12c. The maintain procedures the onboard skill routes to exist.
assert_eq "add_facility.md procedure exists" \
    "$([[ -f .skills/maintain/procedures/add_facility.md ]] && echo yes)" "yes"
assert_eq "bump_schema.md procedure exists" \
    "$([[ -f .skills/maintain/procedures/bump_schema.md ]] && echo yes)" "yes"

# 12d. The conversion-adapter scaffold exists and exposes the canonical schema,
#      and fails loudly (never silently emits data) when its mapping is unfilled.
adp=$(python conversion/scripts/adapter_template.py --show-schema 2>&1)
assert_contains "adapter --show-schema lists the operational columns" "$adp" \
    "operational: date, facility_id, units, cph, error_rate, hours_run"
adp_err=$(python conversion/scripts/adapter_template.py 2>&1 || true)
assert_contains "adapter refuses to run unimplemented (no silent empty data)" "$adp_err" \
    "NotImplementedError"

# 12e. reset_demo_state --dry-run is non-destructive in any mode (preview only).
inv_before=$(find data/investigations -name '*.md' ! -name INDEX.md | wc -l | tr -d ' ')
dry=$(python .skills/onboard/reset_demo_state.py --dry-run 2>&1)
assert_contains "reset --dry-run prints a summary" "$dry" "Would clear"
inv_after_dry=$(find data/investigations -name '*.md' ! -name INDEX.md | wc -l | tr -d ' ')
assert_eq "reset --dry-run changed nothing" "$inv_before" "$inv_after_dry"

# 12f. reset_demo_state on a throwaway copy clears the investigation INDEX to
#      header-only and leaves the metrics tree untouched (mode-agnostic: compares
#      counts before/after rather than asserting demo-specific totals).
RESET_TMP=$(mktemp -d)
cp -r data "$RESET_TMP/data"
op_before=$(ls "$RESET_TMP/data/metrics/operational"/*.csv 2>/dev/null | wc -l | tr -d ' ')
python .skills/onboard/reset_demo_state.py --root "$RESET_TMP/data" --force >/dev/null 2>&1
rows_left=$(grep -c '^| 20' "$RESET_TMP/data/investigations/INDEX.md" || true)
assert_eq "reset cleared investigation INDEX data rows" "$rows_left" "0"
op_after=$(ls "$RESET_TMP/data/metrics/operational"/*.csv 2>/dev/null | wc -l | tr -d ' ')
assert_eq "reset left the metrics tree untouched" "$op_before" "$op_after"
rm -rf "$RESET_TMP"

# 13. Review / reporting capability (artifact access layer) ---------------------
section "13. Review / reporting capability"

# 13a. Every artifact type now has a consistent catalog (kaizens was the gap).
assert_eq "kaizens/INDEX.md catalog exists" \
    "$([[ -f data/kaizens/INDEX.md ]] && echo yes)" "yes"

# 13b. The review skill exists and is registered.
assert_eq "review SKILL exists" \
    "$([[ -f .skills/review/SKILL.md ]] && echo yes)" "yes"
assert_contains "review registered in MANIFEST" "$(cat .skills/MANIFEST.yaml)" "name: review"

# 13c. The status renderer runs and produces the standard banner + sections.
dash=$(python .skills/review/status.py 2>&1)
assert_contains "status dashboard prints the ACI banner" "$dash" "ACI  ·  Status dashboard"
assert_contains "status dashboard rolls up investigations" "$dash" "Investigations"
assert_contains "status dashboard rolls up kaizens"        "$dash" "Kaizens"
assert_contains "status dashboard rolls up follow-ups"     "$dash" "Follow-ups"

# 13d. Every status view runs without error (read-only, mode-agnostic).
status_ok=yes
for v in investigations a3s kaizens patterns follow-ups open due; do
    python .skills/review/status.py "$v" >/dev/null 2>&1 || status_ok="FAILED:$v"
done
assert_eq "every status.py view runs cleanly" "$status_ok" "yes"

# 13e. The morning brief is standardized: fixed template + shared renderer.
assert_eq "morning brief template exists" \
    "$([[ -f .skills/signal-detect/morning_brief_template.md ]] && echo yes)" "yes"
sd=$(cat .skills/signal-detect/SKILL.md)
assert_contains "signal-detect points at the brief template" "$sd" "morning_brief_template.md"
assert_contains "morning brief renders OPEN/DUE via status.py brief" "$sd" "status.py brief"
brief=$(python .skills/review/status.py brief 2>&1)
assert_contains "status.py brief renders the OPEN section" "$brief" "OPEN investigations"
assert_contains "status.py brief renders the DUE section" "$brief" "DUE follow-ups"

# 14. Export / shareable HTML capability (artifact -> HTML for management) ------
# STRUCTURAL: renders self-contained fixtures (not the demo artifacts), so it
# asserts the renderer's contract independent of deployment mode or demo data.
section "14. Export / shareable HTML capability"

# 14a. The renderer and the export skill exist and are registered.
assert_eq "reports/render_html.py exists" \
    "$([[ -f reports/render_html.py ]] && echo yes)" "yes"
assert_eq "export SKILL exists" \
    "$([[ -f .skills/export/SKILL.md ]] && echo yes)" "yes"
assert_contains "export registered in MANIFEST" "$(cat .skills/MANIFEST.yaml)" "name: export"
assert_contains "export capability declared in deployment template" \
    "$(cat config/deployment.yaml.example)" "export:"

# 14b. An A3 renders with the full fixed section skeleton, even when the source
#      omits sections (omitted ones become labelled placeholders, never dropped),
#      and the output is self-contained (inline CSS, no external asset links).
EXPORT_TMP=$(mktemp -d)
cat > "$EXPORT_TMP/a3.md" <<'A3FIX'
# A3: Fixture problem

**A3 ID:** a3-fixture-001
**State:** open
**Owner:** Test Owner

---

## Current state
Throughput dipped, confirmed by `bash calc/descriptive/avg_cph.sh x`.

## Root cause
Mechanism was Y, not the label.

## Plan
| Action | Owner | Status |
|--------|-------|--------|
| do thing | me | open |
A3FIX
python reports/render_html.py "$EXPORT_TMP/a3.md" -o "$EXPORT_TMP/a3.html" >/dev/null 2>&1
a3html=$(cat "$EXPORT_TMP/a3.html" 2>/dev/null)
assert_contains "A3 export carries the A3 badge" "$a3html" 'badge a3">A3'
a3_sections_ok=yes
for s in "Current state" "Target state" "Root cause" "Countermeasures" "Plan" \
         "Follow-up schedule" "Lessons learned" "Closing"; do
    [[ "$a3html" == *"<h2>$s</h2>"* ]] || a3_sections_ok="MISSING:$s"
done
assert_eq "A3 export emits all 8 canonical sections in fixed structure" "$a3_sections_ok" "yes"
assert_contains "A3 export placeholders an omitted section (structure constant)" \
    "$a3html" "Not yet recorded."
assert_contains "A3 export renders markdown tables" "$a3html" "<table>"
assert_contains "A3 export is self-contained (inline CSS)" "$a3html" "<style>"
if [[ "$a3html" == *"<link"* ]]; then
    ko "A3 export has no external asset links" "found a <link ...> tag"
else
    ok "A3 export has no external asset links"
fi

# 14c. A Kaizen renders with its own fixed 4-section skeleton and badge — even a
#      frontmatter-less source (id/heading carry the type).
cat > "$EXPORT_TMP/k.md" <<'KFIX'
# Kaizen: Fixture change

**Kaizen ID:** k-fixture-001
**State:** open

---

## Observation
Saw a thing in the data.

## Change
Made a concrete change.
KFIX
python reports/render_html.py "$EXPORT_TMP/k.md" -o "$EXPORT_TMP/k.html" >/dev/null 2>&1
khtml=$(cat "$EXPORT_TMP/k.html" 2>/dev/null)
assert_contains "Kaizen export carries the Kaizen badge" "$khtml" 'badge kaizen">Kaizen'
k_sections_ok=yes
for s in "Observation" "Change" "Tracking" "Outcome"; do
    [[ "$khtml" == *"<h2>$s</h2>"* ]] || k_sections_ok="MISSING:$s"
done
assert_eq "Kaizen export emits all 4 canonical sections in fixed structure" "$k_sections_ok" "yes"

# 14d. --all renders to an output dir and writes an index landing page.
python reports/render_html.py --all --out-dir "$EXPORT_TMP/out" >/dev/null 2>&1
assert_eq "export --all writes an index.html landing page" \
    "$([[ -f "$EXPORT_TMP/out/index.html" ]] && echo yes)" "yes"

# 14e. The combined investigation BUNDLE report ties an investigation to its
#      A3(s) + Kaizen(s) + outcome history, in a fixed part order. Rendered
#      against a hermetic fixture data tree (ACI_DATA_DIR) so it is structural.
FIX="$EXPORT_TMP/data"
mkdir -p "$FIX/investigations" "$FIX/a3s/open" "$FIX/kaizens/open" "$FIX/follow_ups"
cat > "$FIX/investigations/INDEX.md" <<'INV'
# Investigations Index
## Investigations
| date | facility | signal | state | disposition | file |
|------|----------|--------|-------|-------------|------|
| 2026-01-01 | tst-01 | throughput_drop | kaizen_open | a3-fixture-001 + k-fixture-001 | fix_inv.md |
INV
cat > "$FIX/investigations/fix_inv.md" <<'INVF'
---
investigation_id: fix_inv
facility: tst-01
signal_type: throughput_drop
signal_date: 2026-01-01
state: kaizen_open
disposition: a3 + kaizen
---

# Floor Brief: tst-01 fixture

**Signal:** Fixture signal description for the bundle test.

## What we see
A fixture observation.
INVF
cat > "$FIX/a3s/INDEX.md" <<'A3I'
# A3 Index
## A3s
| a3_id | opened | state | scope | owner | source | next_follow_up | file |
|-------|--------|-------|-------|-------|--------|----------------|------|
| a3-fixture-001 | 2026-01-02 | open | network | T | fix_inv | 2026-03-01 | open/a3-fixture-001.md |
A3I
cp "$EXPORT_TMP/a3.md" "$FIX/a3s/open/a3-fixture-001.md"
cat > "$FIX/kaizens/INDEX.md" <<'KZI'
# Kaizen Index
## Kaizens
| kaizen_id | opened | state | facility | source | next_follow_up | file |
|-----------|--------|-------|----------|--------|----------------|------|
| k-fixture-001 | 2026-01-02 | open | tst-01 | fix_inv | 2026-02-01 | open/k-fixture-001.md |
KZI
cp "$EXPORT_TMP/k.md" "$FIX/kaizens/open/k-fixture-001.md"
cat > "$FIX/follow_ups/INDEX.md" <<'FUI'
# Follow-Ups Index
## Rows
| artifact_id | follow_up_date | target_metric | target_value | direction | calc_invocation | status | last_run |
|-------------|----------------|---------------|--------------|-----------|------------------|--------|----------|
| k-fixture-001 | 2026-02-01 | cph | 138 | >= | `bash x` | PASS (140.0) | 2026-01-15 |
| a3-fixture-001 | 2026-03-01 | cph | 138 | >= | `bash x` | pending | |
FUI
ACI_DATA_DIR="$FIX" python reports/render_html.py --bundle fix_inv -o "$EXPORT_TMP/bundle.html" >/dev/null 2>&1
bhtml=$(cat "$EXPORT_TMP/bundle.html" 2>/dev/null)
assert_contains "bundle carries the Bundle badge" "$bhtml" 'badge bundle">Bundle'
bundle_parts_ok=yes
for s in "At a glance" "A3" "Kaizen" "Outcome history"; do
    [[ "$bhtml" == *"<h2>$s</h2>"* ]] || bundle_parts_ok="MISSING:$s"
done
assert_eq "bundle emits the fixed part order (glance/A3/Kaizen/outcome)" "$bundle_parts_ok" "yes"
assert_contains "bundle embeds the source investigation" "$bhtml" 'badge inv">Investigation'
assert_contains "bundle embeds the A3 with its sections" "$bhtml" "<h3>Current state</h3>"
assert_contains "bundle embeds the Kaizen with its sections" "$bhtml" "<h3>Observation</h3>"
assert_contains "bundle outcome history shows a PASS result" "$bhtml" "status-pass"
assert_contains "bundle outcome history lists a tracked artifact" "$bhtml" "k-fixture-001"
assert_contains "bundle is self-contained (inline CSS)" "$bhtml" "<style>"

# 14f. --all-bundles against the fixture writes bundle + index.
ACI_DATA_DIR="$FIX" python reports/render_html.py --all-bundles --out-dir "$EXPORT_TMP/bout" >/dev/null 2>&1
assert_eq "export --all-bundles writes the bundle file" \
    "$([[ -f "$EXPORT_TMP/bout/bundle-fix_inv.html" ]] && echo yes)" "yes"
assert_eq "export --all-bundles writes an index.html" \
    "$([[ -f "$EXPORT_TMP/bout/index.html" ]] && echo yes)" "yes"
rm -rf "$EXPORT_TMP"

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
