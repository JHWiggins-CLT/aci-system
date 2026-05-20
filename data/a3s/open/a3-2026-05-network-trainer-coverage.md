---
a3_id: a3-2026-05-network-trainer-coverage
title: Trainer capacity is modeled as nominal availability but is shared with shift coverage
opened: 2026-05-20
state: open
owner: Priya Nair (regional operations director)
source_investigation: 2026-03-15_dal-02_throughput_drop
related_pattern: (none yet — pattern library gated on 3+ same-mechanism cases; this A3 is the first)
network_applicability: network (target scope); confirmed evidence single-facility (dal-02) as of 2026-05-20 — see Current state
companion_kaizen: k-2026-05-dal-02-trainer-ratio
---

# A3: Trainer capacity is modeled as nominal availability but is shared with shift coverage

**A3 ID:** a3-2026-05-network-trainer-coverage
**Opened:** 2026-05-20
**State:** open
**Owner:** Priya Nair (regional operations director)
**Source investigation:** investigations/2026-Q1/2026-03-15_dal-02_throughput_drop.md
**Companion Kaizen:** kaizens/open/k-2026-05-dal-02-trainer-ratio.md (the dal-02 facility fix)
**Related pattern:** none yet — this is the first case of the mechanism; flagged as a seed for `cohort_overload_throughput_dip`
**Network applicability:** network (target scope); evidence confirmed single-facility (dal-02). Network scope is a hypothesis pending the peer-evidence gate (see Follow-up schedule), not a finding.

---

## Current state

The dal-02 cohort of 6 new hires (onboarded 2026-03-02) produced a measurable throughput dip during week-1 pick certification:

- **Magnitude:** `bash calc/descriptive/avg_cph.sh dal-02 --start 2026-03-08 --end 2026-03-22` → 128.10 vs February baseline `bash calc/descriptive/avg_cph.sh dal-02 --start 2026-02-01 --end 2026-02-28` → 141.82 (**−9.68%**).
- **Worst day:** `bash calc/descriptive/worst_day.sh dal-02 cph --start 2026-03-08 --end 2026-03-22` → 2026-03-18 | 120.81 (the date the floor intake logged the week-3 cohort resignation).
- **Drivers:** `bash calc/diagnostic/change_drivers.sh dal-02 --baseline 2026-02-01:2026-02-28 --comparison 2026-03-08:2026-03-22 --top 4` ranks mispick **+74.62%** and headcount_new **+54.83%** an order of magnitude above the rest — the cohort-overload signature.
- **Duration:** 15 days (2026-03-08 to 2026-03-22), recovering to 141.56 in April.
- **Business impact estimate:** ≈ 12,300 units forgone over the window (13.72 cph delta × ~60 hours_run/day × 15 days). At dal-02's run rate this is roughly two-thirds of a single day's output spread across the cohort window.

**Why this is an A3 and not just the dal-02 Kaizen.** The floor confirmed the *mechanism* was not "new hires are slow" but "the lead trainer was simultaneously covering a vacant night-shift lead role, stretching the trainer ratio from the nominal 1:4 to an effective 1:6." That is a **structural** assumption error: the network's onboarding standard work models trainer availability as nominal headcount, but in practice trainer time is silently shared with shift-coverage gaps. The dal-02 Kaizen fixes dal-02; this A3 addresses the assumption, which can recur at any facility that hits a coverage gap during a cohort onboarding.

**Scope evidence as of 2026-05-20 (honest, calc-grounded).** A network sweep of the cohort-overload signature — `bash calc/diagnostic/correlate.sh <facility> cph headcount_new` for all 8 facilities over the full window — shows the signature is **currently single-facility**:

| facility | pearson_r (cph ~ headcount_new) | reading |
|----------|----------------------------------|---------|
| dal-02   | −0.32 | weak negative — the proof case |
| ral-02   | −0.19 | negligible (most-exposed peer) |
| sav-01   | −0.13 | negligible |
| chr-03, chr-05, hou-01, atl-01, atl-03 | ≈ 0 | negligible |

So the network claim is **not yet data-supported** — no peer currently exhibits the signature. This A3 therefore opens with single-facility evidence and a **peer-evidence gate** (below): the structural countermeasure is staged, but network-wide standardization waits on the gate so we don't standardize against a one-facility sample.

---

## Target state

