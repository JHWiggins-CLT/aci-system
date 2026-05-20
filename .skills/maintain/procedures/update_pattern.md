# Procedure: Update a pattern

## When to use

An existing pattern needs revision because a new investigation taught the system something. The usual triggers, from `close-loop` intake (handoff §3, "pattern feedback"):

- **Confirms** — a new instance matched the pattern and resolved as expected. Add it to Historical instances; if a countermeasure was applied, record its result.
- **Refutes / refines** — a matched signal turned out to have a different cause, or the pattern's signal-shape band was wrong. Tighten the Signal shape or note the exception.
- **Extends** — a new countermeasure worked (or failed). Add it to the appropriate Countermeasures section with its measured result.

Do NOT use to create a new pattern (`add_pattern.md`) or to fix a typo with no semantic change (just edit and note it in the commit). This procedure is for changes that alter what the pattern *claims*.

> **Build-state note (2026-05-20):** one pattern now exists — `data/patterns/equipment_downtime_throughput_drag.md`. This procedure has not yet had its first run (no new instance or countermeasure outcome has arrived since the pattern was authored). The first natural trigger will be the ral-02 conveyor PM Kaizen closing: its outcome updates the pattern's "countermeasures that worked / didn't work" section.

## Prerequisites

- **The pattern file exists** in `data/patterns/` and the change is real (it alters Signal shape, Investigation steps, Countermeasures, or Historical instances — not just formatting).
- **The evidence is a closed artifact.** A countermeasure result must come from a closed A3/Kaizen or a fired outcome check, not a guess. A refutation must come from a completed investigation with a confirmed different cause.
- **The triggering investigation/intake is identifiable** so the update is traceable to its source.

## Steps

1. **Name the change type** — confirm / refute-refine / extend (above). This determines which sections you touch and keeps the edit scoped.

2. **Read the current pattern file end to end before editing.** Patterns have invariants (countermeasures cite artifacts; historical instances are real paths; signal shape is a generalization, not one instance). Know them before you change anything.

3. **Make the scoped edit:**
   - *Confirm:* append the investigation path to Historical instances; if a countermeasure was applied, add/extend its Countermeasures entry with the measured result.
   - *Refute / refine:* tighten the Signal shape band or add an explicit exception ("does NOT match when ..."). If the pattern was genuinely wrong, say so plainly rather than burying it.
   - *Extend:* add the new countermeasure to "worked" or "didn't work" with its cited result.

4. **Keep every numeric/result claim cited.** Any new countermeasure result or instance points at a real artifact path (A3, Kaizen, investigation, or follow-up row). Uncited claims are exactly the drift this procedure exists to prevent.

5. **Update `data/patterns/INDEX.md`** if the change affects the catalog row — the instance count, or the one-line signal description if you retuned the Signal shape.

6. **Record the rationale.** Until this build had the procedure, the maintain SKILL's anti-pattern said to capture *why* a pattern changed in the commit message or tracker. Keep doing that: the commit message names the triggering investigation and what claim changed. This is the audit trail for a file that is, by design, edited repeatedly over time.

7. **Re-check the consuming playbook.** If you changed Investigation steps or Signal shape, confirm the matching `investigate/playbooks/{signal}.md` still agrees with the pattern (they should describe the same calc spine). Update the playbook if they've diverged.

## Verification

The procedure completed only if all of the following hold:

- The pattern file reflects the change with **no** new uncited claims and no leftover `{...}` placeholders.
- `data/patterns/INDEX.md` matches the file (instance count / signal line current).
- The change is traceable — the commit message or tracker entry names the triggering investigation and the claim that changed.
- The consuming playbook still agrees with the pattern's Signal shape and Investigation steps.
- `bash verify.sh` still passes.

If any is missing, report the partial state — an untraceable or playbook-divergent pattern edit is worse than no edit.

## Common mistakes

- **Editing the pattern without recording why.** A pattern is edited many times across its life; an unexplained change can't be audited or reverted intelligently. Always name the trigger.
- **Adding an instance whose investigation isn't closed.** No disposition means no outcome to learn from.
- **Letting the pattern and its playbook drift.** If the pattern's investigation steps change but the playbook doesn't (or vice versa), a future investigation gets two different answers.
- **Turning a refutation into a new pattern silently.** If the "exception" is really a distinct mechanism with its own 3+ instances, that's `add_pattern.md`, not a footnote here.
- **Scope creep.** One trigger, one scoped edit. Bundling several unrelated pattern changes makes the audit trail useless.
