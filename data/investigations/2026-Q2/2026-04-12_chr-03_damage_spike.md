---
investigation_id: 2026-04-12_chr-03_damage_spike
facility: chr-03
signal_type: damage_spike
signal_date: 2026-04-12
state: kaizen_open
drafted_on: 2026-05-19
floor_visit_on: 2026-05-19
closed_on: 2026-05-19
investigator: ACI-assistant
playbook: investigate/playbooks/damage_spike.md
disposition: k-2026-05-chr-03-bin-relocation
kaizen_id: k-2026-05-chr-03-bin-relocation
---

# Floor Brief: chr-03 damage spike, 2026-04-12 to 2026-04-24

**Investigation ID:** 2026-04-12_chr-03_damage_spike
**Investigator:** ACI-assistant
**Date drafted:** 2026-05-19
**Signal:** Damage at chr-03 jumped from a baseline mean of 11.39 units/day to 28.36 units/day during Apr 12-24 (+149%), with error_rate hitting 4.03 on 2026-04-22 (target <=2.8). Signal coincides with bin relocation SOP change in zones 3-4 on 2026-04-08.

> PLAYBOOK PROVENANCE: This investigation was run off-playbook (no damage_spike playbook existed at draft time); its structure mirrored the dal-02 throughput_drop worked example. `investigate/playbooks/damage_spike.md` was subsequently authored *from* this investigation's diagnostic sequence — the same pattern by which throughput_drop was authored from the dal-02 case. Future chr-03-style damage signals follow that playbook directly.

> After your floor visit, return to update findings via close-loop.
> Likely next states: confirmed -> Kaizen (reversal of bin relocation) or A3 (if SOP change process is systemically flawed).

## What we see

Damage at chr-03 spiked starting 2026-04-13, four days after a documented bin relocation SOP change consolidated high-velocity SKUs into zones 3-4 (2026-04-08). The spike ran through 2026-04-24 -- 13 operating days -- averaging 28.36 units/day vs a long-run baseline of 11.39 (a 149% increase). Worst single day was 2026-04-22 at 43 damaged units. A team huddle introducing the new bin map was logged 2026-04-11. Critically, CPH did not decline (135.74 vs baseline 135.48), confirming this is a handling/accuracy problem, not a throughput problem. No cooccurring events other than the bin relocation and its associated huddle.

## What the data says about why

### Hypothesis A -- Bin relocation increased physical damage risk (strongest)

- **Mechanism:** Relocating high-velocity SKUs into zones 3-4 likely placed them in tighter aisles or at higher stacking heights, making frequent pulldowns more hazardous. High-velocity bins are accessed many times per shift, so even a modest per-touch damage rate amplifies rapidly into a large daily total.
- **Supporting evidence:**
  - change_drivers ranks damage as the #1 mover (+149.05%) over the spike window, far above all other metrics.
  - cooccurrence (bash calc/diagnostic/cooccurrence.sh chr-03 2026-04-15 --window 14): 2026-04-08 sop_change "Bin relocation in zones 3-4 to consolidate high-velocity SKUs" and 2026-04-11 training "Brief team huddles introducing new bin map." No other events in window.
  - Damage elevated uniformly across all days of the week (Mon 28.50, Tue 27.50, Wed 24.50, Thu 31.50, Fri 31.00, Sat 26.00) vs flat baseline (Mon 11.67 through Sat 11.50). Uniform elevation consistent with a sustained physical condition change, not shift-specific.
  - Missort also up +73.37% -- consistent with navigation confusion in a reconfigured zone.
- **Counter-evidence:** No direct calc for bin height, aisle width, or per-bin touch frequency. Causal chain is mechanistic inference from timing; floor visit must confirm the physical configuration change.
- **Pattern match:** data/patterns/ directory is empty (Phase 6 deferred). No pattern match performed.

### Hypothesis B -- Picker unfamiliarity with new bin map (likely; probably compounds A)

