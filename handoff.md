# Operations Investigation Architecture — Handoff

> ## ⚠️ PLACEHOLDER DATA NOTICE
>
> **All facility IDs, schema fields, calc names, playbook names, pattern names, intake examples, A3/Kaizen contents, dates, and operational details in this document are illustrative examples — not real data.** They exist to show the *shape* of each file, not its contents.
>
> Before this architecture is used in production, substitute the following with values from the real environment:
>
> - **Facility IDs, names, regions, types** — actual operations naming
> - **Schema columns across all four metric families** — the actual columns your data pipeline outputs
> - **Event taxonomy** — real categories of changes your operations track
> - **Calc script names, signatures, logic** — calcs that compute what your operation actually measures
> - **Playbook contents** — examples show structure; real playbooks reflect your actual investigation workflows
> - **Pattern files** — patterns emerge from real investigations, not theoretical ones
> - **Intake examples** — the DAL-02 example is illustrative; real intakes come from real floor visits
> - **A3 and Kaizen templates** — examples show shape; real artifacts reflect your operation's A3/Kaizen conventions
> - **Targets, thresholds, peer pairings, SOP references** — real operational values
> - **Column positions in `_schema_v1.sh`** — must match real schema after substitution
>
> Treat every code block, table, and inline example as a template. The *structure* is the deliverable; the *values* are scaffolding.

---

**Audience:** Fresh assistant session with no prior conversation state
**Status:** Architecture specified; current scale 8 facilities across 3 states; designed to scale without restructure
**Designed for:** A continuous improvement manager who needs the system to crunch numbers so human time can go to the shop floor — and who needs the floor's findings to flow back into structured CI artifacts
**Designed to be:** Model-agnostic. Any reasonably capable assistant with filesystem access should be able to operate this architecture by reading `.skills/README.md` first and following the protocol it describes.

---

## TL;DR

You are picking up an **eight-layer** system designed to take a CI manager from "I see a signal" through "here is the floor brief" to "here is the A3 or Kaizen, here is whether it worked, here is what we learned" — without the manager personally crunching numbers, drafting structured documents from scratch, or remembering to follow up.

The eight layers:

1. **Skill descriptions** — gate which skill loads (signal-detect, investigate, close-loop, or maintain)
2. **Facility directory** — flat index with state, type, and peer pairings
3. **Manifest layer** — five manifests (metrics, events, investigations, patterns, A3s/Kaizens), each a contract
4. **Metrics layer** — four sub-schemas per facility: operational, inputs, exceptions, equipment
5. **Events layer** — per-facility and network-wide event logs for context correlation
6. **Calc library** — descriptive, diagnostic, comparative, and outcome calcs, all deterministic
7. **Investigation + pattern history** — every completed investigation feeds institutional memory
8. **A3s + Kaizens + closed loop** — structured improvement artifacts generated from floor intake, tracked through follow-up, feeding pattern learning

**Four skills route the work:**
- `signal-detect` — proactive scan, surfaces what needs attention today (new signals + open investigations + due follow-ups)
- `investigate` — runs a playbook end-to-end against a specific signal, produces a floor brief
- `close-loop` — captures structured findings from floor visits, generates A3s/Kaizens, schedules follow-ups
- `maintain` — edits the architecture (facilities, calcs, events taxonomy, playbooks, patterns, A3 conventions)

**If you only remember four things:**
1. Floor briefs are the *handoff* to the floor; A3s and Kaizens are the *deliverable* of CI work. The architecture's purpose is to produce both consistently and reproducibly.
2. Every analytical number — descriptive, diagnostic, comparative, or outcome — comes from a named calc invocation. No improvised math anywhere in the system.
3. Structured floor intake is the input that makes the loop close. Free-text "yeah it was the cohort thing" loses the diagnostic value; structured per-hypothesis intake feeds calibration of every other layer.
4. Outcome tracking happens automatically. The follow-up checks run themselves through signal-detect. Honest CI work becomes the path of least resistance because the architecture won't let you skip it.

---

## How an unfamiliar assistant should orient

This architecture is built so any reasonably capable assistant with filesystem access can operate it. The orientation sequence:

1. **Read `tracking.md` first.** It tells you what phase of the build is active and what the next concrete action is. Trust the status header.
2. **Read `.skills/README.md` next.** It explains how the skills system works: how to read the manifest, when to load a specific `SKILL.md`, what NOT to do. This is the protocol contract.
3. **Read `.skills/MANIFEST.yaml` next.** It is the registry of available skills with their descriptions. Match the user's request to a description before loading any skill body.
4. **Load only the skill that matches.** Read its `SKILL.md` in full. Do not preemptively read other skills' files.
5. **Use this document for architectural reference.** It is the specification of what the system is — not the to-do list, not the protocol. Pull from it when you need to understand a layer, a contract, or a flow that you encounter during operation.

If filesystem access is not available in the current session, the operator should paste the relevant files in directly. The architecture does not rely on any model-specific feature beyond ordinary file reading and instruction-following.

---

## 1. Goal and non-goals

### Goal
Make a CI manager 3-5x more leveraged. Replace time spent crunching rework numbers with time spent on the floor talking to associates and drafting solutions. Produce defensible, reproducible, hypothesis-driven floor briefs *and* the structured A3s/Kaizens that follow, *and* track whether those interventions actually worked. Preserve the human's role in confirmation, judgment, and corrective action; eliminate the human's role in number-crunching, follow-up reminders, and document-formatting.

### Non-goals
- Not a database or BI tool. Markdown + CSV + bash. Built for AI-driven access, not human dashboard browsing.
- Not a replacement for floor judgment. The architecture surfaces hypotheses and structures the findings; the floor confirms or rules them out.
- Not an automation system. It produces briefs, A3s, Kaizens, and follow-up surfacing — not actions on equipment or people.
- Not for real-time monitoring. Daily granularity, weekly data drops. Real-time is a different problem.
- Does not enforce A3/Kaizen review processes. Whoever your operation has reviewing A3s reviews these the same way; the architecture just produces the artifacts.
- Not a build-state tracker. This document specifies *what* the architecture is when complete. Tracking *what has been built so far* — current phase, completed steps, decisions, deviations — lives in a separate file: `tracking.md`. A fresh assistant session picking up the work should read `tracking.md` first to orient, then return to this document for architectural reference.
- Not tied to any specific assistant or model. The skills protocol is documented in `.skills/README.md` so any capable model can operate the system. Model-specific features are not relied upon.

### Currently in scope
Eight facilities across three states. One CI manager (you) as primary user. Warehouse operations only.

### Designed to scale to
~100 facilities, multiple regions with parallel CI managers, parallel domains (manufacturing, last-mile, returns). Expansions are additive — new files, not restructuring (see section 14).

---

## 2. File layout

```
project-root/
├── .skills/
│   ├── README.md                       # Protocol explainer — read this first
│   ├── MANIFEST.yaml                   # Registry of available skills
│   ├── .meta/
│   │   ├── reconcile.py                # Sync manifest with on-disk SKILL.md files
│   │   └── create_skill.py             # Scaffold a new skill
│   ├── signal-detect/                  # Proactive daily scan
│   │   └── SKILL.md
│   ├── investigate/                    # The deep work
│   │   ├── SKILL.md
│   │   ├── playbooks/
│   │   │   ├── throughput_drop.md
│   │   │   ├── error_spike.md
│   │   │   ├── headcount_efficiency_decline.md
│   │   │   ├── peer_divergence.md
│   │   │   └── slow_drift.md
│   │   └── brief_template.md
│   ├── close-loop/                     # Floor intake + artifact generation
│   │   ├── SKILL.md
│   │   ├── intake_template.md          # Full intake form
│   │   ├── quick_close_template.md     # Short variant for non-event closes
│   │   ├── reopen_template.md          # Variant when brief was wrong
│   │   └── procedures/
│   │       ├── log_floor_findings.md
│   │       ├── open_a3.md
│   │       ├── open_kaizen.md
│   │       ├── close_a3.md
│   │       ├── close_kaizen.md
│   │       └── reopen_investigation.md
│   └── maintain/                       # Architecture edits
│       ├── SKILL.md
│       ├── procedures/
│       │   ├── add_facility.md
│       │   ├── add_calc.md
│       │   ├── add_playbook.md
│       │   ├── add_event_type.md
│       │   ├── add_pattern.md
│       │   ├── update_pattern.md
│       │   ├── update_aliases.md
│       │   ├── bump_schema.md
│       │   └── deprecate_facility.md
│       └── templates/
│           ├── facility_profile.md
│           ├── calc.sh
│           ├── playbook.md
│           ├── pattern.md
│           ├── investigation_log.md
│           ├── a3.md
│           └── kaizen.md
│
├── data/
│   ├── facilities/
│   │   ├── INDEX.md
│   │   └── profiles/{id}.md
│   │
│   ├── metrics/
│   │   ├── MANIFEST.md
│   │   ├── operational/{id}.csv
│   │   ├── inputs/{id}.csv
│   │   ├── exceptions/{id}.csv
│   │   ├── equipment/{id}.csv
│   │   └── archive/{year}/
│   │
│   ├── events/
│   │   ├── MANIFEST.md
│   │   ├── {id}.csv
│   │   └── network.csv
│   │
│   ├── investigations/
│   │   ├── INDEX.md
│   │   ├── YYYY-Qn/{date}_{facility}_{signal}.md
│   │   └── open/                       # In-progress, with state field
│   │
│   ├── patterns/
│   │   ├── INDEX.md
│   │   └── {pattern_name}.md
│   │
│   ├── a3s/
│   │   ├── INDEX.md
│   │   ├── open/
│   │   │   └── {a3_id}.md
│   │   └── closed/
│   │       └── YYYY-Qn/{a3_id}.md
│   │
│   ├── kaizens/
│   │   ├── INDEX.md
│   │   ├── open/
│   │   │   └── {kaizen_id}.md
│   │   └── closed/
│   │       └── YYYY-Qn/{kaizen_id}.md
│   │
│   └── follow_ups/
│       └── INDEX.md                    # Calendar of pending outcome checks
│
├── conversion/                         # Bridges raw source data to canonical CSVs
│   ├── MANIFEST.md                     # Source-to-target mapping + validation contract
│   ├── README.md                       # How to run conversions, cadence, failure modes
│   ├── scripts/
│   │   └── extract_{source}.{py,sh}    # One script per source file
│   ├── validation/
│   │   └── common.{py,sh}              # Shared validation routines
│   └── logs/
│       └── {date}_{script}.log         # Validation results from each run
│
└── calc/
    ├── README.md
    ├── lib/
    │   ├── common.sh
    │   └── _schema_v1.sh
    ├── descriptive/
    │   ├── avg_cph.sh
    │   ├── total_units.sh
    │   ├── days_below_target.sh
    │   ├── worst_day.sh
    │   └── month_summary.sh
    ├── diagnostic/
    │   ├── correlate.sh
    │   ├── segment_by.sh
    │   ├── change_drivers.sh
    │   ├── cooccurrence.sh
    │   ├── outlier_days.sh
    │   └── compare_to_baseline.sh
    ├── comparative/
    │   ├── rank_facilities.sh
    │   ├── peer_benchmark.sh
    │   └── divergence_analysis.sh
    ├── outcome/
    │   ├── follow_up_check.sh          # Did the metric hit the target by the date?
    │   ├── countermeasure_effectiveness.sh  # Before/after comparison
    │   └── intervention_attribution.sh # Distinguish intervention from noise
    └── tests/
        ├── golden/
        └── expected/
```

