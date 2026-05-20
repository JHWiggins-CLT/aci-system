---
investigation_id: 2026-03-15_dal-02_throughput_drop
facility: dal-02
signal_type: throughput_drop
signal_date: 2026-03-15
state: kaizen_open
drafted_on: 2026-05-18
floor_visit_on: 2026-05-18
closed_on: 2026-05-18
investigator: portfolio-demo
playbook: investigate/playbooks/throughput_drop.md
disposition: kaizen + a3
kaizen_id: k-2026-05-dal-02-trainer-ratio
a3_id: a3-2026-05-network-trainer-coverage
---

<!--
PAIRED DISPOSITION NOTE: this investigation disposed as a Kaizen on 2026-05-18
(the dal-02 facility fix). On 2026-05-20 a companion A3
(a3-2026-05-network-trainer-coverage) was opened from the same investigation to
address the *systemic* assumption the case revealed — trainer capacity modeled
as nominal but shared with shift coverage. The investigation state stays
`kaizen_open` (its original, primary disposition); the A3 is a network-scope
follow-on, not a re-disposition. This deviates from open_a3.md steps 11-12,
which assume the A3 closes a still-open investigation; here the investigation
was already closed as a Kaizen. See tracking.md decision log (2026-05-20).
-->


# Floor Brief: dal-02 throughput drop, 2026-03-08 to 2026-03-22

**Investigation ID:** 2026-03-15_dal-02_throughput_drop
**Investigator:** portfolio-demo
**Date drafted:** 2026-05-18
**Signal:** Average CPH at dal-02 fell from a Feb baseline of 141.82 to 128.10 over Mar 8-22 — a 9.68% drop, ~12 CPH below the 140 facility target. Full recovery to 141.56 in April was complete and unexplained-by-action.

> This investigation will be tracked through resolution.
> After your floor visit, return to update findings via close-loop.
> Likely next states: confirmed → Kaizen (trainer-ratio guardrail) or A3 (if systemic to onboarding cadence across facilities).

## What we see

Throughput at dal-02 dipped sharply during a two-week window in March, then recovered fully without any documented intervention. Peer facility hou-01 — paired with dal-02 by size and SKU mix — held flat at ~135 CPH across the same window (vs 136.01 in February), ruling out a network-wide demand or weather cause. The dip aligns precisely with a cohort onboarding event captured in the events log on 2026-03-02. `change_drivers` shows mispick volume rose 74.62% and `headcount_new` rose 54.83% — the largest two upstream movements by a wide margin — consistent with an inexperienced-picker hypothesis rather than equipment or volume issues. Day-of-week segmentation shows the dip distributed evenly across operating days, consistent with cohort-wide drag rather than a single shift or trainer.

## What the data says about why

### Hypothesis A — Cohort onboarding overload (**strongest**)

- **Mechanism:** A cohort of 6 new hires onboarded on 2026-03-02 with pick certification beginning 2026-03-06 lifted `headcount_new` from a baseline of 22.88 to 35.42 during the dip window (+54.83%). Trainer attention split across the cohort produced a rework spike (mispick +74.62%), which mechanically slowed throughput both directly (lower picker output) and indirectly (verification/rework drag on tenured pickers). The April recovery — `headcount_new` back to ~23, mispick back to ~19 — coincides with cohort certification completing.
- **Supporting evidence:**
  - CPH drop confirmed: `bash calc/descriptive/avg_cph.sh dal-02 --start 2026-02-01 --end 2026-02-28` → 141.82 vs `--start 2026-03-08 --end 2026-03-22` → 128.10 (−9.68%).
  - Peer hou-01 unaffected: `bash calc/descriptive/avg_cph.sh hou-01 --start 2026-03-08 --end 2026-03-22` → 135.48 vs February baseline 136.01.
  - Cohort events in window: `bash calc/diagnostic/cooccurrence.sh dal-02 2026-03-15 --window 14` returns the 2026-03-02 cohort onboard and the 2026-03-06 pick certification kickoff. No competing events.
  - Upstream movement: `bash calc/diagnostic/change_drivers.sh dal-02 --baseline 2026-02-01:2026-02-28 --comparison 2026-03-08:2026-03-22 --top 5` ranks mispick (+74.62%) and headcount_new (+54.83%) as the top two drivers by an order of magnitude over the third (error_rate +18.99%). Volume and mix drivers (inbound_units +4.43%, order_mix_complex flat) are bottom-of-table.
  - Time distribution: `bash calc/diagnostic/segment_by.sh dal-02 operational cph --by dow --start 2026-03-08 --end 2026-03-22` shows CPH within ~7 CPH across Mon-Sat (Mon 126.08, Sat 131.61). No single shift or weekday cluster — the drag is cohort-wide.