- **Mechanism:** Brief team huddles may be insufficient for high-velocity muscle-memory workflows. Pickers navigating unfamiliar bin locations may handle product less carefully, driving both damage and missort in the transition period.
- **Supporting evidence:**
  - Missort co-spike (+73.37%) is consistent with bin-map navigation confusion.
  - Spike onset 2026-04-13 (2 days post-huddle) is consistent with normal operations revealing new-configuration hazards.
- **Counter-evidence:** No taper visible through 2026-04-24 -- if unfamiliarity were primary, we would expect decline as pickers adapted. Sustained flat elevation suggests physical configuration (A) dominates.

### Hypothesis C -- Volume or headcount shock (ruled out)

- **Mechanism:** Volume surge or headcount shortfall forcing rushed picks and more damage.
- **Evidence:** change_drivers shows inbound_units -4.73%, headcount_new +5.42% -- minor, neither directionally consistent. error_rate up only +28.33% while damage up +149% -- disproportionate to general quality degradation; consistent with a physical-configuration cause.
- **RULED OUT** -- confirm on floor only if floor raises a volume concern.

## Questions for the floor

- (Hypothesis A) After the relocation, were zones 3-4 physically tighter -- narrower aisles, greater stacking heights, or bin positions requiring overhead reach or below-knee pulls? This is the central question.
- (Hypothesis A) Which specific SKUs moved into zones 3-4? Are they heavy, fragile, or awkwardly packaged items with higher inherent damage risk?
- (Hypothesis B) Was the Apr-11 huddle the only training for the new bin map? Did any pickers report confusion about the new locations in the first week?
- (Hypothesis A+B) Was damage concentrated on specific bin positions or SKUs within zones 3-4, or spread evenly?
- (Open) Has the damage rate started to come down after Apr-24?
- (Open) Were any informal adjustments made to the bin layout after the spike was noticed?

## Methodology (every invocation reproducible)

Step 1 -- Confirm signal shape:
- bash calc/descriptive/avg_cph.sh chr-03 --start 2026-01-19 --end 2026-04-11 => 135.48
- bash calc/descriptive/avg_cph.sh chr-03 --start 2026-04-12 --end 2026-04-24 => 135.74 (flat -- not a throughput event)
- bash calc/descriptive/avg_cph.sh chr-03 --start 2026-04-25 --end 2026-05-18 => 135.87
- bash calc/descriptive/days_below_target.sh chr-03 error_rate --max 2.8 --start 2026-04-12 --end 2026-04-24 => 6/11
- bash calc/descriptive/worst_day.sh chr-03 error_rate --start 2026-04-12 --end 2026-04-24 => 2026-04-22 | 4.03

Step 2 -- Rule out network-wide (peer atl-01):
- bash calc/descriptive/days_below_target.sh atl-01 error_rate --max 2.8 --start 2026-04-19 --end 2026-05-18 => 0/25 (chr-03 signal is facility-isolated)

Step 3 -- Cooccurring events:
- bash calc/diagnostic/cooccurrence.sh chr-03 2026-04-15 --window 14 => 2026-04-08 sop_change "Bin relocation in zones 3-4" + 2026-04-11 training "Brief team huddles introducing new bin map"

Step 4 -- Rank upstream drivers:
- bash calc/diagnostic/change_drivers.sh chr-03 --baseline 2026-01-19:2026-04-11 --comparison 2026-04-12:2026-04-24 --top 10
  => damage +149.05%, missort +73.37%, wms_incidents -45.47%, conveyor_down_m +45.08%, scanner_faults -33.71%, error_rate +28.33%, late_pick +12.69%, mhe_down_m -12.51%, headcount_new +5.42%, inbound_units -4.73%

Step 5 -- Day-of-week segmentation:
- bash calc/diagnostic/segment_by.sh chr-03 exceptions damage --by dow --start 2026-04-12 --end 2026-04-24
  => Mon 28.50, Tue 27.50, Wed 24.50, Thu 31.50, Fri 31.00, Sat 26.00