### About the `.skills/` directory

Three files at the root of `.skills/` define the protocol contract:

- **`README.md`** is the explainer. An assistant session entering this directory for the first time reads this to learn how the system works: how to scan the manifest, when to load a specific `SKILL.md`, what NOT to do. This is what makes the system operable by an unfamiliar model.
- **`MANIFEST.yaml`** is the registry. It lists every skill with its name, description, trigger keywords, path to `SKILL.md`, and a content hash. An assistant reads this once at session start and uses it to decide which skill (if any) matches the user's request.
- **`.meta/`** holds the tooling that operates *on* the skills system. `reconcile.py` walks the tree and synchronizes the manifest with on-disk `SKILL.md` files (catching drift, adding new skills, flagging removals). `create_skill.py` scaffolds new skills with the right structure and updates the manifest. Neither is itself a skill — both are infrastructure.

The `.meta/` directory is dot-prefixed to make it clear it is not a skill. Tree walks performed by `reconcile.py` ignore anything starting with a dot.

A previously deferred subagent capability (an investigation deep-dive helper) is intentionally not included in this layout. It can be added under whatever subagent convention your host runtime uses if you adopt one; for now, the four-skill model handles all current work.

---

## 3. Resolution flows

The architecture has **four** distinct paths, gated by which skill description matches. Only one skill loads per conversation. The match is performed against `.skills/MANIFEST.yaml`; the assistant reads only the matching skill's `SKILL.md`.

### Path A — Daily signal scan (signal-detect)

Surfaces three categories of things needing attention.

```
User asks "what should I look at today?" / "anything to follow up?"
   ↓
signal-detect description matches → skill loads
   ↓
Read facilities/INDEX.md (full network in scope)
   ↓
Read metrics/MANIFEST.md to confirm schema + freshness
   ↓
Three parallel scans:
   1. Threshold scans across operational metrics → new signals
   2. Read investigations/open/ → in-progress investigations needing
      attention (drafted but not yet on floor, floor_pending but no
      intake recorded yet, etc.)
   3. Read follow_ups/INDEX.md → due outcome checks; run
      outcome/follow_up_check.sh for each
   ↓
Return three ranked sections:
   - NEW: signals worth investigating
   - OPEN: investigations needing your next step
   - DUE: A3/Kaizen follow-ups (did the intervention work?)
```

### Path B — Investigation (investigate)

The investigation file has an explicit `state` field set to `drafted` when the brief is produced. The file is saved to `investigations/open/` until the loop closes.

```
User asks "investigate X" / picks from signal-detect output
   ↓
investigate description matches → skill loads
   ↓
Pin down the signal: facility, metric, time window, magnitude
   ↓
Pick playbook, read in full
   ↓
Run diagnostic calcs in playbook order
   ↓
Check investigations/INDEX.md + patterns/INDEX.md for matches
   ↓
Draft hypotheses ranked by evidence weight
   ↓
Produce floor brief from brief_template.md
   ↓
Save to investigations/open/{date}_{facility}_{signal}.md with state=drafted
   Update investigations/INDEX.md
```

### Path C — Close the loop (close-loop)

```
User returns from floor: "closing out the DAL-02 investigation"
   ↓
close-loop description matches → skill loads
   ↓
Identify which investigation by ID or facility+date
   ↓
Read the open investigation file in full
   ↓
Conversationally walk through the intake template field by field:
   - Hypothesis disposition (per hypothesis from brief)
   - What the data missed
   - Surprises
   - New questions raised
   - Floor-attributed observations to log
   - Disposition (close / Kaizen / A3 / re-open / escalate)
   - Pattern feedback (confirms, refutes, extensions)
   - Follow-up commitments
   ↓
Append filled intake to the investigation file
Set investigation state based on disposition:
   - confirmed → state=confirmed, then kaizen_open or a3_open via procedure
   - close → state=resolved, move to investigations/YYYY-Qn/
   - re-open → state=superseded; new investigation drafted with `supersedes` reference
   ↓
If disposition includes "open A3":
   → procedures/open_a3.md → creates a3s/open/{a3_id}.md from template
     with current state, root cause, supporting evidence auto-populated
   → user fills target state, countermeasures, plan
   → schedule follow-ups (writes to follow_ups/INDEX.md)
   ↓
If disposition includes "open Kaizen":
   → procedures/open_kaizen.md → creates kaizens/open/{kaizen_id}.md
   → user fills change, owner, target, follow-up dates
   → schedule follow-ups
   ↓
If pattern feedback proposes a pattern update:
   → suggest invoking maintain/procedures/update_pattern.md
   ↓
If events were attributed to the floor visit:
   → suggest appending to events/{facility}.csv with source=floor-intake
```

### Path D — Architecture edits (maintain)

```
User asks to add/edit something structural
   ↓
maintain description matches → skill loads
   ↓
Identify operation → pick procedure
   ↓
Read procedure in full, check prerequisites
   ↓
Copy template, execute steps in order
   ↓
Run verification step (uses signal-detect or investigate)
```

The four paths share data layers but no skills. The skill descriptions enforce mutual exclusion.

---

## 4. Investigation states

Every investigation has a `state` field in its frontmatter that progresses through these values. This is the **canonical state machine** — the `data/investigations/INDEX.md` schema, every SKILL body, every close-loop procedure, and every investigation frontmatter must use these exact values.

| State | Meaning | Set by | Next typical state |
|-------|---------|--------|--------------------|
| `drafted` | Brief produced, not yet taken to floor | investigate skill | `floor_pending` |
| `floor_pending` | User has taken brief to floor; intake not yet recorded | user, via close-loop | `confirmed` / `ruled_out` / `inconclusive` |
| `confirmed` | Floor confirmed a hypothesis; pre-disposition | close-loop intake | `kaizen_open` / `a3_open` / `resolved` |
| `ruled_out` | All hypotheses ruled out by floor | close-loop intake | `resolved` / `superseded` |
| `inconclusive` | Floor visit did not resolve, more data needed | close-loop intake | `resolved` / `superseded` |
| `kaizen_open` | Kaizen drafted, follow-ups pending | open_kaizen procedure | `resolved` / `escalated` |
| `a3_open` | A3 drafted, follow-ups pending | open_a3 procedure | `resolved` / `escalated` |
| `superseded` | Brief was wrong; replaced by a new investigation | reopen_investigation procedure | (terminal — see `superseded_by`) |
| `resolved` | Signal returned to baseline; investigation closed | close-loop or follow-up pass | (terminal) |
| `escalated` | Outside CI scope or follow-ups showed no improvement | close-loop or follow-up fail | (terminal — handed off) |

