# Operations Investigation Architecture — Implementation Plan

> **Companion to:** `handoff.md` (architecture specification) and `tracking.md` (build state)
> **This document:** how to build the architecture from nothing, calibrated for solo work over an open-ended timeline, starting from mixed CSV/Excel data sources.
> **Model-agnostic:** the build assumes any reasonably capable assistant with filesystem access. Specific tool names and surfaces are not relied upon.

---

## How to use this plan

This is not a project plan with deadlines. It is a **dependency-ordered sequence of build phases**, each producing a concrete, testable deliverable, that you work through at your own pace.

Three rules govern how to move through it:

1. **Do not start a phase until the prior phase's exit criteria pass.** Exit criteria are listed at the end of each phase. They are not aspirational — if any of them fail, you stop and fix that phase before moving on. Silent partial completion is the most common way a build like this rots.
2. **Build one slice end-to-end before thickening.** Inside any phase that involves multiple files or facilities or calcs, pick one and finish it completely (including tests) before starting the second. The temptation to build all the templates first and then fill in their content is real and wrong. Templates without working content drift.
3. **The plan assumes you'll need to revise.** Schemas will change. Templates will get clearer after first contact with reality. A handful of calc signatures will turn out wrong. The plan is structured so revision is a normal expected event, not a crisis — but only if you do real validation at every checkpoint instead of pushing through.

The plan has nine phases (0 through 8). Phase 0 is data acquisition and is by far the longest. Phase 7 is the "stop here if you want to" checkpoint — beyond that, expansions are useful but not required for the system to deliver real value.

---

## Keeping the build state current

This plan describes *what should happen*. The companion file `tracking.md` records *what has happened so far*. The plan and the tracker are read together — the plan tells you what to do; the tracker tells you what's already done.

**At the start of every work session:**

1. Read `tracking.md` first. The status header tells you what's active and what comes next.
2. Read the plan section for the current phase.
3. Pull from `handoff.md` for any architectural reference needed.

**During work:**

- Mark sub-steps complete in the tracker's phase sub-table as you finish them.
- Log any decision that deviates from the plan in the tracker's Decisions table.
- If you stop mid-step, update the "in-progress work" field in the status header.

**At the end of every work session:**

1. Update the status header: current phase, last completed step, next concrete action.
2. Update the phase progress table if a phase status changed.
3. Append a working-log entry: what you did, what you noticed, what's next.
4. If a fresh assistant session might pick up the work, double-check the status header is accurate — that's the only field they will trust without verification.

The discipline matters: a tracker that lags reality by even a few sessions becomes useless. The next assistant session reads it expecting truth; if it gets stale truth, the architecture's continuity property breaks.

This is the equivalent of the close-loop skill's discipline applied to the build itself. The architecture insists every investigation produces a saved record; the build process insists every session produces a tracker update. Same principle, same reason.

### A note on session surface and filesystem access

Different assistant deployments expose the project to the model differently. The build accommodates this:

- **Sessions with filesystem access** (typically desktop apps, command-line agents, or any tooling that lets the model read files directly): Read `tracking.md` automatically. The protocol above ("read tracker first") works as written.
- **Sessions without filesystem access** (typically chat-only web interfaces or anything that cannot read project files directly): Cannot orient from the tracker. The operator should briefly state current state verbally at the start of the session — for example: "We're in phase 4, just finished step 4.3 (writing the throughput_drop playbook), and I'm about to start running real investigations through it."

A session without filesystem access that proceeds without this verbal orientation may confidently misreport the build state — for example, assuming the build hasn't started because no tracker content has been shared. The cure is operator awareness: when opening such a session for build work, lead with the current phase rather than letting the assistant infer.

The recommended workflow (described in the project root `README.md`) is to use filesystem-capable sessions for operational work (phase 4 onward, where the build is read-write against many files) and to use chat-only sessions only for architecture work that can be done against a small set of pasted files. Web or chat-only sessions during phases 0-3 don't strictly need tracker access because the work is on a small set of committed files; the verbal orientation is enough. Desktop or CLI sessions during phases 4+ rely on tracker access more heavily, which is another argument for that surface split.

If you switch to a different assistant or model entirely, the same principles apply — the architecture's skills protocol (documented in `.skills/README.md`) is designed to work with any reasonably capable instruction-following model.

---

## Phase dependency graph

```
Phase 0 (Data conversion)
   ↓
Phase 1 (Architecture skeleton + skills protocol infrastructure)
   ↓
Phase 2 (First metric family + descriptive calcs)
   ↓
Phase 3 (Diagnostic calcs + events layer)
   ↓
Phase 4 (signal-detect + investigate skills with one playbook)
   ↓ ← FIRST INVESTIGATIONS RUN HERE (5-10)
Phase 5 (close-loop + first A3/Kaizen + outcome calcs)
   ↓ ← FIRST CLOSED LOOPS RUN HERE (3-5)
Phase 6 (Pattern emergence + maintain skill)
   ↓
Phase 7 (THRESHOLD: SYSTEM IS REAL — STOP HERE IF YOU WANT)
   ↓
Phase 8 (Remaining playbooks, remaining metric families, comparative calcs)
```

The vertical bars at phases 4 and 5 are where you start doing real work *through* the system, not just *on* it. Most of the value is created in those phases, not in the foundation work that precedes them. This is why phase 0-3 frustration is worth pushing through — phases 4-5 are where the architecture starts paying for itself.

---

## Phase 0 — Data conversion

**Goal:** Get your real Excel and CSV files into canonical CSV form that bash tools can read, with the conversion boundary fully documented and validated.

This phase is unglamorous and probably the longest in calendar time. You are not yet building the architecture. You are building the **conversion boundary** that the architecture trusts. Without this, every later phase is theoretical — the calc library cannot consume Excel directly, and undocumented conversions silently corrupt downstream analysis without anyone noticing.

**Why this exists as its own phase:** Excel files are binary, contain multiple sheets, often have headers that don't start on row 1, frequently have merged cells or formulas that mask the underlying data structure, and are edited by humans in ways that break programmatic parsing. The calc library is built on bash tools (awk, grep, sort) that cannot read Excel directly. The architecture also enforces a boundary: every CSV in `data/metrics/` must be produced by a recorded, validated conversion script. That contract is established here.

### Steps

**0.1 Inventory your data sources.**