1. **dal-02 (confirmed scope):** through the week-1 certification of the next cohort onboarding (≥5 trainees), CPH stays within 5% of the pre-cohort 30-day baseline. (This is the companion Kaizen's target; the A3 inherits it as the proof point.)
2. **Network (target scope, gated):** every facility onboarding a cohort >4 has **dedicated** trainer coverage for week-1 certification — trainer time not shared with shift coverage — and that coverage is *measurable* (a pre-staged second trainer is recorded as an event before certification begins). This target is rolled out only to facilities the peer-evidence gate flags as exposed, or network-wide if the gate plus the 2026-06-15 peer poll confirms the exposure is structural rather than a dal-02 idiosyncrasy.
3. **Quality constraint during recovery:** mispick rate at any onboarding facility stays within 20% of its pre-cohort baseline through week-1 (the cohort overload showed up first as a mispick spike, so quality is the leading indicator).

---

## Root cause

- **Confirmed hypothesis (from the floor intake):** the lead trainer was pulled to dual-cover a vacant night-shift lead role during week-1 pick certification, stretching the trainer-to-trainee ratio from the nominal 1:4 to an effective 1:6.
- **Mechanism:** onboarding standard work assumes a trainer is fully available at nominal ratio. It has no guardrail against that trainer being the same person who absorbs a shift-coverage gap. When a coverage gap and a cohort onboarding coincide, trainer attention is silently halved and the cohort under-performs — visible downstream as a CPH dip and a mispick spike, not as a staffing exception.
- **Floor observation that pinned it:** the cohort's worst day (2026-03-18) coincided with a week-3 cohort-member resignation; the night-shift lead vacancy (2026-03-02 leadership_change event) is what created the dual-cover demand. Both are now in `data/events/dal-02.csv` as floor-intake rows.
- **Supporting evidence:** mispick +74.62% and headcount_new +54.83% (change_drivers, above); peer facilities unaffected in the same window (`bash calc/descriptive/avg_cph.sh hou-01 --start 2026-03-08 --end 2026-03-22` → 135.48, flat vs its baseline), ruling out a network-wide cause for *this* occurrence.

---

## Countermeasures

1. **Make trainer coverage dedicated, explicit standard work** (owner: Priya Nair). Amend the onboarding SOP so that for any cohort >4, the assigned trainer is formally relieved of all secondary/shift-coverage duties for week-1 certification, network-wide. (The dal-02 Kaizen already implements this locally; this generalizes it.)
2. **Make trainer coverage measurable** (owner: facility ops managers). Require a `pre-staged second trainer` event logged before week-1 certification begins for any cohort >4, so coverage is auditable rather than assumed.
3. **Peer-evidence gate before network rollout** (owner: Priya Nair). Run the cross-facility cohort-overload sweep (`correlate.sh <peer> cph headcount_new`) plus the 2026-06-15 network-sync poll on informal dual-cover arrangements. Roll the SOP amendment to facilities the gate flags as exposed; standardize network-wide only if the gate confirms structural (not dal-02-specific) exposure. *Cite the pattern's worked-countermeasures here once the pattern exists; for now the only worked countermeasure is the dal-02 Kaizen, outcome pending.*

---

## Plan

| Action | Owner | Start | Complete by | Status |
|--------|-------|-------|-------------|--------|
| dal-02 Kaizen in force (proof case) | Lisa Chen | 2026-05-18 | 2026-05-18 | done |
| Draft network SOP amendment (dedicated trainer coverage, cohort >4) | Priya Nair | 2026-05-20 | 2026-06-12 | in progress |
| Run peer-evidence gate: correlate sweep + 2026-06-15 network-sync poll | Priya Nair | 2026-06-15 | 2026-06-15 | pending |
| Decide rollout scope (exposed-facilities vs network-wide) from gate result | Priya Nair | 2026-06-15 | 2026-06-22 | pending |
| Add `pre-staged second trainer` to the event taxonomy (maintain/add_event_type) | Priya Nair | TBD by 2026-06-22 gate | 2026-07-01 | pending |

---

## Follow-up schedule

| Date | Check | Calc invocation | Target |
|------|-------|-----------------|--------|
| 2026-06-15 | Proof case still at target when the network decision is made | `bash calc/outcome/follow_up_check.sh dal-02 cph --target 138 --by 2026-06-15 --window-days 14` | RESULT PASS |
| 2026-06-15 | Peer-evidence gate: most-exposed peer has not developed the cohort-overload signature | `bash calc/diagnostic/correlate.sh ral-02 cph headcount_new` | r ≥ −0.35 (no peer worse than weak-negative; investigate any that is before rollout) |

*The full gate sweep runs `correlate.sh <peer> cph headcount_new` for all 7 peers; ral-02 is the row tracked here as the current most-exposed peer (−0.19). Any peer that crosses −0.35 triggers a facility investigation before that peer is included in the rollout.*

---

## Lessons learned

*Filled in at A3 close. Will feed the pattern library via `maintain/procedures/update_pattern.md` once a `cohort_overload_throughput_dip` pattern exists (3+ same-mechanism cases; currently 1).*

---

## Closing

*Filled in at A3 close.*

- Outcome at each follow-up: did the metric hit the target?
- What worked, what didn't
- Network applicability assessment: did the gate confirm structural exposure, or was dal-02 idiosyncratic?
- Pattern updates triggered

---

*An A3 without a populated follow-up schedule is incomplete. This A3's two follow-up rows are mirrored in `data/follow_ups/INDEX.md` under `artifact_id = a3-2026-05-network-trainer-coverage`.*
