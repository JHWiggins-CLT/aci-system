# ACI System — Onboarding & Deployment-Mode Design (sketch)

> **Status: slices 1–6 BUILT; only the optional capability modules remain.**
> This proposes how a forked or downloaded copy of the system moves from
> portfolio-demo to a real production deployment, and how the system greets a
> first-time operator and remembers their choice. It is a companion to
> `handoff.md` (architecture), not a replacement. Built: the first-run mode gate
> (`config/deployment.yaml(.example)`, `config/deployment.py`, `.skills/README.md`
> Step 0), the `onboard` skill + `SETUP.md`, `reset_demo_state.py`, the
> `add_facility` / `bump_schema` maintain procedures, and the conversion-adapter
> scaffold — all covered by `verify.sh` Sections 11–12. Still pending: a
> mode-aware `verify.sh` split (slice 6, built — structural tier auto-runs in
> production). Only the optional capability modules (Section 5) remain. The
> conversion adapter ships as a template the operator completes.

---

## 1. Goals and non-goals

**Goals**
- A first-time operator who forks/downloads the repo is **greeted with a choice**: explore in **demo** mode, or **set up** the system against their own production data.
- The choice is **remembered**. Pick demo once and every later session stays in demo until the operator explicitly says otherwise — no re-prompting.
- The operator can **flip to setup at any time**, from any mode.
- Production setup reuses the machinery that already exists (the conversion boundary, validators, MANIFEST/audit discipline, maintain templates, `verify.sh`) rather than inventing a parallel path.
- Stay **model-agnostic and stdlib-only** at the core, consistent with the rest of the system. The "wizard" is a guided procedure an LLM walks the operator through, not a GUI.
- **Extensible by construction.** Onboarding is *expected to grow* as the system gains capabilities beyond the core CI loop — reports, presentations, graphing/visualization, exports, integrations. Adding a capability must **add its own setup**, not require rewriting the wizard (Section 5).

**Non-goals**
- Not a magic data importer. The system cannot auto-map an arbitrary spreadsheet to the schema; setup *scaffolds and contract-enforces* the conversion adapter, with the operator (LLM-assisted) doing the column mapping.
- Not an attempt to eliminate the events backfill — that step is irreducibly human; the wizard only structures and validates it.
- Not a multi-tenant or hosted product. One repo = one deployment.

---

## 2. Two modes

| | **demo** | **production** |
|---|---|---|
| Data source | `conversion/scripts/simulate_facility_data.py` (deterministic, fictional 8 facilities) | the operator's real source → a **conversion adapter** they write during setup |
| `data/` contents | committed simulated CSVs + the demo investigations/Kaizens/A3/pattern | the operator's real metrics/events + their own (initially empty) investigation history |
| Purpose | explore the architecture, run the skills against safe sample data | actually do CI work |
| Default | **yes** — the safe sandbox is the sticky default | only after explicit setup |

Demo data is always **regenerable** (`python conversion/scripts/simulate_facility_data.py`) and lives in git history, so choosing demo is never a one-way door.

---

## 3. First-run mode gate (the wizard entry)

### 3.1 Mode state

A single small file records the deployment mode:

```
config/deployment.yaml
---
mode: unset          # unset | demo | production
chosen_at:           # ISO date the mode was last set
chosen_by:           # who/what set it
schema_version: v1   # tracked once production setup runs
capabilities:        # optional feature modules + their settings (Section 5)
  # reporting:    { enabled: false }
  # graphing:     { enabled: false }
  # presentations:{ enabled: false }
notes:               # free text
```

- On a fresh fork the file is either **absent** or `mode: unset`. That is the trigger for the greeting.
- Once a mode is chosen, the file is rewritten with `mode: demo` or `mode: production` and the prompt never fires again unless the operator asks to change it.

### 3.2 Protocol amendment (how the greeting actually happens)

The system is operated by an LLM that reads `.skills/README.md` at session start. We add a **Step 0** to that protocol:

