# Procedure: Bump the schema version

## When to use

The metric schema must change to fit reality — add, rename, or remove a column or a whole metric family. This is the **highest-risk** maintain operation: a partial bump silently corrupts every downstream number. It is therefore a **single coordinated change, in one commit**, across the manifest, the column map, the conversion source, the calcs, and every golden test.

Do NOT bump the schema casually. If you only need a new *calc* against existing columns, that's `add_calc.md`. Only bump when the underlying data shape itself must change.

## Prerequisites

- **A clear schema delta** written down: for each affected family, exactly which columns are added / renamed / removed, and their order. Column *order* matters — calcs reference 1-based positions via `col_for()`.
- **The current suite is green first.** Run `bash calc/tests/run.sh` and `bash verify.sh` before you start, so any post-bump failure is attributable to the bump.
- **A version name:** the next `v{N}` (current is v1, in `calc/lib/_schema_v1.sh`).

## Steps

Do all of these before running anything that consumes the new shape — the order minimizes the window where producers and consumers disagree.

1. **Author the new column map.** Create `calc/lib/_schema_v{N}.sh` from the current one: update the `COL_*` positions, the `col_for()` resolver, `worse_direction()` if directions change, and bump `SCHEMA_VERSION`. (A new file rather than an in-place edit keeps the old map available for reference during the change.)
2. **Re-point every calc.** Update the `source ".../_schema_v{N}.sh"` line in every calc under `calc/`. They all source the schema lib by name; miss one and it reads the old positions.
3. **Update the conversion source to emit the new shape.** Production: the conversion adapter. Demo: `conversion/scripts/simulate_facility_data.py` and the family headers. Both still write **through `conversion/validation/common.py`** — update the validators' expected headers/ranges for the new columns.
4. **Update the manifest.** `data/metrics/MANIFEST.md` — the schema tables for each family, the `Schema version` line, and the **version history** section (what changed in v{N} and when).
5. **Regenerate / re-map the data** so every `data/metrics/**/*.csv` is in the new shape, and re-validate.
6. **Update every golden test.** Fixtures in `calc/tests/golden/` and expected outputs in `calc/tests/expected/` must reflect the new shape. Re-derive expected values independently — do not just paste new calc output.
7. **Run the full suite.** `bash calc/tests/run.sh` and `bash verify.sh` must both pass. If a calc's output changed in a way the golden didn't anticipate, investigate before relocking.

## Verification

The procedure completed only if all of the following hold:

- `calc/lib/_schema_v{N}.sh` exists with the new positions and `SCHEMA_VERSION=v{N}`, and **every** calc sources it (grep for any lingering `_schema_v{N-1}.sh`).
- `data/metrics/MANIFEST.md` documents v{N} and its version-history entry.
- All `data/metrics/**/*.csv` are in the new shape and pass validation.
- Every golden test passes (`calc/tests/run.sh`) and `verify.sh` is green.
- The conversion source emits the new shape.

A bump where producers and consumers disagree on even one column is a silent-corruption bug; if the suite isn't fully green, the bump is not done.

## Common mistakes

- **Partial bump.** The adapter emits the new shape but a calc still reads an old position (or vice versa). Every number that calc produces is then wrong, with no error. The grep for the old schema filename is the guard.
- **Hand-editing golden expected files to match new output without re-deriving.** That locks in whatever the (possibly wrong) calc now emits.
- **Using the new shape elsewhere before the bump is complete.** Finish the coordinated change first; don't start authoring a new calc against v{N} mid-bump.
- **Forgetting the validators.** New columns with no range/header check pass through unguarded — extend `common.py` so the boundary still enforces the contract.
- **Skipping the version-history note.** Future readers (and the next bump) need to know what changed and why.
