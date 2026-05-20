# ACI System — Operations Investigation Architecture

A portfolio implementation of a continuous-improvement (CI) system for warehouse operations: signal detection, investigation, floor-feedback intake, A3/Kaizen generation, and outcome tracking — all routed through four description-gated skills any reasonably capable model can operate by reading [.skills/README.md](.skills/README.md) first.

> **Portfolio piece, not production.** All data is simulated by [conversion/scripts/simulate_facility_data.py](conversion/scripts/simulate_facility_data.py) with a fixed seed. No real facilities, no PII, no production pipeline. The architectural discipline of the conversion boundary (validators, MANIFEST, audit logs) is preserved exactly as it would be against real Excel/CSV sources — only the source itself is synthetic.

## What this is

An eight-layer system that takes a CI manager from "I see a signal" through "here is the floor brief" to "here is the A3 or Kaizen, here is whether it worked, here is what we learned." The architecture is specified in [handoff.md](handoff.md), built phase by phase per [implementation_plan.md](implementation_plan.md), and the live build state is recorded in [tracking.md](tracking.md).

Four skills route the work:

| Skill | When | Trigger phrases |
|-------|------|----------------|
| [signal-detect](.skills/signal-detect/SKILL.md) | Proactive daily scan | "what should I look at today" |
| [investigate](.skills/investigate/SKILL.md) | Dig into a specific signal | "investigate dal-02's throughput drop" |
| [close-loop](.skills/close-loop/SKILL.md) | Back from the floor | "closing out the dal-02 investigation" |
| [maintain](.skills/maintain/SKILL.md) | Edit the architecture | "add a calc", "update the pattern" |

The skills layer is described in [.skills/README.md](.skills/README.md). Only one skill loads per request; descriptions are mutually exclusive on purpose.

## Model-agnostic by design

Nothing here depends on a specific assistant or runtime. Python scripts use only the standard library. Bash calcs are POSIX-ish with a BSD-`date` fallback. The skills protocol is documented for a model that has never seen this pattern before. If the dominant or most cost-effective model changes — within Claude, or across vendors — the system continues to operate as long as the new model can read files and follow instructions.

## Quick verification

```bash
# 1. Generate the simulated dataset (deterministic, ~1 second):
python conversion/scripts/simulate_facility_data.py

# 2. Calc library golden tests:
bash calc/tests/run.sh
#   → PASS: avg_cph_all
#   → PASS: avg_cph_windowed

# 3. End-to-end signal detection (cohort dip at dal-02 in March):
bash calc/descriptive/avg_cph.sh dal-02 --start 2026-02-01 --end 2026-02-28
#   → 141.82  (baseline)
bash calc/descriptive/avg_cph.sh dal-02 --start 2026-03-08 --end 2026-03-22
#   → 128.10  (cohort dip, ~9% below baseline)
bash calc/descriptive/avg_cph.sh dal-02 --start 2026-04-01 --end 2026-04-30
#   → 141.56  (recovery)

# 4. Diagnostic cooccurrence finds the training event near the dip:
bash calc/diagnostic/cooccurrence.sh dal-02 2026-03-15 --window 14
#   → 2026-03-02 | training | Cohort of 6 new hires onboarded; ...
#   → 2026-03-06 | training | Pick certification week 1 begins for Mar-02 cohort

# 5. Skills protocol in sync:
python .skills/.meta/reconcile.py
#   → No changes detected. Manifest is in sync.
```

## Project layout

```
.skills/         # Protocol README, MANIFEST, four skills, .meta tooling
calc/            # Bash calc library (descriptive, diagnostic, comparative, outcome)
conversion/      # The data boundary — validators, simulator, manifest, audit logs
data/            # Canonical CSVs (metrics, events, facilities, investigations, ...)
simulate/        # Helper scripts used to scaffold the portfolio dataset
handoff.md       # Architecture specification (what the system is when complete)
implementation_plan.md  # Build sequence (how to get from nothing to complete)
tracking.md      # Live build state (where the build is right now)
```

A fresh assistant session should read `tracking.md` first to orient, then `.skills/README.md` for the skill-loading protocol, and only pull from `handoff.md` when architectural reference is needed.

## Embedded scenarios in the simulated data

The simulator threads several plausible operational stories through the dataset so that real investigations have something real to find:

| Facility | Window | Story |
|----------|--------|-------|
| dal-02 | 2026-03-08 to 2026-03-22 | Cohort-of-6 throughput dip, mispick spike, trainer ratio violation |
| chr-03 | 2026-04-12 to 2026-04-24 | Damage spike following bin relocation SOP change |
| ral-02 | 2026-04-20 to 2026-04-27 | Conveyor failure → throughput drag during repair |
| sav-01 | 2026-03-09 to 2026-03-16 | MHE drive failure → throughput drag (equipment-downtime pattern) |
| atl-03 | 2026-04-06 to 2026-04-13 | Conveyor gearbox failure → throughput drag (equipment-downtime pattern) |
| chr-05 | 2026-03-14 to 2026-03-17 | Refrigeration excursion → damage spike |
| atl-01 | 2026-03-01 to 2026-05-18 | Slow drift up following Q4 WMS release |

The sav-01, atl-03, and ral-02 equipment failures share one mechanism — together they form the first abstracted **pattern** (`data/patterns/equipment_downtime_throughput_drag.md`), which the `throughput_drop` playbook now consults before drafting hypotheses.

Plus background events (audits, weather, volume shocks, leadership changes, network deployments) for cooccurrence richness.

## Current build state

See [tracking.md](tracking.md) for the live status header, phase progress table, and working log. Phase 0 (conversion boundary, adapted for simulated data) and Phase 1 (architecture skeleton) are complete; Phases 2-7 are the remaining build sequence per the implementation plan.
