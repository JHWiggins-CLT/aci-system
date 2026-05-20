# Setting up the ACI System with your own data

This is the human-readable mirror of the `onboard` skill (`.skills/onboard/SKILL.md`).
You can read it cold, or just tell your assistant *"set up production"* / *"onboard my data"*
and it will walk you through the same steps.

> **The system ships in demo mode.** On first run it greets you with **demo vs setup**
> (see `.skills/README.md` → Deployment mode). Demo runs against built-in simulated data
> and is the safe default. Setup — this document — points it at your real data. You can
> switch to setup at any time; the choice is remembered.

## What setup does (and the safety net)

Setup **replaces the demo dataset and clears the demo CI history** so you start clean.
That's reversible — the demo regenerates from `conversion/scripts/simulate_facility_data.py`
and lives in git — but you'll be asked to confirm before anything destructive. Nothing
outside `data/`, `config/`, and your new conversion adapter is touched.

The mode is **not** flipped to `production` until the final verification passes, so an
interrupted setup never leaves you with a deployment that *claims* to be ready but isn't.

## Steps

1. **Facilities.** List your real sites — IDs, type (Fulfillment / Distribution / Cold
   Storage / …), aliases, peer pairings, and per-facility targets. These become
   `data/facilities/INDEX.md` + one profile per site. (Procedure:
   `.skills/maintain/procedures/add_facility.md`.)
2. **Schema.** Either adopt the built-in v1 schema and map your metrics onto it
   (simplest, the default for a first run), or bump the schema to match your reality
   (`.skills/maintain/procedures/bump_schema.md` — a coordinated change across the
   manifest, the calc column map, the adapter, and the golden tests).
3. **Conversion adapter.** Copy `conversion/scripts/adapter_template.py` and fill in the
   "read my source → map to schema columns" middle. Point it at your Excel/CSV/WMS export.
   It must emit canonical CSVs **through `conversion/validation/common.py`** — the
   validators reject a bad mapping loudly before any calc sees it. Run it to populate
   `data/metrics/`.
4. **Thresholds.** Set per-facility CPH targets and exceptions ceilings (recorded in the
   facility profiles; used by `signal-detect` and follow-ups).
5. **Events backfill.** Log ~90 days of events per facility against the taxonomy in
   `data/events/MANIFEST.md`. Tedious, but it's what makes `cooccurrence.sh` (and real
   investigations) work — don't skip it.
6. **Reset demo state.** Clear the fictional investigations/Kaizens/A3s/pattern:
   ```bash
   python .skills/onboard/reset_demo_state.py --dry-run   # preview
   python .skills/onboard/reset_demo_state.py             # do it
   ```
   It refuses to run in `production` mode without `--force`, and never touches
   metrics/events/facilities.
7. **Verify, then go live.**
   ```bash
   bash verify.sh                              # all checks (while still in demo/unset)
   python config/deployment.py set production  # flip the mode last
   bash verify.sh                              # now runs the STRUCTURAL tier only — must be green
   ```
   `verify.sh` is mode-aware: in `production` it runs the structural tier (golden tests,
   manifest, validators, onboarding plumbing) and automatically skips the demo-scenario
   sections, so a green run in production is the real acceptance gate. (Force a tier with
   `--structural` or `--all` if needed.)

## Adding capabilities later

The system is built to grow (reports, graphing, presentations, exports). Each capability
brings its own setup and its own `capabilities:` entry in `config/deployment.yaml`, so
enabling one is a *partial* re-onboard — you don't redo the whole flow. See
`onboarding_design.md` Section 5. (No optional capabilities ship yet.)

## Build status

The mode gate, this guided flow, `reset_demo_state.py`, the `add_facility`/`bump_schema`
procedures, and the mode-aware `verify.sh` split are all built. The one piece you complete
yourself is the conversion adapter (a validator-wired template). Optional capability modules
(reports, graphing, presentations) are designed but not yet built. See `onboarding_design.md`
(build sequence) for the full status.