- bash calc/diagnostic/segment_by.sh chr-03 exceptions damage --by dow --start 2026-01-19 --end 2026-04-11
  => Mon 11.67, Tue 11.25, Wed 12.25, Thu 10.17, Fri 11.50, Sat 11.50 (baseline -- flat)

Pattern check: data/patterns/ directory is empty (Phase 6 deferred). No pattern match performed.
History check: data/investigations/INDEX.md -- no prior damage_spike investigations at chr-03 or any facility.

## Bring back from the floor (feeds intake)

### Hypothesis A check (bin relocation physical hazard)

- **Confirm / rule out:** Can the floor lead describe a specific physical configuration change in zones 3-4 that makes pulldowns harder? Is damage concentrated on the bins that moved?
- **Strength:** If floor confirms tighter aisles/higher stacking and damage concentrates on relocated bins -- hypothesis confirmed at high confidence -> Kaizen to reverse/reconfigure.

### Hypothesis B check (unfamiliarity)

- **Confirm / rule out:** Any reported picker confusion in the first week? Has damage started declining by visit date (taper = unfamiliarity-driven; sustained = physical configuration-driven)?

### Hypothesis C check (volume/staffing)

- Skip unless floor raises a volume or headcount concern. Pre-floor data ruled out.

### Surprises to capture

- Whether informal adjustments to bin layout have already been made after Apr-24 (and whether damage came back down as a result -- strong evidence for Hypothesis A)
- Whether specific SKUs or specific pickers account for a disproportionate share of damage
- Whether the bin relocation had management sign-off or was a floor-level informal rearrangement (affects Kaizen scope)
- Whether brief team huddles are the standard change-management protocol for bin relocations at chr-03

### Disposition pre-think

- **Most likely:** Kaizen -- reverse or reconfigure the high-risk bin positions for the top high-velocity SKUs. Well-bounded physical fix, operational not architectural.
- **Could escalate to A3 if:** bin relocations routinely happen without a damage-impact review -- that is a process-architecture problem.
- **Pattern-worthy?** Probably yes after floor confirmation. Candidate pattern: bin_relocation_damage_spike. Signal shape: sop_change (bin relocation) -> damage spike within <=5 days -> no CPH impact -> missort co-spike -> uniform DOW distribution.

---

*This brief is the starting point of a floor conversation, not the conclusion. Its purpose is to make floor time maximally productive. The brief being defensible and reproducible is what matters, not the brief being right.*

---

# Floor Feedback Intake

**Investigation ID:** 2026-04-12_chr-03_damage_spike
**Floor visit:** 2026-05-19
**Visited by:** CI manager (direct floor confirmation)
**Floor contacts:** chr-03 ops floor (confirmed via CI manager relay)
**Intake recorded:** 2026-05-19

## 1. Hypothesis disposition

### Hypothesis A -- Bin relocation increased physical damage risk

- **Status:** CONFIRMED
- **Floor evidence:**
  - The bin relocation moved high-velocity SKUs into a tighter aisle in zones 3-4.
  - Stack heights increased for the relocated SKUs as part of the consolidation.
  - Damage during pulldowns spiked as a result: pickers pulling high-frequency SKUs from tighter aisles with higher stacks were at elevated risk of dropping or crushing units on each pull.
  - The floor has already informally reversed the move for the top 6 SKUs; damage has returned to normal levels.
- **Strength:** STRONG -- floor observation directly confirms the physical mechanism hypothesized. The informal reversal acting as a natural experiment (damage back to normal after reversal) is the strongest possible corroboration.

### Hypothesis B -- Picker unfamiliarity with new bin map

- **Status:** INCONCLUSIVE (secondary factor; subsumed by A)
- **Floor evidence:**
  - Not separately confirmed by the floor. The physical configuration change (Hypothesis A) is the confirmed primary driver.
  - Unfamiliarity likely contributed in the first few days but the floor did not attribute the sustained spike to map confusion -- physical conditions were the identified cause.
- **Strength:** WEAK as standalone; likely compound with A in the early days of the spike.

### Hypothesis C -- Volume or headcount shock

