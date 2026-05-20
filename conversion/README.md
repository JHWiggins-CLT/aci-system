# Conversion — operator instructions

This directory is the boundary between raw source data and the canonical CSVs the calc library trusts. Anything inside `data/metrics/` and `data/events/` must have been produced by a script in `scripts/` that passed the shared validators in `validation/`.

For this portfolio deployment the "source" is a deterministic simulator (see [MANIFEST.md](MANIFEST.md) for the rationale). The operator-facing flow is identical to a production deployment with real Excel sources: run the script, check the logs, trust the output.

## Re-running all conversions

```bash
python conversion/scripts/simulate_facility_data.py
```

The script is idempotent and atomic. Same seed → same 41 CSVs. Failed validation aborts without overwriting the previous canonical files.

## Alternative seeds (different dataset, same shape)

```bash
python conversion/scripts/simulate_facility_data.py --seed 42
```

Useful for stress-testing the calc library or for producing demonstrably-different datasets without touching the architecture.

## Where outputs land

| Path | Files | Notes |
|------|-------|-------|
| `data/metrics/operational/{id}.csv` | 8 | One per facility |
| `data/metrics/inputs/{id}.csv` | 8 | One per facility |
| `data/metrics/exceptions/{id}.csv` | 8 | One per facility |
| `data/metrics/equipment/{id}.csv` | 8 | One per facility |
| `data/events/{id}.csv` | 8 | One per facility |
| `data/events/network.csv` | 1 | Network-wide events |

## Where logs land

`conversion/logs/{YYYY-MM-DD}_{script}_{target}.log` — one log per target per run. PASS logs are kept as evidence; FAIL logs are kept as audit. Old logs are not auto-rotated; sweep manually if needed.

## What to do when validation fails

1. Read the FAIL log. It lists the exact failures (e.g. `row 47 has null in column 3`).
2. Fix the source (the simulator scenario or facility config) or the script. **Never** loosen the validator to make a stubborn source pass — see `MANIFEST.md` for why.
3. Re-run the script. The previous canonical CSV stays in place until validation passes again.

## Cadence

- **This deployment:** on-demand. The dataset is fixed by the seed; re-run only when scenarios or facility configuration changes.
- **Production analog:** weekly drop, Mondays after the prior week closes.

## Adding a new source (production analog)

1. Add the source to `notes/data_inventory.md` (not present in this portfolio piece).
2. Write `scripts/extract_{source}.{py,sh}`. Import the validators from `validation.common`.
3. Use `write_csv_atomic()` so partial files never land.
4. Add the source/target mapping row to `MANIFEST.md`.
5. Test the bad-row case (deliberately break a row, confirm the script aborts).
6. Commit script + manifest entry in the same change.

## Adding a new scenario or facility (portfolio analog)

1. Edit `scripts/simulate_facility_data.py`:
   - Append to `FACILITIES` (and update `data/facilities/INDEX.md` + profile)
   - Append to `SCENARIOS` and/or `EVENT_SEEDS` to embed a new story
2. Re-run `python conversion/scripts/simulate_facility_data.py`.
3. Confirm the calc library still passes its golden tests: `bash calc/tests/run.sh`.
4. If a new facility was added, run `peer_benchmark.sh` to confirm pairings still make sense.

## Sanity checks before trusting a new run

After every regenerate:
- `bash calc/tests/run.sh` — must pass
- `bash calc/descriptive/avg_cph.sh dal-02 --start 2026-02-01 --end 2026-02-28` — should land within ~5% of the facility's CPH target
- `bash calc/diagnostic/cooccurrence.sh dal-02 2026-03-15 --window 14` — should surface the dal-02 cohort training event(s)

If any of these change unexpectedly after a non-substantive edit, the seed handling or the validator may have regressed.
