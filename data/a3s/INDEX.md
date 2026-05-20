# A3 Index

Catalog of all A3s — open and closed. The close-loop skill appends a row here when it opens an A3 (`procedures/open_a3.md`). The "show me all open A3s" query reads this file rather than globbing `open/`.

Open A3s live in `data/a3s/open/{a3_id}.md`; closed A3s move to `data/a3s/closed/{YYYY-Qn}/{a3_id}.md` at close.

## Schema

| Column | Meaning |
|--------|---------|
| a3_id | A3 identifier (`a3-{YYYY-MM}-{facility_or_network}-{slug}`) |
| opened | Date opened |
| state | `open` / `closed` |
| scope | network applicability (single facility / regional / network) |
| owner | Accountable owner |
| source | Source investigation id |
| next_follow_up | Next pending follow-up date (from `follow_ups/INDEX.md`) |
| file | Path to the A3 |

## A3s

| a3_id | opened | state | scope | owner | source | next_follow_up | file |
|-------|--------|-------|-------|-------|--------|----------------|------|
| a3-2026-05-network-trainer-coverage | 2026-05-20 | open | network (evidence single-facility, gated) | Priya Nair | 2026-03-15_dal-02_throughput_drop | 2026-06-15 | open/a3-2026-05-network-trainer-coverage.md |
