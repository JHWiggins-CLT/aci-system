# Playbook: damage_spike

## When to use

A specific facility's `damage` count (exceptions family) has risen meaningfully above its own recent baseline. "Meaningfully" means: at least one full week of data, the spike is at least ~40% above baseline, and it is not network-wide (peer facilities are not also up). This playbook generalizes to any single exceptions metric that *rises* — `missort`, `mispick`, `lost`, `late_pick` — by substituting the metric name and the `--family exceptions` flag throughout. Damage is the worked example because it is the most common exceptions signal tied to a physical/SOP cause.

This playbook is for **investigative work that produces a floor brief**, not for proactive scanning (use `signal-detect`) and not for returning from the floor (use `close-loop`).

Note on direction: exceptions metrics are "higher is worse." Every calc below that takes a threshold uses `--max` (count/▒check days *above* a ceiling), and `worst_day.sh` auto-selects `max` direction for the exceptions family. This is the mirror image of `throughput_drop.md`, where cph is "lower is worse."

## Prerequisites

- The signal date (typically the midpoint of the spike window, or the date the user noticed).
- The spike window (start and end dates). If unknown, estimate with a quick `worst_day.sh ... --family exceptions` sweep over recent weeks before running the playbook.
- A baseline window — typically the period immediately preceding the spike (the architecture's `change_drivers.sh` takes an explicit baseline range, so use the longest clean pre-spike stretch available).
- A peer facility for comparison. Default: the facility's pairing in `data/facilities/INDEX.md`. If no pairing exists, use the same-type facility with the closest profile.

## Procedure

Run these calcs in order. Stop and reassess if any step contradicts the working hypothesis — the order is "cheap, broad-context calcs first; targeted calcs after."

**Step 1 — Confirm the spike shape.**

```
bash calc/descriptive/avg.sh <facility> damage --family exceptions --start <baseline_start> --end <baseline_end>
bash calc/descriptive/avg.sh <facility> damage --family exceptions --start <spike_start>    --end <spike_end>
bash calc/descriptive/avg.sh <facility> damage --family exceptions --start <post_start>     --end <post_end>
bash calc/descriptive/worst_day.sh <facility> damage --family exceptions \
    --start <spike_start> --end <spike_end>
bash calc/descriptive/days_below_target.sh <facility> damage --max <ceiling> \
    --family exceptions --start <spike_start> --end <spike_end>
```

The three `avg.sh` calls are the magnitude check — the exceptions mirror of `throughput_drop`'s three `avg_cph` numbers. You should see baseline → spike → recovery (or baseline → spike → still-elevated). A spike <~40% above baseline does not justify a full investigation; close the loop with the user first. `worst_day` then gives the peak day and value; `days_below_target --max` counts how many days in the window breached the ceiling (use the facility's normal high-water mark as `<ceiling>`). A spike that breaches on only 1–2 days may be a one-off incident rather than a sustained problem — note that distinction in the brief.

**Step 2 — Rule out network-wide.**

```
bash calc/descriptive/avg.sh <peer_facility> damage --family exceptions --start <baseline_start> --end <baseline_end>
bash calc/descriptive/avg.sh <peer_facility> damage --family exceptions --start <spike_start>    --end <spike_end>
bash calc/descriptive/worst_day.sh <peer_facility> damage --family exceptions \
    --start <spike_start> --end <spike_end>
```

Compare the peer's baseline→spike movement against the facility's. If the peer also spiked by a comparable amount, this is not a facility-specific damage issue — likely a network-wide cause (a shared carrier change, a network SOP rollout, a seasonal volume surge). Reframe with the user.

**Step 3 — Find cooccurring events.**

```
bash calc/diagnostic/cooccurrence.sh <facility> <signal_date> --window 14
```

Read every event returned. For damage specifically, the highest-leverage event types are `sop_change` (bin relocation, pack process change, stacking rule change), `equipment_install` (new MHE that handles product differently), `incident` (a one-time event), and `system_change`. A `sop_change` in the window is the single most common damage driver — that is the chr-03 bin-relocation case.

If nothing returns, widen the window to 21 days. If still nothing, the events log was not maintained for that window — flag this and proceed with reduced confidence.

**Step 4 — Rank upstream drivers.**

```
bash calc/diagnostic/change_drivers.sh <facility> \
    --baseline   <baseline_start>:<baseline_end> \
    --comparison <spike_start>:<spike_end> \
    --top 10
```

`change_drivers` reads all four metric families, so it surfaces the damage spike alongside whatever moved with it. Read the top 5 lines and look for the *mechanistic* link, not just the biggest number. Typical patterns and what they suggest:

