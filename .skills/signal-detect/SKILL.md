---
name: signal-detect
description: >
  Use when the user asks what to look at today, wants a proactive scan,
  or asks about open investigations and due follow-ups. Returns three
  sections: NEW signals worth investigating, OPEN investigations needing
  the user's next step, and DUE A3/Kaizen follow-ups with their check
  results. Do NOT use for running a specific investigation (use
  `investigate`), for closing out floor findings (use `close-loop`), or
  for editing the architecture (use `maintain`).
triggers:
  - 'what should I look at today'
  - 'anything to follow up'
  - 'daily scan'
  - 'morning briefing'
  - 'open investigations'
  - 'due follow-ups'
---

# Signal Detect

## When to use

The user wants a proactive scan of the operational state across the facility network. Typical phrasings: "what should I look at today," "any signals worth investigating," "anything follow-up-wise," "morning briefing." The scan returns three ranked sections so the user can pick what to act on.

Do NOT use when the user has already identified a specific signal and wants to investigate it — that is the `investigate` skill. Do NOT use when the user is returning from the floor with findings — that is `close-loop`.

## Procedure

1. **Read `data/facilities/INDEX.md`** to scope the scan to the full network.
2. **Read `data/metrics/MANIFEST.md`** to confirm the schema is v1 and the data is fresh. If the "Generated" timestamp is more than 8 days old, surface this prominently before the scan results — stale data means the scan may miss recent signals.
3. **Run three parallel scans:**
   - **NEW signals:** threshold scans across both **operational** and **exceptions** metrics for each facility. Surface metrics that crossed a threshold or showed unusual deviation. Use `days_below_target.sh` and `worst_day.sh` from `calc/descriptive/`:
     - Operational (lower is worse for cph/units/hours_run): e.g. `days_below_target.sh <fac> cph --target <T>`.
     - Exceptions (higher is worse — damage, missort, mispick, lost, late_pick): pass `--family exceptions` and use `--max`: e.g. `days_below_target.sh <fac> damage --max <ceiling> --family exceptions` and `worst_day.sh <fac> damage --family exceptions`. Damage/mispick spikes are common signals and were invisible to this scan before the calcs became family-aware — do not skip the exceptions pass.
     Cite the exact calc invocations in the output.
   - **OPEN investigations:** read every file in `data/investigations/open/`. Everything in that folder is pre-disposition by design (see `handoff.md` §4 active-vs-closed rule), so every file there is something the user still owes action on. Surface each with its `state` value and how long it has been in that state — the state tells the user *what* action: `drafted` (take to floor), `floor_pending` (record intake), `confirmed` (pick disposition: kaizen, a3, or close as resolved), `ruled_out` / `inconclusive` (close as resolved or supersede with a re-open).
   - **DUE follow-ups:** read `data/follow_ups/INDEX.md`. For every row where `Due date ≤ today`, run the calc invocation in that row and report pass/fail. If pass, suggest closing the corresponding A3/Kaizen. If fail, surface prominently and suggest re-opening or extending.
4. **Return all three sections** ranked by urgency within each. Do not collapse them — the user wants to see all three even if one is empty.
5. **Do not start an investigation.** This skill surfaces what to look at; the user decides what to do next.

## Output format (consistent every day)

Render the brief in this fixed shape so the operator sees the **same layout every morning** (the same visual the `review` skill uses). Reuse `status.py` for the OPEN and DUE sections so they match the catalog views exactly.

- **Header banner:** `ACI  ·  Morning brief  ·  <today>`
- **Three sections, always in this order, each with a count — never omit one even if empty** (an empty section is information: "queue clear"):
  1. **NEW signals** — the live threshold scan (unique to signal-detect). Rank by severity; each row: `facility · metric · what crossed the threshold · the exact calc to reproduce it`. Annotate any signal that already has an investigation (cross-check `data/investigations/INDEX.md`) so handled items aren't mistaken for new work.
  2. **OPEN investigations** — render with `python .skills/review/status.py open`. Each row's `state` is the action owed.
  3. **DUE follow-ups** — list with `python .skills/review/status.py due`, then for every row still `pending`, run its `calc_invocation` and report `PASS` / `FAIL` / `NO DATA` inline.
- **Close with one line:** "My read:" + the single highest-priority item to act on.

Do not vary the section order or headers. Consistency is the contract — the operator should be able to scan the same three places in the same order every day.

## Inputs and outputs

- **Reads:** `data/facilities/INDEX.md`, `data/metrics/MANIFEST.md`, `data/metrics/operational/*.csv`, `data/metrics/exceptions/*.csv`, `data/investigations/INDEX.md`, `data/investigations/open/*.md`, `data/follow_ups/INDEX.md`
- **Writes:** nothing. This skill is read-only.
- **Calls:** `calc/descriptive/days_below_target.sh` and `calc/descriptive/worst_day.sh` (both operational and `--family exceptions`), `calc/outcome/follow_up_check.sh`, `python .skills/review/status.py open|due` (for the OPEN/DUE sections' consistent rendering)

## Anti-patterns

- **Do not jump straight into investigating** a signal you surfaced. The user picks from the output; you wait. The boundary between detection and investigation is the user's decision.
- **Do not collapse the three sections** into a single ranked list. The categories carry meaning — they correspond to different user actions.
- **Do not skip the freshness check.** A stale `metrics/MANIFEST.md` timestamp means everything below is suspect; flag it before any scan results.
- **Do not improvise calcs.** Every number in the output traces to a named calc invocation. If a number doesn't have a calc that produces it, that's a gap to flag, not a number to compute inline.

## Variants and edge cases

- **First scan with no open investigations and no follow-ups:** sections OPEN and DUE will both be empty. Return them as empty rather than omitting — the user benefits from seeing that those queues are clear.
- **Many facilities, many signals:** if more than ~10 NEW signals surface, group them by facility before returning so the user can scan by site.
- **A follow-up check errors out:** report the error in the DUE section rather than silently dropping the row. The user needs to know follow-up tracking is broken.

## Verification

The scan output should contain three labeled sections (NEW, OPEN, DUE), each row tied to a specific facility and a specific reproducible calc invocation. If the user could not, from your output alone, re-run any cited calc and get the same number, the output is incomplete.
