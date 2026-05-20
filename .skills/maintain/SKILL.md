---
name: maintain
description: >
  Use when the user wants to edit the architecture itself — add a
  facility, add or update a calc, add or update a playbook, add an
  event type, add or update a pattern, update facility aliases, bump
  the schema version, or deprecate a facility. **Currently scaffold-only:**
  the procedure files that would normally enforce each edit have not
  been authored yet (only the templates in `maintain/templates/` exist).
  Operate as a discipline reminder plus a hand-walked checklist; confirm
  scope with the user, copy any relevant template, execute the edit,
  and verify by hand (`bash verify.sh`, `bash calc/tests/run.sh`,
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

## Current scope (scaffold-only)

This skill is **scaffold-only at present.** The procedure files that would normally enforce each edit (`add_calc.md`, `add_pattern.md`, etc.) have not been authored yet — only the templates in `maintain/templates/` exist. Until the procedure set lands, this skill operates as a **discipline reminder plus a checklist**, not as a turnkey workflow.

When the user asks for an architectural edit:

1. **Name the operation explicitly.** Match the request to one of the planned procedures (list below). If it doesn't map to one, surface that — it may mean the edit is novel and a new procedure should be drafted first.
2. **Confirm with the user before editing.** Walk them through the steps below verbally, agree on scope, then execute. The point of the missing-procedure caveat is that the user is doing the verification you'd otherwise delegate to a procedure file.
3. **Copy the relevant template** from `maintain/templates/` if one exists for the artifact (`facility_profile.md`, `kaizen.md`, `a3.md`). Author from the template, not from scratch.
4. **Execute the edit, then verify by hand.** Read the resulting file. Run any relevant tests (`bash calc/tests/run.sh` after a calc edit, `bash verify.sh` for any structural change, `python .skills/.meta/reconcile.py` after any `SKILL.md` edit).
5. **Update the indexes the edit implies.** A new calc → update `calc/README.md`. A new pattern → update `patterns/INDEX.md`. A new facility → update `facilities/INDEX.md` and add peer-pairing entries.

## Planned procedures (not yet authored)

These procedures are listed in `handoff.md` §2 as part of the full architecture but do not exist on disk yet. Each will, when authored, encode the prerequisites, ordered steps, and verification gate for one operation:

- `add_facility.md` — new site joining the network
- `add_calc.md` — new calc function (descriptive, diagnostic, comparative, or outcome)
- `add_playbook.md` — new investigation procedure for a new signal type
- `add_event_type.md` — extending the event taxonomy
- `add_pattern.md` — new pattern derived from 3+ similar investigations
- `update_pattern.md` — revising an existing pattern (typically from close-loop intake feedback)
- `update_aliases.md` — fixing or extending facility aliases
- `bump_schema.md` — coordinated schema version bump across `metrics/MANIFEST.md`, `_schema_v1.sh`, and every conversion script
- `deprecate_facility.md` — taking a site out of active scope

The implementation plan (Phase 6.5) prioritizes `add_pattern.md`, `update_pattern.md`, and `add_calc.md` for first authoring, because those are the operations the build hits most often. Until those exist, prefer to defer non-urgent edits and batch them when the procedures land — the discipline a procedure encodes is the value, and ad-hoc edits accumulate the inconsistencies the procedures were designed to prevent.

## Inputs and outputs

- **Reads:** the relevant `maintain/templates/*` (when one exists for the artifact), and whichever index or manifest the operation touches. Once procedure files are authored, this list grows to include `maintain/procedures/{operation}.md`.
- **Writes:** new files under `data/`, `calc/`, or `investigate/playbooks/` (depending on operation); updates the relevant index file; updates `metrics/MANIFEST.md` or `_schema_v1.sh` for schema operations.
- **Calls:** calc test runners (`bash calc/tests/run.sh`), the skills reconciler (`python .skills/.meta/reconcile.py`), and the project smoke test (`bash verify.sh`) — whichever applies to the edit type.

## Anti-patterns

- **Do not edit templates during an edit-the-architecture operation.** If the template itself needs to change, that's a separate, deliberate change — templates are load-bearing.
- **Do not skip verification.** Silent partial completion of an architectural edit is the slowest, most expensive failure mode in this system. In scaffold-only mode, verification is done by hand; do not skip it just because no procedure file forces you.
- **Do not edit a pattern file directly without recording why.** Patterns have invariants (countermeasures section format, historical-instances links, signal-shape conventions). Until `update_pattern.md` lands, capture the rationale for the edit in the commit message or tracker note so the next session can audit the change.
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
