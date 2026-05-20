---
name: investigate
description: >
  Use when the user wants to investigate a specific signal at a specific
  facility — typically picked from the output of `signal-detect` or
  arrived at independently. Runs a playbook end-to-end, executes
  diagnostic calcs, checks pattern history, drafts hypotheses, and
  produces a floor brief saved to `data/investigations/open/` with
  state=drafted. Do NOT use for proactive scans (use `signal-detect`),
  for closing out floor findings (use `close-loop`), or for editing
  the architecture (use `maintain`).
triggers:
  - 'investigate'
  - 'look into'
  - 'dig into'
  - 'why is X dropping'
  - 'what is going on with'
  - 'draft a brief for'
---

# Investigate

## When to use

The user has identified a specific signal at a specific facility and wants a hypothesis-driven investigation that produces a floor brief. Typical phrasings: "investigate the DAL-02 throughput drop," "look into why CHR-03's error rate spiked," "dig into HOU-01's headcount issue."

Do NOT use when the user is asking for a proactive scan — that is `signal-detect`. Do NOT use when the user is returning from the floor with findings on an already-drafted investigation — that is `close-loop`.

## Procedure

1. **Pin down the signal.** Confirm with the user: which facility, which metric, what time window, what magnitude. If any of these is ambiguous, ask before proceeding.
2. **Pick the playbook** that matches the signal type. The playbooks live in `investigate/playbooks/`. If no playbook matches, tell the user and offer to either improvise (clearly marked as off-playbook) or add a new playbook via the `maintain` skill.
3. **Read the playbook in full.** Don't summarize it to yourself — actually load and follow it.
4. **Check history first:**
   - Read `data/investigations/INDEX.md` for prior investigations at the same facility or of the same signal type.
   - Read `data/patterns/INDEX.md` for any pattern whose signal shape matches. The library is live (the first pattern, `equipment_downtime_throughput_drag`, landed 2026-05-20); it may still be small, so if no pattern matches, note that in the brief's methodology section and continue. Do not stall on a thin library.
   - If a pattern matches, that pattern's investigation steps and countermeasures become the starting point for this investigation.
5. **Run the diagnostic calcs in playbook order.** Cite the exact invocation for every calc; never compose inline awk. The order matters — playbooks are sequenced so cheap calcs run first and expensive ones run only if cheaper ones don't resolve the question.
6. **Draft hypotheses ranked by evidence weight.** Each hypothesis carries: a one-sentence mechanism, the calc invocation and number that supports it, the counter-evidence that weakens it, and (if applicable) the pattern it matches.
7. **Produce the floor brief** using `brief_template.md`. Every section must be filled. The "Bring back from the floor" section is mandatory — it is what makes the brief feed into close-loop later.
8. **Save the investigation** to `data/investigations/open/{date}_{facility}_{signal}.md` with frontmatter `state: drafted`. Update `data/investigations/INDEX.md` to add the new row.

## Inputs and outputs

- **Reads:** `investigate/playbooks/{signal_type}.md`, `brief_template.md`, `data/investigations/INDEX.md`, `data/patterns/INDEX.md` (live since 2026-05-20), `data/metrics/operational/{facility}.csv`, `data/events/{facility}.csv`, any historical investigation file referenced.
- **Writes:** `data/investigations/open/{date}_{facility}_{signal}.md`, `data/investigations/INDEX.md` (appends one row).
- **Calls:** every calc the playbook specifies. Currently implemented: `cooccurrence.sh`, `segment_by.sh`, `change_drivers.sh`, `correlate.sh` in `calc/diagnostic/`. `outlier_days.sh` is listed in the handoff but not yet authored — playbooks should not reference it until it exists.

## Anti-patterns

- **Do not skip the history check.** The single biggest source of leverage in this architecture is past investigations; skipping the index lookup means re-doing work that's already been done.
- **Do not produce numbers without calc invocations.** Every figure in the brief traces to a specific named calc with specific arguments. If you find yourself doing inline arithmetic, stop and either add the missing calc (via `maintain`) or escalate the gap to the user.
- **Do not omit the "Bring back from the floor" section.** The brief's purpose is to feed close-loop; without that section, the loop can't close.
- **Do not save the brief in a folder other than `investigations/open/`.** Closed investigations move to `YYYY-Qn/` only after close-loop runs.
- **Do not draft conclusions when the data is inconclusive.** "Inconclusive — needs floor confirmation" is a valid hypothesis state. Forcing a confident hypothesis from weak evidence destroys calibration.

## Variants and edge cases

- **Multiple signals at the same facility:** investigate them separately unless the playbook explicitly handles compound signals. Combining them in one brief usually muddies both.
- **No matching playbook:** tell the user, offer to improvise (clearly labeled), and recommend adding a playbook after the investigation via `maintain/procedures/add_playbook.md`.
- **Strong pattern match (e.g. >0.8 match score):** the brief should lead with the pattern's countermeasures-that-worked as a starting hypothesis, not bury them in section three.
- **Open investigation already exists for the same signal:** ask the user whether to extend the existing investigation or open a new one with a "supersedes" reference.

## Verification

A successful investigation produces:
- A file at `data/investigations/open/{date}_{facility}_{signal}.md` with `state: drafted` in its frontmatter
- A brief inside that file with all sections filled, including hypotheses with calc-cited evidence and the "Bring back from the floor" section
- A new row in `data/investigations/INDEX.md`
- Every number in the brief reproducible by re-running its cited calc

If any of these are missing, the investigation did not complete; do not tell the user it's done.
