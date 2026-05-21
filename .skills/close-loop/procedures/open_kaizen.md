# Procedure: Open a Kaizen

## When to use

The close-loop intake disposition includes "Open Kaizen." A Kaizen is the right artifact for a narrow, well-scoped, facility-specific change with a measurable outcome — not for systemic root-cause work (that's an A3) and not for "we should keep watching this" (that's close + monitor).

Often paired with an A3 in the same disposition: Kaizen for the immediate facility fix, A3 for the systemic problem the case revealed.

## Prerequisites

- The investigation file in `data/investigations/open/` exists and has a filled intake with at least one CONFIRMED hypothesis. A Kaizen without a confirmed cause is just an experiment — name it that.
- The Kaizen has a named owner. "TBD" blocks the procedure.
- At least one outcome metric is identifiable. If nothing measurable changes, the Kaizen has no follow-up and should not be opened.

## Steps

1. **Mint the Kaizen ID** in the form `k-{YYYY-MM}-{facility}-{short-slug}`. Use the month the Kaizen is opened, not the investigation date. Example: `k-2026-05-dal-02-trainer-ratio`.

2. **Copy the template** at `maintain/templates/kaizen.md` to `data/kaizens/open/{kaizen_id}.md`. Do not author from scratch — the template carries the contract (Observation, Change, Tracking, Outcome).

3. **Fill the frontmatter** from the source investigation: `source_investigation`, `facility`, `owner`, `opened` (today). Set `state: open` and `related_pattern` to `(none yet — flagged as seed for ...)` if the intake's section 7 proposed a pattern seed.

4. **Fill the Observation** with the data that motivated the change. Every number must cite the exact calc invocation that produced it. If a number can't be cited, either run the calc or remove the number — do not weaken the contract.

5. **Fill the Change** in one paragraph. The reader must be able to act on it without further clarification. "Improve onboarding" is too vague; "trainer is formally relieved of secondary coverage duties for week-1 of any cohort >4" is right.

6. **Fill the Tracking section**:
   - **Baseline:** the calc-cited current value of the outcome metric.
   - **Target:** the value the metric must reach and by when. Use percentages of baseline when an absolute number isn't natural.
   - **Follow-up checks:** at least one row, each with a future date and the exact `bash calc/outcome/follow_up_check.sh ...` invocation that will verify it. Cohort-event-triggered checks count if their trigger date is also written down somewhere observable (typically a cohort onboarding event).

7. **Append every follow-up row to `data/follow_ups/INDEX.md`** with columns: `artifact_id`, `follow_up_date`, `target_metric`, `target_value`, `direction` (`>=` or `<=`), `calc_invocation`, `status` (`pending` initially, or `PASS`/`FAIL`/`NO DATA` if you fired the check at open time), `last_run` (blank or today). **This step is the gate** — if you cannot append at least one row here, the Kaizen does not open.

8. **Update the investigation file**:
   - Frontmatter: set `state: kaizen_open`, add `kaizen_id: {kaizen_id}`, set `closed_on: {today}`.
   - Move the file from `data/investigations/open/` to `data/investigations/{YYYY-Qn}/`. The quarter is derived from the investigation's `signal_date`, not today.

9. **Update `data/investigations/INDEX.md`**: change the row's `state` to `kaizen_open`, `disposition` to the kaizen_id, and `file` to the new `{YYYY-Qn}/...` path.

10. **Append a row to `data/kaizens/INDEX.md`** (the Kaizen catalog the `review` skill and "show me open Kaizens" queries read): `kaizen_id`, `opened`, `state` (`open`), `facility`, `source` (investigation id), `next_follow_up` (the earliest pending follow-up date from step 7), `file` (`open/{kaizen_id}.md`). Without this, the Kaizen is invisible to `review`.

## Verification

The procedure completed only if all of the following hold:

- A file exists at `data/kaizens/open/{kaizen_id}.md` with non-placeholder Observation, Change, and Tracking sections.
- At least one row in `data/follow_ups/INDEX.md` has `artifact_id = {kaizen_id}`.
- The investigation file has been moved to `{YYYY-Qn}/` and its frontmatter `state` is `kaizen_open`.
- `data/investigations/INDEX.md` shows the same state and the new file path.
- `data/kaizens/INDEX.md` has a row for `{kaizen_id}` (so `review` can list it).
- `verify.sh` Section 6 ("Close-loop artifacts") still passes.

If any of these is missing, report the partial state to the user — do not declare the Kaizen opened.

## Common mistakes

- **Opening a Kaizen with `Owner: TBD`.** An unowned Kaizen has no one to verify the follow-up. Block on owner before any other step.
- **Writing "follow up in 30 days" without a calc invocation.** Vague follow-ups silently rot. The exact command goes in the row.
- **Forgetting to move the investigation file.** The investigation index row points at a stale path; signal-detect's "OPEN" scan misses that the loop closed.
- **Skipping the `data/follow_ups/INDEX.md` append.** The Kaizen file alone is not enough — signal-detect reads the follow-ups index, not Kaizen files.
- **Padding the Tracking section with checks you can't actually fire** (e.g. "ask the owner each week"). Outcome checks must be runnable from a single calc invocation against existing data; everything else is a commitment, not a follow-up.
