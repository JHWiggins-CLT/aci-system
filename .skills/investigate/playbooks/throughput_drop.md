# Playbook: throughput_drop

## When to use

A specific facility's CPH has dropped meaningfully below its target or its own recent baseline. "Meaningfully" means: at least one full week of data, drop of at least 5% off baseline, and the drop is not network-wide (peer facilities are not also down). If the drop is network-wide, this is not a throughput investigation — it's likely a demand/volume or system-level issue and a different conversation.

This playbook is for **investigative work that produces a floor brief**, not for proactive scanning (use `signal-detect`) and not for returning from the floor (use `close-loop`).

## Prerequisites

- The signal date (typically the midpoint of the dip window, or the date the user noticed).
- The dip window (start and end dates). If unknown, estimate from a quick `avg_cph.sh` sweep over recent weeks before running the playbook.
- A baseline window — typically the calendar month immediately preceding the dip, or the same month from the prior year if the dip overlaps a seasonal pattern.
- A peer facility for comparison. Default: the facility's pairing in `data/facilities/INDEX.md`. If no pairing exists, use the same-type facility with closest CPH target.

## Procedure

Run these calcs in order. Stop and reassess if any step contradicts the working hypothesis — the order is "cheap, broad-context calcs first; targeted calcs after."

**Step 0 — Check the pattern library first.**

Read `data/patterns/INDEX.md` before drafting hypotheses. If a pattern's signal shape plausibly matches this throughput drop, open the pattern file and let it seed your hypotheses and floor questions — that is the compounding payoff (you start from "which known cause is this?" rather than a blank page). For throughput drops, the live pattern to check is:

- **`equipment_downtime_throughput_drag`** — CPH 8-15% below baseline for ~1 week, V-shaped recovery, with an equipment-family metric (`conveyor_down_m`/`mhe_down_m`) as the dominant driver and quality/headcount_new flat. If Steps 3-4 below confirm that shape, you have a pattern match: surface its "countermeasures that have worked" in the brief and use its investigation steps to confirm fast.

A pattern match is a *starting hypothesis*, not a verdict — still run the confirming steps. If no pattern matches, proceed normally; a novel shape may itself become a future pattern once it recurs (3+ cases → `maintain/procedures/add_pattern.md`).

**Step 1 — Confirm the signal shape.**

```
bash calc/descriptive/avg_cph.sh <facility> --start <baseline_start> --end <baseline_end>
bash calc/descriptive/avg_cph.sh <facility> --start <dip_start>      --end <dip_end>
bash calc/descriptive/avg_cph.sh <facility> --start <post_start>     --end <post_end>
```

Three numbers. You should see baseline → drop → recovery (or baseline → drop → still-dropped). A drop of <5% off baseline does not justify a full investigation; close the loop with the user before continuing.

**Step 2 — Rule out network-wide.**

```
bash calc/descriptive/avg_cph.sh <peer_facility> --start <dip_start> --end <dip_end>
bash calc/descriptive/avg_cph.sh <peer_facility> --start <baseline_start> --end <baseline_end>
```

If the peer also dropped by a comparable amount, this is not a facility-specific throughput issue. Reframe with the user (likely a demand or system signal) and consider a different playbook or off-playbook work.

**Step 3 — Find cooccurring events.**

```
bash calc/diagnostic/cooccurrence.sh <facility> <signal_date> --window 14
```

Read every event returned. Note `system_change`, `deployment`, `training`, `sop_change`, `leadership_change`, and `equipment_install` types — these are the most likely throughput drivers. Weather and audit events are usually low-leverage but worth noting.

If nothing returns, widen the window to 21 days. If still nothing, this means the events log was not maintained for that window — flag this to the user and proceed with reduced confidence.

**Step 4 — Rank upstream drivers.**

```
bash calc/diagnostic/change_drivers.sh <facility> \
    --baseline   <baseline_start>:<baseline_end> \
    --comparison <dip_start>:<dip_end> \
    --top 10
```

This is the highest-leverage calc in the playbook. Read the top 5 lines carefully. Typical patterns and what they suggest:

- **`headcount_new` up >20%** → cohort onboarding (Hypothesis A in the brief). Look for the corresponding `training` event in step 3's output.
- **`mispick` or `missort` up >30%** → quality breakdown that drags throughput via rework. Often co-occurs with cohort onboarding (new pickers make mistakes) but can stand alone (scanner reliability, SOP confusion).
- **`conveyor_down_m` or `mhe_down_m` up >50%** → equipment issue. Cross-check against `equipment_install` events in step 3 (a recent install often precedes a wave of teething downtime).
- **`inbound_units` up >15%** → volume shock; throughput is suppressed by warehouse saturation, not by anything the floor did. Different playbook may apply.
- **`order_mix_complex` up >15%** → mix shift; pickers are doing fundamentally harder work. Often coincides with promotional periods or new SKU launches.
- **`wms_incidents` up at all** → WMS instability; check the events log for `deployment` events and ask the floor whether the system "felt off."