**Active vs. closed (where each state's file lives):**

- `investigations/open/` holds **pre-disposition** states — `drafted`, `floor_pending`, `confirmed`, `ruled_out`, `inconclusive`. The user still owes the next action (take it to floor / record intake / pick a disposition). Files move out of `open/` only when a disposition procedure runs.
- `investigations/{YYYY-Qn}/` holds **post-disposition** states — `kaizen_open`, `a3_open`, `superseded`, `resolved`, `escalated`. The disposition is recorded; further tracking happens via `follow_ups/INDEX.md` (for kaizen_open/a3_open) or is terminal.

The signal-detect skill reads `open/` on every scan to surface what needs your next attention (any of the 5 pre-disposition states qualifies); it reads `follow_ups/INDEX.md` to surface due A3/Kaizen checks regardless of the investigation file's location.

**Why this set, not a more granular one:** earlier drafts split `kaizen_open` / `a3_open` into `action_planned` → `action_in_flight` → `awaiting_followup`. The follow-up status is already tracked authoritatively in `data/follow_ups/INDEX.md` (pending / PASS / FAIL / NO DATA per check), so the investigation state collapses to "the disposition is live" until follow-ups close. Splitting it further duplicated state without adding signal.

The state transitions are not free-form — they're enforced by the procedures in close-loop and by the follow-up check calc. This is what prevents the system from rotting into "everything is open forever."

---

## 5. File contracts

In the "Read by" column, "assistant" means the active assistant session — whichever model is running the skills system. "Operator" means the human (you).

| File | Read by | Job | Size budget |
|------|---------|-----|-------------|
| `.skills/README.md` | Assistant, first thing in any session that will use skills | Explains the protocol: how to scan manifest, when to load SKILL.md, what NOT to do | ≤4KB |
| `.skills/MANIFEST.yaml` | Assistant, once per session at start | Registry of all skills with description, triggers, path, content hash | ≤3KB |
| `.skills/.meta/reconcile.py` | Operator, on demand | Walk skills tree, sync MANIFEST.yaml with on-disk SKILL.md files | Self-contained |
| `.skills/.meta/create_skill.py` | Operator, on demand | Scaffold a new skill folder + SKILL.md + manifest update | Self-contained |
| `signal-detect/SKILL.md` | Assistant, on proactive scans | Three-part scan: new signals, open investigations, due follow-ups | Desc ≤200w; body ≤3KB |
| `investigate/SKILL.md` | Assistant, on investigation requests | Playbook routing + brief production rules | Desc ≤200w; body ≤3KB |
| `close-loop/SKILL.md` | Assistant, on floor returns | Intake routing + artifact generation | Desc ≤200w; body ≤3KB |
| `maintain/SKILL.md` | Assistant, on edit requests | Procedure routing + edit discipline | Desc ≤200w; body ≤2KB |
| `intake_template.md` | Walked by close-loop conversationally | Full intake form fields | ~4KB |
| `quick_close_template.md` | For non-event closes | Short intake variant | ~1KB |
| `reopen_template.md` | When brief was wrong | What was wrong + new starting point | ~1.5KB |
| `close-loop/procedures/*.md` | Assistant, one per disposition | Generate A3/Kaizen, schedule follow-ups, etc. | ~2KB per procedure |
| `playbooks/*.md` | Assistant, one per investigation | Diagnostic recipe per signal type | ~3KB per playbook |
| `maintain/procedures/*.md` | Assistant, one per edit | Edit recipe | ~2KB per procedure |
| `templates/*` | Copied during creation/edit | Canonical file shapes | Self-contained |
| `facilities/INDEX.md` | Assistant, every facility op | Flat directory + state + type + peers | ≤3KB |
| `profiles/*.md` | Assistant, per facility query | Dossier + metric pointers | ~4KB per facility |
| `metrics/MANIFEST.md` | Assistant, once per conv if metrics queried | Schema for all four families + freshness | ~5KB |
| `metrics/{family}/*.csv` | Calc scripts only | Raw daily measurements (only trusted if produced by validated conversion) | ~90 rows per file |
| `conversion/MANIFEST.md` | Operator, referenced by assistant when a conversion question arises | Source-to-target mapping + validation contract | ~3KB |
| `conversion/scripts/*` | Operator, run on data drop cadence | Read source files, validate, write canonical CSVs | Self-contained per script |
| `conversion/validation/*` | Sourced by conversion scripts | Shared validation routines (date format, ranges, schema match) | ≤1KB per file |
| `conversion/logs/*` | Audit + debugging | Per-run validation results, append-only | Grows over time |
| `conversion/README.md` | Operator | How to run conversions, cadence, fragile sources | ~2KB |
| `events/MANIFEST.md` | Assistant, once per conv if events queried | Taxonomy + entry conventions | ~2KB |
| `events/{id}.csv` | `cooccurrence.sh` | Per-facility event log | Variable, grep-friendly |
| `events/network.csv` | `cooccurrence.sh` | Cross-network events | Variable |
| `investigations/INDEX.md` | Assistant, during every investigation | Searchable history | ≤8KB |
| `investigations/open/*.md` | signal-detect + close-loop | In-progress investigations with state field | ~6KB per file |
| `investigations/YYYY-Qn/*.md` | Assistant, when history is needed | Closed investigations | ~6KB per file |
| `patterns/INDEX.md` | Assistant, during every investigation | Catalog of recurring causes | ≤4KB |
| `patterns/*.md` | Assistant, when pattern matches | Causal pattern + countermeasures-that-worked section | ~4KB per pattern |
| `a3s/INDEX.md` | Assistant, during A3 work | A3 catalog with state | ≤6KB |
| `a3s/open/*.md` | signal-detect + close-loop | Open A3 with follow-up schedule | ~5KB per A3 |
| `a3s/closed/YYYY-Qn/*.md` | Assistant, when history is needed | Closed A3 with outcome | ~6KB per A3 |
| `kaizens/INDEX.md` | Assistant, during Kaizen work | Kaizen catalog with state | ≤6KB |
| `kaizens/open/*.md` | signal-detect + close-loop | Open Kaizen with follow-up | ~2KB per Kaizen |
| `kaizens/closed/YYYY-Qn/*.md` | Assistant, when history is needed | Closed Kaizen with outcome | ~3KB per Kaizen |
| `follow_ups/INDEX.md` | signal-detect, daily | Calendar of pending outcome checks | ≤4KB |
| `calc/README.md` | Assistant, once per conv if calc used | Catalog of all calcs | ≤7KB |
| `calc/**/*.sh` | Bash, invoked by name | Deterministic, tested calculations | Self-contained |
| `calc/lib/_schema_v1.sh` | Sourced by every calc | Column positions, all four schemas | ≤1KB |
| `calc/tests/` | CI, on every calc change | Lock outputs against drift | Golden + expected per calc |
| `brief_template.md` | End of every investigation | Canonical brief shape | ~2KB |
| `a3.md` template | Used by open_a3.md | Canonical A3 shape | ~3KB |
| `kaizen.md` template | Used by open_kaizen.md | Canonical Kaizen shape | ~1.5KB |
| `tracking.md` | Read FIRST by every fresh assistant session | Orient to current build state — phase, completed steps, decisions, working log | Grows with the build; target ≤8KB, archive older log entries when exceeded |

> **Contract violation = silent failure.** None of these will produce an error if violated — they will produce slower, lower-quality outputs that look fine on the surface. The most insidious failure modes: (1) producing a number without a calc invocation that made it, (2) producing an A3/Kaizen without linking back to the source investigation, (3) creating an A3/Kaizen without scheduling follow-ups, (4) closing an investigation without an intake, (5) a CSV in `data/metrics/` produced by an unrecorded path or an unvalidated conversion script, (6) the `.skills/MANIFEST.yaml` drifting from the on-disk `SKILL.md` files. The first four are caught by verification steps in `close-loop/`. The fifth is caught by `conversion/MANIFEST.md` and the validation contract. The sixth is caught by running `.skills/.meta/reconcile.py`.

---

## 6. The metric layer — four sub-schemas per facility

Where most systems would have a single CSV per facility, this architecture has four separate CSVs per facility, each with its own schema documented in `metrics/MANIFEST.md`.

The reason: root cause work is multivariate. You can't form a hypothesis about *why* a metric moved from a file that only contains that metric and one downstream variable. You need inputs (what the facility was given to work with), exceptions (categorized failure modes), and equipment state (what was working or not). Four files isn't expensive — they share a date key, they're tiny — and the analytical capability difference is enormous.

### The `metrics/MANIFEST.md` (illustrative)

```markdown
# Metrics Manifest — Week of 2026-05-12

## Operational metrics (operational/{id}.csv)
Daily outputs of the facility.

| Col | Field        | Type       | Notes                                |
|-----|--------------|------------|--------------------------------------|
| 1   | date         | YYYY-MM-DD | Daily granularity                    |
| 2   | facility_id  | string     |                                      |
| 3   | units        | int        | Total units shipped that day         |
| 4   | cph          | float      | Cases per hour, facility-wide        |
| 5   | error_rate   | float      | Total errors per 1000 units          |
| 6   | hours_run    | float      | Total operating hours that day       |

## Input metrics (inputs/{id}.csv)
What the facility was given to work with that day.

| Col | Field             | Type       | Notes                          |
|-----|-------------------|------------|--------------------------------|
| 1   | date              | YYYY-MM-DD |                                |
| 2   | facility_id       | string     |                                |
| 3   | headcount_total   | int        | FTE on shift, excludes seasonal|
| 4   | headcount_new     | int        | New hires (<30 days)           |
| 5   | headcount_shift1  | int        | Day shift                      |
| 6   | headcount_shift2  | int        | Evening shift                  |
| 7   | headcount_shift3  | int        | Night shift                    |
| 8   | inbound_units     | int        | Units received that day        |
| 9   | order_mix_complex | float      | % orders with >3 SKUs          |

## Exception metrics (exceptions/{id}.csv)
Categorized failures per day.

| Col | Field        | Type       | Notes                          |
|-----|--------------|------------|--------------------------------|
| 1   | date         | YYYY-MM-DD |                                |
| 2   | facility_id  | string     |                                |
| 3   | damage       | int        | Damaged units                  |
| 4   | missort      | int        | Routed to wrong lane           |
| 5   | mispick      | int        | Wrong item picked              |
| 6   | lost         | int        | Inventory not found            |
| 7   | late_pick    | int        | Pick completed after cutoff    |

## Equipment metrics (equipment/{id}.csv)
Asset health and uptime.

| Col | Field           | Type       | Notes                        |
|-----|-----------------|------------|------------------------------|
| 1   | date            | YYYY-MM-DD |                              |
| 2   | facility_id     | string     |                              |
| 3   | conveyor_down_m | int        | Conveyor downtime, minutes   |
| 4   | mhe_down_m      | int        | MHE downtime, minutes        |
| 5   | wms_incidents   | int        | WMS-related incidents        |
| 6   | scanner_faults  | int        | Handheld/fixed scanner faults|

## This week's drop
- Period: 2026-02-12 through 2026-05-11 (90 days)
- Facilities included: 8 of 8
- Generated: 2026-05-12 06:00 ET
- Schema version: v1 (all four families)

## Schema version history
- v1 (current, since 2026-01-01): initial 4-family schema as defined above
```

The trade-off: four CSVs instead of one means four times the file management. The maintenance skill's `bump_schema.md` procedure has to update four schema sections, not one. Calcs that join across families read four files instead of one. None of these costs are large at this scale — the analytical capability gain is multiple-orders-of-magnitude larger than the maintenance cost.

---

## 7. The conversion boundary

Raw source data lives outside the architecture. The CSVs in `data/metrics/` are the architecture's input interface — everything past this point trusts the schema and the data quality. Everything before it is the responsibility of whoever maintains the data pipeline (in a one-operator deployment, that's you).

The conversion layer is the bridge between those two worlds. It exists as a deliberate boundary, not as an accident.

### Why this boundary needs to be explicit

