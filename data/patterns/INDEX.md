# Patterns Index

Catalog of recurring causal patterns. A pattern is the generic causal shape shared
by 3+ closed investigations, with the countermeasures that have and haven't worked.
The investigate skill checks this index early in every investigation (see
`investigate/playbooks/*` step "pattern check") to surface a candidate cause and its
known countermeasures before drafting hypotheses from scratch.

Patterns are added via `maintain/procedures/add_pattern.md` (3+-same-mechanism
threshold) and revised via `maintain/procedures/update_pattern.md`.

## Schema

| Column | Meaning |
|--------|---------|
| pattern | Pattern name |
| signal | One-line trigger shape |
| distinguishes_by | The tell that separates it from look-alike signals |
| instances | Count of historical instances |
| file | Path to the pattern file |

## Patterns

| pattern | signal | distinguishes_by | instances | file |
|---------|--------|------------------|-----------|------|
| Equipment-downtime throughput drag | CPH 8-15% below baseline ~1 week, V-shaped recovery | equipment-family metric is the top change_drivers mover; quality + headcount_new flat | 3 | equipment_downtime_throughput_drag.md |
