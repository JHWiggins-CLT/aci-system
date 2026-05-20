# Procedure: Add a facility

## When to use

A new site joins the network, or — during onboarding — you are registering each of the operator's real facilities for the first time. One run of this procedure = one facility fully wired into the system (directory, profile, aliases, peer pairing, data, events).

Do NOT use to edit an existing facility's attributes (just edit its profile + the INDEX row directly and note why). Use `deprecate_facility.md` (planned) to take a site out of scope.

## Prerequisites

- **A facility ID** in the project convention `{city3}-{NN}` (lowercase), e.g. `dal-02`, `chr-05`. It must be unique and stable — it's the key used in every filename and CSV.
- **Core attributes:** display name, state, city, type (Fulfillment / Distribution / Cold Storage / …), the aliases ops actually uses for it, and per-facility targets (at minimum a CPH target; exceptions ceilings if known).
- **A source for its metrics** — in production, the conversion adapter must be able to map this facility's data; in demo, the simulator must produce it.
- **A peer** (optional but recommended) — a same-type, similar-scale site for `peer_benchmark.sh` and network rule-outs.

## Steps

1. **Register it in `data/facilities/INDEX.md`:**
   - Add a row to the **Directory** table: `| {id} | {name} | {state} | {city} | {type} | profiles/{id}.md |`.
   - Add an **Aliases** row: `| {id} | "Alias A", "Alias B", … |`.
   - If it has a peer, add a **Peer pairings** row (and update the peer's, if pairings are bidirectional in your convention).
2. **Render the profile** from `.skills/maintain/templates/facility_profile.md` to `data/facilities/profiles/{id}.md`. Fill every templated field — name, location, type, targets, shift structure, and any site notes. Record the **targets here** (this is where thresholds from onboarding step 4 live).
3. **Wire the data source:**
   - *Production:* extend the conversion adapter so this facility's source rows map to `data/metrics/{operational,inputs,exceptions,equipment}/{id}.csv`, emitted **through `conversion/validation/common.py`**.
   - *Demo:* add a `FacilityConfig(...)` entry to `conversion/scripts/simulate_facility_data.py` and re-run it.
   - Either way, confirm all four family CSVs exist for `{id}` with the schema-v1 header and pass validation.
4. **Create the events log** `data/events/{id}.csv` (header row from `data/events/MANIFEST.md`) and backfill known events (~90 days) against the taxonomy. An empty events file is acceptable at registration but flag that `cooccurrence.sh` will return nothing until it's backfilled.
5. **Smoke-test the facility** with a descriptive calc against real ranges, e.g. `bash calc/descriptive/avg.sh {id} cph --start <S> --end <E>` and `bash calc/descriptive/worst_day.sh {id} damage --family exceptions --start <S> --end <E>`. A clean number (not `NA`/file-not-found) confirms the wiring.

## Verification

The procedure completed only if all of the following hold:

- `data/facilities/INDEX.md` has a Directory row, an Aliases row, and (if applicable) a peer-pairing row for `{id}`.
- `data/facilities/profiles/{id}.md` exists with no unfilled template placeholders and the targets recorded.
- All four metric CSVs exist for `{id}`, carry the schema-v1 header, and pass validation.
- `data/events/{id}.csv` exists (header at minimum).
- A descriptive calc returns a real value for `{id}`.

If any is missing, report the partial state — a half-registered facility is invisible to `signal-detect` (which scopes the scan from the facilities INDEX).

## Common mistakes

- **ID drift.** Using a different string in the INDEX vs the CSV filenames vs the profile silently breaks every lookup. Pick the ID once and use it verbatim everywhere.
- **Registering the directory row but not the data.** `signal-detect` will scan a facility that has no CSVs and error or return nothing. Wire the data in the same pass.
- **Skipping the events file.** Investigations at the new site will find no cooccurring events and you'll distrust the architecture. Backfill, or explicitly flag it as pending.
- **Forgetting the peer pairing.** Network rule-outs (`peer_benchmark.sh`, the "is this network-wide?" step in the playbooks) need a comparable site; without one, pick the same-type facility with the closest target.