Create a single document — `notes/data_inventory.md` — that lists, for every data source you currently use for CI work:

- File name and location (path or share)
- File type (xlsx, xls, csv)
- Update cadence (daily, weekly, monthly, ad hoc)
- How it's produced (manual export, automated dump, vendor-supplied, etc.)
- What metrics or fields it contains
- Which facility (or facilities) it covers
- Known quirks (merged cells, sheets, formulas, header offsets)

This inventory IS the project plan for phase 0. Every file on it needs a conversion path before phase 1 can start.

**0.2 Classify each source by destination.**

For each source in the inventory, decide which of the four metric families it feeds: operational, inputs, exceptions, equipment. Some sources may feed two families; that's fine, but note it.

Sources that don't fit any of the four families belong in one of three buckets:
- **Events** — gets handled in phase 3, not now
- **Reference data** — used to build facility profiles, handled in phase 1
- **Out of scope** — note it and set it aside

If a source contains data that genuinely doesn't fit the four families and isn't an event or reference data, you may need to expand the schema. Don't decide this yet — flag it and revisit at the end of phase 0.

**0.3 Build the shared validation routines.**

Before writing any conversion script, write the validation library every script will use. Create `conversion/validation/common.py` (or `.sh`, depending on your tool choice) with reusable functions:

- `validate_date_format(column)` — every value in the column matches YYYY-MM-DD
- `validate_no_nulls(column)` — no blank/null values in a required column
- `validate_facility_match(column, expected_id)` — every row's facility_id matches what the filename expects
- `validate_row_count(df, min_expected)` — output has at least N rows (catches truncated exports)
- `validate_value_range(column, min, max)` — numeric values fall in plausible range
- `validate_schema_match(df, expected_columns)` — column count and order matches the schema version

Each validator returns success or fails with a clear error message and writes to `conversion/logs/{date}_{script}.log`. The script never writes a partial or invalid CSV; if any validator fails, the run aborts and the existing canonical CSV (if any) is preserved untouched.

This step exists before the conversion scripts because *every conversion script will invoke these validators in the same way*. Building them once means consistent validation across all sources, and revising a validator (when you find a new failure mode) updates every script at once.

**0.4 Build a conversion script for the simplest source.**

Pick the source in your inventory that looks easiest. Probably a CSV that's already in roughly the right shape, or a single-sheet xlsx with no merged cells.

Write a script in `conversion/scripts/` that:
- Reads the source file
- Extracts only the columns you need
- Normalizes column names to match the canonical schema (`date`, `facility_id`, `units`, `cph`, etc.)
- Invokes the validators from `conversion/validation/common.py`
- Writes to `data/metrics/{family}/{id}.csv` ONLY if all validators pass
- Logs the run (success or failure) to `conversion/logs/`
- Exits non-zero on validation failure so a wrapping orchestrator can detect it

Name scripts clearly: `conversion/scripts/extract_dal02_operational.py`.

**0.5 Build conversion scripts for every remaining source.**

One at a time. Each one should produce a CSV that the calc library can later consume. Do not move on until *all* sources from your inventory have working conversion scripts that pass validation.

This is where the open-ended timeline matters most. Excel files are unpredictable; some will take 20 minutes to convert and some will take a full afternoon because the structure is hostile. Take the time. A flaky conversion script makes every downstream calc unreliable, and a silent validation gap makes every downstream calc *misleading*.

**0.6 Write `conversion/MANIFEST.md`.**

This is the contract that the architecture trusts. Document:

- Every source-to-target mapping (which raw file produces which canonical CSV via which script, on what cadence)
- The validation guarantees every script provides (the list of validators that must pass)
- The schema version currently being produced (v1, matching `metrics/MANIFEST.md`)
- Known fragile sources, with reasons
- The cadence for re-running conversions

The handoff's section 7 has an illustrative example of this manifest's shape. Match that structure.

**0.7 Write `conversion/README.md`.**

The operator-facing instructions:
- How to run all conversions (one command if possible)
- How to run a single conversion (for debugging)
- Where outputs go, where logs go
- What to do when a validation fails
- What cadence to run on

### Exit criteria

- All data sources from `notes/data_inventory.md` have working conversion scripts in `conversion/scripts/`
- Shared validation routines exist in `conversion/validation/` and are invoked by every script
- Running every conversion script produces files in `data/metrics/{family}/{id}.csv` for all 8 facilities × at least 1 metric family
- Spot-check at least 5 random rows from each output CSV against the source file — values match
- **`conversion/MANIFEST.md` exists**, documenting every source → script → target mapping, the validation contract, schema version, and known fragile sources
- **`conversion/logs/`** has at least one successful run log per script
- `conversion/README.md` exists and could be followed by a stranger to re-run all conversions
- You have at minimum 90 days of historical operational metric data per facility, in canonical CSV form
- Deliberately introducing a bad row in a source file (wrong date format, missing facility_id, negative CPH) causes the corresponding script's validation to fail loudly — confirm this works for at least one script before considering the phase done

### Common pitfalls

- **Trying to make conversion scripts handle every possible Excel format quirk.** Don't. Make them work for *your specific files as they exist today*. If the format changes, you'll fix the script. Don't pre-build robustness you don't need.
- **Building scripts before the shared validators.** This leads to inconsistent validation across scripts. Build the validators first; reuse them everywhere.
- **Writing the MANIFEST after the scripts are "working."** This makes the manifest a chore that gets done badly or skipped. Write the MANIFEST entry for each source AS YOU build its script — the entry IS the documentation of what the script does and guarantees.
- **Weakening validators to make a stubborn source pass.** This is the most dangerous failure mode. If a source can't pass validation, fix the source or fix the script — never loosen the validator. A loosened validator silently corrupts every downstream calc.
- **Skipping the bad-row test.** A validator that has never failed in testing has never actually been tested. Confirm by hand that breaking the source data triggers a validation failure.
- **Letting the conversion phase drag because it's boring.** It is boring. Set a minimum bar — 1 conversion script completed per work session — to maintain momentum.

---

## Phase 1 — Architecture skeleton and skills protocol infrastructure

**Goal:** Create the folder structure, the smallest set of files that lets you read the architecture as a thing, AND the skills protocol infrastructure that lets any capable assistant operate the system.

This is the fastest phase. A day or two of work. No skills bodies yet, no calcs, no playbooks — just the folder structure, the foundational reference files, and the protocol contract that the skills layer will publish.