> **Step 0 — Check deployment mode.** Read `config/deployment.yaml` before the
> manifest. If `mode` is `unset` (or the file is missing), do not process any
> request yet — first present the mode choice (below) and persist the answer.
> If `mode` is `demo` or `production`, note it and continue normally.

The greeting the assistant presents on `unset`:

```
This is the ACI System. How do you want to run it?
  • demo  — explore the architecture with built-in simulated data (safe, reversible)
  • setup — configure the system against your own production data
You can switch to setup at any time later by saying "set up production".
```

- **Operator picks demo** → write `mode: demo`, then proceed to a normal demo session (signal-detect, investigate, etc. against the simulated data). All later sessions skip Step 0's prompt.
- **Operator picks setup** → write `mode: production` *only after setup completes* (until then keep `unset` so an interrupted setup re-prompts), and hand off to the `onboard` skill (Section 4).

### 3.3 Flipping rules

- **demo → setup:** always available. Triggered by intent ("set up production", "switch to setup", "onboard my data") → loads the `onboard` skill regardless of current mode. Because this **replaces demo data with real data**, it is gated behind an explicit confirmation (Section 9).
- **production → demo:** not a normal operation (real data would have to be set aside), but supported as a deliberate escape hatch: regenerate the simulated dataset and set `mode: demo`. Documented, confirmation-gated, and noted as "your production data in `data/` will be overwritten by simulated data — back it up first."
- **Re-prompt:** "what mode am I in?" / "reset onboarding" sets `mode: unset` so the greeting fires again.

### 3.4 No-filesystem fallback

Mirroring `.skills/README.md`'s existing "Operating without filesystem access" section: if the assistant can't read files, the operator states the mode verbally at session start. The protocol is identical; only the persistence is manual.

---

## 4. The setup flow (production onboarding)

Delivered as an **`onboard` skill** whose body is a step-by-step procedure (and a human-readable `SETUP.md` mirror for operators who want to read it cold). Each step composes existing machinery.

1. **Facilities.** Collect the operator's real sites (IDs, type, aliases, peer pairings, per-facility targets). Render `data/facilities/INDEX.md` + one profile per site from `.skills/maintain/templates/facility_profile.md`. → uses the planned **`add_facility.md`** maintain procedure.
2. **Schema.** Adopt v1 as-is, or bump it to fit their metrics. → uses the planned **`bump_schema.md`** maintain procedure (coordinated change across `metrics/MANIFEST.md`, `_schema_v1.sh`, conversion, golden tests).
3. **Conversion adapter.** The bespoke step (Section 7): scaffold a conversion script that reads their source (Excel/CSV/WMS export) and emits canonical CSVs **through `conversion/validation/common.py`**. Replaces the simulator as the source of `data/metrics/*`.
4. **Thresholds.** Set per-facility cph targets and exceptions ceilings (used by signal-detect and follow-ups).
5. **Events backfill.** Guide the ~90-day events backfill facility-by-facility, validating against the event taxonomy. (Manual but structured.)
6. **Reset demo state.** Clear the fictional investigations/Kaizens/A3s/pattern so history starts empty (Section 8).
7. **Verify.** Run a production-adapted `verify.sh` (the structural checks; the demo-specific scenario assertions are demo-only) as the acceptance gate. Setup is "done" only when this is green and `mode` flips to `production`.

---

## 5. Extensibility — onboarding grows with new capabilities

> **This is a load-bearing requirement, not an afterthought.** The system will
> gain capabilities beyond the core CI loop — reporting, presentations,
> graphing/visualization, data exports, external integrations. Each may need its
> own setup (config, dependencies, prompts) and its own demo behavior. The design
> below ensures that adding a capability **adds its own onboarding**, so the
> wizard never has to be rewritten as the system expands.

### 5.1 Capabilities are modules that self-declare their setup

Each optional capability is a module that declares, in one place:

