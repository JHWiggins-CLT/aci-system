---
investigation_id: 2026-03-11_sav-01_throughput_drop
facility: sav-01
signal_type: throughput_drop
signal_date: 2026-03-11
state: resolved
drafted_on: 2026-05-20
floor_visit_on: 2026-05-20
closed_on: 2026-05-20
investigator: portfolio-demo
playbook: investigate/playbooks/throughput_drop.md
disposition: resolved (reactive repair, self-recovered)
related_pattern: patterns/equipment_downtime_throughput_drag.md
---

# Floor Brief: sav-01 throughput drop, 2026-03-09 to 2026-03-16

**Investigation ID:** 2026-03-11_sav-01_throughput_drop
**Investigator:** portfolio-demo
**Date drafted:** 2026-05-20
**Signal:** CPH ~12% below baseline for one week following a primary-sort MHE failure.

> PATTERN PROVENANCE: one of the three investigations behind the
> `equipment_downtime_throughput_drag` pattern. This brief is intentionally
> concise — by the third case of this shape the diagnosis is fast (the value
> of a pattern). The mechanism was confirmed in a single pass.

## What we see

sav-01 CPH fell from a February baseline of 69.89 (`bash calc/descriptive/avg.sh sav-01 cph --start 2026-02-01 --end 2026-02-28`) to 61.18 over 2026-03-09..16 (`bash calc/descriptive/avg.sh sav-01 cph --start 2026-03-09 --end 2026-03-16`) — a 12.5% drop — then recovered to 70.59 in April (`bash calc/descriptive/avg.sh sav-01 cph --start 2026-04-01 --end 2026-04-30`). Worst day 2026-03-16 | 57.18.

## What the data says about why

### Hypothesis A — Primary-sort MHE outage drags throughput (confirmed)

- **Mechanism:** the primary sorter's drive failed, forcing slower manual sortation until the drive unit was replaced.
- **Supporting evidence:** `bash calc/diagnostic/change_drivers.sh sav-01 --baseline 2026-02-01:2026-02-28 --comparison 2026-03-09:2026-03-16 --top 3` ranks `equipment|mhe_down_m` +1039% (11.50 → 131.00 min/day) as the dominant mover; `bash calc/diagnostic/cooccurrence.sh sav-01 2026-03-11 --window 10` returns the `incident` (2026-03-09 MHE drive failure) and the `equipment_install` (2026-03-11 drive replaced).
- **Pattern match:** patterns/equipment_downtime_throughput_drag.md (high — equipment downtime top driver, quality flat, V-shaped recovery).

### Hypotheses B/C — quality breakdown, cohort onboarding (RULED OUT)

- Quality (mispick/missort) and `headcount_new` are not among the top movers; this is an equipment drag, not a cohort dip or a rework spiral.

## Methodology (every invocation reproducible)

- `bash calc/descriptive/avg.sh sav-01 cph --start 2026-02-01 --end 2026-02-28` → 69.89
- `bash calc/descriptive/avg.sh sav-01 cph --start 2026-03-09 --end 2026-03-16` → 61.18
- `bash calc/descriptive/avg.sh sav-01 cph --start 2026-04-01 --end 2026-04-30` → 70.59
- `bash calc/descriptive/worst_day.sh sav-01 cph --start 2026-03-09 --end 2026-03-16` → 2026-03-16 | 57.18
- `bash calc/diagnostic/change_drivers.sh sav-01 --baseline 2026-02-01:2026-02-28 --comparison 2026-03-09:2026-03-16 --top 3`
- `bash calc/diagnostic/cooccurrence.sh sav-01 2026-03-11 --window 10`
- peer check: `bash calc/descriptive/avg.sh chr-05 cph --start 2026-03-09 --end 2026-03-16` → 71.62 (peer unaffected)

## Floor intake (2026-05-20)

- **Hypothesis A — CONFIRMED.** Primary sorter drive failed 2026-03-09; degraded manual sortation until the drive unit was replaced 2026-03-11. CPH recovered after the replacement.
- **Disposition:** resolved (reactive repair, self-recovered). No Kaizen opened — the systemic/preventive question (critical-spare staging, PM cadence) is carried by the ral-02 Kaizen and the `equipment_downtime_throughput_drag` pattern, which this case feeds as a historical instance.