### Steps

**1.1 Create the folder structure.**

Use the file layout from section 2 of the handoff. Create every folder. Most will be empty.

```bash
mkdir -p .skills/.meta
mkdir -p .skills/signal-detect
mkdir -p .skills/investigate/playbooks
mkdir -p .skills/close-loop/procedures
mkdir -p .skills/maintain/{procedures,templates}
mkdir -p data/facilities/profiles
mkdir -p data/metrics/{operational,inputs,exceptions,equipment,archive}
mkdir -p data/events
mkdir -p data/investigations/{open}
mkdir -p data/patterns
mkdir -p data/a3s/{open,closed}
mkdir -p data/kaizens/{open,closed}
mkdir -p data/follow_ups
mkdir -p calc/{descriptive,diagnostic,comparative,outcome,lib,tests/{golden,expected}}
```

**1.2 Write `.skills/README.md`.**

This is the protocol explainer for any unfamiliar model that enters the project. The handoff's section 2 describes what this file is for; the file itself should be concise (<300 lines, ideally <150) and contain:

- A one-paragraph orientation explaining what skills are and why they exist in this project
- The protocol, stated as numbered imperative steps: (1) read this README; (2) read `MANIFEST.yaml`; (3) match user request to a skill description; (4) read only the matching skill's `SKILL.md`; (5) follow that skill's instructions
- Triggering rules: when to load a skill vs. not, what to do if multiple skills match, what to do if none do
- A short schema description and example for `MANIFEST.yaml`
- A short schema description and example for the frontmatter at the top of each `SKILL.md`
- What NOT to do: don't read all `SKILL.md` files upfront, don't modify skill files unless asked, don't invoke skills the user didn't request, etc.
- A pointer to the tooling in `.skills/.meta/`

The README is the file that makes this system operable by any reasonable assistant, not just one that's been trained on a particular skills convention. Write it for a model that's never seen this pattern before.

**1.3 Write `.skills/MANIFEST.yaml`.**

Initially, the manifest will be nearly empty — the skills don't exist yet. The file should still exist with the right shape:

```yaml
version: 1
generated_at: 2026-MM-DDTHH:MM:SSZ
skills: []
```

As skills are added in phases 4-6, entries get appended via `.skills/.meta/create_skill.py` (or via the reconcile tool if skills are authored by hand). Each entry includes name, path, description, trigger keywords, and a content hash so drift can be detected.

**1.4 Write `.skills/.meta/reconcile.py`.**

The reconciliation tool. Walks the `.skills/` tree, finds every `SKILL.md`, parses out its frontmatter, and synchronizes with `MANIFEST.yaml`. Behavior:

- Skills found on disk but missing from manifest → added
- Skills in manifest but missing from disk → flagged (not auto-deleted; require `--prune` flag)
- Skills present in both but with mismatched description or content hash → flagged as drift; default behavior is "prefer disk version" (manifest is regenerated from the on-disk `SKILL.md` frontmatter)
- Malformed `SKILL.md` frontmatter → warned, skipped

The script should be invoked by the operator (you) on demand, and automatically as the last step of `create_skill.py`. Keep it simple — under 200 lines is enough for the current scale.

**1.5 Write `.skills/.meta/create_skill.py`.**

The scaffolder. Prompts the operator for a skill name, description, and trigger keywords. Creates the appropriate directory under `.skills/{name}/`, writes a starter `SKILL.md` with valid frontmatter, then invokes reconcile to update the manifest.

This is what makes adding new skills frictionless once the architecture is running. In phases 4-6 you'll create four skills (signal-detect, investigate, close-loop, maintain); having the scaffolder ready means you create each one in seconds rather than fighting with structure.

**1.6 Write the `data/facilities/INDEX.md`.**

This is the flat directory of your 8 facilities. Include for each:
- Canonical facility ID
- Name
- State
- City
- Type (Fulfillment / Distribution / Cross-dock / Cold Storage / other)
- Aliases (how operations actually refers to it — ask the people who work there for the nicknames)
- Path to its profile file

Add the peer-pairing section: which facilities are operational peers for benchmarking purposes (same type, similar scale). At 8 facilities you'll have ~4 peer pairs.

Add the state-rollup and type-rollup helper sections so signal-detect can quickly find "all NC facilities" or "all cold storage sites."

**1.7 Write one facility profile in full as a template.**

Pick the facility you know best. Write its profile file completely. Use this as the canonical shape; copy it for the other 7 facilities and fill in the specifics.

The profile contains: quick facts, operational profile, metric file pointers, targets/context, related facilities. The handoff has the structure; don't reinvent.

**1.8 Write the metrics MANIFEST.md.**

Document the schema for whichever metric families you have data for after phase 0. If you only have operational metrics so far, document just that — leave the others as "v1 placeholder, populated in phase X." Be explicit about the schema version (v1) so the calcs reference it correctly.

**1.9 Write `calc/lib/_schema_v1.sh`.**

Bash variable definitions for column positions. Example:
```bash
# Schema v1 column positions
export COL_DATE=1
export COL_FACILITY=2
export COL_UNITS=3
export COL_CPH=4
export COL_ERROR_RATE=5
export COL_HOURS_RUN=6
```

Source this in every calc. Never hardcode column positions in a calc.

### Exit criteria

- Folder structure matches the handoff's section 2 layout, including `.skills/` and `.skills/.meta/`
- `.skills/README.md` exists, documents the protocol, and is followable by a model that's never seen the skill pattern before
- `.skills/MANIFEST.yaml` exists with the right shape (even if `skills: []` for now)
- `.skills/.meta/reconcile.py` exists, runs cleanly against the current (empty) manifest, and adds/flags entries as expected when tested with a dummy `SKILL.md`
- `.skills/.meta/create_skill.py` exists and successfully scaffolds a test skill that reconcile then registers
- `data/facilities/INDEX.md` lists all 8 facilities with aliases verified by talking to operations
- 8 facility profiles exist (one as the template, 7 copied and customized)
- `metrics/MANIFEST.md` documents the schema for at least one metric family
- `calc/lib/_schema_v1.sh` exists and is sourced cleanly when tested with `bash -c 'source calc/lib/_schema_v1.sh; echo $COL_CPH'`

### Common pitfalls

