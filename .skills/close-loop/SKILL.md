---
name: close-loop
description: >
  Use when the user returns from a floor visit and wants to close out
  an investigation — capture floor findings, decide what comes next
  (Kaizen, A3, close, re-open, escalate), and produce the corresponding
  artifacts with follow-up schedules. Triggers on phrases like "closing
  out the investigation," "back from the floor," "floor findings on X,"
  "we confirmed it was Y," "draft the A3 for Z," "open a Kaizen for W,"
  or any phrasing that indicates the user has been to the floor and is
  bringing findings back. Do NOT use for proactive scans (use
  `signal-detect`), for new investigations (use `investigate`), or for
  editing the architecture (use `maintain`).
triggers:
  - 'closing out'
  - 'back from the floor'
  - 'floor findings'
  - 'we confirmed'
  - 'draft the A3'
  - 'open a Kaizen'
  - 'we ruled out'
---

# Close Loop

## When to use

The user has been to the floor for an investigation drafted earlier (via `investigate`) and is bringing findings back. The job is to capture those findings in a structured intake, decide disposition (close, Kaizen, A3, re-open, escalate), and produce the corresponding artifacts with follow-up tracking.

Also used directly for drafting a Kaizen or A3 that did not come from a prior investigation — e.g. an idea that surfaced on the floor without a formal signal. Use the quick-close template variant in that case.

Do NOT use for new investigations, proactive scans, or architecture edits.

## Procedure

1. **Identify the investigation.** Ask the user by ID, or by facility + date + signal type. Read the investigation file in full. Confirm with the user this is the right one before walking the intake.
2. **Walk `intake_template.md` conversationally.** Do not ask the user to fill out a form. Ask the questions one at a time, in order, in plain English. Record their answers in the structured fields as you go.
3. **For each hypothesis from the brief, capture disposition with floor evidence.** Status (CONFIRMED / RULED OUT / INCONCLUSIVE), specific floor observations or quotes, strength. This section feeds future calibration — do not skip or compress.
4. **Capture what the data missed and surprises.** These are the highest-information fields. If the user is brief on them, probe once with "anything the data didn't show?" but don't force.
5. **Decide disposition with the user.** Multi-select allowed. Common combinations: Kaizen + A3 (Kaizen for the immediate fix, A3 for the systemic root cause); close + pattern update (one-off but the pattern library should learn from it).
6. **Execute downstream procedures based on disposition.** These live in `close-loop/procedures/`:
   - "Open A3" → `procedures/open_a3.md` (procedure moves file to `{YYYY-Qn}/`)
   - "Open Kaizen" → `procedures/open_kaizen.md` (procedure moves file to `{YYYY-Qn}/`)
   - "Close" → set `state: resolved` (or `ruled_out` / `inconclusive` if pre-disposition close), then move the investigation file to `data/investigations/{YYYY-Qn}/`. The quarter is derived from the investigation's `signal_date`.
   - "Re-open" → `procedures/reopen_investigation.md` (procedure moves the original to `{YYYY-Qn}/` and creates a new file in `open/`)
   - "Escalate" → set `state: escalated`, log the handoff target in the file, **then move to `{YYYY-Qn}/`** so signal-detect stops re-surfacing it.

   Every disposition moves the file out of `open/`. This is what keeps `open/` as the canonical "needs your attention" queue.
7. **Update the events log** with floor-attributed observations. Source field is `floor-intake-{date}`. Floor visits are the largest single source of new events; don't skip this.
8. **Update the matched pattern** if the intake suggested a revision. The canonical path is `maintain/procedures/update_pattern.md`, but that procedure has not been authored yet (Phase 6 deferred). Until it lands: edit the pattern file directly, but log the edit's rationale in `tracking.md` decision log so the next session can audit it. Once `update_pattern.md` exists, this step uses it instead.
9. **Schedule follow-ups** for any A3 or Kaizen opened. Every artifact must have at least one row in `data/follow_ups/INDEX.md` with the target metric, target value, follow-up date, and the calc invocation that will verify outcome. The procedures enforce this gate — do not bypass it.

## Inputs and outputs

- **Reads:** the relevant investigation file in `data/investigations/open/`, `intake_template.md` (or quick / reopen variants), `data/patterns/INDEX.md`, `maintain/templates/a3.md`, `maintain/templates/kaizen.md`
- **Writes:** the investigation file (appends intake), possibly moves it to `YYYY-Qn/`. Creates `data/a3s/open/{a3_id}.md` or `data/kaizens/open/{kaizen_id}.md`. Appends to `data/follow_ups/INDEX.md`, `data/events/{facility}.csv`, `data/investigations/INDEX.md` (state column).
- **Calls:** no calcs directly. Procedures may invoke `outcome/follow_up_check.sh` if a follow-up date has already passed at intake time.

## Anti-patterns

- **Do not accept free-text dispositions.** "Yeah, it was the cohort thing" is not a structured disposition. Walk the per-hypothesis fields with floor evidence; that's the data that makes the calibration loop work.
- **Do not skip the events log update.** Floor visits produce events that no other layer captures. Without this step, the cooccurrence calc stays sparse forever.
- **Do not open A3s or Kaizens without scheduling follow-ups.** The procedures should refuse to save the artifact until at least one follow-up row exists.
- **Do not update patterns silently.** The canonical path will be `maintain/procedures/update_pattern.md` once it's authored. Until then, direct edits are allowed but must be logged in the tracker — undocumented pattern edits accumulate inconsistencies.
- **Do not close an investigation without an intake.** Even one-off non-event closes require `quick_close_template.md` — there is no "skip intake" path. The discipline is the architecture's value.

## Variants and edge cases

- **Quick close** (`quick_close_template.md`): for investigations where the floor confirmed the signal was a non-event. Two fields: rationale and pattern feedback. ~150 words total.
- **Re-open** (`reopen_template.md`): for when floor feedback contradicted the brief substantially. The re-opened investigation gets a new ID and a `supersedes` reference to the original.
- **A3 + Kaizen sequenced:** Kaizen for the immediate facility-specific fix, A3 for the network-scope systemic problem the case revealed. Common pattern.
- **No matched pattern:** capture in the intake that no pattern matched, and note whether this case might be the seed of a new pattern (3+ similar cases threshold).

## Verification

A completed close-loop produces:
- An intake appended to the investigation file with all template sections filled
- The investigation file's `state` field updated to match the disposition
- For each "Open A3" / "Open Kaizen" disposition: a corresponding file in `data/a3s/open/` or `data/kaizens/open/` and at least one row in `data/follow_ups/INDEX.md` linked to it
- For each floor-attributed event: a new row in `data/events/{facility}.csv` with source `floor-intake-{date}`
- If a pattern was updated: a corresponding edit visible in the pattern file
- The `data/investigations/INDEX.md` state column updated for this investigation

If the user could not, from these artifacts alone, reconstruct what happened on the floor and what was decided, the close-loop did not complete.