Operations data sources are messy. Excel files with multiple sheets, vendor-supplied CSVs with shifting column orders, BI tool exports with formatting quirks, manual spreadsheets that humans edit. The calc library cannot consume any of this directly — it needs canonical, schema-conformant CSVs.

If conversion is implicit ("data gets into `data/metrics/` somehow"), three things go wrong over time:

1. Calcs start failing on subtle schema violations (a header row shifted, a date column changed format) and nobody knows whether the bug is in the data or the calc.
2. New facilities get added with subtly different conversion pipelines, and silently their metrics aren't comparable to other facilities'.
3. When the conversion logic lives in one person's head, the architecture has a single point of failure that the rest of the design carefully avoids.

The conversion boundary makes the pipeline visible, versioned, and testable. Same discipline the calc library applies to computations, applied to data ingestion.

### What the conversion layer contains

The `conversion/` directory (see file layout in section 2) holds:

- **`MANIFEST.md`** — the contract describing what enters the architecture, from where, on what cadence, with what validation guarantees.
- **`scripts/`** — one conversion script per source file. Reads the source, normalizes, writes a canonical CSV to `data/metrics/{family}/{id}.csv`.
- **`validation/`** — shared validation routines that every conversion script invokes before writing output.
- **`logs/`** — per-run validation results, kept for audit and debugging.
- **`README.md`** — operating instructions: how to run conversions, expected cadence, known fragile sources.

### `conversion/MANIFEST.md` (illustrative)

```markdown
# Conversion Manifest

## Purpose
Documents every raw source file that feeds the architecture, the
conversion script that processes it, and the canonical CSV it produces.
The architecture trusts CSVs in `data/metrics/` only if produced by a
script listed here that has passed validation on the run that produced
the file.

## Source-to-target mappings

| Source                            | Type | Cadence | Script                              | Target                              |
|-----------------------------------|------|---------|-------------------------------------|-------------------------------------|
| `~/ops_exports/DAL02_daily.xlsx`  | xlsx | weekly  | scripts/extract_dal02_operational.py| data/metrics/operational/dal-02.csv |
| `~/ops_exports/ATL01_weekly.csv`  | csv  | weekly  | scripts/extract_atl01_operational.py| data/metrics/operational/atl-01.csv |
| `~/hr_dumps/headcount_all.xlsx`   | xlsx | weekly  | scripts/extract_all_inputs.py       | data/metrics/inputs/*.csv (8 files) |
| ... (one row per source)          |      |         |                                     |                                     |

## Validation guarantees

Every conversion script must validate its output BEFORE writing to
`data/metrics/`. If validation fails, the script writes a failure log
to `conversion/logs/` and exits non-zero. It does NOT write a partial
or invalid CSV.

Required validations:
- **Date format:** all values in column 1 match YYYY-MM-DD
- **No nulls in key columns:** date and facility_id never blank
- **Facility ID matches:** every row's facility_id matches the
  filename's facility (no cross-facility data leakage)
- **Row count threshold:** output has at least 80% of expected rows
  for the period (catches truncated exports)
- **Value range sanity:** numeric metrics are non-negative; CPH is
  between 0 and 500; percentages are between 0 and 100
- **Schema match:** output column count and order matches the
  schema version declared in `metrics/MANIFEST.md`

## Cadence

- **Weekly drop:** Mondays after operations closes the prior week's
  numbers. All operational and exceptions metrics refreshed.
- **Bi-weekly:** Inputs metrics (HR data is slower to settle).
- **As-needed:** Equipment metrics, when downtime events are logged.

## Schema version
Current: v1 (matches `metrics/MANIFEST.md` v1).
When `metrics/MANIFEST.md` bumps to v2, every conversion script in
scripts/ must be updated to produce v2-shaped output in the same
commit. The `bump_schema.md` procedure enforces this.

## Known fragile sources

Sources that break the conversion pipeline most often, with reasons:
- `~/ops_exports/DAL02_daily.xlsx` — humans add comment columns to
  the right of the data periodically. Script tolerates extra columns
  but flag if column count exceeds 20.
- `~/hr_dumps/headcount_all.xlsx` — sheet name changes quarterly.
  Script tries both "Headcount" and "HC Summary" before failing.
```

### Why this is a contract, not just documentation

`metrics/MANIFEST.md` is a contract that calcs trust — calcs read column positions from `_schema_v1.sh` assuming the schema holds. `conversion/MANIFEST.md` is the upstream contract that makes that trust justified. When a calc returns a wrong number, the diagnostic question is "did conversion validate this file's run?" If the log in `conversion/logs/` shows a clean validation, the bug is in the calc. If the log shows a failure or is missing, the bug is upstream of the architecture entirely.

This is the same discipline patterns apply to causes and golden tests apply to calcs — making the boundary between "trusted" and "untrusted" explicit, so failures surface at the right layer.

### What's NOT inside the conversion boundary

To be explicit about scope:

- **The source data itself.** Excel files in shared drives, vendor CSVs, BI exports — these live wherever they live. The architecture does not manage them.
- **The systems that produce source data.** WMS exports, HR systems, manual spreadsheet maintenance. Not in scope.
- **Real-time data flow.** Conversion is batch (weekly typical). Real-time ingestion would be a different boundary; see section 15 future scope.
- **Source-data governance.** Who owns the source files, who is allowed to edit them, what happens when they change format — these are operational questions for whoever maintains the data pipeline, not the architecture's concern.

The boundary is sharp on purpose. Everything inside has known shape and known guarantees. Everything outside is somebody else's problem (or yours, but wearing a different hat).

### The bootstrap question

A fresh deployment with no source data at all cannot run any conversion scripts, which means `data/metrics/` is empty, which means no calcs work, which means the architecture is inert. The implementation plan handles this — phase 0 is dedicated entirely to building the conversion layer before any architecture work begins. Once the conversion layer is producing canonical CSVs, the rest of the architecture activates.

---

## 8. The events layer — context for "why"

Without an events log, every investigation eventually reaches a wall where the data says "X co-varied with Y" but can't say *what changed in the world* that caused either. The events layer fills that gap.

### `events/MANIFEST.md` (illustrative)

```markdown
# Events Manifest

## Per-facility event log (events/{id}.csv)

| Col | Field         | Type       | Notes                              |
|-----|---------------|------------|------------------------------------|
| 1   | date          | YYYY-MM-DD | When the event occurred            |
| 2   | facility_id   | string     |                                    |
| 3   | event_type    | string     | One of the taxonomy below          |
| 4   | description   | string     | Short free-text (≤200 chars)       |
| 5   | source        | string     | Who logged it (CI mgr, ops mgr, system)|

## Event taxonomy (event_type values)
- `system_change`     — WMS, scanner, label printer, asset software change
- `deployment`        — major software/hardware install
- `training`          — formal training events (cohort start, certification)
- `incident`          — safety, security, or operational incident
- `leadership_change` — manager/supervisor change at the facility
- `sop_change`        — written process change
- `weather`           — significant weather event affecting operations
- `holiday`           — observed holiday (impacts staffing/volume)
- `audit`             — internal or external audit underway
- `equipment_install` — new equipment installed/decommissioned
- `volume_shock`      — unusual inbound or outbound volume

## Network event log (events/network.csv)
Same schema, no facility_id column. Used for things that hit all
facilities (network-wide WMS releases, corporate policy changes,
regulatory changes).

## Entry conventions
- One event per row. Two things same day = two rows.
- Description neutral and factual. Interpretation goes in investigations.
- Source matters for trust. CI-mgr-logged events get verified later;
  system-logged events are authoritative.
- Backfill is allowed but flag it: add "(backfilled)" to description.
```

The diagnostic calc `cooccurrence.sh dal-02 2026-03-08 --window 14` reads the per-facility log plus `network.csv` and returns every event in the ±14 day window around the signal date. Suddenly every investigation starts with a list of what changed in the world before the signal appeared.

The events log is the slowest layer to populate. Don't expect it to be useful in week 1. Expect it to be useful in month 3, after obvious recent events have been backfilled and the habit of logging new events as they happen has formed. The largest single source of new event log entries over time is the close-loop intake — every floor visit systematically generates new entries (source = `floor-intake-{date}`).

---

## 9. The calc library — four families

### 9.1 Descriptive calcs (`calc/descriptive/`)
Single-variable aggregations: averages, totals, counts, max/min, summaries. They answer "what is the value of metric M at facility F over time window T."

### 9.2 Diagnostic calcs (`calc/diagnostic/`)
Multi-variable analysis. They answer "why might metric M have the value it has."

| Calc | Question it answers | Example invocation |
|------|--------------------|--------------------|
| `correlate.sh` | How correlated are two columns? | `correlate.sh dal-02 cph headcount_new --start 2026-01-01 --end 2026-03-31` |
| `segment_by.sh` | Break metric M down by dimension D | `segment_by.sh dal-02 cph day_of_week --start 2026-01-01 --end 2026-03-31` |
| `change_drivers.sh` | Which inputs changed most in a bad period? | `change_drivers.sh dal-02 cph --bad 2026-03-08:2026-03-14 --baseline 2026-02-08:2026-03-07` |
| `cooccurrence.sh` | What events occurred near this date? | `cooccurrence.sh dal-02 2026-03-08 --window 14` |
| `outlier_days.sh` | Which days deviated most from the facility norm? | `outlier_days.sh dal-02 cph --top 5 --window 90d` |
| `compare_to_baseline.sh` | Period-over-period delta on every variable | `compare_to_baseline.sh dal-02 --bad 2026-03 --baseline 2026-02` |

### 9.3 Comparative calcs (`calc/comparative/`)
Cross-facility analysis.

| Calc | Question | Example |
|------|----------|---------|
| `rank_facilities.sh` | Rank all facilities by metric M | `rank_facilities.sh cph --start 2026-03-01 --end 2026-03-31` |
| `peer_benchmark.sh` | How does facility F compare to its peers? | `peer_benchmark.sh dal-02 cph --start 2026-03-01 --end 2026-03-31` |
| `divergence_analysis.sh` | Where did facility F diverge from peers? | `divergence_analysis.sh dal-02 --period 2026-03 --compare-to hou-01` |