- **Treating `.skills/README.md` as throwaway.** This is the load-bearing document for cross-model portability. If a future assistant can't operate the system because the README is vague, the whole skills layer is fragile. Write it as if a stranger had to follow it.
- **Skipping the scaffolder and writing skill folders by hand.** This works at first but causes manifest drift the moment you forget to run reconcile. The scaffolder takes an hour to write and saves that hour back within the first few skills you create.
- **Guessing aliases instead of asking.** Aliases that don't match how operations actually talks will silently break facility resolution later. Spend the 30 minutes per facility to get them from real conversations.
- **Skipping the peer pairings.** They feel optional now and become hard to add later when comparative calcs depend on them. Define them now even if you're not building comparative calcs until phase 8.

---

## Phase 2 — First metric family and descriptive calcs

**Goal:** One metric family fully populated for all 8 facilities, with the five descriptive calcs working and tested against it.

This is the first phase where you produce something you can actually *query*. By the end, you can run `avg_cph.sh dal-02 --start 2026-02-01 --end 2026-03-01` against your real data and get a real number.

### Steps

**2.1 Populate `data/metrics/operational/` for all 8 facilities.**

Run your phase 0 conversion scripts. Confirm all 8 operational CSVs exist with at minimum 90 days of history. Spot-check values.

**2.2 Build `calc/descriptive/avg_cph.sh` end to end.**

This is the canonical first calc. The shape:

```bash
#!/usr/bin/env bash
# avg_cph.sh — Average CPH for a facility's operational metrics
#   over an optional date range.
#
# Usage: ./avg_cph.sh <facility_id> [--start YYYY-MM-DD] [--end YYYY-MM-DD]
# Schema: requires v1 operational schema
# Output: single decimal number, 2 decimal places, or "NA"

set -euo pipefail
source "$(dirname "$0")/../lib/_schema_v1.sh"

FACILITY="$1"; shift
FILE="data/metrics/operational/${FACILITY}.csv"
START=""; END=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --start) START="$2"; shift 2 ;;
    --end)   END="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

[[ -f "$FILE" ]] || { echo "No data file for $FACILITY: $FILE" >&2; exit 1; }

awk -F',' -v start="$START" -v end="$END" -v col="$COL_CPH" '
  NR==1 { next }
  $col == "" || $col+0 == 0 { next }
  start != "" && $1 < start { next }
  end   != "" && $1 > end   { next }
  { s += $col; n++ }
  END { if (n>0) printf "%.2f\n", s/n; else print "NA" }
' "$FILE"
```

Write it. Make it executable. Run it against your real data. Confirm the output looks right.

**2.3 Write a golden test for avg_cph.sh.**

In `calc/tests/golden/`, create a small fixed CSV (say 14 rows of known data). Compute the expected average by hand. Save the expected output to `calc/tests/expected/avg_cph_test.txt`. Write a small test runner (`calc/tests/run.sh`) that runs the calc against the golden input and diffs the output against expected.

This is the discipline that will pay off enormously in phases 4-8. Skipping it now means future schema changes silently break calcs.

**2.4 Build the remaining four descriptive calcs.**

`total_units.sh`, `days_below_target.sh`, `worst_day.sh`, `month_summary.sh`. Each one follows the same shape: source the schema, parse args, awk over the file, output a single result (or a small fixed-format block). Each gets a golden test.

**2.5 Write `calc/README.md`.**

Catalog of available calcs with: name, one-line description, usage, schema requirement. This file is what the skills will read to discover what calcs exist.

### Exit criteria

- All 8 facilities have operational metric CSVs with ≥90 days of data
- All 5 descriptive calcs exist, are executable, and pass their golden tests
- Running `calc/descriptive/avg_cph.sh dal-02 --start 2026-02-01 --end 2026-03-01` against real data produces a number that matches a hand-computed average
- `calc/README.md` lists all 5 calcs with usage strings
- A test runner (`calc/tests/run.sh`) executes all golden tests and exits 0 on success

### Common pitfalls

- **Hardcoding column positions.** Every calc must source `_schema_v1.sh`. If you find yourself typing `$4` instead of `$COL_CPH`, stop and fix it. This is the single most important discipline in the calc library.
- **Skipping golden tests because the calc "obviously works."** It works today; in three months when you add a column to the operational schema, you'll need the golden test to tell you which calcs broke.
- **Trying to make calcs handle every edge case at once.** Start simple. Add edge case handling when you hit edge cases. The first version of `avg_cph.sh` doesn't need to handle leap years or timezone conversion.

---

## Phase 3 — Diagnostic calcs and events layer

**Goal:** The diagnostic calc family exists, and the events log infrastructure is in place. You can now ask not just "what is the value" but "why might it be that value."

### Steps

**3.1 Build the events layer infrastructure.**

Create `data/events/MANIFEST.md` with the event taxonomy. Create empty `data/events/{id}.csv` files for each facility (header row only, no data yet).

Skip `data/events/network.csv` for now — defer to phase 7 when you have a real network-wide event to log.

**3.2 Backfill events for the last 90 days.**

Sit down with your calendar, your email archive, and your memory. For each facility, log every event you can remember from the last 90 days that falls in the taxonomy. Don't try to be exhaustive — focus on events you'd want surfaced by `cooccurrence.sh` when investigating a recent signal.

This will probably feel slow and unsatisfying. It is also the single highest-ROI investment for everything downstream. Without backfilled events, the first investigations you run in phase 4 will find nothing in their cooccurrence checks and you won't trust the architecture.

A reasonable target: 5-15 events per facility over the last 90 days. If you can't think of that many, you probably forgot some — talk to operations.

**3.3 Build the four core diagnostic calcs.**

In this order:

1. **`cooccurrence.sh`** — reads `data/events/{id}.csv`, returns events in a date window. Build this first because it's the calc that makes the events layer immediately useful.
2. **`segment_by.sh`** — break a metric down by a dimension (day-of-week, shift, etc.). Useful immediately for any investigation.
3. **`change_drivers.sh`** — rank input variables by change vs baseline. This is the big one for root cause work.
4. **`correlate.sh`** — correlation between two columns. More specialized; build it after the above three.

For now, skip `outlier_days.sh` and `compare_to_baseline.sh` — they're useful but not blocking. Add them when you hit a specific need.

Every one of these gets a golden test, same as the descriptive calcs.

