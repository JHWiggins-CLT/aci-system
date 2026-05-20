# Playbook: {signal_type — e.g. throughput_drop, damage_spike, missort_spike}

<!--
  A playbook is the repeatable investigation procedure for ONE signal type. It
  turns "a number looks wrong" into a floor brief, using only named calc
  invocations (no improvised arithmetic). Author it FROM a real investigation
  you already ran end-to-end — the steps below should be the calcs you actually
  used, in the order that worked. Fill every section. Delete these comments and
  every {placeholder}. Mirror the depth of throughput_drop.md.
-->

## When to use

{The precise signal that triggers this playbook: which metric, which family,
how far off baseline/target, over what minimum window. State the threshold for
"meaningful" (e.g. ">=5% off baseline for >=1 week") and the scope test that
rules the playbook OUT (e.g. "if the move is network-wide, it's a different
conversation").}

This playbook is for **investigative work that produces a floor brief**, not for
proactive scanning (use `signal-detect`) and not for returning from the floor
(use `close-loop`).

## Prerequisites

- The signal date ({how to derive it — usually the midpoint of the move window}).
- The move window (start and end). {How to estimate it if unknown — a quick calc sweep.}
- A baseline window ({the convention — e.g. the prior calendar month}).
- {Any comparison entity the playbook needs — e.g. a peer facility from `data/facilities/INDEX.md`.}

## Procedure

Run these calcs in order. Stop and reassess if any step contradicts the working
hypothesis — the order is "cheap, broad-context calcs first; targeted calcs after."

**Step 0 — Check the pattern library first.**

Read `data/patterns/INDEX.md` before drafting hypotheses. If a pattern's signal
shape plausibly matches this signal, open the pattern file and let it seed your
hypotheses and floor questions. {Name the live pattern(s) most likely to match
this signal type, with a one-line shape, or state "no pattern matches this signal
type yet."} A pattern match is a *starting hypothesis*, not a verdict — still run
the confirming steps. A novel shape may itself become a pattern once it recurs
(3+ cases → `maintain/procedures/add_pattern.md`).

**Step 1 — Confirm the signal shape.**

```
{calc invocation(s) with {facility}/{window} placeholders that establish
 baseline -> move -> recovery (or still-moved)}
```

{What the numbers should show, and the threshold below which a full investigation
is not justified.}

**Step 2 — {rule-out / scope test}.**

```
{calc invocation(s)}
```

{What result reframes the investigation (e.g. peer also moved -> network-wide).}

**Step 3 — Find cooccurring events.**

```
bash calc/diagnostic/cooccurrence.sh {facility} {signal_date} --window 14
```

{Which event types matter most for this signal; what to do if nothing returns
(widen to 21 days; if still empty, flag the events-log gap and proceed with
reduced confidence).}

**Step 4 — Rank upstream drivers.**

```
bash calc/diagnostic/change_drivers.sh {facility} \
    --baseline {baseline_start}:{baseline_end} \
    --comparison {move_start}:{move_end} --top 10
```

{The driver-reading rubric for THIS signal: which upstream metrics, what
magnitude, and the mechanism each implies. Read the top 5, not just the top line.}

**Step 5+ — {targeted calcs: segment_by, correlate, family-specific drills}.**

```
{calc invocation(s)}
```

{What each targeted calc localizes and how it sharpens the floor questions.}

## Hypothesis-generation guidance

Generate hypotheses ranked by evidence weight, not prior belief:

- **Strongest:** {the evidence combination that makes a hypothesis strong for this signal}.
- **Likely:** {two-or-more weaker drivers with a plausible mechanistic link}.
- **Possible:** {a single weak driver; state as possible, not likely}.
- **Inconclusive — needs floor:** {the move is real but the data is silent — a legitimate disposition; do not invent a hypothesis}.

Always include a "Hypothesis ruled out" entry for what the data already eliminated.
Common rule-outs for this signal: {list with the calc condition that rules each out}.

## Common floor questions

Always ask:

1. {question}
2. {question}
3. {question}

Add hypothesis-specific questions only when the data points to them.

## Common mistakes

- {The most common analytical error for this signal type and why it misleads.}
- {Correlation-vs-causation trap specific to this signal.}
- **Inventing a hypothesis when the data is silent.** If the drivers are flat and
  cooccurrence is empty, the right disposition is "inconclusive — floor visit needed."
- **Crediting a recovery to an action** without an outcome calc (`follow_up_check.sh`
  / `countermeasure_effectiveness.sh`) whose dates support the claim.

## Outputs

Use [brief_template.md](../brief_template.md) without modification. Required sections:

- "What we see" — {the headline numbers for this signal} + scope comparison.
- "What the data says about why" — at least one hypothesis with cited calc evidence.
- "Questions for the floor" — the common questions above plus hypothesis-specific ones.
- "Methodology" — every calc invocation exactly as run, no shorthand.
- "Bring back from the floor" — disposition pre-think (Kaizen vs A3 vs no-action) and pattern-worthiness.

Save to `data/investigations/open/{date}_{facility}_{signal_type}.md` with frontmatter `state: drafted`.
