# Morning brief — fixed output template

This is the canonical layout for the `signal-detect` morning brief. **Reproduce it
exactly, every day** — same banner, same three sections in the same order (each
with a count, never omitted even when empty), same closing line. Consistency is
the contract: the operator scans the same places in the same order daily.

The OPEN and DUE sections are rendered by the shared renderer
(`python .skills/review/status.py brief`) so they are byte-for-byte consistent
with the `review` skill's catalog views. Only the NEW-signals section and the
`My read:` line are composed by signal-detect.

## Skeleton (fill the bracketed parts; keep everything else verbatim)

```
==================================================================
 ACI  ·  Morning brief  ·  {YYYY-MM-DD}
==================================================================

▸ NEW signals ({count})
    {facility} · {metric} · {what crossed the threshold} · `{calc to reproduce}`
    {…one row per signal, ranked most severe first…}
    {annotate any signal that already has an investigation: "(already investigated → {id})"}
    {if none: "(none — operations within normal variance)"}

▸ OPEN investigations ({count})
    {from `status.py brief` — each row's state = the action owed}
    {if none: "(queue clear)"}

▸ DUE follow-ups ({count})
    {from `status.py brief`, then re-run each pending check's calc and append its
     live result inline: PASS / FAIL / NO DATA}
    {if none: "(none due)"}

My read: {one line — the single highest-priority item to act on, or "nothing pressing today"}
```

## How to produce it

1. Print the banner with today's date.
2. **NEW signals:** run the live threshold scan (`days_below_target.sh` /
   `worst_day.sh`, operational + `--family exceptions`); render one row per
   crossing in the format above; cross-check `data/investigations/INDEX.md` and
   annotate already-handled ones.
3. **OPEN + DUE:** run `python .skills/review/status.py brief` and place its output
   under the NEW section. For every DUE row still `pending`, run its
   `calc_invocation` and append the live `PASS`/`FAIL`/`NO DATA` result.
4. Close with the single-line `My read:` recommendation.

Do not vary the banner, section names, or order. An empty section is information
("queue clear" / "none due"), so always show all three.
