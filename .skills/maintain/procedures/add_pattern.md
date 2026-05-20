# Procedure: Add a pattern

## When to use

Three or more **closed** investigations have turned out to share the same underlying causal mechanism (not just the same signal — the same *cause*). New-hire cohorts depressing throughput. SOP/layout changes spiking damage. Cross-shift handoff gaps causing missorts. The recurrence is the trigger; a pattern abstracts it into reusable institutional memory plus the countermeasures that have and haven't worked.

Do NOT use to record a single interesting investigation — that's what the investigation file is for. A pattern with one instance is an over-generalization.

> **Build-state note (2026-05-20):** the threshold is **not yet met** in this build. Two investigations are closed (dal-02 throughput / cohort, chr-03 damage / SOP change) and they have *different* mechanisms — no mechanism has 3 instances. So `data/patterns/` is intentionally empty and this procedure has had no first real run. It encodes the discipline for when the third matching investigation lands. Until then, when a closed investigation looks pattern-worthy, record it as a **pattern seed** in the investigation's "Bring back from the floor" section and in the tracker, and wait.

## Prerequisites

- **3+ closed investigations** (state `kaizen_open`, `a3_open`, or `resolved`) with the same mechanism. Have their file paths ready — they become the Historical instances list.
- **At least one closed A3 or Kaizen** among them with a measured outcome, so the "Countermeasures that worked / didn't work" sections cite real results, not theory.
- **A pattern name** that describes the *cause*, not the signal ("Throughput dip after new-hire cohort", not "Low CPH").

## Steps

1. **Confirm the threshold honestly.** List the 3+ investigations and write one line each on why they share a mechanism. If you're stretching to reach three, stop — record seeds and wait. This gate is the whole point; premature patterns are the documented Phase 6 pitfall.

2. **Pick the pattern filename** `data/patterns/{pattern_slug}.md`, slug lowercase-hyphenated from the cause (e.g. `cohort-onboarding-throughput-dip`, `sop-change-damage-spike`).

3. **Copy the template** `maintain/templates/pattern.md` to the target path. Author from the template — it carries the section contract (Signal shape, Co-occurring events, Investigation steps, Floor questions, Resolution timeline, Countermeasures worked/didn't, Historical instances).

4. **Fill Signal shape** from what the matching investigations actually showed — the metric, family, magnitude band, duration, and the secondary tells (co-moving metrics, shift concentration). Generalize across the instances; don't just copy one.

5. **Fill Investigation steps** with the calc sequence that worked across the instances, using `{facility}`/`{signal_date}` placeholders. These should match the relevant playbook's spine so a matched pattern and its playbook agree.

6. **Fill Countermeasures that worked / didn't work** from the closed A3s/Kaizens. Every entry cites its artifact path and the measured result. This section is the reason the pattern is worth more than three separate investigations — do not leave it thin.

7. **Fill Historical instances** with the exact investigation file paths. Minimum three.

8. **Create or update `data/patterns/INDEX.md`.** If it doesn't exist, create it with a header and one row per pattern: `pattern` (name), `file`, `signal` (one-line trigger), `instances` (count). If it exists, append the row. Keep it ≤4KB — it's a catalog, not a copy.

9. **Wire the matching playbook to check the pattern library.** In the relevant `investigate/playbooks/{signal}.md`, ensure an early step reads `data/patterns/INDEX.md` and, on a match, surfaces the pattern's hypotheses and countermeasures as the starting point. (Until the first pattern existed, playbooks annotated this lookup as "Phase 6 deferred — do not stall"; once a pattern lands, that annotation comes off for the matching signal type.)

10. **Update the tracker** — note the new pattern, the instances it abstracts, and flip the relevant Phase 6 exit-criterion line.

## Verification

The procedure completed only if all of the following hold:

- `data/patterns/{slug}.md` exists with **no** unfilled `{...}` placeholders and a Countermeasures section citing at least one real artifact.
- `data/patterns/INDEX.md` lists it.
- The Historical instances list has 3+ real investigation paths, each of which actually exists on disk.
- The matching playbook now references the pattern check (no stale "deferred" note for that signal type).
- `bash verify.sh` still passes.

If any is missing, report the partial state — an unindexed or under-cited pattern is not "added."

## Common mistakes

- **Reaching the threshold by counting signals instead of mechanisms.** Three throughput dips with three different causes are not a pattern. Three throughput dips all caused by new-hire cohorts are.
- **Thin countermeasures.** A pattern without "what worked / what didn't" is just a signal catalog. The countermeasures are the value.
- **Citing instances that aren't closed.** A still-open investigation has no outcome to learn from; wait for disposition.
- **Forgetting the INDEX row or the playbook wire-up.** An unindexed pattern is invisible to the next investigation; an unwired playbook never consults it. Either omission means the pattern can't actually compound.
- **Leaving template placeholders in the file.** A half-filled pattern reads as authoritative but isn't. Fill every section or don't ship it.
