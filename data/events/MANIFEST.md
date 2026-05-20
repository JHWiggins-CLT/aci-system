# Events Manifest

> **Simulated data.** Events backfilled by `conversion/scripts/simulate_facility_data.py` to seed plausible diagnostic context. See [conversion/MANIFEST.md](../../conversion/MANIFEST.md).

## Per-facility event log — `events/{id}.csv`

One row per discrete event affecting that facility.

| Col | Field         | Type       | Notes                                      |
|-----|---------------|------------|--------------------------------------------|
| 1   | date          | YYYY-MM-DD | When the event occurred                    |
| 2   | facility_id   | string     | Lowercase canonical ID                     |
| 3   | event_type    | string     | One of the taxonomy below                  |
| 4   | description   | string     | Short free-text (≤200 chars, quoted in CSV)|
| 5   | source        | string     | Who/what logged it                         |

Header row required: `date,facility_id,event_type,description,source`

## Network event log — `events/network.csv`

Same schema, no `facility_id` column. Used for things that hit all facilities (network-wide WMS releases, corporate policy changes, regulatory changes).

| Col | Field         | Type       | Notes                                      |
|-----|---------------|------------|--------------------------------------------|
| 1   | date          | YYYY-MM-DD |                                            |
| 2   | event_type    | string     | One of the taxonomy below                  |
| 3   | description   | string     | Short free-text (≤200 chars)               |
| 4   | source        | string     |                                            |

Header row required: `date,event_type,description,source`

## Event taxonomy (`event_type` values)

| Value | Meaning |
|-------|---------|
| `system_change`     | WMS, scanner, label printer, asset software change |
| `deployment`        | Major software/hardware install |
| `training`          | Formal training events (cohort start, certification) |
| `incident`          | Safety, security, or operational incident |
| `leadership_change` | Manager/supervisor change at the facility |
| `sop_change`        | Written process change |
| `weather`           | Significant weather event affecting operations |
| `holiday`           | Observed holiday (impacts staffing/volume) |
| `audit`             | Internal or external audit underway |
| `equipment_install` | New equipment installed/decommissioned |
| `volume_shock`      | Unusual inbound or outbound volume |

New values may be added via `.skills/maintain/procedures/add_event_type.md`.

## Entry conventions

- One event per row. Two things on the same day = two rows.
- `description` is neutral and factual. Interpretation belongs in investigations, not in event log entries.
- `source` matters for trust. Examples: `simulator-seed` (initial backfill), `floor-intake-{date}` (logged from close-loop), `ci-mgr` (logged ad hoc), `system` (auto-detected).
- Backfilled events: add `(backfilled)` suffix to description.

## How the events layer is read

The diagnostic calc `cooccurrence.sh {facility} {date} --window N` reads `events/{id}.csv` plus `events/network.csv` and returns every event within ±N days. This is the primary mechanism by which investigations get context for "what changed in the world."