If `change_drivers` shows nothing moving more than 10%, the throughput drop may be unmeasured (a culture or attention issue the floor will need to surface). Note this in the brief honestly rather than over-interpreting small percentages.

**Step 5 — Segment the operational metric to localize timing.**

```
bash calc/diagnostic/segment_by.sh <facility> operational cph --by dow \
    --start <dip_start> --end <dip_end>
```

If one day-of-week is much worse than others, that suggests a shift-specific or weekly-cadence cause (e.g. a single trainer who works only Tuesdays, or a Sunday-night ETL job degrading Monday). If the drop is even across days, the cause is continuous rather than periodic.

For longer dips (>4 weeks), also run `--by month` to confirm the dip is bounded in time.

**Step 6 — (optional) Drill on the strongest driver.**

If `change_drivers` named a specific upstream metric, segment it by dow over the same window:

```
bash calc/diagnostic/segment_by.sh <facility> <family> <metric> --by dow \
    --start <dip_start> --end <dip_end>
```

This often surfaces the shift or day where the driver is concentrated. Use this to sharpen the floor questions.

## Hypothesis-generation guidance

Generate hypotheses ranked by evidence weight, not by your prior beliefs. Use this rubric:

- **Strongest:** a single driver from `change_drivers` moved >50%, a matching event appears in `cooccurrence` within 7 days of the dip start, and the peer facility was unaffected. (Pattern: cohort overload, equipment teething, SOP change.)
- **Likely:** two or more drivers each moved 20-50%, with a plausible mechanistic link (e.g. headcount_new + mispick both up = cohort story).
- **Possible:** one driver moved 10-20%, no cooccurring event, weak mechanism. State as possible, not likely.
- **Inconclusive — needs floor:** no driver moved >10%, no cooccurring events, but the CPH drop is real. This is a legitimate brief disposition. Do not invent a hypothesis to fill a blank.

Always include a "Hypothesis ruled out" entry for what the data already eliminated. The most common rule-outs for throughput_drop:

- Volume/mix shock (rules out if `inbound_units` and `order_mix_complex` are within ±5% of baseline)
- Network-wide demand (rules out if peer facility held steady)
- Equipment failure (rules out if `equipment_install` not in cooccurrence and `*_down_m` columns flat)

## Common floor questions

Always ask:

1. "Walk me through what changed at this facility in [window]. Anything that didn't make it into the events log?"
2. "Did trainer-to-trainee ratio hold during the window? Any cohort that felt rougher than normal?"
3. "Any equipment or scanner issues that didn't escalate to a formal incident?"
4. "Any shift-lead or supervisor changes in the window?"

Add hypothesis-specific questions only when the data points to them. The floor brief's "Bring back from the floor" section enumerates these.

## Common mistakes

- **Skipping the peer comparison.** A facility-specific CPH drop and a network demand shift look identical from one facility's data alone. The peer comparison is what separates them. Never skip it.
- **Reading `change_drivers` top line and stopping.** The top driver is often correlated with — not the cause of — a deeper driver further down. Read at least the top 5 and look for the *mechanistic* link, not the biggest number.
- **Assuming the cooccurring event is causal.** Cooccurrence is correlation. Use it to generate hypotheses; use the floor visit to confirm causation. A training event in the window doesn't mean training caused the dip.
- **Inventing a hypothesis when the data is silent.** If `change_drivers` shows no movement and `cooccurrence` is empty, the right brief disposition is "inconclusive — floor visit needed for hypothesis generation." Forcing a confident hypothesis from weak evidence destroys calibration.
- **Treating the dip's end as a "solution worked."** Many throughput dips resolve on their own (cohort certifies, weather passes, a temporary process glitch self-corrects). Do not credit a recovery to an action unless the action's date precedes the recovery and an outcome calc supports it.

## Outputs

Use [brief_template.md](../brief_template.md) without modification. Required sections:

- "What we see" — three CPH numbers, peer comparison, one-line characterization of the dip shape.
- "What the data says about why" — at least one hypothesis, with `change_drivers` and `cooccurrence` evidence cited.
- "Questions for the floor" — at minimum, the four common questions above plus any hypothesis-specific ones.
- "Methodology" — every calc invocation exactly as you ran it, no shorthand.
- "Bring back from the floor" — disposition pre-think (Kaizen vs A3 vs no-action) and pattern-worthiness assessment.

Save to `data/investigations/open/{date}_{facility}_throughput_drop.md` with frontmatter `state: drafted`.