- **Counter-evidence:** None decisive. We have no calc-derived trainer-to-trainee ratio metric, so the "trainer overload" story is mechanistic inference, not measured. The floor visit should confirm the ratio was stretched.
- **Pattern match:** No pattern library yet — `data/patterns/INDEX.md` does not exist (Phase 6). If a pattern is later authored from this investigation, candidate name: *cohort_overload_throughput_dip*. Signal shape: headcount_new spike + mispick co-spike + CPH dip + clean recovery on certification completion.

### Hypothesis B — Volume or mix shock (**ruled out**)

- **Mechanism:** A volume spike or shift toward complex orders would depress CPH mechanically.
- **Evidence:** `change_drivers` shows `inbound_units` +4.43% and `order_mix_complex` change effectively zero — both bottom-of-table movements. Peer hou-01 absorbed the same network demand and held steady.
- **RULED OUT** — confirm on the floor only if asked.

### Hypothesis C — Equipment or WMS incident (**possible but low**)

- **Mechanism:** Conveyor outage, MHE downtime, or WMS instability suppressing CPH.
- **Evidence:** `change_drivers` shows `conveyor_down_m` +9.09%, `mhe_down_m` −4.69%, `wms_incidents` (below top-10 cut) — none of these reach the 50% threshold the playbook flags as equipment-driven. No `equipment_install` or `system_change` event in the cooccurrence window. The dip's gradual onset and gradual recovery do not match an outage shape (outages produce sharp on/off transitions).
- **Action:** Brief floor question to maintenance lead, but don't promote unless the floor surfaces something the events log missed.

## Questions for the floor

- (Hypothesis A) Confirm the Mar-02 cohort size and that pick certification ran the standard 2-week curriculum. Was the trainer-to-trainee ratio (typically 1:4 here) maintained, or was it stretched? *This is the central question.*
- (Hypothesis A) Inputs data says 4 of 6 cohort members went to night shift. Does the floor agree, and did night shift see the worst of the CPH drag? (Note: segment_by dow shows the drag was even across days — does the floor have shift-level intuition we should investigate further?)
- (Hypothesis A) Are the 6 cohort members still on the floor in April, and are their individual CPH numbers now in normal range? (Answers whether the recovery was certification-driven or attrition-driven — these have very different Kaizen implications.)
- (Hypothesis C) Any conveyor or scanner trouble during the window that wasn't escalated to a formal incident?
- (Open) Anything else that started or ended in the 2026-03-08 to 2026-03-22 window — SOP change, shift-lead swap, vendor SKU change — that the data didn't capture?

## Methodology (every invocation reproducible)

Step 1 — Confirm signal shape:
- `bash calc/descriptive/avg_cph.sh dal-02 --start 2026-02-01 --end 2026-02-28` → 141.82 (baseline)
- `bash calc/descriptive/avg_cph.sh dal-02 --start 2026-03-01 --end 2026-03-07` → 140.83 (pre-cohort week)
- `bash calc/descriptive/avg_cph.sh dal-02 --start 2026-03-08 --end 2026-03-22` → 128.10 (dip window)
- `bash calc/descriptive/avg_cph.sh dal-02 --start 2026-03-23 --end 2026-03-31` → 138.59 (mid-recovery)
- `bash calc/descriptive/avg_cph.sh dal-02 --start 2026-04-01 --end 2026-04-30` → 141.56 (full recovery)

Step 2 — Rule out network-wide:
- `bash calc/descriptive/avg_cph.sh hou-01 --start 2026-03-08 --end 2026-03-22` → 135.48
- `bash calc/descriptive/avg_cph.sh hou-01 --start 2026-02-01 --end 2026-02-28` → 136.01

Step 3 — Cooccurring events:
- `bash calc/diagnostic/cooccurrence.sh dal-02 2026-03-15 --window 14` → 2026-03-02 training (cohort onboard), 2026-03-06 training (pick certification kickoff)

Step 4 — Rank upstream drivers:
- `bash calc/diagnostic/change_drivers.sh dal-02 --baseline 2026-02-01:2026-02-28 --comparison 2026-03-08:2026-03-22 --top 10` → mispick +74.62%, headcount_new +54.83%, error_rate +18.99%, lost −15.52%, scanner_faults −10.35%, cph −9.68%, conveyor_down_m +9.09%, damage +7.74%, mhe_down_m −4.69%, inbound_units +4.43%

