# Procedure: Re-open an investigation

## When to use

The close-loop intake disposition is "Re-open" — the floor visit contradicted the original brief enough that the right next step is a new investigation, not a Kaizen or A3 against the original. This is not a failure mode; it's the architecture working correctly. Briefs are sometimes wrong; the discipline is to capture *what was wrong* rather than silently restart.

Do NOT use re-open when:
- The brief was mostly right but missed nuance — that's still a close (Kaizen or A3) with a pattern update.
- The original signal was a non-event — that's `quick_close_template.md` + close.
- You want to extend the same investigation with more data — that's not re-open, that's continuing the existing investigation.

## Prerequisites

- An intake exists on the original investigation, using `reopen_template.md` (not the full intake). The reopen template captures the structured "what was wrong" — without it, the next investigation restarts from zero.
- The "what was wrong" section names at least one hypothesis or piece of data that pulled the original brief in the wrong direction. "The whole brief was wrong" is not specific enough.
- A new investigation can be drafted from the new starting point. If the floor visit raised more questions than it answered, the disposition is usually `inconclusive` (close as monitoring) rather than re-open.

## Steps

1. **Mint a new investigation ID** following the same pattern as the original: `{date}_{facility}_{signal}.md`. The date is the *signal* date, not today — typically the same as the original investigation unless the floor visit identified a different time window.

2. **Create the new investigation file** at `data/investigations/open/{new_id}.md`. Frontmatter must include:
   - `state: drafted`
   - `supersedes: {original_investigation_id}`
   - Standard fields (`facility`, `signal_type`, `signal_date`, `drafted_on`, `investigator`, `playbook`)

3. **Seed the new investigation body** with what the reopen intake established:
   - Carry forward the "Ruled out causes" — these are now known, not hypothesized.
   - Carry forward the "Confirmed floor observations" — these constrain the new hypotheses.
   - Note the "New suspected mechanism" as the leading hypothesis (with appropriate confidence labeling — it's floor-suggested, not yet calc-confirmed).
   - List the "Data that should be re-pulled" as the methodology starting point.

4. **Run the investigate skill on the new investigation.** The new investigation goes through the same playbook flow as any other, just with stronger prior context. Do not skip the playbook — even a strong floor lead deserves the diagnostic discipline.

5. **Update the original investigation file**:
   - Frontmatter: set `state: superseded`, add `superseded_by: {new_id}`, set `closed_on: {today}`.
   - Append the filled `reopen_template.md` content if not already appended.
   - Move from `data/investigations/open/` to `data/investigations/{YYYY-Qn}/` (quarter from the original `signal_date`).

6. **Update `data/investigations/INDEX.md`**:
   - Original row: change `state` to `superseded`, `disposition` to the new investigation ID, `file` to the new `{YYYY-Qn}/` path.
   - New row: append for the new investigation with `state: drafted`.

7. **Log floor-attributed events.** Even a re-open generates events worth logging — appending these to `data/events/{facility}.csv` with source `floor-intake-{date}` is mandatory, same as a regular close.

## Verification

The procedure completed only if all of the following hold:

- The original investigation file is in `{YYYY-Qn}/`, has `state: superseded`, and contains an appended reopen intake.
- A new investigation file exists at `data/investigations/open/{new_id}.md` with `state: drafted` and `supersedes: {original_id}` in frontmatter.
- `data/investigations/INDEX.md` has both rows updated.
- Floor-attributed events have been appended to the events log.

If any of these is missing, report the partial state to the user — do not declare the re-open complete.

## Common mistakes

- **Discarding the original investigation silently.** The original brief was wrong in a *specific* way; that specificity is signal for future investigations. Always file the reopen template before opening the new investigation.
- **Treating re-open as "we'll fix it later."** If you cannot draft the new investigation now, the disposition is `inconclusive` (close as monitoring), not re-open. A re-open with no new investigation is just a closed loop pretending to be open.
- **Re-using the original investigation ID for the new investigation.** This breaks the audit trail. New investigation gets a new ID; the relationship is captured by `supersedes` in the new frontmatter and `superseded_by` in the original.
- **Skipping the events log update.** Same anti-pattern as a regular close. Floor visits are the largest single source of new events; re-opens generate the most because they reveal what the data missed.
- **Re-opening when the brief was directionally right.** If the floor agreed with the strongest hypothesis but disputed the magnitude or mechanism details, that's a confirm-with-revision, not a re-open. Close with a pattern update.