**3.4 Skip building the inputs/exceptions/equipment metric families.**

This is a deliberate departure from the handoff's full architecture. You're staying with operational metrics + events for the first end-to-end investigation. Adding the other three metric families requires phase 0 conversion work plus schema documentation plus updating diagnostic calcs to handle multi-file queries. That's a phase 8 task.

The diagnostic calcs you're building in this phase work against the operational schema only. `change_drivers.sh` will be limited until you have inputs/exceptions data — but it can still rank operational variables (CPH, units, error_rate, hours_run) against each other, which is useful.

### Exit criteria

- `data/events/{id}.csv` exists for all 8 facilities with backfilled events
- At least 5 events per facility over the last 90 days
- 4 diagnostic calcs exist, executable, with golden tests
- `cooccurrence.sh dal-02 2026-03-08 --window 14` returns the events you logged for DAL-02 in that window
- `calc/README.md` updated with the diagnostic calcs

### Common pitfalls

- **Trying to backfill events perfectly.** You'll miss some. That's fine. The events log gets better as you log new events in real-time from phase 4 onward.
- **Building all six diagnostic calcs before testing any of them.** Build one. Use it on a real question. Adjust if needed. Then build the next.
- **Skipping events backfill because it's tedious.** This is the single most common failure mode for systems like this. Without backfilled events, the cooccurrence calc returns nothing, you stop trusting it, and the architecture loses its core "why" capability.

---

## Phase 4 — signal-detect and investigate skills, one playbook

**Goal:** You can produce a real floor brief for a real signal at one of your facilities. The system is starting to do CI work.

This is the first phase where you stop building infrastructure and start building things that will be used. By the end, the architecture is functionally usable for one signal type.

### Steps

**4.1 Create the `signal-detect` skill.**

Use `.skills/.meta/create_skill.py` to scaffold the skill folder. Then write the body of `signal-detect/SKILL.md` following the SKILL.md shape shown in section 11.1 of the handoff (the close-loop example is the most fully-illustrated, but the structure applies to all four skills). The description gates loading on "what should I look at today" style queries. The body describes the scan procedure laid out in handoff section 3 (Path A).

For this phase, signal-detect only scans for new signals — it doesn't yet check `investigations/open/` (none exist yet) or `follow_ups/INDEX.md` (none exist yet). That's fine. The skill grows in phases 5 and 6 to add those scans.

After writing the body, run `.skills/.meta/reconcile.py` to confirm the manifest reflects the new skill's description.

**4.2 Create the `investigate` skill.**

Same approach. Scaffold via `create_skill.py`, then write the body. Description gates on investigation-style queries. Body describes the investigation flow. Anti-patterns section explicit.

Reconcile afterwards.

**4.3 Write your first playbook: `throughput_drop.md`.**

This is the playbook you'll run first because throughput drops are the most common warehouse signal and the one you have strongest intuition about. The playbook is a procedure file: when to use, prerequisites, ordered diagnostic steps, hypothesis-generation guidance, common floor questions, common mistakes.

Don't try to make the playbook exhaustive. Make it the playbook you'd give to a smart but inexperienced analyst — the steps they should run in order, the questions they should ask, the things they should check before drawing conclusions. The playbook will get better through use.

**4.4 Write the `brief_template.md`.**

Use section 13 of the handoff. This is the artifact the investigate skill produces at the end of every investigation.

**4.5 Run your first real investigation.**

Pick a real signal from your last 30 days — a facility where CPH was notably below target, or units dropped, or whatever a throughput-drop pattern looks like in your operation.

Walk through the investigation with the assistant using the investigate skill. Run the diagnostic calcs the playbook specifies. Draft the brief. Critically examine it. Then go to the floor and have the conversation the brief was designed to enable.

You're not yet using close-loop (that's phase 5). For now, just walk through the front half of the loop and see what you learn.

**4.6 Refine the playbook based on what you learned.**

Almost certainly, your first investigation will surface things missing from the playbook. Maybe the order of diagnostic calcs was wrong. Maybe a floor question you ended up asking wasn't in the standard list. Maybe one of the hypotheses the brief generated was obviously wrong in a way the playbook should help avoid.

Update the playbook. Don't update it perfectly — update it for the next time you'll use it.

**4.7 Run 4-9 more investigations through the playbook.**

Different facilities, different time periods, similar signal type. Each investigation refines the playbook. By investigation 5, the playbook should feel stable. By investigation 10, you're ready for phase 5.

You can save these investigations to `data/investigations/open/` for now since you don't have close-loop yet. They'll move to YYYY-Qn folders once the loop closes in phase 5.

### Exit criteria

- `signal-detect` and `investigate` skills both exist on disk with valid frontmatter
- Both skills are registered in `.skills/MANIFEST.yaml` (verify with reconcile)
- Both trigger appropriately when tested with sample user prompts
- `throughput_drop.md` playbook exists and has been refined through use
- `brief_template.md` exists and produces consistently-shaped briefs
- At least 5 real investigations have been run end-to-end, producing briefs that you'd be willing to take to the floor
- Each brief has reproducible methodology (every number traces to a calc invocation)

### Common pitfalls

- **Trying to write the playbook perfectly before using it.** The playbook gets better through use, not through pre-thought. Write a draft, use it, revise it. Five iterations of revision through real use beats unlimited time spent on the first draft.
- **Running investigations without saving them.** If you run investigations in your head or in throwaway conversations, you can't refine the playbook or build pattern history. Every investigation goes into `investigations/open/` as a file.
- **Asking the floor different questions than the brief specifies.** The brief is also a tool for you to be disciplined. If you find yourself asking floor questions the brief didn't suggest, that's fine — but write them into the playbook so next time they're there from the start.
- **Skipping reconcile after writing a skill body.** If the manifest doesn't update, the skill exists on disk but is invisible to fresh assistant sessions that only read the manifest. Make reconcile a reflex after any skill edit.

---

## Phase 5 — close-loop, first A3/Kaizen, outcome calcs

**Goal:** The loop closes. Floor findings come back into the system, generate structured A3s/Kaizens, and outcome tracking gets scheduled.

This phase converts the architecture from "produces briefs" to "produces and tracks improvements." It's where the system stops looking like a reporting tool and starts looking like a CI system.

### Steps

**5.1 Build the outcome calc family.**