Step 5 — Day-of-week segmentation:
- `bash calc/diagnostic/segment_by.sh dal-02 operational cph --by dow --start 2026-03-08 --end 2026-03-22` → Mon 126.08, Tue 128.32, Wed 124.74, Thu 127.24, Fri 130.58, Sat 131.61

Step 6 — Driver drill (mispick by dow):
- `bash calc/diagnostic/segment_by.sh dal-02 exceptions mispick --by dow --start 2026-03-08 --end 2026-03-22` → Mon 33.50, Tue 33.50, Wed 30.50, Thu 36.50, Fri 35.50, Sat 33.50

Pattern check: `data/patterns/INDEX.md` does not exist (Phase 6). No pattern match performed.
History check: `data/investigations/INDEX.md` lists no prior throughput_drop investigations at dal-02.

## Bring back from the floor (feeds intake)

### Hypothesis A check (cohort overload)

- **Confirm / rule out:** trainer-ratio observation during the window, cohort-vs-tenured CPH breakdown if floor leads kept rough notes, anecdotal "we knew this was rough." If pickers individually report the mentor-pairing felt thin, that's strong corroboration.
- **Strength:** if trainer ratio confirmed at 1:6+ during the window and cohort members are now hitting normal CPH, hypothesis confirmed at high confidence → Kaizen on trainer-ratio guardrail + cohort-staggering policy.

### Hypothesis B check (volume/mix)

- Skip unless floor proactively raises a volume or SKU concern. Pre-floor data ruled out.

### Hypothesis C check (equipment)

- **Confirm / rule out:** one direct question to the maintenance lead — any conveyor or scanner trouble during the window that didn't escalate. The data doesn't support equipment as primary, but a clean rule-out from the floor is worth the 60 seconds.
- **Strength:** unlikely to flip disposition; rules out the alternative cleanly.

### Surprises to capture

- Anything the floor remembers from the window that the events log missed
- Whether the night-shift lead changed during the window (no event captured, but worth asking)
- Whether the cohort itself reports anything unusual (curriculum gap, mentor pairing problem, equipment learning curve)

### Disposition pre-think

- **Most likely:** Kaizen — narrow, well-scoped countermeasure (trainer-ratio guardrail + cohort-size cap + staggered onboarding when ratio would otherwise stretch). The mechanism is well-understood; the countermeasure is operational, not architectural.
- **Could escalate to A3 if:** the floor reveals that cohort onboardings frequently hit this without being noticed, i.e. this is the *visible* instance of a recurring slow drag across multiple facilities. Then it's systemic and an A3 is warranted to change the standard onboarding plan.
- **Pattern-worthy?** Probably yes. If the floor confirms, this should become `data/patterns/cohort_overload_throughput_dip.md` with signal shape (headcount_new spike → CPH dip → mispick co-spike → recovery on certification) and the Kaizen countermeasure that worked.

---

*This brief is the starting point of a floor conversation, not the conclusion. Its purpose is to make floor time maximally productive — you walk in knowing what to look for, what to ask, and how to interpret what you hear. The brief is wrong sometimes; that's expected. The brief being **defensible and reproducible** is what matters, not the brief being **right**.*

---

# Floor Feedback Intake

**Investigation ID:** 2026-03-15_dal-02_throughput_drop
**Floor visit:** 2026-05-18 (single-day walkthrough)
**Visited by:** portfolio-demo (simulated)
**Floor contacts:** Lisa Chen (ops manager, dal-02); Marco Reyes (lead trainer, day shift); Priya Shah (maintenance lead); Jordan Webb (senior picker, day shift)
**Intake recorded:** 2026-05-18

## 1. Hypothesis disposition

### Hypothesis A — Cohort onboarding overload

- **Status:** CONFIRMED
- **Floor evidence:**
  - Ops manager confirmed cohort of 6 onboarded 2026-03-02; 4 went to night shift as inputs data showed.
  - Lead trainer's nominal ratio is 1:4. Actual ratio during week-1 certification was 1:6 because the trainer was simultaneously covering a vacant night-shift lead role (informal arrangement, not in the system).
  - 5 of 6 cohort members are still on the floor as of May. Individual CPH measurements taken the week of 2026-05-11 by the ops manager show all 5 in the 135-145 range — fully normalized.
  - 1 cohort member resigned in week 3 of training. Not captured in events log.
  - Quote from Jordan Webb (senior picker): "I lost half a shift one Tuesday training Maria when I should've been picking. It happened more than once."
  - Mispick spike of +74.62% in change_drivers corroborated anecdotally — multiple pickers volunteered that week 2 of the cohort window had unusually high rework volume.