Peer pairings come from `facilities/INDEX.md`. At 8 facilities you have 4 natural type-based peer pairs.

### 9.4 Outcome calcs (`calc/outcome/`)
Multi-period analysis specifically for verifying whether an intervention worked.

| Calc | Question it answers | Example invocation |
|------|--------------------|--------------------|
| `follow_up_check.sh` | Did metric M hit target T at facility F by date D? | `follow_up_check.sh dal-02 cph --target 138 --by 2026-04-08 --baseline 2026-02` |
| `countermeasure_effectiveness.sh` | Did metric M change between pre-intervention and post-intervention? | `countermeasure_effectiveness.sh dal-02 cph --pre 2026-03-08:2026-03-21 --post 2026-03-22:2026-04-04` |
| `intervention_attribution.sh` | Is the change in metric M attributable to the intervention or to other variables that also changed? | `intervention_attribution.sh dal-02 cph --intervention-date 2026-03-22 --check-variables headcount_new,inbound_units` |

The key property: **the same follow-up check run today and re-run a month from now (against newly-arrived data) returns updated numbers but uses the same methodology**. This is what makes the architecture's claim of "the system follows up automatically" actually true rather than a slogan.

Every calc across all four families is a deterministic bash script with a golden test. The same invocation today and three weeks from now returns the same number (against the same data window). This is what makes the analytical layer *trustworthy*, not just useful.

### 9.5 Calc invocation rules

- Every computed metric goes through a named calc invocation
- Never compose inline awk for computed metrics
- Every calc cited in a brief, intake, A3, or Kaizen must include its exact invocation so the user can re-run it
- Calc gaps surface as friction — when no calc covers a question, flag it and suggest adding one rather than improvising

---

## 10. The investigation and pattern history

This is the layer that makes the architecture compound over time. Without these two folders, every investigation starts from zero. With them, you build institutional memory that makes future investigations faster and better.

### 10.1 `investigations/` — every investigation is a file

When an investigation completes (the floor brief is produced, the floor visit happens, the intake is recorded, and the disposition is resolved), the investigation is saved to `investigations/YYYY-Qn/{date}_{facility}_{signal}.md`. The filename pattern enables grep-based history search by date, facility, or signal type.

Each file contains: the signal that triggered the investigation, the playbook used, calcs run with their invocations and results, hypotheses considered, the floor brief produced, the structured intake from the floor visit, the disposition, the linked A3s/Kaizens, and the outcome.

`investigations/INDEX.md` is a searchable table:

```markdown
# Investigations Index

| Date       | Facility | Signal type             | State       | Linked A3/Kaizen | File |
|------------|----------|-------------------------|-------------|------------------|------|
| 2026-03-15 | DAL-02   | throughput_drop         | resolved    | k-2026-03-DAL-02-trainer-ratio, a3-2026-03-DAL-02-cohort-onboarding | 2026-Q1/2026-03-15_DAL-02_throughput_drop.md |
| 2026-03-22 | CHR-03   | error_spike (damage)    | resolved    | k-2026-03-CHR-03-bin-relocation | 2026-Q1/2026-03-22_CHR-03_error_spike.md |
| 2026-04-04 | DAL-02   | throughput_drop         | floor_pending | (pending intake) | open/2026-04-04_DAL-02_throughput_drop.md |
```

Before drafting a new floor brief, the investigate skill **always** checks this index for: prior investigations of the same facility, prior investigations of the same signal type, any open investigations that might be related.

### 10.2 `patterns/` — recurring causes get abstracted

When 3-5 investigations turn out to have the same underlying cause, you write a pattern file. The pattern captures the *generic* causal shape: typical signal, typical co-occurring metrics, typical events, recommended investigation steps, historical instances, **and the countermeasures that have worked or failed in past A3s/Kaizens**.

The pattern file shape:

```markdown
# Pattern: Throughput dip after new-hire cohort

## Signal shape
CPH 3-8% below target for 5-14 days. Often accompanied by:
- Error rate elevation (especially mispicks and missorts)
- Disproportionate impact on the shift where new hires are concentrated
- Normal headcount totals but elevated headcount_new column

## Typical co-occurring events
- training event 1-3 weeks prior (cohort start)
- Sometimes coincides with seasonal hiring waves

## Investigation steps (run these first when signal matches)
1. `segment_by.sh {facility} cph headcount_new_pct --window 30d`
2. `segment_by.sh {facility} cph shift --window 30d`
3. `cooccurrence.sh {facility} {signal_date} --window 21`
4. Look for training event in window; check trainer-to-trainee ratio
   against SOP

## Floor questions when this pattern is suspected
- Was the cohort size larger than usual?
- Were experienced staff available to pair with new hires?
- Did the training schedule run as planned?
- Are any specific new hires struggling more than others?

## Expected resolution timeline
2-4 weeks. If signal persists past 4 weeks, escalate.

## Countermeasures that have worked
- 2026-03 DAL-02: Paired-buddy onboarding for new hires, 4-week period.
  Result: CPH recovered to baseline in 18 days.
  See a3s/closed/2026-Q2/a3-2026-03-DAL-02-cohort-onboarding.md
- 2025-11 ATL-01: Extended training week from 3 to 5 days.
  Result: Mixed — CPH faster recovery but error rate slower.
  See a3s/closed/2025-Q4/a3-2025-11-ATL-01-cohort.md

## Countermeasures that didn't work
- 2025-08 HOU-01: Added overtime to cover learning curve.
  Result: CPH did not improve; error rate worsened.
  See investigations/2025-Q3/2025-08-04_HOU-01_throughput_drop.md

## Historical instances
- investigations/2025-Q4/2025-11-08_ATL-01_throughput_drop.md
- investigations/2026-Q1/2026-03-15_DAL-02_throughput_drop.md
- investigations/2026-Q1/2026-02-22_HOU-01_throughput_drop.md
```

When a new signal matches a pattern, the floor brief surfaces not just hypotheses but **which actions have worked in similar situations at other facilities and which haven't**. That's the entire promise of cross-facility CI compressed into one paragraph.

### 10.3 The compounding property

Investigation #1 has no history. Investigation #10 has 9 priors, maybe 2 patterns. Investigation #30 has 29 priors and 6-8 patterns covering the most common signal shapes — at which point most new investigations get matched to a pattern within minutes, and calc work narrows to confirming or ruling out the candidate pattern. The system's value-per-investigation increases over time without architectural change.

---

## 11. The close-loop layer

This is the layer that closes the CI loop. It captures structured findings from floor visits, generates A3s and Kaizens from those findings, and schedules outcome tracking that runs automatically through signal-detect.

### 11.1 The `close-loop/SKILL.md`

```markdown
---
name: close-loop
description: Use this skill when the user returns from a floor visit and wants to close out an investigation — capture floor findings, decide what comes next (Kaizen, A3, close, re-open, escalate), and produce the corresponding artifacts. Triggers on "closing out the investigation", "back from the floor", "floor findings on X", "we confirmed it was Y", "draft the A3 for Z", "open a Kaizen for W", or any phrasing that indicates the user has been to the floor and is bringing findings back. Do NOT use for proactive scans — that is signal-detect. Do NOT use for new investigations — that is investigate. Do NOT use for architecture edits — that is maintain.
---

# Close Loop

## When to use
The user is returning from a floor visit with findings on a specific
investigation, OR drafting an A3/Kaizen, OR closing one out after
follow-up.

## How to close a loop

1. **Identify the investigation.** By ID, or by facility + date + signal.
   Read the investigation file in full. Confirm with the user this is
   the right one.

2. **Walk the intake conversationally** using `intake_template.md`.
   Don't ask the user to fill out a form. Ask the questions one at a
   time, in order, in plain English. Record the answers in the
   intake's structured fields as you go.

3. **For each hypothesis from the brief, capture disposition** with
   floor evidence. This is the section that feeds future calibration —
   don't skip it.

4. **Capture what the data missed and surprises.** These are the
   highest-information fields. If the user is brief on these, probe
   once with "anything the data didn't show?" but don't force.

5. **Decide disposition** with the user. Multi-select allowed. Common
   combinations: Kaizen + A3 (Kaizen now, A3 for systemic), close +
   pattern update (one-off but the pattern should learn).

6. **Execute downstream procedures** based on disposition:
   - "Open A3" → procedures/open_a3.md
   - "Open Kaizen" → procedures/open_kaizen.md
   - "Close" → move investigation to YYYY-Qn/, set state=resolved
   - "Re-open" → procedures/reopen_investigation.md
   - "Escalate" → set state=escalated, log the handoff

7. **Update the events log** with floor-attributed observations.
   Source field = "floor-intake-{date}".

8. **Update the pattern** if intake suggested a revision.
   procedures/update_pattern.md handles this — don't edit patterns
   directly.

9. **Schedule follow-ups** for any A3 or Kaizen opened.
   Write entries to follow_ups/INDEX.md with the target metric,
   target value, follow-up date, and the calc invocation that
   will verify outcome.

## Variants

- **Quick close** (`quick_close_template.md`): for investigations
  that turn out to be non-events. Two fields: disposition rationale
  and pattern feedback. Skip everything else.
- **Re-open** (`reopen_template.md`): for when floor feedback
  contradicted the brief. Captures what was wrong with the original
  analysis and what the new starting point should be.

## Anti-patterns

- Don't accept free-text "yeah it was the cohort thing" — walk the
  per-hypothesis disposition field
- Don't skip the events log update — floor visits are the largest
  source of new events
- Don't open A3s or Kaizens without scheduling follow-ups
- Don't update patterns directly — use maintain/procedures/update_pattern.md
- Don't close an investigation without an intake — even quick-close
  requires the quick template
```

### 11.2 The full intake template (`intake_template.md`)

The template the assistant walks conversationally. Filled-in example below the empty template.

