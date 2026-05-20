---
kaizen_id: k-2026-05-ral-02-conveyor-pm
title: ral-02 line-3 conveyor critical-spare + preventive inspection
opened: 2026-05-20
state: open
owner: Dana Okafor (maintenance lead, ral-02)
source_investigation: 2026-04-22_ral-02_throughput_drop
related_pattern: patterns/equipment_downtime_throughput_drag.md
facility: ral-02
---

# Kaizen: ral-02 line-3 conveyor critical-spare + preventive inspection

**Kaizen ID:** k-2026-05-ral-02-conveyor-pm
**Opened:** 2026-05-20
**Owner:** Dana Okafor
**Source:** 2026-04-22_ral-02_throughput_drop
**Related pattern:** patterns/equipment_downtime_throughput_drag.md

---

## Observation

A line-3 conveyor belt failure on 2026-04-20 dragged ral-02 CPH from a March baseline of 90.98 to 77.43 over 2026-04-20..27 (−14.9%; `bash calc/descriptive/avg.sh ral-02 cph --start 2026-04-20 --end 2026-04-27`), recovering to 91.79 in May once the belt was replaced. `bash calc/diagnostic/change_drivers.sh ral-02 --baseline 2026-03-01:2026-03-31 --comparison 2026-04-20:2026-04-27 --top 3` shows `conveyor_down_m` +1250% as the dominant driver; `bash calc/descriptive/worst_day.sh ral-02 conveyor_down_m --family equipment --start 2026-04-20 --end 2026-04-27` peaks at 178 min on 2026-04-24. The reactive repair worked; the cost was the ~2-day gap to replacement with no on-site critical spare.

## Change

Stage a critical spare drive belt for conveyor line 3 on-site (eliminating the parts-wait portion of the repair gap), and add a preventive inspection of line-3 belt/drive condition to the weekly maintenance cadence so wear is caught and scheduled before it becomes an unplanned outage. The intent is not zero failures but to cap unplanned downtime: a caught-early scheduled replacement runs during off-peak hours instead of dragging a full week of throughput.

## Tracking

- **Baseline:** ral-02 conveyor_down_m averages 12.85 min/day in normal operation (`bash calc/descriptive/avg.sh ral-02 conveyor_down_m --family equipment --start 2026-03-01 --end 2026-03-31`); the outage spiked it to a 178-min peak.

- **Target:** no unplanned line-3 outage. Operationalized as: conveyor_down_m stays at or below a 60-min/day ceiling (≈ 4.5× normal — well below the 170+ outage range) over rolling 30-day windows.

- **Follow-up checks:**
  - **2026-05-18** (baseline-health check, fired at open): `bash calc/outcome/follow_up_check.sh ral-02 conveyor_down_m --max 60 --by 2026-05-18 --family equipment --window-days 18` → ACTUAL 11.73, RESULT PASS. Confirms the line is healthy post-repair.
  - **2026-06-20** (+30 days): `bash calc/outcome/follow_up_check.sh ral-02 conveyor_down_m --max 60 --by 2026-06-20 --family equipment --window-days 30` — verifies no recurrence through June. Pending.
  - **2026-07-20** (+60 days): same calc shape, `--by 2026-07-20`. Pending.

## Outcome

*Filled in at Kaizen close. Pending — the preventive cadence has not yet had a wear-cycle to act on.*

- Did conveyor_down_m stay under the ceiling?
- Did a preventive inspection catch a wear-out before failure (the real win), or did the period simply have no failures?
- Lessons that feed `patterns/equipment_downtime_throughput_drag.md` — specifically, whether critical-spare staging + inspection actually shortened or prevented the next outage.

---

*This Kaizen is the preventive countermeasure for the `equipment_downtime_throughput_drag` pattern. The pattern's "countermeasures that worked" section cites the reactive repair (component replacement → fast recovery, confirmed across ral-02 / sav-01 / atl-03); whether the preventive layer (this Kaizen) reduces recurrence is the open outcome it will learn from.*