Three calcs: `follow_up_check.sh`, `countermeasure_effectiveness.sh`, `intervention_attribution.sh`. Same discipline as before: source the schema, parse args, deterministic output, golden test. The handoff section 9.4 has the example invocations.

`follow_up_check.sh` is the most important — it's what makes signal-detect able to surface due follow-ups automatically. Build it first.

**5.2 Create the `close-loop` skill.**

Scaffold via `create_skill.py`, then write the body following section 11.1 of the handoff. The description carefully excludes the other three skills' triggers.

Reconcile afterwards.

**5.3 Write the three intake templates.**

`intake_template.md` (full intake, the workhorse), `quick_close_template.md` (non-events), `reopen_template.md` (brief was wrong). The full intake template is the most important; sections 11.2 and 11.3 of the handoff have the shape and a filled-in example.

**5.4 Write the close-loop procedures.**

Six procedure files: `log_floor_findings.md`, `open_a3.md`, `open_kaizen.md`, `close_a3.md`, `close_kaizen.md`, `reopen_investigation.md`. Each one is a procedure-shaped recipe (When to use, Prerequisites, Steps, Verification, Common mistakes).

The most important ones to nail are `open_a3.md` and `open_kaizen.md`, because they're the ones that link the artifact back to the source investigation and schedule follow-ups. Spend the time to make those procedures explicit about the verification step.

**5.5 Write the A3 and Kaizen templates.**

`maintain/templates/a3.md` and `maintain/templates/kaizen.md`. Use the shapes from sections 12.1 and 12.2 of the handoff.

**5.6 Run the close-loop on one of your phase-4 investigations.**

Pick the investigation from phase 4 where you had the strongest floor finding. Run it through close-loop:

- Walk the intake template conversationally with the assistant
- Decide disposition (open A3, open Kaizen, or both)
- Generate the A3 and/or Kaizen via the procedures
- Schedule follow-ups in `follow_ups/INDEX.md`

You'll almost certainly find that the intake template needs adjustment after the first real walk-through. Adjust it.

**5.7 Run the close-loop on 2-4 more investigations.**

Each one tests a different disposition path (close, A3 only, Kaizen only, both, re-open). By the end, every disposition path has been exercised at least once and the procedures have been refined.

**5.8 Update signal-detect to include open investigations and due follow-ups.**

Now that you have open investigations and follow-ups scheduled, signal-detect's scan can include them. Update its `SKILL.md` to do the three-part scan described in the handoff section 3 (Path A).

Reconcile after editing — the description may not change but the content hash will, and the manifest needs to track that.

### Exit criteria

- 3 outcome calcs exist with golden tests
- `close-loop` skill exists with all three intake templates and is registered in the manifest
- 6 close-loop procedures exist
- A3 and Kaizen templates exist
- At least 3 investigations have been closed via the loop, generating at least 1 A3 and 2 Kaizens (or similar mix)
- `follow_ups/INDEX.md` has scheduled follow-ups
- signal-detect now surfaces three categories: new signals, open investigations, due follow-ups
- The first follow-up date has either arrived (and been surfaced) or is scheduled in a verifiable place

### Common pitfalls

- **Walking the intake as a form to fill out, not a conversation.** The intake template is the structure; the user experience is conversation. If close-loop reads the intake like a form, the user will fill it out lazily and the diagnostic value evaporates. Test the conversational walk early and adjust the skill.
- **Opening A3s/Kaizens without scheduling follow-ups.** This is the single most common quiet failure of CI systems. The procedures should refuse to save the A3 or Kaizen until a follow-up is scheduled. Build that gate.
- **Skipping the events log update from the intake.** Floor visits produce events the system doesn't otherwise capture. If close-loop doesn't actively prompt to log these, the events layer grows slowly and the cooccurrence calc stays sparse.

---

## Phase 6 — Pattern emergence and maintain skill

**Goal:** The system starts to compound. Recurring causal shapes get abstracted into patterns. The maintain skill exists so you can add new patterns, calcs, and playbooks without improvising the edits.

### Steps

**6.1 Look for patterns in your phase-4 and phase-5 investigations.**

You should now have 8-15 investigations completed (5+ from phase 4, 3-5 closed in phase 5). Read through them. Look for recurring causal shapes.

A pattern exists when 3+ investigations had the same underlying mechanism. New-hire cohorts causing throughput dips. Equipment-aging causing damage spikes. Cross-shift handoff failures causing missort spikes. Whatever recurs in *your* operation.

You may find zero patterns yet. That's fine; it just means the threshold hasn't been reached. More investigations needed.

You may find 2-3 emerging patterns. That's typical.

**6.2 Write the first pattern file.**

Use the shape from handoff section 10.2. Include:
- Signal shape (what triggers a match)
- Typical co-occurring events
- Investigation steps to run when the pattern is suspected
- Floor questions when the pattern is suspected
- Expected resolution timeline
- Countermeasures that have worked (from your closed A3s/Kaizens)
- Countermeasures that didn't work
- Historical instances (links to investigations)

The countermeasures sections are what make patterns valuable beyond just "this signal recurs." They're the institutional memory of what to actually do.

**6.3 Write `patterns/INDEX.md`.**

Simple catalog of pattern files. Updated whenever a new pattern is added.

**6.4 Update the throughput-drop playbook to include a pattern check.**

The playbook should now, as one of its early steps, check `patterns/INDEX.md` to see if any pattern matches the current signal. If yes, the brief surfaces the pattern's hypotheses and countermeasures as a starting point.

**6.5 Create the `maintain` skill and its procedures.**

You've been doing maintain-skill work manually so far (editing the architecture as needed). Now formalize it. Scaffold via `create_skill.py`, write the body, then reconcile.

Priority order for the procedures:
1. `add_pattern.md` and `update_pattern.md` — you'll use these immediately
2. `add_calc.md` — you'll use this every time you build a new calc
3. `add_playbook.md` — you'll use this when you start phase 8
4. `add_event_type.md`, `update_aliases.md`, `bump_schema.md`, `deprecate_facility.md`, `add_facility.md` — less frequently used; write them when you have the first real need

**6.6 Write the maintain templates.**

`facility_profile.md`, `calc.sh`, `playbook.md`, `pattern.md`, `investigation_log.md`. These are the skeletons that procedures reference. Most of them you've already created informally — formalize them now.

### Exit criteria

