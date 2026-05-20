# Metrics Manifest — Schema v1

> **Simulated data.** All CSVs in `data/metrics/` are produced by `conversion/scripts/simulate_facility_data.py`. This is a portfolio demonstration of the architecture's conversion boundary discipline, not a production data pipeline. See [conversion/MANIFEST.md](../../conversion/MANIFEST.md).

## This drop
- **Period:** 2026-01-19 through 2026-05-18 (120 days)
- **Facilities included:** 8 of 8
- **Generated:** 2026-05-18 (deterministic; same seed → same data)
- **Schema version:** v1 (all four families)
- **Validation:** every CSV passed `conversion/validation/common.py` checks at generation time. See `conversion/logs/` for per-run audit trail.

## Operational metrics — `operational/{id}.csv`

Daily outputs of the facility.

| Col | Field        | Type       | Notes                                       |
|-----|--------------|------------|---------------------------------------------|
| 1   | date         | YYYY-MM-DD | Daily granularity, sorted ascending         |
| 2   | facility_id  | string     | Lowercase canonical ID, matches filename    |
| 3   | units        | int        | Total units shipped that day                |
| 4   | cph          | float      | Cases per hour, facility-wide, 2 decimals   |
| 5   | error_rate   | float      | Errors per 1000 units, 2 decimals           |
| 6   | hours_run    | float      | Total operating hours that day, 1 decimal   |

Header row required: `date,facility_id,units,cph,error_rate,hours_run`

## Input metrics — `inputs/{id}.csv`

What the facility was given to work with that day.

| Col | Field             | Type       | Notes                            |
|-----|-------------------|------------|----------------------------------|
| 1   | date              | YYYY-MM-DD |                                  |
| 2   | facility_id       | string     |                                  |
| 3   | headcount_total   | int        | FTE on shift (excludes seasonal) |
| 4   | headcount_new     | int        | New hires (<30 days)             |
| 5   | headcount_shift1  | int        | Day shift                        |
| 6   | headcount_shift2  | int        | Evening shift                    |
| 7   | headcount_shift3  | int        | Night shift (0 for 2-shift sites)|
| 8   | inbound_units     | int        | Units received that day          |
| 9   | order_mix_complex | float      | % orders with >3 SKUs (0.0-1.0)  |

Header row required: `date,facility_id,headcount_total,headcount_new,headcount_shift1,headcount_shift2,headcount_shift3,inbound_units,order_mix_complex`

## Exception metrics — `exceptions/{id}.csv`

Categorized failures per day.

| Col | Field        | Type       | Notes                                  |
|-----|--------------|------------|----------------------------------------|
| 1   | date         | YYYY-MM-DD |                                        |
| 2   | facility_id  | string     |                                        |
| 3   | damage       | int        | Damaged units                          |
| 4   | missort      | int        | Routed to wrong lane                   |
| 5   | mispick      | int        | Wrong item picked                      |
| 6   | lost         | int        | Inventory not found                    |
| 7   | late_pick    | int        | Pick completed after cutoff            |

Header row required: `date,facility_id,damage,missort,mispick,lost,late_pick`

## Equipment metrics — `equipment/{id}.csv`

Asset health and uptime.

| Col | Field           | Type       | Notes                             |
|-----|-----------------|------------|-----------------------------------|
| 1   | date            | YYYY-MM-DD |                                   |
| 2   | facility_id     | string     |                                   |
| 3   | conveyor_down_m | int        | Conveyor downtime, minutes        |
| 4   | mhe_down_m      | int        | Material-handling downtime, mins  |
| 5   | wms_incidents   | int        | WMS-related incidents             |
| 6   | scanner_faults  | int        | Handheld/fixed scanner faults     |

Header row required: `date,facility_id,conveyor_down_m,mhe_down_m,wms_incidents,scanner_faults`

## Schema cross-references

- Column positions: [calc/lib/_schema_v1.sh](../../calc/lib/_schema_v1.sh)
- Bump procedure: `.skills/maintain/procedures/bump_schema.md` (to be authored in phase 6)

## Schema version history

- **v1** (current, since 2026-01-01): initial 4-family schema as defined above.
