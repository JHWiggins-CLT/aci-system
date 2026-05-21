# Kaizen Index

Catalog of all Kaizens — open and closed. The close-loop skill appends a row here when it opens a Kaizen (`procedures/open_kaizen.md`). The `review` skill and "show me open Kaizens" queries read this file rather than globbing `open/`.

Open Kaizens live in `data/kaizens/open/{kaizen_id}.md`; closed Kaizens move to `data/kaizens/closed/{YYYY-Qn}/{kaizen_id}.md` at close.

## Schema

| Column | Meaning |
|--------|---------|
| kaizen_id | Kaizen identifier (`k-{YYYY-MM}-{facility}-{slug}`) |
| opened | Date opened |
| state | `open` / `closed` |
| facility | Facility id |
| source | Source investigation id |
| next_follow_up | Next pending follow-up date (from `follow_ups/INDEX.md`) |
| file | Path to the Kaizen |

## Kaizens

| kaizen_id | opened | state | facility | source | next_follow_up | file |
|-----------|--------|-------|----------|--------|----------------|------|
| k-2026-05-dal-02-trainer-ratio | 2026-05-18 | open | dal-02 | 2026-03-15_dal-02_throughput_drop | 2026-06-17 | open/k-2026-05-dal-02-trainer-ratio.md |
| k-2026-05-chr-03-bin-relocation | 2026-05-19 | open | chr-03 | 2026-04-12_chr-03_damage_spike | 2026-06-19 | open/k-2026-05-chr-03-bin-relocation.md |
| k-2026-05-ral-02-conveyor-pm | 2026-05-20 | open | ral-02 | 2026-04-22_ral-02_throughput_drop | 2026-06-20 | open/k-2026-05-ral-02-conveyor-pm.md |