- At least 1 pattern file exists, with the countermeasures section populated from your closed A3s/Kaizens
- `patterns/INDEX.md` exists
- `throughput_drop.md` playbook now checks the pattern library before drafting hypotheses
- `maintain` skill exists with at least 3 procedures (`add_pattern`, `update_pattern`, `add_calc`) and is registered in the manifest
- Maintain templates exist for all the file types you've actively been creating

### Common pitfalls

- **Writing patterns prematurely.** A pattern with one historical instance isn't a pattern; it's a single investigation. Wait until you have 3+ similar cases. Otherwise you're just abstracting from insufficient data.
- **Updating patterns without using the procedure.** Once `update_pattern.md` exists, use it. Ad-hoc pattern edits accumulate inconsistencies that the procedure was designed to prevent.

---

## Phase 7 — Threshold checkpoint

**Goal:** Stop and assess. The system is now functionally complete for one signal type, with the loop closing and patterns emerging. You can stop here and use it indefinitely.

This isn't really a build phase — it's a deliberate pause to evaluate.

### Steps

**7.1 Confirm the working slice.**

Run the verification queries from handoff section 16 against your real system. Specifically:
- A fresh assistant session opens, reads `.skills/README.md`, scans the manifest, and routes correctly to the first user query
- "What should I look at today?" returns the three-section signal-detect output
- "Investigate {facility}'s {signal}" produces a real brief with reproducible methodology
- "Closing out the investigation" walks you through the intake conversationally
- A scheduled follow-up surfaces automatically when its date arrives
- The pattern library has at least one entry with countermeasures
- Reconcile detects drift when a `SKILL.md` is edited directly

If all of these work, you have a real working CI system. If any fail, fix that layer before continuing.

**7.2 Reflect on what you've actually built.**

You should have at this point:
- 8 facility profiles, INDEX.md, peer pairings
- 1 metric family fully populated, schema documented
- Events log with ~90 days of backfilled events
- 5 descriptive calcs, 4 diagnostic calcs, 3 outcome calcs (12 total) with golden tests
- 1 working playbook
- All 4 skills (signal-detect, investigate, close-loop, maintain) functional and registered in the manifest
- 8-15 investigations completed, 3-5 closed via the loop
- 1-3 A3s, 2-5 Kaizens, several with follow-up checks executed
- 1-2 patterns with countermeasures populated
- Skills protocol infrastructure (README, MANIFEST, reconcile, create_skill) operating cleanly

This is enough to run continuous improvement work at 8 facilities for one signal type indefinitely. The system delivers value as-is. Phase 8 expansions are useful but not required.

**7.3 Decide whether to continue.**

Two valid choices:

- **Stop here and use it.** Run the system for 2-3 months. Let the investigation history compound. Let patterns refine. Don't add new playbooks or metric families until you feel a specific need. This is the highest-quality choice if your goal is to actually do CI work rather than build CI infrastructure.

- **Continue to phase 8.** Add more playbooks, more metric families, comparative calcs. This is the right choice if you've hit specific limitations during phase 4-6 that you know will recur.

The honest answer for most builders in your context is: stop here, run it for a month, then decide based on what limitations actually bite.

---

## Phase 8 — Expansion (optional, demand-driven)

**Goal:** Address specific limitations identified during real use.

This phase is not a single sequence — it's a menu of expansions, prioritized by what you actually need. Pick the one that addresses your most-pressing limitation; build it; pause; repeat.

### Possible expansions

**8.1 Additional playbooks** (highest typical priority)

Each new playbook follows the same shape as `throughput_drop.md`: when to use, prerequisites, diagnostic steps, hypothesis guidance, floor questions, common mistakes. Use the maintain skill's `add_playbook.md` procedure.

Priority order based on warehouse CI experience:
1. `error_spike.md` — error rate or category up
2. `headcount_efficiency_decline.md` — units/FTE falling
3. `slow_drift.md` — gradual degradation
4. `peer_divergence.md` — one facility falling behind operational peers

For each new playbook, run 3-5 real investigations through it before considering it stable.

**8.2 Additional metric families**

If your investigations are repeatedly hitting "we don't have the data for that" walls, add the missing metric families. Each new family is a phase-0-like effort: build conversion scripts, document the schema, populate the CSVs, update diagnostic calcs to work with the new family.

Priority order:
1. **Exceptions** — usually the most valuable next family because categorized failures are central to root cause work
2. **Equipment** — useful for facilities with significant MHE or conveyor systems
3. **Inputs** — most valuable but also the messiest data (HR/payroll source); save for last

**8.3 Comparative calc family**

If you find yourself wanting to rank facilities, benchmark against peers, or run divergence analysis, build out `calc/comparative/`. Three calcs: `rank_facilities.sh`, `peer_benchmark.sh`, `divergence_analysis.sh`. Same discipline.

These are most valuable once you have data for multiple metric families, because the most useful comparisons are multi-variable.

**8.4 Network events file**

When you have a real network-wide event to log (a corporate WMS rollout, a policy change), create `data/events/network.csv`. Update `cooccurrence.sh` to read it in addition to the per-facility file.

**8.5 Remaining diagnostic calcs**

`outlier_days.sh` and `compare_to_baseline.sh` — useful but not blocking. Add them when you hit specific needs.

**8.6 Investigation deep-dive subagent**

If you find yourself hitting context limits in main-thread investigations (rare at 8 facilities; more common at 25+), add a subagent or auxiliary helper using whatever subagent or multi-agent convention your host runtime supports. The architecture doesn't depend on any particular subagent mechanism — the request is just "delegate deep investigative work to a separate context so the main thread doesn't fill up." Until you actually feel the context limit bite, don't bother.

### Anti-priorities (do not build until forced)

- **Manufacturing parallel root** — only when manufacturing data enters scope
- **Real-time monitoring layer** — only when daily granularity is provably insufficient
- **Tier-2 escalation pipeline** — only when A3s start needing cross-functional review
- **Standard-work documentation folder** — only when Kaizens start producing permanent SOP changes regularly

These are all in the handoff's section 15 (Future scope). They are valid extensions but they are *speculative* at your current scale and shouldn't be pre-built.

---

## Risk register

