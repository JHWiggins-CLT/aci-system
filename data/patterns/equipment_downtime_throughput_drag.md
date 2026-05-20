# Pattern: Equipment-downtime throughput drag

Three closed investigations share this mechanism: a discrete equipment failure
(conveyor or MHE) drives a one-week CPH drop that recovers as soon as the
component is repaired. First authored 2026-05-20 from ral-02, sav-01, and atl-03.

## Signal shape

CPH **8-15% below baseline for roughly one week (5-8 days)**, in a **V-shape** that
recovers fully once the equipment is fixed. The defining tell, which separates this
from a cohort-overload dip:

- An **equipment-family metric is the dominant `change_drivers` mover** — `conveyor_down_m`
  or `mhe_down_m` up by an order of magnitude (10x+ baseline).
- **Quality is roughly flat** — `mispick`/`missort` are NOT among the top movers.
- **`headcount_new` is flat** and `correlate.sh cph headcount_new` is negligible
  (rules out the cohort mechanism).

Most common at Distribution-type facilities (high conveyor/MHE dependence), but seen
at Cold Storage too (sav-01).

## Typical co-occurring events

- `incident` (the equipment failure) at or just before the window start.
- `equipment_install` (repair / component replacement) 1-3 days into the window;
  CPH recovery follows it closely.

## Investigation steps (run these first when the signal matches)

1. `bash calc/descriptive/avg.sh {facility} cph --start {baseline_start} --end {baseline_end}` then the drag window then the post window — confirm the V-shape and magnitude.
2. `bash calc/diagnostic/change_drivers.sh {facility} --baseline {baseline} --comparison {drag_window} --top 3` — expect an equipment-family metric on top, quality flat.
3. `bash calc/diagnostic/cooccurrence.sh {facility} {signal_date} --window 10` — expect an `incident` + `equipment_install` pair.
4. `bash calc/diagnostic/correlate.sh {facility} cph headcount_new` — expect negligible (confirms it is NOT a cohort dip).
5. Peer check with `avg.sh` on a same-type facility over the same window — expect the peer unaffected (rules out a network cause).

## Floor questions when this pattern is suspected

- Confirm the failure and the workaround used during the outage — how much of the window ran fully down vs degraded?
- Was the failure sudden, or had the equipment shown wear/warning signs? (Determines whether preventive inspection would have caught it.)
- Is a critical spare for the failed component stocked on-site, or did the repair wait on a part?

## Expected resolution timeline

Recovers within **1-3 days of the `equipment_install`** (component replacement). If CPH
stays depressed after the repair event, the replacement did not fix the root cause —
escalate and re-investigate rather than crediting a recovery that hasn't happened.

## Countermeasures that have worked

- **Reactive component replacement → fast recovery (confirmed across all 3 instances).**
  ral-02: belt replaced 2026-04-22, CPH 77.43 (drag) → 91.79 (May). sav-01: MHE drive
  replaced 2026-03-11, 61.18 → 70.59 (Apr). atl-03: gearbox replaced 2026-04-08,
  81.23 → 91.89 (May). See the three investigation files under Historical instances.
- **Critical-spare staging + preventive inspection cadence (preventive; outcome pending).**
  See kaizens/open/k-2026-05-ral-02-conveyor-pm.md — caps unplanned downtime by removing
  the parts-wait gap and catching wear before failure. Whether it reduces *recurrence*
  is the open outcome this pattern will learn from at Kaizen close.

## Countermeasures that didn't work

- None observed yet. (Honest: only one preventive countermeasure is in flight, outcome
  pending. Update via maintain/procedures/update_pattern.md when an A3/Kaizen closes.)

## Historical instances

- investigations/2026-Q2/2026-04-22_ral-02_throughput_drop.md (conveyor belt, −14.9%)
- investigations/2026-Q1/2026-03-11_sav-01_throughput_drop.md (MHE drive, −12.5%)
- investigations/2026-Q2/2026-04-07_atl-03_throughput_drop.md (conveyor gearbox, −12.7%)
