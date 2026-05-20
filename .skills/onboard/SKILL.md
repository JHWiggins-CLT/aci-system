---
name: onboard
description: >
  Use when the operator wants to set up or onboard the system against their own
  production data — first-time setup, or flipping a demo deployment to
  production. Walks the full setup flow: facilities, schema, the conversion
  adapter, thresholds, events backfill, resetting demo state, and the
  deployment-mode switch, then verifies. Do NOT use for normal CI work in an
  already-configured deployment (use `signal-detect`, `investigate`, or
  `close-loop`), and do NOT use for one-off incremental edits to an existing
  deployment's architecture (use `maintain`).
triggers:
  - 'set up production'
  - 'set up the system'
  - 'onboard'
  - 'onboard my data'
  - 'configure with my data'
  - 'use my own data'
  - 'switch to production'
  - 'go to production'
---

# Onboard

## When to use

The operator wants to move from the built-in demo to a real deployment against their own data — or is running setup for the first time. This is the holistic, ordered setup flow. It is the skill the first-run mode gate (`.skills/README.md` → Deployment mode) hands off to when the operator picks **setup**, and the skill any "set up production" / "onboard my data" request routes to later.

Do NOT use for routine CI work (that's `signal-detect` / `investigate` / `close-loop`) or for a single incremental architecture edit on an already-running deployment (that's `maintain`). Onboarding *uses* maintain procedures as steps, but it owns the whole sequence and the mode switch.

## Before you start — confirm and guard

1. **State what setup will do and confirm.** Setup replaces the demo dataset and clears the demo CI history. Say so plainly and get an explicit go-ahead before any destructive step. Demo data is regenerable (`python conversion/scripts/simulate_facility_data.py`) and lives in git, so this is reversible — but confirm anyway.
2. **Do not flip the mode to `production` yet.** Leave `config/deployment.yaml` at `unset` (or `demo`) until the final verify passes. An interrupted setup must re-prompt, never present a half-configured deployment as ready.

## Procedure

Run these in order. Each step is small and composes existing machinery; stop and surface any failure rather than pressing on.

1. **Facilities.** Collect the operator's real sites — IDs, type, aliases, peer pairings, per-facility targets — and render `data/facilities/INDEX.md` + one profile per site. Follow `maintain/procedures/add_facility.md` for each site.
2. **Schema.** Decide whether their metrics fit schema v1 as-is (adopt + map) or need a bump. For a bump, follow `maintain/procedures/bump_schema.md` (coordinated change across `data/metrics/MANIFEST.md`, `calc/lib/_schema_v1.sh`, the conversion adapter, and every golden test — in one pass). Default for a first run: adopt v1 and map the operator's columns onto it.
3. **Conversion adapter.** Copy `conversion/scripts/adapter_template.py` and fill the "read my source → map to schema columns" middle. Read the operator's column headers / a sample file and draft the mapping; have them confirm each field. The adapter MUST emit canonical CSVs through `conversion/validation/common.py` — the validators are the safety net that makes a bespoke adapter safe. Run it to populate `data/metrics/*` (and events, if sourced).
4. **Thresholds.** Set per-facility cph targets and exceptions ceilings (used by `signal-detect` and follow-ups). Record them in the facility profiles.
5. **Events backfill.** Guide the ~90-day events backfill facility-by-facility, validating against the event taxonomy in `data/events/MANIFEST.md`. Tedious but the highest-ROI step — `cooccurrence.sh` returns nothing without it.
6. **Reset demo state.** Clear the fictional investigations/Kaizens/A3s/pattern so history starts empty: `python .skills/onboard/reset_demo_state.py --dry-run` first (preview), then without `--dry-run`. It refuses in `production` mode without `--force`, and never touches metrics/events/facilities.
7. **Verify, then flip the mode.** Run `bash verify.sh`. It auto-detects the mode: while still `unset`/`demo` it runs all checks, and once you set `production` it runs the structural tier only (golden tests, manifest, validators, onboarding plumbing) — the demo-scenario sections are skipped automatically. Set the mode last: `python config/deployment.py set production`, then re-run `bash verify.sh` to confirm the structural tier is green in production mode. (You can also force the tier with `--structural` / `--all`.)

## Capabilities (extensible setup)

Optional capabilities (reporting, graphing, presentations, exports) each carry their own setup contribution and config under `capabilities:` in `config/deployment.yaml`. When one exists, offer it during onboarding and run only its setup contribution (a partial onboard). See `onboarding_design.md` Section 5. None are built yet — when the first lands, add a step here that enumerates enabled capabilities and runs each one's setup.

## Inputs and outputs

- **Reads:** `config/deployment.yaml`, `.skills/maintain/templates/*`, `maintain/procedures/{add_facility,bump_schema}.md`, `conversion/scripts/adapter_template.py`, `conversion/validation/common.py`, `data/events/MANIFEST.md`.
- **Writes:** `data/facilities/*`, the conversion adapter, `data/metrics/*` (via the adapter), `data/events/*`, and (via `reset_demo_state.py`) clears demo CI artifacts. Sets `config/deployment.yaml` mode at the end.
- **Calls:** `python .skills/onboard/reset_demo_state.py`, the operator's conversion adapter, `bash verify.sh`, `python config/deployment.py set production`, `python .skills/.meta/reconcile.py` if any SKILL.md changed.

## Anti-patterns

- **Do not flip to `production` before `verify.sh` passes.** A half-configured deployment that reports "production" is the worst failure mode.
- **Do not skip the events backfill** because it's tedious — it's what makes diagnostics work.
- **Do not hand-author canonical CSVs.** Everything goes through the conversion adapter and the validators; that contract is the whole point of the boundary.
- **Do not run `reset_demo_state.py` without a dry-run first**, and never with `--force` unless the operator explicitly accepts that real history will be deleted.
- **Do not bump the schema and start using the new shape elsewhere in the same breath** — a bump is a coordinated, single-pass change (see `bump_schema.md`).

## Verification

Setup is complete only when: facilities + profiles exist for the operator's real sites; the conversion adapter populates `data/metrics/*` through the validators; thresholds are recorded; events are backfilled; demo CI artifacts are cleared (indexes header-only); `verify.sh` structural checks pass; and `config/deployment.yaml` reads `production`. If any is missing, report the partial state and leave the mode at `unset`.

> **Note on `verify.sh` after a production cutover.** `verify.sh` is mode-aware: in `production` it runs only the structural tier (golden tests, manifest sync, validators, deployment-mode gate, onboard tooling) and automatically skips the demo-scenario sections (the dal-02 dip, chr-05, the equipment pattern, etc.). So a green `verify.sh` in production is the real acceptance gate — no expected-failures to reason around.
