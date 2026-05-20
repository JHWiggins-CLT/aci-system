---
investigation_id: 2026-04-22_ral-02_throughput_drop
facility: ral-02
signal_type: throughput_drop
signal_date: 2026-04-22
state: kaizen_open
drafted_on: 2026-05-20
floor_visit_on: 2026-05-20
closed_on: 2026-05-20
investigator: portfolio-demo
playbook: investigate/playbooks/throughput_drop.md
disposition: kaizen
kaizen_id: k-2026-05-ral-02-conveyor-pm
related_pattern: patterns/equipment_downtime_throughput_drag.md
---

# Floor Brief: ral-02 throughput drop, 2026-04-20 to 2026-04-27

**Investigation ID:** 2026-04-22_ral-02_throughput_drop
**Investigator:** portfolio-demo
**Date drafted:** 2026-05-20
**Signal:** CPH ~15% below baseline for one week following a conveyor belt failure.

> PATTERN PROVENANCE: this is one of the three investigations the
> `equipment_downtime_throughput_drag` pattern was authored from. The pattern
> postdates this brief; the `related_pattern` link was added when the pattern
> landed.

## What we see

ral-02 CPH fell from a March baseline of 90.98 (`bash calc/descriptive/avg.sh ral-02 cph --start 2026-03-01 --end 2026-03-31`) to 77.43 over 2026-04-20..27 (`bash calc/descriptive/avg.sh ral-02 cph --start 2026-04-20 --end 2026-04-27`) — a 14.9% drop — then recovered to 91.79 in May (`bash calc/descriptive/avg.sh ral-02 cph --start 2026-05-01 --end 2026-05-18`). The worst day was 2026-04-27 | 72.64 (`bash calc/descriptive/worst_day.sh ral-02 cph --start 2026-04-20 --end 2026-04-27`). The drop is bounded, V-shaped, and fully recovered — the shape of a discrete incident, not a drift.

## What the data says about why

### Hypothesis A — Conveyor outage drags throughput (strongest)

- **Mechanism:** a conveyor belt failure forces manual workarounds / partial line shutdown, so the same labor moves fewer units per hour until the line is restored.
- **Supporting evidence:** `bash calc/diagnostic/change_drivers.sh ral-02 --baseline 2026-03-01:2026-03-31 --comparison 2026-04-20:2026-04-27 --top 3` ranks `equipment|conveyor_down_m` +1250% (12.85 → 173.43 min/day) and `equipment|wms_incidents` +1261% as the dominant movers; `bash calc/descriptive/worst_day.sh ral-02 conveyor_down_m --family equipment --start 2026-04-20 --end 2026-04-27` peaks at 2026-04-24 | 178. `bash calc/diagnostic/cooccurrence.sh ral-02 2026-04-22 --window 10` returns the `incident` (2026-04-20 belt failure) and the `equipment_install` (2026-04-22 belt replacement) directly.
- **Counter-evidence:** none material — the downtime spike, the incident event, and the CPH window line up exactly.
- **Pattern match:** patterns/equipment_downtime_throughput_drag.md (high — equipment downtime is the top driver, quality flat, V-shaped recovery).

### Hypothesis B — Quality breakdown dragging throughput via rework (RULED OUT)

- RULED OUT: mispick/missort are not among the top movers in `change_drivers` (the top three are all equipment-family). Quality stayed roughly flat through the window, which is the signature that separates an equipment drag from a cohort-overload dip.

### Hypothesis C — Cohort onboarding (RULED OUT)

- RULED OUT: `headcount_new` is not a top driver, and `bash calc/diagnostic/correlate.sh ral-02 cph headcount_new` → −0.19 (negligible). No cohort signature.

## Questions for the floor

- Confirm the line-3 belt failure and the manual workaround used during the outage — how much of the week ran degraded vs fully down?
- Was the belt failure sudden, or had line 3 shown wear/warning signs beforehand? (Determines whether preventive inspection would have caught it.)
- Is a critical spare belt for line 3 stocked on-site, or was the 2-day gap to replacement waiting on a part?

## Methodology (every invocation reproducible)

- `bash calc/descriptive/avg.sh ral-02 cph --start 2026-03-01 --end 2026-03-31` → 90.98
- `bash calc/descriptive/avg.sh ral-02 cph --start 2026-04-20 --end 2026-04-27` → 77.43
- `bash calc/descriptive/avg.sh ral-02 cph --start 2026-05-01 --end 2026-05-18` → 91.79
- `bash calc/descriptive/worst_day.sh ral-02 cph --start 2026-04-20 --end 2026-04-27` → 2026-04-27 | 72.64
- `bash calc/diagnostic/change_drivers.sh ral-02 --baseline 2026-03-01:2026-03-31 --comparison 2026-04-20:2026-04-27 --top 3`
- `bash calc/diagnostic/cooccurrence.sh ral-02 2026-04-22 --window 10`
- `bash calc/diagnostic/correlate.sh ral-02 cph headcount_new` → −0.19 (rules out cohort)
- peer check: `bash calc/descriptive/avg.sh atl-03 cph --start 2026-04-20 --end 2026-04-27` → 93.19 (peer unaffected in this window)

## Floor intake (2026-05-20)

- **Hypothesis A — CONFIRMED.** Line 3 drive belt failed 2026-04-20; the zone ran a manual cross-feed workaround at reduced rate until the replacement belt was installed and commissioned 2026-04-22..23. CPH recovered immediately after commissioning.
- **Root cause / mechanism:** unplanned conveyor outage with no on-site critical spare → ~2-day repair gap during which throughput ran degraded.
- **Disposition:** Kaizen — `k-2026-05-ral-02-conveyor-pm`. The reactive repair worked (recovery confirmed); the Kaizen addresses the *preventable* part: critical-spare staging + a preventive inspection cadence so the next wear-out is caught before it becomes an unplanned outage.
- **Pattern note:** this is the third equipment-downtime throughput drag observed (with sav-01 Mar and atl-03 Apr). Together they cross the 3-instance threshold → `equipment_downtime_throughput_drag` pattern authored.
