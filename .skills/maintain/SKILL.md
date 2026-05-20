---
name: maintain
description: >
  Use when the user wants to edit the architecture itself — add a
  facility, add or update a calc, add or update a playbook, add an
  event type, add or update a pattern, update facility aliases, bump
  the schema version, or deprecate a facility. **Partially proceduralized:**
  three procedures are authored and authoritative — `add_calc.md`,
  `add_pattern.md`, `update_pattern.md` in `maintain/procedures/` (plus
  templates in `maintain/templates/`); follow them step by step when they
  match. Every other operation is still hand-walked — confirm scope with
  the user, copy any relevant template, execute, and verify by hand
  (`bash verify.sh`, `bash calc/tests/run.sh`,
  `python .skills/.meta/reconcile.py` as applicable). Do NOT use for
  running investigations (use `investigate`), for proactive scans (use
  `signal-detect`), or for closing the loop on a floor visit (use
  `close-loop`).
triggers:
  - 'add a facility'
  - 'add a calc'
  - 'new playbook'
  - 'update the pattern'
  - 'bump the schema'
  - 'add an event type'
  - 'deprecate'
  - 'update aliases'
---

# Maintain

## When to use

The user wants to change the architecture itself: schema, facilities, calcs, playbooks, patterns, event taxonomy, aliases, or A3/Kaizen conventions.

Do NOT use during normal investigative or close-loop work. Architectural edits during an investigation usually mean the investigation is being contaminated — finish the investigation first, then edit the architecture.

## Current scope

This skill is **partially proceduralized.** Three operations have authored, authoritative procedure files; the rest are still hand-walked.

**Authored procedures (follow them step by step):**

- `procedures/add_calc.md` — new calc function (descriptive, diagnostic, comparative, or outcome)
- `procedures/add_pattern.md` — new pattern derived from 3+ similar investigations
- `procedures/update_pattern.md` — revising an existing pattern (typically from close-loop intake feedback)

When the request matches one of these, **read the procedure and follow it** — its prerequisites, ordered steps, and verification gate are the contract. Do not improvise around it.

**Everything else is hand-walked.** When the user asks for an architectural edit with no procedure yet:

1. **Name the operation explicitly.** Match the request to one of the planned procedures (list below). If it doesn't map to one, surface that — it may mean the edit is novel and a new procedure should be drafted first.
2. **Confirm with the user before editing.** Walk them through the steps verbally, agree on scope, then execute. Without a procedure file, the user is doing the verification you'd otherwise delegate.
3. **Copy the relevant template** from `maintain/templates/` if one exists for the artifact (`facility_profile.md`, `kaizen.md`, `a3.md`, `pattern.md`). Author from the template, not from scratch.
4. **Execute the edit, then verify by hand.** Read the resulting file. Run any relevant tests (`bash calc/tests/run.sh` after a calc edit, `bash verify.sh` for any structural change, `python .skills/.meta/reconcile.py` after any `SKILL.md` edit).
5. **Update the indexes the edit implies.** A new calc → update `calc/README.md`. A new pattern → update `patterns/INDEX.md`. A new facility → update `facilities/INDEX.md` and add peer-pairing entries.

## Planned procedures (not yet authored)

These are listed in `handoff.md` §2 as part of the full architecture but do not exist on disk yet. Each will, when authored, encode the prerequisites, ordered steps, and verification gate for one operation:

- `add_facility.md` — new site joining the network
- `add_playbook.md` — new investigation procedure for a new signal type
- `add_event_type.md` — extending the event taxonomy
- `update_aliases.md` — fixing or extending facility aliases
- `bump_schema.md` — coordinated schema version bump across `metrics/MANIFEST.md`, `_schema_v1.sh`, and every conversion script
- `deprecate_facility.md` — taking a site out of active scope

The implementation plan (Phase 6.5) prioritized `add_pattern.md`, `update_pattern.md`, and `add_calc.md` for first authoring (now done) because those are the operations the build hits most often. For the rest, prefer to defer non-urgent edits and batch them when the procedures land — the discipline a procedure encodes is the value, and ad-hoc edits accumulate the inconsistencies the procedures were designed to prevent. `add_playbook.md` is the next priority (needed at Phase 8).

## Inputs and outputs

- **Reads:** the relevant `maintain/templates/*` (when one exists for the artifact), and whichever index or manifest the operation touches. Once procedure files are authored, this list grows to include `maintain/procedures/{operation}.md`.
- **Writes:** new files under `data/`, `calc/`, or `investigate/playbooks/` (depending on operation); updates the relevant index file; updates `metrics/MANIFEST.md` or `_schema_v1.sh` for schema operations.
- **Calls:** calc test runners (`bash calc/tests/run.sh`), the skills reconciler (`python .skills/.meta/reconcile.py`), and the project smoke test (`bash verify.sh`) — whichever applies to the edit type.

## Anti-patterns

- **Do not edit templates during an edit-the-architecture operation.** If the template itself needs to change, that's a separate, deliberate change — templates are load-bearing.
- **Do not skip verification.** Silent partial completion of an architectural edit is the slowest, most expensive failure mode in this system. In scaffold-only mode, verification is done by hand; do not skip it just because no procedure file forces you.
- **Do not edit a pattern file directly without recording why.** Patterns have invariants (countermeasures section format, historical-instances links, signal-shape conventions). Use `procedures/update_pattern.md` — it requires you to name the triggering investigation and the claim that changed, so the edit stays auditable.
- **Do not perform multiple unrelated maintain operations in one pass.** Each operation has its own verification; mixing them makes it hard to attribute failures.
- **Do not bump the schema and immediately start using the new shape elsewhere.** A schema bump requires conversion scripts to produce the new shape AND every calc to consume it AND every golden test to pass — in the same commit. Partial schema bumps silently corrupt data.

## Variants and edge cases

- **The operation isn't in the planned procedures list.** Treat it as novel — discuss with the user, then author a procedure for it (the meta-operation of adding a new procedure) before executing.
- **The template is stale.** If using a template produces an artifact that's visibly inconsistent with recent examples, the template needs an update first. Pause, fix the template, then resume.
- **Verification fails.** Stop, leave the half-done edit in place, surface the failure to the user. Do not "clean up" by reverting silently — the failure is information about what went wrong.

## Verification

A successful maintain operation produces:
- The new or modified artifact in the right location, matching the relevant template
- Every index file the procedure listed as needing update has been updated
- Every test the procedure listed as needing to pass has passed
- A diff that's reviewable by someone who didn't run the operation — i.e., the change is contained, named, and explained

If any of these are absent, the operation did not complete; report the partial state to the user rather than declaring success.
