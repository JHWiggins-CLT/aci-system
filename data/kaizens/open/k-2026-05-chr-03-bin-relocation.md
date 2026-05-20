# Kaizen: Restore high-velocity SKU bin positions in zones 3-4, chr-03

**Kaizen ID:** k-2026-05-chr-03-bin-relocation
**Opened:** 2026-05-19
**State:** open
**Owner:** chr-03 ops manager
**Source:** 2026-04-12_chr-03_damage_spike
**Related pattern:** (none yet -- flagged as seed for patterns/bin_relocation_damage_spike.md)

---

## Observation

A bin relocation SOP change on 2026-04-08 moved high-velocity SKUs into tighter aisles in zones 3-4 with increased stacking heights. Damage during pulldowns spiked from a baseline mean of 11.39 units/day (max 17 across the 72-day pre-spike window) to 28.36 units/day, peaking at 43 on 2026-04-22 (+149%), across 2026-04-12 to 2026-04-24 — confirmed by `bash calc/diagnostic/change_drivers.sh chr-03 --baseline 2026-01-19:2026-04-11 --comparison 2026-04-12:2026-04-24 --top 10` and `bash calc/descriptive/worst_day.sh chr-03 damage --family exceptions --start 2026-04-12 --end 2026-04-24`. The floor informally reversed the move for the top 6 highest-velocity SKUs; damage returned to baseline (10.83 units/day in the 2 weeks ending 2026-05-18, confirmed by `bash calc/outcome/follow_up_check.sh chr-03 damage --max 18 --by 2026-05-18 --family exceptions --window-days 14`). The informal reversal was not formally logged and the remaining relocated SKUs beyond the top 6 have not yet been reviewed.

---

## Change

1. **Formalize the partial reversal already done:** chr-03 ops manager to formally document the restoration of original bin positions for the top 6 high-velocity SKUs in zones 3-4, and log the positions in the bin map system.
2. **Zone inspection for remaining relocated SKUs:** within 14 days of Kaizen open (by 2026-06-02), the chr-03 ops manager will conduct a physical inspection of all remaining SKUs relocated in the April 8 SOP change. Any SKU now in a position with reduced aisle clearance or increased stacking height that creates pulldown hazard is to be returned to its original position.
3. **Bin relocation change gate:** before any future bin relocation in zones 3-4 involving high-velocity SKUs, the ops manager must confirm: (a) no aisle clearance reduction, and (b) no stacking height increase for the affected SKUs. This gate is informal until a formal SOP update is drafted; CI manager to flag if a second relocation-damage event occurs at chr-03 or any peer facility.

---

## Tracking

Tracks `damage` directly (exceptions family) — the metric that actually moved — rather than the operational `error_rate` proxy. The ceiling of 18 sits just above the historical baseline max (17 over the 72-day pre-spike window), so normal operation passes and a genuine spike (mean 28.36, peak 43) fails.

- **Baseline:** damage mean 11.39 units/day, max 17 (2026-01-19 to 2026-04-11)
- **Target:** damage <= 18 units/day sustained (14-day rolling mean), confirmed by follow_up_check at 30 days and 60 days
- **Current (at Kaizen open):** damage 10.83 units/day (2-week window ending 2026-05-18) -- already back at baseline after the informal reversal; Kaizen formalizes the fix and schedules verification
- **Follow-up checks:**
  - 2026-06-19: `bash calc/outcome/follow_up_check.sh chr-03 damage --max 18 --by 2026-06-19 --family exceptions --window-days 14`
  - 2026-07-19: `bash calc/outcome/follow_up_check.sh chr-03 damage --max 18 --by 2026-07-19 --family exceptions --window-days 14`

---

## Outcome

*Filled in at close.*

- Did damage stay at or below 18 (14-day mean) through the 30-day and 60-day checks?
- Was the zone inspection completed by 2026-06-02 and were any additional SKUs found in hazardous positions?
- Was the change standardized (becomes SOP amendment) or was a second relocation-damage event triggered?
- Lessons that feed pattern library: if confirmed, this case becomes the seed for patterns/bin_relocation_damage_spike.md

---

*A Kaizen is deliberately lower-ceremony than an A3. The A3 question -- whether the bin relocation SOP process should require a physical configuration impact assessment -- is flagged but deferred. If a second relocation-damage case surfaces at chr-03 or any peer facility, escalate to A3.*