- **Strength:** STRONG — every element of the data-side story was confirmed by independent floor sources, and the mechanism (trainer pulled to dual-cover) explains why the ratio stretched without being visible to the system.

### Hypothesis B — Volume or mix shock

- **Status:** RULED OUT
- **Floor evidence:**
  - No volume concern from ops manager during the window. Inbound forecasted within normal Q1 patterns.
  - Order mix described as "normal Q1." No promotional or vendor-driven complexity shifts.
- **Strength:** STRONG — consistent with pre-floor data ruling.

### Hypothesis C — Equipment or WMS incident

- **Status:** RULED OUT
- **Floor evidence:**
  - Maintenance lead confirmed no unrecorded conveyor or scanner trouble during the window. Routine maintenance ran on schedule.
  - WMS held steady; no deployment events near the window.
- **Strength:** STRONG.

## 2. What the data missed

- The trainer's informal dual-cover role on night shift — this is the *mechanism* that stretched the 1:4 ratio to 1:6, and it's a hidden coupling between training capacity and shift coverage. The system models the trainer as 100% available for training but the floor knew otherwise.
- The cohort member resignation in week 3 (no event captured). This means the effective cohort during week 3+ was 5, not 6 — small effect on the numbers but worth logging for completeness.

## 3. Surprises

- The dual-cover arrangement is informal and not specific to dal-02. The ops manager believes other facilities may have similar informal arrangements with their certified trainers. This investigation may surface a network-scope systemic issue, not just a dal-02 one.
- Individual cohort CPH numbers are now fully normal — the recovery was certification-driven, not attrition-driven. The one resignation removed an underperformer, but the remaining 5 all reached normal output without further intervention.

## 4. New questions raised

- How often is the lead trainer pulled for night-shift coverage in normal operations? If frequent, the trainer-ratio guardrail must model actual rather than nominal availability.
- Do other facilities have similar trainer/shift-coverage couplings? Worth a quick poll of ops managers at the next network sync. *(Flagged for potential A3 follow-up if 2+ other facilities report the same pattern.)*
- Should the cohort-size cap policy depend on facility size, or be a network-wide standard?

## 5. Floor-attributed observations to log

Add to `data/events/dal-02.csv`:
- `2026-03-02, dal-02, leadership_change, "Night-shift lead role vacant — lead trainer pulled to dual-cover during week-1 certification", floor-intake-2026-05-18`
- `2026-03-18, dal-02, training, "Cohort member resigned in week 3 of pick certification; effective cohort size dropped to 5", floor-intake-2026-05-18`

No candidate new metrics — existing schema captured what mattered. The "informal dual-cover" mechanism is captured naturally as a leadership_change event tied to the vacancy.

## 6. Disposition

- [ ] Close as resolved — signal was a one-off
- [ ] Close as monitoring — watch for recurrence
- [ ] Open A3 — systemic, structured root-cause work
- [x] **Open Kaizen — quick targeted change**
- [ ] Re-open as investigation — brief was wrong
- [ ] Escalate — outside CI scope

**Rationale:** Single confirmed cause, well-bounded fix at the facility level. Kaizen, not A3, because the change is operational (trainer release policy + cohort cap) rather than structural (re-architecting how training capacity is modeled). If the network-poll question (section 4) surfaces 2+ other facilities with the same dual-cover pattern, escalate to A3 at that point.

**Suggested Kaizen scope:** Trainer is formally relieved of all secondary coverage duties for the duration of week-1 pick certification when cohort size >4. Standard ratio target: 1:4. Cohorts >4 require a pre-staffed second trainer. Owner: Lisa Chen. Target metric: CPH stays within 5% of pre-cohort 30-day baseline through week-1 of next cohort onboarding.

## 7. Pattern feedback

- **Matched pattern:** none — pattern library does not yet exist (Phase 6 deferred).
- **Pattern-seeding recommendation:** this case is the seed for `patterns/cohort_overload_throughput_dip.md`. Signal shape: `headcount_new` spike → CPH dip (5-15%) → `mispick` co-spike → recovery on certification completion. Countermeasure that worked: trainer-ratio guardrail + cohort-size cap. Pattern threshold (3+ cases) not yet met; flag for revisit after 2 more similar cases at any facility.

## 8. Follow-up commitments

- 2026-05-18 — Lisa Chen: publish trainer release policy to dal-02 ops bulletin within 7 days; confirm in writing.
- Next cohort onboarding date — Lisa Chen: notify CI manager 30 days before next onboarding so the follow-up window can be observed.
- 2026-06-15 (network sync) — CI manager: poll other facility ops managers about informal dual-cover trainer arrangements.
