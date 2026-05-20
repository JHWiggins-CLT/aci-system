# Procedure: Open an A3

## When to use

The close-loop intake disposition includes "Open A3." An A3 is the right artifact when the confirmed cause is systemic — the floor visit revealed a problem that extends beyond the single facility, or the mechanism reflects a structural assumption the architecture got wrong (e.g. "training capacity is modeled as nominal availability but is actually shared with shift coverage across the network").

If the change is narrow, well-scoped, and facility-specific, use `open_kaizen.md` instead. If both, do both — Kaizen for the immediate facility fix, A3 for the systemic problem.

## Prerequisites

- The investigation file has a filled intake with at least one CONFIRMED hypothesis whose mechanism plausibly applies beyond the single facility. If "could be wider" isn't supported by anything in the intake, the case isn't A3-ready yet — flag it and gather more evidence first (often: poll peer facilities, run `peer_benchmark.sh`, wait for one more similar case).
- A named owner. A3 ownership tends to span multiple groups; pick the one accountable for the countermeasure, not the one closest to the symptom.
- A target state that is measurable and bounded. "Reduce variability" is not a target; "CPH within 5% of baseline through week-1 of next 3 cohort onboardings" is.

## Steps

1. **Mint the A3 ID** as `a3-{YYYY-MM}-{facility_or_network}-{slug}`. Use `network` (not a facility id) when the A3's scope is multi-facility. Example: `a3-2026-07-network-trainer-coverage`.

2. **Copy the template** at `maintain/templates/a3.md` to `data/a3s/open/{a3_id}.md`.

3. **Fill the frontmatter**: `source_investigation`, `network_applicability` (`single facility` | `regional` | `network`), `owner`, `opened: {today}`, `state: open`, `related_pattern` if applicable.

4. **Fill the Current state** auto-populated from the source investigation. Include calc invocations for the signal magnitude, duration of issue, and a business impact estimate (units, dollars, or hours — whichever the operation tracks).

5. **Fill the Target state** with measurable conditions. Each condition specifies a metric, a target value, a time window, and the network scope where it must hold. If the A3 is network-scoped, the target should explicitly say "at all peer facilities" or name the subset where it applies.

6. **Fill the Root cause** with the confirmed hypothesis from the intake. The mechanism matters more than the label — `mechanism: lead trainer pulled to dual-cover during week-1 certification, stretching ratio from 1:4 to 1:6` is right; `cause: trainer ratio` is too thin.

7. **Fill the Countermeasures**. If a pattern matched, the pattern's "Countermeasures that have worked" section is the starting point; cite it. Otherwise, the CI manager picks. Each countermeasure has a named owner.

8. **Fill the Plan table** — one row per action with owner, start, complete-by, status. Empty cells are not allowed; use "TBD" only if explicitly time-boxed (e.g. "TBD by 2026-06-15 network sync").

9. **Fill the Follow-up schedule** with at least one row per countermeasure. Each row: a future date, a one-sentence check description, the exact calc invocation, and the target the calc must satisfy.

10. **Append every follow-up row to `data/follow_ups/INDEX.md`** with `artifact_id = {a3_id}`. **This step is the gate** — if you cannot append at least one row, the A3 does not open.

11. **Update the investigation file**:
    - Frontmatter: set `state: a3_open`, add `a3_id: {a3_id}`, set `closed_on: {today}`.
    - Move from `data/investigations/open/` to `data/investigations/{YYYY-Qn}/` (quarter from the investigation's `signal_date`).

12. **Update `data/investigations/INDEX.md`**: change the row's `state` to `a3_open`, `disposition` to the a3_id, and `file` to the new path.

## Verification

The procedure completed only if all of the following hold:

- A file exists at `data/a3s/open/{a3_id}.md` with non-placeholder Current state, Target state, Root cause, Countermeasures, Plan, and Follow-up schedule sections.
- At least one row in `data/follow_ups/INDEX.md` has `artifact_id = {a3_id}`.
- The investigation file has been moved to `{YYYY-Qn}/` and its frontmatter `state` is `a3_open`.
- `data/investigations/INDEX.md` reflects the same state and path.
- If a pattern was cited, the pattern file's "Countermeasures that have worked" or "didn't work" sections will be updated once outcome data arrives (this is enforced at A3 close, not at open).

If any of these is missing, report the partial state to the user.

## Common mistakes

- **Opening an A3 when a Kaizen would have closed the loop.** A3s are heavy. If the change is narrow and facility-specific, use Kaizen. The right test: would another facility's CI manager benefit from reading this A3? If no, it's a Kaizen.
- **Network-scope claims without network-scope evidence.** "This probably affects other facilities" is hypothesis, not finding. If the intake doesn't have peer-facility data, write the A3 with `network_applicability: single facility` and add a follow-up commitment to poll peers, then upgrade the scope when evidence arrives.
- **Plan table full of TBDs.** TBD is allowed only with a hard deadline for resolving it. Open TBDs hide unfinished planning.
- **Skipping the `data/follow_ups/INDEX.md` append.** Same as Kaizen — signal-detect doesn't read the A3 file, it reads the follow-ups index.
- **Citing a countermeasure from the pattern library without citing the pattern's specific historical instance.** "Pattern X says this works" is weaker than "Pattern X says this worked at facility Y in YYYY-MM, see {a3 path}."
