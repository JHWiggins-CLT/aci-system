# Morning brief — fixed output template

The canonical layout for the `signal-detect` morning brief. **Reproduce it exactly,
every day** — same banner, same three sections in the same order (each with a count,
never omitted), same closing line, same spacing (one blank line under each section
header). Consistency is the contract: the operator scans the same places, the same
way, every morning.

The OPEN and DUE sections are rendered by the shared renderer
(`python .skills/review/status.py brief`) so they match the `review` catalog views.
Only the NEW-signals section and the `My read:` line are composed by signal-detect.

## Skeleton (fill the braces; keep everything else verbatim)

(Sections are separated by a blank line of spacing — two blank lines between the
end of one section and the next header, one blank line under each header.)

```
==================================================================
 ACI  ·  Morning brief  ·  {YYYY-MM-DD}
==================================================================


▸ NEW signals ({count})

    {facility-id} ({Facility Name}) · {concern in plain English, with how far off normal} · {date range}
    {…one line per signal, most severe first…}
    {if none: "none — operations within normal variance"}


▸ OPEN investigations ({count})

    {rendered by status.py brief — each line is facility · signal · state}


▸ DUE follow-ups ({count})

    {rendered by status.py brief — append the live PASS/FAIL/NO DATA to any pending row}


My read: {one line — the single thing most worth acting on, or "nothing pressing today"}
```

## Rules for the NEW-signals lines

- **Location, concern, dates — nothing else.** Show the facility id *and* its name
  (from `data/facilities/INDEX.md`), the concern in plain English with its magnitude
  (e.g. "damage spike, ~3× normal"), and the relevant date(s).
- **Do not print calc commands or raw invocations** — the brief is a glance, not a
  worksheet. You still *run* the calcs to get the figures (no improvised numbers),
  and the exact invocations are recorded later in the investigation's methodology if
  one is opened — they just don't belong in the daily brief.
- Rank most-severe first. Annotate an already-investigated signal briefly
  (e.g. "(already investigated)") so it isn't mistaken for new work, after cross-
  checking `data/investigations/INDEX.md`.

## How to produce it

1. Print the banner with today's date.
2. **NEW signals:** run the live threshold scan (`days_below_target.sh` /
   `worst_day.sh`, operational + `--family exceptions`); render one clean line per
   crossing per the rules above; resolve facility names from `data/facilities/INDEX.md`.
3. **OPEN + DUE:** run `python .skills/review/status.py brief` and place its output
   under the NEW section; for any DUE row still `pending`, run its check and append
   the live `PASS`/`FAIL`/`NO DATA`.
4. Close with the one-line `My read:`.

Keep one blank line under each section header; don't pad columns or vary the order.
An empty section is information ("none — queue clear" / "none due") — always show all three.