- **Name + what it adds** (e.g. `graphing` — renders metric/series charts from the canonical CSVs).
- **A setup contribution** — a small `setup` procedure (prompts + steps), mirroring how `maintain` procedures and skills already self-describe. This is what the wizard runs for that capability.
- **A config fragment it owns** — written under `capabilities:` in `config/deployment.yaml` (enabled flag + per-capability settings).
- **Optional dependencies** — any libraries beyond stdlib it needs, and how to **degrade gracefully** if they're absent.
- **Demo behavior** — how it works against the simulated dataset so it's demonstrable in demo mode, not just production.

### 5.2 The wizard composes core + enabled capabilities (registry, not hardcode)

The onboard flow = the **core steps (Section 4)** + each enabled capability's **setup contribution**, discovered from a **capability registry** rather than a hardcoded list. Adding "graphing" later means dropping in its module + setup contribution; the wizard and the first-run/`enable` flow pick it up automatically. The mode greeting (and a later "enable a capability" intent) can offer the available capabilities.

### 5.3 Config carries capability state

`config/deployment.yaml` gains a `capabilities:` block (enabled/disabled + per-capability settings). Any session can see which output/feature layers are live; the wizard knows what to configure or reconfigure. This block is reserved in the schema from **slice 1**, even before any capability exists, so adding one is additive.

### 5.4 Dependency posture (where stdlib-only bends)

The **core stays stdlib-only**. Output capabilities (graphing, presentations) may legitimately need third-party libraries (a plotting lib, a slide/deck generator). The rule: such deps are **(a) optional, (b) isolated to their capability, (c) checked at enable-time** with a clear "capability unavailable — install X to enable" message, and **never break the core loop** if missing. Rendered artifacts (charts, decks, report files) land in a dedicated output location (e.g. `reports/`, `exports/`) outside the canonical `data/` tree.

### 5.5 Adding a capability is a *partial* re-onboard

Enabling a capability on an existing deployment runs **only that capability's setup contribution** (plus any schema/data needs it has), not the whole flow. The mode gate is unaffected. Demo deployments can enable capabilities against the simulated data too — so a capability can be demoed before it's ever pointed at production data.

This is the invariant the design guarantees: **onboarding adapts as the system grows, because each new element ships its own onboarding** rather than forcing a wizard rewrite.

---

## 6. Components to build

| Component | New / exists | Notes |
|---|---|---|
| `config/deployment.yaml` | new | mode state |
| `.skills/README.md` Step 0 | edit | the mode gate |
| `onboard` skill (`.skills/onboard/SKILL.md`) | new | guided setup; description-gated on "set up / onboard / production data" |
| `SETUP.md` | new | human-readable mirror of the onboard flow |
| `add_facility.md`, `bump_schema.md` | new (planned) | already on the maintain roadmap; setup needs them |
| Conversion adapter scaffold | new | template + `conversion/README` guidance (Section 7) |
| `reset_demo_state.py` (or a maintain procedure) | new | stdlib; clears demo artifacts, optional `--keep-as-examples` |
| Capability registry + per-capability `setup` contributions | new | each optional capability (reports, graphing, presentations, …) self-declares its onboarding; the wizard composes them (Section 5). Establish the pattern when the first capability lands. |
| Validators, MANIFEST discipline, templates, `verify.sh` | exists | reused unchanged |

---

## 7. The conversion adapter (the one genuinely bespoke piece)

This is where setup cannot be fully automated, and the design should be honest about it. Every operation's raw data differs, so the wizard:

- Provides a **scaffold** (`conversion/scripts/adapter_template.py`) with the canonical-CSV writers and the validator calls already wired — the operator only fills the "read my source → map to schema columns" middle.
- Has the **LLM assist the mapping**: it reads the operator's column headers / a sample file and drafts the field mapping, which the operator confirms.
- Relies on **`conversion/validation/common.py` as the safety net**: a bad mapping fails validation loudly (header, date format, sort order, nulls, ranges, taxonomy) before any downstream calc ever sees it. The conversion boundary is exactly the contract that makes a bespoke adapter safe.

