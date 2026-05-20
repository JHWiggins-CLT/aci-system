# Investigations Index

Flat directory of all investigations — open and closed. The investigate skill reads this on every new investigation to surface prior work at the same facility or on the same signal type. The close-loop skill appends to this when an investigation transitions to closed/A3/Kaizen.

Closed investigations move from `open/` to `YYYY-Qn/` (e.g. `2026-Q1/`) by close-loop. Open investigations stay in `open/` until disposition.

## Schema

| Column | Meaning |
|--------|---------|
| date | Signal date (when the investigation focuses) |
| facility | Facility id |
| signal | Short signal type (throughput_drop, error_spike, damage_spike, etc.) |
| state | one of the canonical states defined in `handoff.md` §4: `drafted` / `floor_pending` / `confirmed` / `ruled_out` / `inconclusive` / `kaizen_open` / `a3_open` / `superseded` / `resolved` / `escalated` |
| disposition | A3 id, Kaizen id, "no_action", or blank if pre-floor |
| file | Path to investigation brief |

## Investigations

| date       | facility | signal           | state         | disposition                          | file                                                       |
|------------|----------|------------------|---------------|--------------------------------------|------------------------------------------------------------|
| 2026-03-15 | dal-02   | throughput_drop  | kaizen_open   | k-2026-05-dal-02-trainer-ratio + a3-2026-05-network-trainer-coverage | 2026-Q1/2026-03-15_dal-02_throughput_drop.md |
| 2026-04-12 | chr-03   | damage_spike     | kaizen_open   | k-2026-05-chr-03-bin-relocation      | 2026-Q2/2026-04-12_chr-03_damage_spike.md                  |
| 2026-03-11 | sav-01   | throughput_drop  | resolved      | resolved (reactive repair)           | 2026-Q1/2026-03-11_sav-01_throughput_drop.md               |
| 2026-04-07 | atl-03   | throughput_drop  | resolved      | resolved (reactive repair)           | 2026-Q2/2026-04-07_atl-03_throughput_drop.md               |
| 2026-04-22 | ral-02   | throughput_drop  | kaizen_open   | k-2026-05-ral-02-conveyor-pm         | 2026-Q2/2026-04-22_ral-02_throughput_drop.md               |
