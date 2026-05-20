# Procedure: Add a playbook

## When to use

A real investigation hit a signal type with **no matching playbook** — `investigate`
told the user "no playbook matches" and improvised (clearly labeled off-playbook).
Now formalize that improvised work into a repeatable playbook so the next instance
of the signal starts from a procedure instead of a blank page.

Do NOT author a playbook speculatively. A playbook encodes a procedure you have
**actually executed end to end**; if you haven't run a real investigation of this
signal type, you'll be encoding guesses about which calcs matter and in what order.
The signal to add a playbook is the same friction `add_calc.md` describes: a real
case had no procedure, so the next case shouldn't be improvised either. (This is
the Phase 8 expansion path — one new signal type at a time.)

## Prerequisites

- **A completed, real investigation of this signal type** to author from. Its calc
  sequence — the calls that actually resolved the question — becomes the playbook's
  Procedure. Without a source case, stop: run the investigation first (off-playbook),
  then return here.
- **Every calc the playbook will reference already exists and runs.** A playbook must
  never cite an unbuilt calc — `investigate` will hard-stop at that step. Check
  `calc/` and `col_for` for each metric. If a calc is missing, run `add_calc.md`
  first. (Mirror the standing rule: playbooks do not reference `outlier_days.sh`
  until it is authored.)
- **A `signal_type` name** in lowercase snake_case that matches the signal vocabulary
  `signal-detect` and `data/investigations/INDEX.md` use (e.g. `throughput_drop`,
  `damage_spike`, `missort_spike`). The filename IS the routing key — `investigate`
  loads `investigate/playbooks/{signal_type}.md` by exact name.
- **Knowledge of the pattern library state** (`data/patterns/INDEX.md`) so Step 0 can
  name any live pattern whose signal shape this playbook should consult.

## Steps

1. **Copy the template — do not start from a blank file.**
   `cp .skills/maintain/templates/playbook.md .skills/investigate/playbooks/{signal_type}.md`.
   The template carries the section contract (`When to use`, `Prerequisites`,
   `Procedure` with a mandatory **Step 0 pattern check**, hypothesis rubric, floor
   questions, common mistakes, outputs). Match the depth of `throughput_drop.md` —
   it is the reference standard, not `damage_spike.md`'s lighter shape.

2. **Write `When to use` as a precise trigger plus a scope rule-out.** State the
   metric, family, threshold for "meaningful" (e.g. ">=5% off baseline for >=1 week"),
   and the test that rules the playbook OUT (e.g. "if the move is network-wide, it's a
   different conversation"). A vague trigger produces investigations that shouldn't
   have run.

3. **Author the Procedure as the actual calc sequence from the source case**, cheap
   broad-context calcs first, targeted calcs after. **Step 0 must be the
   pattern-library check** (`data/patterns/INDEX.md`) — name the live pattern(s) that
   plausibly match, or state none exists yet. Every computed number is a **named calc
   invocation with `{facility}`/`{window}` placeholders** — no inline awk anywhere
   (the architecture's no-improvised-arithmetic rule applies inside playbooks too).

4. **Confirm every referenced calc exists and runs** before saving. Run each
   invocation once against the source case's facility and window. If any calc is
   missing or errors, the playbook is not ready — fix the calc (via `add_calc.md`),
   don't ship a playbook that references it.

5. **Fill the judgment sections from what the real case taught you:** the hypothesis
   rubric (Strongest / Likely / Possible / Inconclusive), the common floor questions,
   the common mistakes (especially the correlation-vs-causation trap for this signal),
   and the required brief sections. Delete every `{placeholder}` and `<!-- comment -->`.

6. **Cross-link the pattern library.** If a pattern already matches this signal,
   reference it in Step 0. If the source case is the 3rd+ instance of one mechanism,
   ensure a pattern file exists (`add_pattern.md`) so Step 0 has something to consult.

7. **Validate end to end:** re-run the playbook's steps against the source
   investigation's facility and window. The numbers it produces must reproduce the
   figures cited in that investigation's brief. If they don't, the playbook's windows
   or calcs are wrong — fix before saving.

8. **No manifest or registry update is needed for the playbook file itself** —
   `investigate` discovers playbooks by filename, and there is no playbook index.
   BUT: if you also edit a `SKILL.md` (e.g. to move `add_playbook` out of `maintain`'s
   "planned" list into "authored," or to mention the new playbook in `investigate`),
   run `python .skills/.meta/reconcile.py` so `MANIFEST.yaml` content hashes stay in
   sync. Authoring this procedure file and the playbook alone does not change any hash.

9. **Run `bash verify.sh`** — it must stay all-green. If you touched a `SKILL.md`,
   confirm Section 2 (reconcile shows no drift) passes.

## Verification

The procedure completed only if all of the following hold:

- `.skills/investigate/playbooks/{signal_type}.md` exists, follows the template
  structure, and contains no leftover `{placeholders}` or guidance comments.
- **Step 0 checks `data/patterns/INDEX.md`** before drafting hypotheses.
- Every calc invocation in the playbook references a calc that exists and runs;
  none reference an unbuilt calc.
- Re-running the playbook against the source investigation reproduces the numbers
  cited in that investigation's brief.
- `bash verify.sh` exits 0; if any `SKILL.md` changed, `python .skills/.meta/reconcile.py`
  reports no drift.

If any is missing, report the partial state — the playbook is not "added" until
`investigate` can load and run it cleanly.

## Common mistakes

- **Authoring from imagination, not a real case.** A speculative playbook encodes
  guesses about which drivers matter; the first real investigation then fights the
  procedure instead of being helped by it.
- **Referencing an unbuilt calc.** `investigate` follows the playbook literally and
  hard-stops on a missing calc. Build it first (`add_calc.md`).
- **Omitting Step 0.** Without the pattern-library check, the playbook can't compound
  off prior cases — the single biggest payoff of the architecture is lost.
- **Inline arithmetic instead of named calc invocations.** A brief whose numbers can't
  be re-run is not trustworthy; that discipline is the whole point.
- **Misnaming the file.** `investigate` routes by `{signal_type}.md`; a mismatch means
  the playbook silently never loads.
- **Skipping end-to-end validation.** A playbook whose windows don't reproduce the
  source case's numbers will mislead every future investigation that trusts it.