```markdown
# Floor Feedback Intake

**Investigation ID:** {investigation_id}
**Floor visit:** {start_date} to {end_date}
**Visited by:** {name}
**Floor contacts:** {names + roles}
**Intake recorded:** {date}

---

### 1. Hypothesis disposition

For each hypothesis from the brief, mark its status and cite floor evidence.

**Hypothesis A — {label}**
- Status: {CONFIRMED | RULED OUT | INCONCLUSIVE}
- Floor evidence: {bullet list of specific observations, quotes,
  contacts who said what}
- Strength: {STRONG | MODERATE | WEAK} — {reason}

{repeat per hypothesis}

---

### 2. What the data missed

Facts the floor knew that the data didn't show.

- {bullet list, one per item}

---

### 3. Surprises

Things that contradicted or extended expectations.

- {bullet list}

---

### 4. New questions raised

Things this visit couldn't answer that might need follow-up.

- {bullet list}

---

### 5. Floor-attributed observations to log

Items to add to the events log or as candidate schema additions.

- events/{id}.csv: Add `{date}, {id}, {event_type}, "{description}", floor-intake-{intake_date}`
- Candidate new metric: {description, flagged for bump_schema discussion}

---

### 6. Disposition

What happens next. Multi-select if sequenced.

- [ ] Close as resolved — signal was a one-off
- [ ] Close as monitoring — watch for recurrence
- [ ] Open A3 — systemic, structured root-cause work
- [ ] Open Kaizen — quick targeted change
- [ ] Re-open as investigation — brief was wrong
- [ ] Escalate — outside CI scope

**Rationale:** {1-3 sentences on why this disposition vs alternatives}

**Suggested A3 scope (if A3):** {problem statement, initial facility, network applicability}

**Suggested Kaizen scope (if Kaizen):** {specific change, owner, target metric, target date}

---

### 7. Pattern feedback

If this investigation matched a pattern from patterns/INDEX.md:

- Matched pattern: {patterns/file.md, match score from brief}
- Confirmed pattern elements: {what held}
- Refuted pattern elements: {what didn't hold, if any}
- New element to add to pattern: {extension worth capturing}
- Suggested pattern update: {specific revision proposed}

---

### 8. Follow-up commitments

Things committed to during the visit.

- {bullet list with date, person, what was promised}
```

### 11.3 Filled-in intake example (illustrative)

This is what an intake looks like after a real floor visit. All values are placeholders.

```markdown
# Floor Feedback Intake

**Investigation ID:** 2026-03-15_DAL-02_throughput_drop
**Floor visit:** 2026-03-16 to 2026-03-17
**Visited by:** [CI manager name]
**Floor contacts:** Maria Reyes (night shift sup), J. Chen + R. Okafor (associates)
**Intake recorded:** 2026-03-17

---

### 1. Hypothesis disposition

**Hypothesis A — New-hire cohort assigned to night shift**
- Status: CONFIRMED
- Floor evidence:
  - Maria confirmed cohort of 6 hires started Mar 6, 4 on night shift
  - Trainer-to-trainee ratio was 1:6 actual vs 1:4 per SOP
  - "We were short on certified trainers that week" (Maria)
  - Observed: 2 new hires working a pick zone unsupervised on Mar 16
- Strength: STRONG — multiple sources, observable on visit

**Hypothesis B — WMS update on Mar 7**
- Status: RULED OUT
- Floor evidence:
  - Associates reported "no real change" from the WMS update
  - No support tickets logged at DAL-02 related to the update
  - Day shift CPH was unaffected; floor confirmed they noticed nothing
- Strength: STRONG

**Hypothesis C — Equipment downtime**
- Status: RULED OUT (already in brief)
- Floor evidence: N/A — ruled out by data pre-visit

---

### 2. What the data missed

- Trainer shortage is recurring. Maria mentioned this is the 2nd time
  in 6 months. Earlier instance late 2025, never investigated.
- Specific zones are harder for new hires. Cold-pick zone 4 has higher
  rejection rates for new hires than dry-pick zones. Not captured.
- Pairing wasn't formally tracked. Per SOP, new hires should be paired
  with certified associates; Maria said pairings happen informally
  but aren't logged. So "trainer ratio" in the data is shift-level
  headcount, not paired-pairings — those are different things.

---

### 3. Surprises

- Assumed all 4 night-shift new hires were in similar zones. They
  weren't — 2 in cold-pick, 2 in dry-pick. Cold-pick pair struggled more.
- Expected morale issues from existing crew. Didn't find any —
  associates were sympathetic, not frustrated.
- Maria proactively raised the trainer shortage without prompting.
  Known gap she's been flagging upward without resolution.

---

### 4. New questions raised

- How many certified trainers does DAL-02 currently have vs.
  headcount-based target? Not in any current data file.
- Is the trainer shortage facility-specific or network-wide?
  Worth checking CHR-03 and HOU-01.
- Does cold-pick need a different onboarding track than dry-pick?
  Worth talking to the cold-storage SME.

---

### 5. Floor-attributed observations to log

- events/dal-02.csv: Add `2026-03-06, dal-02, training, "Cohort of 6 new hires started; 4 to night shift; trainer ratio 1:6 vs SOP 1:4", floor-intake-2026-03-17`
- events/dal-02.csv: Add `2025-11-12, dal-02, training, "Prior cohort onboarded with trainer shortage (Maria recollection, approximate date)", floor-intake-2026-03-17 (backfilled)`
- Candidate new metric: paired-pairings tracked per shift, not just headcount. Flag for bump_schema discussion.

---

### 6. Disposition

- [x] Open A3 — systemic, structured root-cause work
- [x] Open Kaizen — quick targeted change (sequenced: Kaizen first, A3 in parallel)

**Rationale:** Proximate cause (one cohort, one shift) is fixable with a Kaizen — restore 1:4 trainer ratio, pair cold-pick new hires with cold-certified associates. Underlying cause (recurring trainer shortage, no formal pairing tracking, cold-pick onboarding gap) is systemic and worth a network-scope A3.

**Suggested A3 scope:** "New-hire onboarding fidelity to SOP — trainer availability and pairing discipline." Network problem statement; DAL-02 as initial case study.

**Suggested Kaizen scope:** "Restore 1:4 trainer ratio at DAL-02 night shift for current cohort + pair cold-pick new hires with cold-certified associates." Owner: Maria Reyes. Target: cohort CPH back to 138+ within 21 days.

---

### 7. Pattern feedback

- Matched pattern: patterns/cohort_throughput_dip.md (match 0.82)
- Confirmed pattern elements: Cohort start 1-3 weeks before signal ✓, shift-concentration ✓, new-hire-pct elevation ✓, mispick spike ✓
- Refuted pattern elements: None
- New element to add: Trainer ratio violation as the *mechanism* behind the cohort impact. Current pattern says "cohorts cause dips"; this case says "cohorts cause dips *when trainer ratio isn't maintained*."
- Suggested pattern update: Add "Check trainer-to-trainee ratio against SOP" as investigation step #2. Add "Trainer shortage" as a candidate root cause beyond cohort size alone.

---

### 8. Follow-up commitments

- Loop back with Maria week of 2026-04-08 to share Kaizen results.
- Bring trainer-shortage issue to facility leadership (separate from this investigation; Maria's existing escalation).
- Share findings with HOU-01 and CHR-03 CI counterparts when those roles exist; trainer shortage may be a network issue.
```

### 11.4 The intake variants

**Quick close** is used when a brief is taken to the floor and the signal turns out to be a non-event. Two fields: rationale and pattern feedback. ~150 words total. Skips everything else.

**Re-open** is used when floor feedback contradicts the brief enough that the investigation has to start over. Captures: what was wrong with the original analysis, what's the new starting point, what data should be re-pulled. The re-opened investigation gets a new ID and a "supersedes" reference to the original.

---

## 12. The A3 and Kaizen layers

### 12.1 The A3 template

Auto-populated where possible from the investigation chain. The CI manager fills in only the human-judgment parts (target state, chosen countermeasures, plan ownership).

```markdown
# A3: {Problem Title}

**A3 ID:** a3-{YYYY-MM}-{facility_or_network}-{slug}
**Opened:** {date}
**State:** open
**Owner:** {name}
**Source investigation:** investigations/{path}.md
**Related pattern:** patterns/{name}.md (if applicable)
**Network applicability:** {single facility | regional | network}

## Current state
{Auto-populated from investigation:
- Signal magnitude with calc invocations
- Duration of issue
- Business impact estimate}

## Target state
{CI manager fills in:
- Metric M back to target T by date D
- Acceptable error rate / quality constraints during recovery}

## Root cause
{From floor intake confirmation:
- Confirmed hypothesis with mechanism
- Floor observation that pinned it down
- Supporting evidence with calc invocations}

## Countermeasures
{CI manager chooses; if a pattern matched, the pattern's
"Countermeasures that have worked" section is surfaced as a
starting point.}

1. {countermeasure with owner}
2. {...}
3. {...}

## Plan
| Action | Owner | Start | Complete by | Status |
|--------|-------|-------|-------------|--------|
| ...    | ...   | ...   | ...         | ...    |

## Follow-up schedule
| Date | Check | Calc invocation | Target |
|------|-------|-----------------|--------|
| 2026-04-08 | Cohort CPH halfway recovery | `follow_up_check.sh dal-02 cph --target 134 --by 2026-04-08 --baseline 2026-02` | 134 |
| 2026-04-22 | Cohort CPH full recovery | `follow_up_check.sh dal-02 cph --target 140 --by 2026-04-22 --baseline 2026-02` | 140 |
| 2026-05-06 | Error rate stabilization | `follow_up_check.sh dal-02 error_rate --max 2.5 --by 2026-05-06 --baseline 2026-02` | ≤2.5 |

## Lessons learned
{Filled in at A3 close, feeds back to pattern library}

## Closing
{Filled in at A3 close:
- Outcome at each follow-up
- What worked, what didn't
- Network applicability assessment
- Pattern updates triggered}
```

### 12.2 The Kaizen template

Deliberately lower-ceremony. Most fields are short.