- **Status:** RULED OUT
- **Floor evidence:** Floor did not raise volume or staffing as a factor.
- **Strength:** STRONG (consistent with pre-floor data ruling).

## 2. What the data missed

- The specific physical details of the aisle narrowing and stack height increase -- the data has no direct measure of bin configuration, aisle clearance, or per-SKU stack height. The cooccurrence captured the relocation event but not the physical outcome.
- The informal partial reversal after Apr-24 (top 6 SKUs moved back) -- this action was not logged in the events system.

## 3. Surprises

- The floor acted before the investigation completed: the top 6 SKUs have already been informally reversed. Damage is back to normal. This is the fastest possible confirmation -- an accidental natural experiment.
- The informal reversal was only for the top 6 SKUs. The full relocation involved more SKUs; not all were reversed. The Kaizen should formalize which SKUs are reverted and confirm the remaining SKUs are safe at their current positions.

## 4. New questions raised

- Are the remaining relocated SKUs (beyond the top 6) also in hazardous positions? The informal reversal covered the highest-velocity ones, but a zone inspection for all relocated SKUs should be part of the Kaizen.
- Should the bin relocation SOP include a physical configuration impact assessment before any future relocation? This is the A3 question -- left open for now.
- Does atl-01 (chr-03 peer) have a similar bin relocation planned or underway? If so, flag proactively.

## 5. Floor-attributed observations to log

- data/events/chr-03.csv: Add `2026-04-12, chr-03, sop_change, "Bin relocation in zones 3-4 effective date -- damage spike begins as high-velocity SKUs now in tighter aisle with higher stacks", floor-intake-2026-05-19`
- data/events/chr-03.csv: Add `2026-05-15, chr-03, sop_change, "Informal partial reversal of bin relocation for top 6 high-velocity SKUs; damage returned to normal levels", floor-intake-2026-05-19`

## 6. Disposition

- [ ] Close as resolved -- signal was a one-off
- [ ] Close as monitoring -- watch for recurrence
- [ ] Open A3 -- systemic, structured root-cause work
- [x] Open Kaizen -- quick targeted change
- [ ] Re-open as investigation -- brief was wrong
- [ ] Escalate -- outside CI scope

**Rationale:** The cause is confirmed and well-bounded: a specific physical configuration change caused a specific damage spike. The informal fix already worked. The Kaizen formalizes the reversal for the top 6 SKUs, schedules a zone inspection for remaining relocated SKUs, and establishes a follow-up check. This is a facility-specific operational fix -- Kaizen, not A3. The A3 question (whether the SOP change process should require a damage-impact assessment) is flagged in section 4 but left open; if a second similar case surfaces, escalate to A3.

**Suggested Kaizen scope:** Formally restore the original bin positions for the top 6 high-velocity SKUs in zones 3-4. Conduct a physical zone inspection for all remaining relocated SKUs within 2 weeks. Owner: chr-03 ops manager. Target metric: error_rate <= 2.8 sustained through next 30-day follow-up check.

## 7. Pattern feedback

- **Matched pattern:** none -- data/patterns/ directory is empty (Phase 6 deferred).
- **Pattern-seeding recommendation:** This case is a strong seed for patterns/bin_relocation_damage_spike.md. Signal shape: sop_change (bin relocation) event -> damage spike within <=5 days -> no CPH impact -> missort co-spike -> uniform DOW distribution -> reversal resolves spike. Countermeasure that worked: restore original bin positions for high-velocity SKUs. Pattern threshold (3+ cases) not yet met; flag for revisit after 2 more similar cases at any facility.

## 8. Follow-up commitments

- 2026-05-19 -- chr-03 ops manager: formally restore top 6 high-velocity SKU bin positions (formalize the informal reversal already done).
- 2026-06-02 -- chr-03 ops manager: complete physical zone inspection of all remaining relocated SKUs in zones 3-4 and confirm no hazardous positions remain.
- 2026-06-19 (30-day check) -- CI manager: run follow_up_check on chr-03 error_rate.
- 2026-07-19 (60-day check) -- CI manager: run follow_up_check on chr-03 error_rate.