Things most likely to go wrong, ranked by likelihood × impact.

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Schema needs revision after phase 4 first investigation | HIGH | MEDIUM | Schema version is in the manifest; bumping to v2 is supported. Don't fight the revision; expect it. |
| Events backfill is incomplete; cooccurrence returns nothing useful for first investigations | HIGH | HIGH | Don't skimp on phase 3. If first investigations are eventless, stop and backfill more before continuing. |
| Conversion scripts break when source files are touched by humans | HIGH | MEDIUM | Build validation into the conversion scripts. When they fail, the script aborts loudly and doesn't write corrupted output; fix the script promptly rather than working around. Logs in `conversion/logs/` make the failure obvious. |
| Conversion validators get loosened over time to make a stubborn source pass | MEDIUM | HIGH | This is the most dangerous slow corruption mode. Validator changes deserve the same scrutiny as schema changes. When tempted, fix the source or the script instead. The conversion MANIFEST documents which validators every script invokes; weakening shows up in diffs. |
| Conversion MANIFEST drifts from reality after months of small changes | MEDIUM | MEDIUM | Update the MANIFEST in the same commit that adds or changes a conversion script. Quarterly audit: confirm every script in `conversion/scripts/` is listed in the MANIFEST, and every MANIFEST entry has a corresponding script. |
| Skills manifest drifts from on-disk `SKILL.md` files | MEDIUM | MEDIUM | Run `.skills/.meta/reconcile.py` after any direct skill edit. Content hashes in the manifest let reconcile detect drift quickly. The scaffolder runs reconcile automatically, so drift only enters when skills are edited by hand — make it a reflex. |
| Playbook drift — early investigations look different from later ones because the playbook evolved | MEDIUM | LOW | Acceptable; the investigation files capture the methodology used at the time. Old investigations remain valid historical record. |
| Intake fatigue — closing the loop feels onerous after the first 3-5 | MEDIUM | HIGH | The conversational walk via close-loop is meant to reduce this. If it still feels heavy, the template needs simplification, not the discipline reducing. |
| Pattern threshold never reached because investigations are too varied | LOW | MEDIUM | Patterns emerge from recurring causes, not from total investigation count. If your operations are stable enough to have recurring issues, patterns will emerge by investigation 15-20. |
| Building the architecture becomes more interesting than using it | MEDIUM | HIGH | This is the single biggest solo-builder failure mode. The phase 7 checkpoint exists specifically to surface this. If you've reached phase 7 and want to keep building rather than using, ask why. |
| Follow-up dates pass without surfacing because signal-detect isn't run regularly | MEDIUM | HIGH | Make signal-detect a daily habit. The follow_up_check.sh calc can also be run on-demand to catch up. Don't let follow-ups become invisible. |
| A schema change in operational data sources breaks every calc silently | LOW | HIGH | Golden tests catch this if run regularly. Run the calc test runner weekly at minimum. |
| Inputs metric family schema turns out wrong because HR data is messier than expected | MEDIUM | LOW (deferred) | Phase 8.2 handles this. Don't try to anticipate the right shape of inputs schema until you actually have the data in hand. |
| A different assistant or model is introduced and operates the system incorrectly | LOW | MEDIUM | `.skills/README.md` is the protocol contract. Any reasonably capable model that reads it should operate correctly. If the model can't read project files at all, the operator pastes README and MANIFEST in directly at session start. |

---

## When to revise this plan

This plan was drafted before you've started building. After phase 4 — your first real investigations — you'll know more about your operation than the plan does. Specifically:

- Whether the throughput_drop playbook is your right starting point or whether a different signal type is more common
- Whether your schema needs adjustment for variables you didn't anticipate
- Whether your conversion scripts are stable enough to trust weekly, or whether they need attention more often
- Whether the intake template captures what you actually bring back from the floor

Revise the plan at the phase 4 boundary, not before. Trying to anticipate these revisions now wastes time. Reacting to them then is the right discipline.

---

## Pragmatic notes for solo work

A few things that matter specifically because you're building this alone:

**Set a minimum work session size.** Solo builds die from context loss between sessions. A 30-minute session loses 10 minutes to remembering where you were. A 90-minute session loses the same 10 minutes but gets 80 minutes of work done. Aim for 90+ minute blocks.

**Keep a build journal.** A simple `notes/build_log.md` that you append to at the end of each session: what you did, what's next, what you noticed. Future-you will thank present-you. (The tracker's working log serves the same purpose at the build-state level; the build journal is for personal notes that don't belong in a shared tracker.)

**Don't try to do this during peak workload.** The plan is open-ended for a reason. CI managers have unpredictable weeks. Some weeks you build; some weeks you do CI work. Both are progress.

**Use the system before it's "ready."** From phase 4 onward, the system can be used for real work even though the architecture is incomplete. Use it. The friction of real use is what tells you what to build next.

**Resist the urge to make it pretty.** Markdown files don't need styling. CSVs don't need explanatory comments. The system's value is in its discipline and reproducibility, not its aesthetics. Solo builders waste enormous time on polish that doesn't change the value delivered.

**Plan for 6-12 months to phase 7 if doing this alongside normal work.** This is realistic, not pessimistic. The architecture is robust; the build is steady. At quality-over-speed and open-ended timeline, that's the natural pace.

**Don't lock yourself into one assistant.** The architecture is designed to work with any reasonably capable model. If your employer changes which model you're allowed to use, the build does not need to restart. The protocol in `.skills/README.md` is the contract that makes this true — keep it well-maintained.

---

## What this plan deliberately does not do

To be explicit about what's missing and why:

- **No time estimates per task.** Solo open-ended timelines invalidate estimates. The plan is sequenced and gated, not scheduled.
- **No detailed pseudocode for every calc.** The handoff has example calcs; this plan only specifies which calcs to build in which order. You'll write them.
- **No discussion of version control or backup strategy.** Use git. Push regularly. Use whatever cloud sync you already use for your CI work. The plan doesn't dictate this.
- **No prescription for which conversion tool to use.** Python is the obvious choice for xlsx handling; awk works fine for CSV cleanup. Use what you're comfortable with.
- **No prescription for which model or assistant to use.** The architecture is model-agnostic by design. Use what's available; switch when you have to. The skills protocol survives the switch.
- **No exhaustive failure recovery procedures.** If you break something, the architecture is plain text and the data is plain CSV. Restore from git. Move on.

The plan trusts you to handle the things that aren't specific to this architecture. Its job is to keep you from getting lost in the things that are.
