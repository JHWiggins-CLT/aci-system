# Conversion Manifest

## Purpose

Documents the contract between raw source data and the canonical CSVs in `data/metrics/` and `data/events/` that the architecture trusts. The architecture trusts a CSV under those paths **only** if produced by a script listed here that passed validation on the run that produced the file.

## Portfolio note — simulated data

This is a portfolio demonstration. There is no real source data, no shared Excel files, and no production data pipeline. Instead, a deterministic simulator (`scripts/simulate_facility_data.py`) plays the role of both the "raw source" and the conversion script. It generates plausible operational, inputs, exceptions, equipment, and events data for 8 fictional facilities, then validates the output against the schema before writing.

The architectural discipline of the conversion boundary is preserved exactly: every CSV under `data/metrics/` and `data/events/` is produced by a recorded script that invoked the shared validators and wrote an audit log to `conversion/logs/`. The only thing different from a production deployment is the source: a seeded RNG instead of an Excel file.

## Source-to-target mappings

| Source                                 | Type        | Cadence | Script                                       | Target                                       |
|----------------------------------------|-------------|---------|----------------------------------------------|----------------------------------------------|
| `scripts/simulate_facility_data.py` (seed=20260518) | python | on demand | `scripts/simulate_facility_data.py`         | `data/metrics/operational/{id}.csv` (8 files)|
| (same)                                 | python      | on demand | `scripts/simulate_facility_data.py`         | `data/metrics/inputs/{id}.csv` (8 files)     |
| (same)                                 | python      | on demand | `scripts/simulate_facility_data.py`         | `data/metrics/exceptions/{id}.csv` (8 files) |
| (same)                                 | python      | on demand | `scripts/simulate_facility_data.py`         | `data/metrics/equipment/{id}.csv` (8 files)  |
| (same)                                 | python      | on demand | `scripts/simulate_facility_data.py`         | `data/events/{id}.csv` (8 files) + `network.csv` |

Total: 41 files per run, all produced atomically (write-temp-then-rename so failed validation never leaves a partial file).

## Validation guarantees

Every conversion run (including the simulator) invokes the shared library in `conversion/validation/common.py` before writing each canonical CSV. If any check fails, the run aborts with a non-zero exit code and the script writes a failure log to `conversion/logs/`. It does **not** write a partial or invalid CSV.

Required validations per metric family CSV:
- **Header matches schema** — column count, order, and names match `data/metrics/MANIFEST.md` (v1)
- **Row count threshold** — at least 90 data rows (the operating-day floor for ~120 calendar days, Mon-Sat)
- **Date format** — every value in the date column matches `YYYY-MM-DD`
- **Dates sorted ascending** — rows are in chronological order
- **Facility ID matches filename** — every row's `facility_id` equals the expected facility (no cross-facility leakage)
- **No nulls** — no blank values anywhere in the row
- **Value range sanity** — numeric metrics within plausible bounds (e.g. CPH in `[0, 500]`, percentages in `[0, 1]`, downtime minutes in `[0, 1440]`)

Required validations per events CSV:
- Header matches schema (per-facility or network variant)
- Date format
- Facility ID matches filename (per-facility only)
- Event type is in the taxonomy declared in `data/events/MANIFEST.md`

The validators are intentionally strict. **Weakening a validator to make a stubborn source pass is the most dangerous slow-corruption failure mode** for this architecture. If a source can't pass, fix the source or the script; never loosen the validator.

## Schema version

Current: **v1** (matches `data/metrics/MANIFEST.md` v1 and `calc/lib/_schema_v1.sh`).

When the metrics manifest bumps to v2, the simulator and any other conversion scripts must be updated in the same commit, and the validator's `SCHEMAS` dict must be updated to match. The `bump_schema.md` procedure (in `.skills/maintain/procedures/`, authored in phase 6) enforces this.

## Cadence

In a production deployment, conversions would run weekly after operations closes the prior week's numbers. For this portfolio piece, the simulator is run on demand: any time the seed or scenario set changes, re-run and the canonical CSVs are regenerated deterministically.

## Audit trail

Every run writes one log file per target to `conversion/logs/` in the form `{date}_{script}_{target}.log`. The log records: which checks ran, row count, PASS/FAIL status, and (on failure) the specific failures. Logs are append-history; old logs accumulate as evidence of the conversion pipeline's behavior over time.

## Known fragile sources

None — the simulator is deterministic and the seed is the only input. A real deployment would list the source files most prone to schema drift here (humans editing Excel files, vendor exports changing format, etc.).

## How to re-run

```bash
python conversion/scripts/simulate_facility_data.py            # default seed
python conversion/scripts/simulate_facility_data.py --seed 42  # alternate dataset
```

Same seed always produces the same 41 files. To regenerate after editing scenarios or facility configuration, re-run; the atomic write means an interrupted run leaves the previous canonical CSVs intact.

## How to add a new source

In a production deployment:
1. Add the source file to the inventory in `notes/data_inventory.md`
2. Write a new script in `conversion/scripts/extract_{source}.py`
3. Have it import the shared validators from `conversion/validation/common.py`
4. Write to `data/metrics/{family}/{id}.csv` only after validation passes
5. Add a row to the source-to-target mapping table above
6. Commit script + manifest entry in the same change

For this portfolio piece, the equivalent flow is: add facilities or scenarios to `simulate_facility_data.py`, re-run, the new canonical CSVs appear automatically.
