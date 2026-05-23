# ACI System — Operations Investigation Architecture

A portfolio implementation of a continuous-improvement (CI) system for warehouse operations: signal detection, investigation, floor-feedback intake, A3/Kaizen generation, and outcome tracking — all routed through description-gated skills any reasonably capable model can operate by reading [.skills/README.md](.skills/README.md) first. It ships in a safe **demo** mode and can be **onboarded onto real production data** when you're ready (see [Demo or production](#demo-or-production)).

> **Portfolio piece by default — but productionizable.** Out of the box all data is simulated by [conversion/scripts/simulate_facility_data.py](conversion/scripts/simulate_facility_data.py) with a fixed seed: no real facilities, no PII, no production pipeline. The architectural discipline of the conversion boundary (validators, MANIFEST, audit logs) is preserved exactly as it would be against real Excel/CSV sources — only the source itself is synthetic. A guided setup flow swaps that synthetic source for your own data without touching the rest of the architecture.

## Invocation entry point

This is the **single documented front door** for the system — the canonical sequence to invoke ACI, for a human, a fresh assistant, or another system. The machine-readable map is the root [MANIFEST.yaml](MANIFEST.yaml) (`entrypoint:` field); this is its human mirror.

1. **Read [MANIFEST.yaml](MANIFEST.yaml)** — the system map: components, per-layer manifests (the contracts), skills, deployment modes, this entry point.
2. **Read [.skills/README.md](.skills/README.md)** — the skills protocol contract.
3. **Check deployment mode** — `python config/deployment.py get`. If `unset`, present the first-run demo/setup greeting and persist the choice before doing any work.
4. **Read [.skills/MANIFEST.yaml](.skills/MANIFEST.yaml)** — the skill registry.
5. **Match the operator's intent to exactly one skill** and load its `SKILL.md`. Skills are never chained automatically; ambiguity is resolved by asking, not guessing.

ACI is invoked **conversationally**, by an assistant-in-the-loop reading these files — there is no network endpoint by design. Request shape: `{ intent, context }`; response shape: `{ skill, artifacts, state_change }`. (A fresh session may also read [tracking.md](tracking.md) first to orient.)

## What this is

An eight-layer system that takes a CI manager from "I see a signal" through "here is the floor brief" to "here is the A3 or Kaizen, here is whether it worked, here is what we learned." The architecture is specified in [handoff.md](handoff.md), built phase by phase per [implementation_plan.md](implementation_plan.md), and the live build state is recorded in [tracking.md](tracking.md).

Seven skills route the work — four drive the CI loop, plus `review` to browse it, `export` to share it, and `onboard` for setup:

| Skill | When | Trigger phrases |
|-------|------|----------------|
| [signal-detect](.skills/signal-detect/SKILL.md) | Proactive daily scan (consistent morning brief) | "what should I look at today" |
| [investigate](.skills/investigate/SKILL.md) | Dig into a specific signal | "investigate dal-02's throughput drop" |
| [close-loop](.skills/close-loop/SKILL.md) | Back from the floor | "closing out the dal-02 investigation" |
| [maintain](.skills/maintain/SKILL.md) | Edit the architecture | "add a calc", "update the pattern" |
| [review](.skills/review/SKILL.md) | See/browse existing work | "show me open Kaizens", "what closed this quarter" |
| [export](.skills/export/SKILL.md) | Share an artifact outside the system | "export the dal-02 A3 to HTML", "make this presentable for management" |
| [onboard](.skills/onboard/SKILL.md) | First-time / production setup | "set up production", "onboard my data" |

The skills layer is described in [.skills/README.md](.skills/README.md). Only one skill loads per request; descriptions are mutually exclusive on purpose. The `review` skill renders every artifact catalog through one consistent view (`.skills/review/status.py`), and the morning brief shares that same format.

## Demo or production

On first run the system **greets you with a choice** (via Step 0 of the skills protocol): run in **demo** mode — explore the architecture against the built-in simulated data, the safe and reversible default — or **setup** mode — configure it against your own production data. The choice is recorded in `config/deployment.yaml` (helper: `python config/deployment.py get`) and is **sticky**; you can flip to setup at any time by saying *"set up production"*.

- **Demo** runs everything in this README against the simulated dataset.
- **Setup** is the [onboard](.skills/onboard/SKILL.md) skill — a guided flow (human mirror in [SETUP.md](SETUP.md)) that registers your facilities, maps your source through the conversion boundary (scaffold: [conversion/scripts/adapter_template.py](conversion/scripts/adapter_template.py)), backfills events, clears the demo history, and verifies. `verify.sh` is **mode-aware**: in production it runs the structural checks and automatically skips the demo-scenario ones, so a green run in production is a real acceptance gate.

The full design and build status live in [onboarding_design.md](onboarding_design.md).

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

# 6. Deployment mode (a fresh checkout greets demo-vs-setup; this repo ships unset):
python config/deployment.py get
#   → unset    (pick demo to explore, or say "set up production" to onboard your data)

# 7. Management reports (A3/Kaizen/investigation .md → executive HTML, jargon-stripped, with charts):
python reports/render_html.py --all
#   → wrote reports/a3-...html, reports/k-...html, reports/bundle-...html + reports/index.html

# 8. Full smoke test (mode-aware: all checks in demo/unset, structural-only in production):
bash verify.sh
#   → Results: 124 passed, 0 failed
```

## Project layout

```
.skills/         # Protocol README, MANIFEST, seven skills (incl. review, export, onboard), .meta tooling
calc/            # Bash calc library (descriptive, diagnostic, comparative, outcome)
conversion/      # The data boundary — validators, simulator, adapter template, manifest, logs
config/          # Deployment mode (demo vs production): deployment.yaml(.example) + helper
data/            # Canonical CSVs (metrics, events, facilities, investigations, patterns, ...)
reports/         # Shareable HTML export of A3/Kaizen artifacts (render_html.py); output gitignored
simulate/        # Helper scripts used to scaffold the portfolio dataset
SETUP.md         # Production onboarding guide (human mirror of the onboard skill)
onboarding_design.md    # Design + build status for the demo→production onboarding
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

See [tracking.md](tracking.md) for the live status header, phase progress table, and working log. The core CI loop is complete and demonstrated end-to-end (signal → investigate → close-loop → outcome tracking, with the first abstracted pattern feeding the playbook), and a production-onboarding path (demo → setup, slices 1–6) is built on top of it. Only optional capability modules (reports, graphing, presentations) remain — see [onboarding_design.md](onboarding_design.md) §5.
