# Calc library

Deterministic bash calculations used by skills. Every calc:

- Sources `lib/_schema_v1.sh` for column positions (never hardcoded)
- Takes a facility ID as its first argument (with the exception of network-scope calcs)
- Accepts `--start YYYY-MM-DD` and `--end YYYY-MM-DD` for time-windowed analysis (most calcs)
- Outputs in a fixed, parseable format
- Has a golden test in `tests/` that locks output against drift

Skills cite every calc invocation in their output. There is no improvised arithmetic anywhere in this architecture — if a calc is missing for a question, that gap is surfaced as friction (run `maintain/procedures/add_calc.md`) rather than papered over with inline computation.

## Descriptive calcs (`descriptive/`)

Single-variable aggregations. Answer "what is the value of metric M at facility F over window T."

| Calc | Question | Example |
|------|----------|---------|
| `avg.sh` | Average any metric (any family) over a window | `avg.sh chr-03 damage --family exceptions --start 2026-04-12 --end 2026-04-24` |
| `avg_cph.sh` | Average CPH over a window (operational shorthand for `avg.sh F cph`) | `avg_cph.sh dal-02 --start 2026-02-01 --end 2026-03-01` |
| `total_units.sh` | Total units shipped over a window | `total_units.sh dal-02 --start 2026-02-01 --end 2026-02-28` |
| `days_below_target.sh` | Count of days a metric was below target (or above with `--max`) | `days_below_target.sh chr-03 damage --max 20 --family exceptions --start 2026-04-12 --end 2026-04-24` |
| `worst_day.sh` | The single worst day for a metric in a window (direction auto-detected) | `worst_day.sh chr-03 damage --family exceptions --start 2026-04-12 --end 2026-04-24` |
| `month_summary.sh` | Multi-metric monthly summary (operational only) | `month_summary.sh dal-02 --month 2026-02` |

**`--family` flag (avg, days_below_target, worst_day):** defaults to `operational`. Pass `--family exceptions` / `inputs` / `equipment` to scan any metric in that family — the metric name is resolved to its column via `col_for()` in `lib/_schema_v1.sh`. `worst_day` auto-selects direction: lower-is-worse for operational cph/units/hours_run, higher-is-worse for error_rate and all exceptions/equipment metrics; override with `--direction min|max`. `avg.sh` is the family-aware generalization of `avg_cph.sh` (which is kept as the operational shorthand); `total_units.sh` and `month_summary.sh` remain operational-specific.

## Diagnostic calcs (`diagnostic/`)

Multi-variable analysis. Answer "why might metric M have the value it has."

| Calc | Question | Example |
|------|----------|---------|
| `cooccurrence.sh` | What events occurred near this date? | `cooccurrence.sh dal-02 2026-03-08 --window 14` |
| `segment_by.sh` | Break metric M (any family) down by dimension D | `segment_by.sh dal-02 exceptions damage --by dow --start 2026-04-12 --end 2026-04-24` |
| `change_drivers.sh` | Which metrics (all families) changed most between comparison and baseline periods? | `change_drivers.sh dal-02 --baseline 2026-02-01:2026-02-28 --comparison 2026-03-08:2026-03-22 --top 10` |
| `correlate.sh` | Pearson correlation between two metrics (any families, paired by date) | `correlate.sh dal-02 cph headcount_new --start 2026-01-01 --end 2026-03-31` |
| `outlier_days.sh` *(to be built)* | Days deviating most from facility norm | `outlier_days.sh dal-02 cph --top 5 --window 90d` |
| `compare_to_baseline.sh` *(to be built)* | Period-over-period delta on every variable | `compare_to_baseline.sh dal-02 --bad 2026-03 --baseline 2026-02` |

## Comparative calcs (`comparative/`)

Cross-facility analysis.

| Calc | Question | Example |
|------|----------|---------|
| `peer_benchmark.sh` | How does facility F compare to its peers? | `peer_benchmark.sh dal-02 cph --start 2026-03-01 --end 2026-03-31` |
| `rank_facilities.sh` *(to be built)* | Rank all facilities by metric M | `rank_facilities.sh cph --start 2026-03-01 --end 2026-03-31` |
| `divergence_analysis.sh` *(to be built)* | Where did facility F diverge from peers? | `divergence_analysis.sh dal-02 --period 2026-03 --compare-to hou-01` |

## Outcome calcs (`outcome/`)

Multi-period analysis specifically for verifying whether an intervention worked.

| Calc | Question | Example |
|------|----------|---------|
| `follow_up_check.sh` | Did metric M hit target T at facility F by date D? (`--family` to track the metric that actually moved, e.g. exceptions/damage, not a proxy) | `follow_up_check.sh chr-03 damage --max 20 --by 2026-06-19 --family exceptions` |
| `countermeasure_effectiveness.sh` *(to be built)* | Did metric M change between pre and post intervention? | `countermeasure_effectiveness.sh dal-02 cph --pre 2026-03-08:2026-03-21 --post 2026-03-22:2026-04-04` |
| `intervention_attribution.sh` *(to be built)* | Is the change attributable to the intervention or to other variables that also changed? | `intervention_attribution.sh dal-02 cph --intervention-date 2026-03-22 --check-variables headcount_new,inbound_units` |

## Tests

`tests/run.sh` runs every golden test and exits non-zero if any fail. Run before any schema or calc change, and on a periodic cadence (weekly minimum). The golden tests are the architecture's defense against silent drift — a schema change that breaks calcs without changing them visibly is caught here.

## Conventions

- Calc output is parseable. Skills that compose calc output never need to do string surgery beyond reading whitespace-separated columns.
- `NA` is returned for "no rows matched" cases. Skills surface NA explicitly rather than substituting a zero or skipping.
- Exit codes carry meaning: 0 = success, 1 = predicate failed (e.g. `follow_up_check.sh` returning FAIL), 2 = bad arguments, 3 = data file missing.
- Calcs do not write to data files. They are read-only against `data/` and write only to stdout.
- The `lib/_schema_v1.sh` header is the single source of truth for column positions. Schema bumps are handled via `maintain/procedures/bump_schema.md`.