The simulator stays in the repo as the demo source and as a **reference implementation** of the adapter contract (it already writes canonical CSVs through the validators).

---

## 8. Data lifecycle and reset

- **`reset_demo_state.py`** removes the demo investigations (`data/investigations/{open,2026-Q*}`), Kaizens, A3s, follow-up rows, and the pattern, resetting their INDEX files to empty headers. Idempotent; refuses to run in `production` mode without `--force` (so it can't nuke real history by accident).
- **Demo data is never destroyed irreversibly** — it regenerates from the simulator and lives in git.
- **Production data** going in is the operator's responsibility to back up; setup warns before any overwrite and never deletes outside `data/`.

---

## 9. Guards and safety

- Switching **into production** (which overwrites `data/`) is confirmation-gated and lists exactly what will change.
- `reset_demo_state.py` is mode-aware (refuses in production without `--force`).
- `mode: production` is only written **after** `verify.sh` passes — an interrupted setup leaves `mode: unset` and re-prompts, so a half-configured deployment never silently presents as ready.
- Nothing in setup touches files outside `data/`, `config/`, and the conversion adapter the operator is writing.

---

## 10. Open questions

- **Schema-bump ergonomics.** Most real operations won't match v1. Is the right default "adopt v1 and map your data onto it" (simpler) or "bump the schema to your reality" (truer)? Leaning: offer both, default to mapping-onto-v1 for first run, with `bump_schema.md` as the power path.
- **How much mapping the LLM should auto-draft** vs. force the operator to specify. Leaning: LLM drafts, operator confirms each field — never silent.
- **Where demo and production data coexist (if at all).** Current sketch: they don't; mode selects one world. An alternative is parallel `data/` and `data_demo/` trees. Leaning: keep it single-world for simplicity; demo is regenerable.
- **Should `config/deployment.yaml` be gitignored in production?** Probably yes once real (it's deployment-local), shipped only as `config/deployment.yaml.example` with `mode: unset`.
- **Output capabilities and the stdlib line (Section 5).** Where do rendered artifacts live (`reports/`, `exports/`?), and how strict is "optional dependency, graceful degrade"? Leaning: a dedicated output dir outside `data/`, capabilities checked at enable-time, core never depends on them. Worth deciding the registry shape before the *first* output capability is built so it doesn't get retrofitted.

---

## 11. Proposed build sequence

1. ✅ **Built (2026-05-20).** `config/deployment.yaml.example` + `config/deployment.py` (stdlib get/set/show helper) + `.skills/README.md` Step 0 + the greeting; the `capabilities:` block is reserved in the schema; live `config/deployment.yaml` is gitignored; covered by `verify.sh` Section 11. *(Smallest slice that delivers the first-run experience.)*
2. ✅ **Built.** `reset_demo_state.py` (mode-aware; refuses in production without `--force`; resets indexes to header-only; leaves metrics/events/facilities untouched).
3. ✅ **Built.** `onboard` skill (`.skills/onboard/SKILL.md`, registered in the manifest) + `SETUP.md` (human mirror).
4. ✅ **Built.** `add_facility.md` and `bump_schema.md` maintain procedures.
5. ✅ **Built.** Conversion adapter scaffold (`conversion/scripts/adapter_template.py`, validator-wired, `--show-schema`, fails loudly when unimplemented) + `conversion/README` guidance.
6. ✅ **Built.** Mode-aware `verify.sh`: it reads `config/deployment.py get` and runs the structural tier only in `production` (skipping the demo-scenario sections, including the simulator re-run that would overwrite real data), all checks in demo/unset, with `--structural` / `--all` overrides. A green production run is the real acceptance gate.

**Remaining (optional):** the capability modules (reports / graphing / presentations) via the Section 5 registry pattern — genuinely optional, built when the first one is wanted.

Slice 1 alone makes the system "greet on first run"; the rest deepens setup behind that gate. The capability-registry pattern (Section 5) is established when the first optional capability (reports/graphing/presentations) is built — at which point onboarding extends itself rather than being rewritten.