```markdown
# Kaizen: {Title}

**Kaizen ID:** k-{YYYY-MM}-{facility}-{slug}
**Opened:** {date}
**State:** open
**Owner:** {name}
**Source:** {investigation ID | pattern name | observation}
**Related pattern:** patterns/{name}.md (if applicable)

## Observation
{1-3 sentences with the data that motivates the change.
Include calc invocations.}

## Change
{Specific change being made. One paragraph.}

## Tracking
- Baseline: {metric, value, period}
- Target: {metric, target value, by date}
- Follow-up checks: {dates with calc invocations}

## Outcome
{Filled in at close: did it work? was it standardized or rolled back?}
```

### 12.3 The `follow_ups/INDEX.md`

A simple calendar of pending outcome checks. Read by signal-detect daily.

```markdown
# Follow-Up Calendar

| Due date | Type | ID | Facility | Metric | Target | Calc invocation |
|----------|------|----|----|---------|--------|-----------------|
| 2026-04-08 | Kaizen | k-2026-03-DAL-02-trainer-ratio | DAL-02 | cph | ≥134 | `follow_up_check.sh dal-02 cph --target 134 --by 2026-04-08 --baseline 2026-02` |
| 2026-04-08 | A3 | a3-2026-03-DAL-02-cohort-onboarding | DAL-02 | cph | ≥134 | `follow_up_check.sh dal-02 cph --target 134 --by 2026-04-08 --baseline 2026-02` |
| 2026-04-22 | Kaizen | k-2026-03-DAL-02-trainer-ratio | DAL-02 | cph | ≥140 | `follow_up_check.sh dal-02 cph --target 140 --by 2026-04-22 --baseline 2026-02` |
| 2026-05-06 | A3 | a3-2026-03-DAL-02-cohort-onboarding | DAL-02 | error_rate | ≤2.5 | `follow_up_check.sh dal-02 error_rate --max 2.5 --by 2026-05-06 --baseline 2026-02` |
```