- **`damage` is the top mover and little else moved** → an isolated damage cause (handling/SOP/equipment), not a downstream symptom. Lean on Step 3's events.
- **`damage` up alongside `headcount_new`** → inexperienced handlers; cohort-onboarding story (cross-reference `throughput_drop.md` — the same cohort may be depressing cph too).
- **`damage` up alongside `conveyor_down_m` / `mhe_down_m`** → equipment mishandling product; check `equipment_install` events.
- **`damage` up alongside `inbound_units` or `order_mix_complex`** → volume/mix surge straining the handling process; may be capacity-driven rather than a defect.

**Step 5 — Segment the damage metric to localize timing.**

```
bash calc/diagnostic/segment_by.sh <facility> exceptions damage --by dow \
    --start <spike_start> --end <spike_end>
```

If one day-of-week is much worse, that suggests a shift-specific or weekly-cadence cause (a specific crew, a weekly restock that overstacks an aisle). If the spike is even across days, the cause is continuous — consistent with a standing SOP or layout change rather than a periodic event.

**Step 6 — (optional) Drill on a co-moving driver.**

If `change_drivers` named a co-moving metric (e.g. `mispick`, or an equipment downtime column), segment it by dow over the same window to see whether it concentrates on the same days as the damage:

```
bash calc/diagnostic/segment_by.sh <facility> <family> <metric> --by dow \
    --start <spike_start> --end <spike_end>
```

## Hypothesis-generation guidance

Generate hypotheses ranked by evidence weight:

- **Strongest:** `damage` is the top `change_drivers` mover by a wide margin, a matching `sop_change` / `equipment_install` event appears in `cooccurrence` within ~7 days of the spike start, and the peer facility was unaffected. (Pattern: SOP/layout change introduces a handling hazard — the chr-03 bin-relocation shape.)
- **Likely:** `damage` plus one mechanistically-linked driver each moved meaningfully (e.g. damage + new equipment downtime), with a plausible link.
- **Possible:** damage moved but no cooccurring event and no co-mover; state as possible, not likely.
- **Inconclusive — needs floor:** damage spike is real but `change_drivers` shows no clear partner and `cooccurrence` is empty. A legitimate brief disposition — do not invent a cause.

Always include a "Hypothesis ruled out" entry. Common rule-outs for damage_spike:

- Network-wide cause (rules out if the peer facility held steady — Step 2).
- Volume/mix surge (rules out if `inbound_units` and `order_mix_complex` are flat in `change_drivers`).
- Inexperience/cohort (rules out if `headcount_new` is flat — otherwise cross-reference the cohort story).

## Common floor questions

Always ask:

1. "Walk me through any layout, bin, packing, or stacking change in [window]. Anything that didn't make the events log?"
2. "Where physically is the damage happening — a specific zone, aisle, or process step (receiving, putaway, pick, pack, load)?"
3. "Did any new equipment start handling this product, or did existing equipment change behavior?"
4. "Is the damage concentrated in specific SKUs or product types? High-velocity items moved recently?"

Add hypothesis-specific questions only when the data points to them.

## Common mistakes

- **Forgetting the direction flips.** Damage is higher-is-worse. Use `--max` for thresholds; `worst_day` auto-selects `max` for the exceptions family. Passing `--target` (the "below" sense) will count the wrong days.
- **Skipping the peer comparison.** A facility-specific damage spike and a network handling change look identical from one facility alone.
- **Assuming the cooccurring SOP change is causal.** Cooccurrence is correlation. A bin relocation in the window is a strong hypothesis, not a confirmed cause — the floor confirms the *mechanism* (e.g. "tighter aisle + higher stacks → pulldown damage").
- **Reading `change_drivers` top line and stopping.** Damage may be a symptom of a deeper driver further down the list. Read the top 5.
- **Treating the spike's end as "solved."** Damage spikes often resolve when a crew adapts or an informal workaround is applied (as at chr-03, where the floor informally reversed the move). Do not credit a recovery to a formal action unless the action's date precedes the recovery and an outcome calc supports it — and remember the outcome check must track `damage` (`--family exceptions`), not an operational proxy like `error_rate`.

## Outputs

Use [brief_template.md](../brief_template.md) without modification. Required sections:

- "What we see" — peak damage day and value, days-over-ceiling count, peer comparison, one-line characterization of the spike shape.
- "What the data says about why" — at least one hypothesis, with `change_drivers` and `cooccurrence` evidence cited.
- "Questions for the floor" — at minimum the four common questions above plus any hypothesis-specific ones.
- "Methodology" — every calc invocation exactly as you ran it, including `--family exceptions`.
- "Bring back from the floor" — disposition pre-think (Kaizen vs A3 vs no-action) and pattern-worthiness assessment. For a confirmed SOP/layout cause, the outcome follow-up must check `damage --family exceptions`, not a proxy metric.

Save to `data/investigations/open/{date}_{facility}_damage_spike.md` with frontmatter `state: drafted`.
