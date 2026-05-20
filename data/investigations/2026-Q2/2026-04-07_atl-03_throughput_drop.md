---
investigation_id: 2026-04-07_atl-03_throughput_drop
facility: atl-03
signal_type: throughput_drop
signal_date: 2026-04-07
state: resolved
drafted_on: 2026-05-20
floor_visit_on: 2026-05-20
closed_on: 2026-05-20
investigator: portfolio-demo
playbook: investigate/playbooks/throughput_drop.md
disposition: resolved (reactive repair, self-recovered)
related_pattern: patterns/equipment_downtime_throughput_drag.md
---

# Floor Brief: atl-03 throughput drop, 2026-04-06 to 2026-04-13

**Investigation ID:** 2026-04-07_atl-03_throughput_drop
**Investigator:** portfolio-demo
**Date drafted:** 2026-05-20
**Signal:** CPH ~13% below baseline for one week following a conveyor gearbox failure.

> PATTERN PROVENANCE: one of the three investigations behind the
> `equipment_downtime_throughput_drag` pattern. Concise by design — the shape
> was recognized immediately from the ral-02 and sav-01 cases.

## What we see

atl-03 CPH fell from a March baseline of 93.03 (`bash calc/descriptive/avg.sh atl-03 cph --start 2026-03-01 --end 2026-03-31`) to 81.23 over 2026-04-06..13 (`bash calc/descriptive/avg.sh atl-03 cph --start 2026-04-06 --end 2026-04-13`) — a 12.7% drop — then recovered to 91.89 in May (`bash calc/descriptive/avg.sh atl-03 cph --start 2026-05-01 --end 2026-05-18`). Worst day 2026-04-07 | 79.09.

## What the data says about why

### Hypothesis A — Conveyor gearbox outage drags throughput (confirmed)

- **Mechanism:** a conveyor line-2 gearbox failure caused a partial shutdown until the gearbox was replaced and the line recommissioned.
- **Supporting evidence:** `bash calc/diagnostic/change_drivers.sh atl-03 --baseline 2026-03-01:2026-03-31 --comparison 2026-04-06:2026-04-13 --top 3` ranks `equipment|conveyor_down_m` +1606% (9.46 → 161.43 min/day) and `equipment|mhe_down_m` +99% as the top movers; `bash calc/diagnostic/cooccurrence.sh atl-03 2026-04-07 --window 10` returns the `incident` (2026-04-06 gearbox failure) and the `equipment_install` (2026-04-08 gearbox replaced). The 2026-04-14 audit event in the window is unrelated (post-recovery, advance-notice).
- **Pattern match:** patterns/equipment_downtime_throughput_drag.md (high).

### Hypotheses B/C — quality breakdown, cohort onboarding (RULED OUT)

- Quality metrics and `headcount_new` are not top movers; equipment downtime alone explains the drag.

## Methodology (every invocation reproducible)

- `bash calc/descriptive/avg.sh atl-03 cph --start 2026-03-01 --end 2026-03-31` → 93.03
- `bash calc/descriptive/avg.sh atl-03 cph --start 2026-04-06 --end 2026-04-13` → 81.23
- `bash calc/descriptive/avg.sh atl-03 cph --start 2026-05-01 --end 2026-05-18` → 91.89
- `bash calc/descriptive/worst_day.sh atl-03 cph --start 2026-04-06 --end 2026-04-13` → 2026-04-07 | 79.09
- `bash calc/diagnostic/change_drivers.sh atl-03 --baseline 2026-03-01:2026-03-31 --comparison 2026-04-06:2026-04-13 --top 3`
- `bash calc/diagnostic/cooccurrence.sh atl-03 2026-04-07 --window 10`
- peer check: `bash calc/descriptive/avg.sh ral-02 cph --start 2026-04-06 --end 2026-04-13` → 89.36 (peer unaffected in this window)

## Floor intake (2026-05-20)

- **Hypothesis A — CONFIRMED.** Line-2 gearbox failed 2026-04-06; partial shutdown until replacement and recommissioning 2026-04-08. CPH recovered after recommissioning.
- **Disposition:** resolved (reactive repair, self-recovered). Feeds the `equipment_downtime_throughput_drag` pattern as a historical instance; the preventive countermeasure is tracked under the ral-02 Kaizen.