When signal-detect runs its daily scan, it reads this file, runs the calc invocations for any rows with `Due date ≤ today`, and surfaces the results. If a check passes (metric hit target), it suggests closing the corresponding A3/Kaizen. If a check fails (metric didn't hit target), it surfaces the failure prominently and suggests either re-opening the investigation or extending the intervention.

---

## 13. The floor brief — the daily deliverable

The brief is the artifact the investigate skill produces at the end of every investigation. It's structured to feed the intake directly — every section of the brief maps to a section of the intake.

```markdown
# Floor Brief: {Facility} {signal_type}, {date range}

**Investigation ID:** {YYYY-MM-DD}_{facility}_{signal_type}
**Investigator:** {name}
**Date drafted:** {date}
**Signal:** {one-line summary with magnitude and target}

> This investigation will be tracked through resolution.
> After your floor visit, return to update findings via close-loop.
> Likely next states: confirmed → A3 (if systemic) or Kaizen (if quick targeted fix).

## What we see
{3-4 sentences in plain English. Include exact calc invocations so
the floor team can verify.}

## What the data says about why

### Hypothesis A — {label} ({strongest/likely/possible})
- Mechanism: {what's happening on the floor in concrete terms}
- Supporting evidence: {calc invocation + number}
- Counter-evidence: {what makes you less certain}
- Pattern match: {patterns/file.md, if applicable}

### Hypothesis B — {label}
{same shape}

### Hypothesis C — {label}
{same shape, or "ruled out: {evidence}"}

## Questions for the floor
- {Specific, falsifiable question that tests Hypothesis A}
- {Question for B}
- {Question for C, if not ruled out}
- {Open data questions — things the floor knows that data doesn't}

## Methodology (every invocation reproducible)
- {calc invocation 1}
- {calc invocation 2}
- {pattern check: patterns/file.md, match score if applicable}
- {history check: related investigations referenced}

## Bring back from the floor (feeds intake)

### Hypothesis A check
- Confirm/rule out: {specific floor evidence to look for}
- Strength: how confident does the floor make you?

### Hypothesis B check
{same shape}

### Hypothesis C check
{same shape}

### Surprises to capture
- Anything you didn't expect
- Anything the data missed

### Disposition pre-think
- Is this likely a Kaizen (quick, narrow) or A3 (systemic, broader)?
- Anything pattern-relevant we should capture?
```

The brief is **the starting point of a floor conversation**, not the conclusion. Its purpose is to make floor time maximally productive — the manager walks in knowing what to look for, what to ask, and how to interpret what they hear. The brief is wrong sometimes; that's expected. The brief being *defensible and reproducible* is what matters, not the brief being *right*. The brief is also a historical document — once filed in `investigations/`, it becomes part of the institutional memory.

---

## 14. Assumptions and risks

| Assumption | What breaks if it fails | Mitigation |
|------------|------------------------|------------|
| Source data has been converted via a documented script with passing validation | Calcs return garbage from malformed CSVs; analytical layer becomes untrustworthy without anyone noticing | Every CSV under `data/metrics/` is produced by a script in `conversion/scripts/`, recorded in `conversion/MANIFEST.md`, with validation logged to `conversion/logs/`. Spot-check logs before trusting a new data drop. |
| Conversion scripts are re-run on the documented cadence | Stale data flows through every calc; investigations work on numbers weeks out of date | The conversion README documents the cadence. `metrics/MANIFEST.md` includes a "Generated" timestamp; if it's stale, signal-detect surfaces this prominently. |
| Conversion validation routines stay strict | A loosened validation lets malformed rows through; bugs surface much later as confusing analytical results | Validation routines are version-controlled. Weakening them requires the same scrutiny as a schema change — never weaken to make a stubborn source pass. |
| Source files retain stable structure between runs | Conversion scripts break when humans edit source spreadsheets in unexpected ways | Validation catches most breakage. Fragile sources are flagged in `conversion/MANIFEST.md`'s "Known fragile sources" section. Fix the script, not the source. |
| `.skills/MANIFEST.yaml` stays in sync with the on-disk `SKILL.md` files | Skill descriptions in the manifest drift from skill bodies; the assistant routes to the wrong skill or describes a skill incorrectly | `.skills/.meta/reconcile.py` is run at skill creation time (automatic) and on demand whenever skill files are edited outside the create flow. Content hashes in the manifest let reconcile detect drift quickly. |
| Events are logged with discipline | Cooccurrence checks find nothing; investigations miss obvious causes | Backfill obvious events week 1; close-loop intake systematically generates new events from every floor visit |
| Investigations are saved after every completed brief | History layer stays empty; pattern library never emerges | Required step in investigate skill |
| Floor intakes are completed for every investigation | Closed-loop property collapses; A3s/Kaizens drift from evidence | Required step in close-loop skill; quick-close variant exists so there's no excuse to skip intake even on non-events |
| Patterns are written when causes recur | Same investigations get re-done from scratch | After every 3rd similar investigation, system prompts "this matches X, Y, Z — write a pattern?" |
| Countermeasure-that-worked sections are updated when A3s/Kaizens close | Pattern library learns causes but not solutions | close_a3 and close_kaizen procedures include a step to update the matched pattern's countermeasure section |
| Follow-ups are scheduled when A3s/Kaizens are opened | Outcome tracking fails silently; honest follow-up disappears | open_a3 and open_kaizen procedures require a follow-up schedule before the A3/Kaizen is saved |
| signal-detect runs daily (or near-daily) | Due follow-ups go unsurfaced; A3s/Kaizens drift into open-forever state | follow_up_check.sh can be run on-demand to catch up; INDEX.md sorts by due date so the oldest overdue checks bubble up |
| Calc library is maintained alongside playbooks and procedures | Stale references to non-existent calcs | Each playbook/procedure addition verifies referenced calcs exist |
| Schema version stays synced (`metrics/MANIFEST.md` ↔ `_schema_v1.sh` ↔ all conversion scripts) | Calcs reference wrong columns, or conversion scripts emit wrong schema | Bump all three together via `bump_schema.md`; the procedure enforces it |
| Peer pairings reflect operational reality | Peer benchmarks compare facilities that aren't comparable | Quarterly peer-pairing review with ops |
| Maintenance procedures and templates stay current | Stale references; files built from stale templates | When architecture changes, audit `procedures/` and `templates/` first |
| Skill descriptions stay mutually exclusive | Two skills load at once; contexts mix | Each description includes explicit "do NOT use for X" pointing at siblings; test with prompts that sound similar across all four skills |
| Floor intakes use structured fields, not free-text | Diagnostic value of intake is lost; calibration becomes impossible | close-loop walks the intake conversationally rather than asking for a form; structure is enforced by the skill, not by the user typing into fields |
| The assistant operating the system reads `.skills/README.md` before invoking any skill | Skills get loaded out of protocol, or two skills' instructions get mixed | The README is the protocol contract. If the assistant cannot or does not read it, the operator should paste it in directly at the start of the session. |

---

## 15. Future scope

### 15.1 Additional CI managers in other regions
Add facilities to `INDEX.md`. Their investigations, intakes, A3s, Kaizens, and patterns all share the same folders. Each manager has their own working slice of facilities but shares the calc library, event taxonomy, playbooks, procedures, patterns, and A3/Kaizen conventions. No structural change required.

The CI-portfolio-view becomes especially valuable in this scenario: "show me all open A3s across the network" produces a complete view of CI activity across managers, which is exactly the question regional or corporate CI leadership asks.

### 15.2 Manufacturing
Add `data/manufacturing/` as a parallel root next to `data/facilities/`. Manufacturing-specific calcs go in `calc/manufacturing/`. A manufacturing-specific signal-detect/investigate/close-loop skill set sits alongside the warehouse ones in `.skills/`. Patterns and investigations can be shared (cross-domain learning) or namespaced — start shared, namespace only when interference appears.

### 15.3 Real-time monitoring
If hourly or real-time monitoring becomes needed, add `data/metrics/realtime/` with its own MANIFEST and its own calc family. Don't try to upgrade the existing daily calcs to handle real-time data — the analytical patterns are different enough they deserve a separate layer.

### 15.4 Tier 2 escalation pipeline
If the operation grows enough that some A3s need cross-functional review (engineering, IT, HR partnerships), add an `a3s/escalated/` folder with its own state machine. The architecture absorbs this without restructuring.

### 15.5 Standard-work documentation
Successful A3s and Kaizens often produce updates to SOPs or work instructions. A `data/standard_work/` folder paralleling A3s would capture these. The A3-close procedure would gain a step: "did this Kaizen result in a permanent process change? If so, flag for standard_work update."

### 15.6 What scaling does NOT require
- Directory does not need re-sharding until any region exceeds ~25 facilities
- The four-skill structure handles any scale
- The calc library does not need to be split — it just grows
- The skills protocol (README + MANIFEST + reconcile) is unchanged at scale; only the contents of `MANIFEST.yaml` grow as new skills are added

---

## 16. How to verify

Before extending the architecture, confirm the working slice behaves correctly. These are the canonical test queries:

> Substitute facility/metric names with real values from your environment. The *shape* of each query is what matters.

| Query | Expected behavior | Failure mode to watch for |
|-------|-------------------|---------------------------|
| Fresh session opens, no prior context | Assistant reads `.skills/README.md` first, then `.skills/MANIFEST.yaml`, then proceeds based on user request. | Assistant skips the README or manifest and pattern-matches a skill from training priors; or reads every `SKILL.md` upfront. |
| "What should I look at today?" | Loads signal-detect, returns three sections: new signals, open investigations needing next step, due follow-ups with check results. | Only surfacing new signals; failing to read `investigations/open/` or `follow_ups/INDEX.md`. |
| "Investigate DAL-02's throughput drop" | Loads investigate, runs playbook, drafts brief with bottom-of-brief floor-intake prompts. | Brief missing the "Bring back from the floor" section. |
| "Closing out the DAL-02 investigation" | Loads close-loop, finds the open investigation, walks the intake conversationally field by field. | Loading investigate or signal-detect instead. Or jumping straight to disposition without per-hypothesis intake. |
| "We confirmed it was the cohort thing" | close-loop captures Hypothesis A as CONFIRMED, asks for floor evidence, asks about other hypotheses, doesn't move on until all fields covered. | Recording the confirmation without floor evidence — destroys calibration value. |
| Disposition: "Open both A3 and Kaizen" | close-loop runs open_a3 then open_kaizen, both linked to source investigation, both with follow-up schedules. | Either artifact missing the source link, or either created without a follow-up schedule. |
| A3 follow-up date arrives | signal-detect surfaces the A3, runs `follow_up_check.sh`, reports pass/fail, suggests close or extend. | Follow-up date passes without surfacing; or surfacing without running the check. |
| A3 closes; pattern that matched should learn | close_a3 procedure prompts: "Update patterns/cohort_throughput_dip.md countermeasures section?" with a draft addition. | Pattern doesn't get updated; the countermeasure-that-worked section stays empty after 5+ closed A3s. |
| Same investigation question asked a month apart | Byte-identical calc results from descriptive and diagnostic calcs. | Numbers drift, indicating inline awk. |
| Re-open path: "Floor feedback contradicted the brief" | close-loop runs reopen_template, captures what was wrong, sets state=drafted, prompts user to run investigate again with the new context. | Just closing the original investigation without producing the re-open context for the new one. |
| "Has DAL-02 had similar issues recently?" | investigate or close-loop checks `investigations/INDEX.md` and `patterns/INDEX.md`, returns related cases. | Skipping the history check. |
| "Show me all open A3s across facilities" | Reads `a3s/INDEX.md`, returns list with state, owner, next follow-up date. | Trying to glob `a3s/open/` directly without reading the index. |
| "Did Kaizen K-2026-03-DAL-02-trainer-ratio work?" | Runs `follow_up_check.sh` and `countermeasure_effectiveness.sh`, returns evidence-based pass/fail with the exact calc invocations. | Producing a verdict without calcs. |
| Build two A3s on different days via close-loop | Both have byte-identical structure (same sections, same order). | Shapes diverge — template not being copied. |
| Edit a `SKILL.md` body directly, then start a new session | Reconcile detects content-hash mismatch; flags the drift. Operator runs `.skills/.meta/reconcile.py` to update the manifest. | Manifest description and skill body diverge silently; assistant continues routing to the stale description. |

The reproducibility tests are the calc library's reason for existing. The state-machine tests are close-loop's reason for existing. The pattern-update test is the system's reason for compounding. The protocol tests (first row, last row) are the cross-model portability tests. If any fail, fix that layer before extending.

---

## 17. What's next

Phased rollout, with closed-loop work interleaved rather than tacked on at the end:

1. **Run the verification queries.** Don't extend until they pass.
2. **Phase 1 — Schema and events.** Build all four metric families and the events log. Backfill obvious recent events. Confirm `_schema_v1.sh` matches actual CSV columns. Also: build the skills infrastructure — write `.skills/README.md`, `.skills/MANIFEST.yaml`, and the `.skills/.meta/` tooling so subsequent skills can be created and reconciled cleanly.
3. **Phase 2 — Diagnostic and outcome calcs.** Build the six diagnostic calcs and the three outcome calcs with golden tests. Run against historical data before relying on them.
4. **Phase 3 — One playbook end-to-end, with intake from day one.** Pick the signal type you investigate most often. Write that playbook. Run 5-10 real investigations through it, *and complete intakes for every single one* via close-loop. Save investigations to `YYYY-Qn/`. Refine playbook and intake template based on what felt awkward.
5. **Phase 4 — First A3s and Kaizens.** As investigations confirm hypotheses, open A3s and Kaizens through close-loop. Schedule follow-ups. Let signal-detect surface them when due. Close out the first cycle of A3s and Kaizens with full outcome tracking.
6. **Phase 5 — Pattern emergence with countermeasures.** After ~10 investigations and ~5 closed A3s/Kaizens, write the first patterns. Each pattern's countermeasures-that-worked section starts populating from the closed A3s. From this point on, the system compounds.
7. **Phase 6 — Replicate to other playbooks.** Once one playbook + intake + A3 cycle is solid, the shape is reusable. Write the remaining four playbooks with confidence.
8. **Quarterly review:** audit `procedures/`, `playbooks/`, `patterns/`, A3 conventions against current reality. Update peer pairings. Bump schemas if pipeline changed. Review aging open investigations and A3s — anything stuck in `kaizen_open` or `a3_open` for an unreasonably long time gets re-examined. Run `.skills/.meta/reconcile.py` to verify no skill drift.
9. **Defer until needed:** investigation deep-dive subagent (under whatever subagent convention the host runtime uses), sub-sharded facilities INDEX, parallel manufacturing root, real-time metrics layer, tier-2 escalation pipeline, standard-work folder.

---

## Glossary

- **Facility** — a logistics or operations site. Atomic unit of the architecture.
- **Region / state** — organizational and geographic groupings. Attributes of facilities.
- **Peer pair** — two facilities of the same type that benchmark naturally.
- **Metric family** — one of operational / inputs / exceptions / equipment. Four CSVs per facility.
- **Event** — something that happened in the world that might explain a signal. Logged in `events/`.
- **Signal** — a metric reading worth investigating.
- **Playbook** — an investigation procedure for one signal type. Lives under `investigate/playbooks/`.
- **Pattern** — a recurring causal shape with confirmed countermeasures. Lives in `patterns/`.
- **Investigation** — a complete analysis from signal through floor brief through outcome. Lives in `investigations/`.
- **Investigation state** — the lifecycle phase (drafted, floor_pending, confirmed, ruled_out, inconclusive, kaizen_open, a3_open, superseded, resolved, escalated). Canonical enum in §4. Tracked in investigation file frontmatter.
- **Floor brief** — handoff to the floor: hypotheses, evidence, floor questions, reproducible methodology.
- **Intake** — structured findings captured *from* the floor visit. Walked conversationally by close-loop.
- **A3** — structured root-cause artifact for systemic problems. Lives in `a3s/`.
- **Kaizen** — smaller-scale improvement event for quick targeted changes. Lives in `kaizens/`.
- **Follow-up** — scheduled outcome check tracked in `follow_ups/INDEX.md`, run automatically by signal-detect.
- **Outcome calc** — calc family that verifies whether an intervention worked (follow_up_check, countermeasure_effectiveness, intervention_attribution).
- **Descriptive / diagnostic / comparative / outcome calc** — the four calc families, distinguishing "what / why / how does this compare / did it work".
- **Manifest** — schema-and-freshness contract for one data family. Read once per conversation. (`.skills/MANIFEST.yaml` is the skills registry; `metrics/MANIFEST.md`, `events/MANIFEST.md`, `conversion/MANIFEST.md` are data-side contracts.)
- **Conversion layer** — the bridge between raw source data (Excel files, vendor CSVs, BI exports) and the canonical CSVs that the architecture consumes. Lives in `conversion/` and is operated outside the skills.
- **Conversion boundary** — the line between "raw source data, outside the architecture's trust" and "validated canonical CSVs, inside the architecture's trust." Crossed by conversion scripts that must validate before writing.
- **Validation contract** — the set of guarantees every conversion script provides about its output before that output is trusted by the calc library. Documented in `conversion/MANIFEST.md`.
- **Skill description** — the YAML frontmatter in a `SKILL.md` file (mirrored in `.skills/MANIFEST.yaml`) that determines whether a skill loads. The router.
- **Skills protocol** — the contract documented in `.skills/README.md` that any assistant operating this system must follow: read README, read manifest, match request to skill description, load only the matched skill's `SKILL.md`.
- **Reconcile** — the operation, performed by `.skills/.meta/reconcile.py`, of synchronizing `.skills/MANIFEST.yaml` with the on-disk `SKILL.md` files. Catches drift between what the manifest claims a skill does and what its body actually says.
- **Procedure** — an edit or close-loop recipe under `maintain/procedures/` or `close-loop/procedures/`.
- **Template** — a canonical file skeleton under `maintain/templates/`. Procedures reference templates to enforce shape consistency.
- **Working slice** — the minimal viable instantiation: data layer populated, one playbook working, ≥5 investigations completed with intakes, ≥3 A3s or Kaizens closed with outcome tracking, first pattern written. Beyond this threshold the system is real and compounding.
