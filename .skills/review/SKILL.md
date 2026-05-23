---
name: review
description: >
  Use when the user wants to SEE or BROWSE existing work — list investigations,
  A3s, Kaizens, patterns, or follow-ups; ask what's open, what closed this
  quarter, what's overdue; or pull up a specific artifact by id. Renders a
  consistent catalog/dashboard view (read-only). Do NOT use for the proactive
  daily scan of NEW signals to act on (use `signal-detect`), for running a new
  investigation (use `investigate`), for closing the loop (use `close-loop`), or
  for editing the architecture (use `maintain`).
triggers:
  - 'show me'
  - 'list'
  - 'pull up'
  - 'review'
  - 'what investigations'
  - 'open kaizens'
  - 'open a3s'
  - 'what did we close'
  - 'browse'
  - 'status of'
---

# Review

## When to use

The user wants to look at the body of work that already exists — a catalog, a rollup, or one specific artifact. Typical phrasings: "show me my open Kaizens," "list the investigations at chr-03," "what did we close this quarter," "pull up the dal-02 A3," "what's the status of our follow-ups."

This is the **browse / show** counterpart to `signal-detect`. The boundary: `signal-detect` answers *"what new thing should I act on today?"* (a forward-looking action queue that runs live calcs). `review` answers *"show me what we already have"* (a backward-looking catalog of stored artifacts, read-only). If the user wants the morning scan, that's `signal-detect`, not this.

## Procedure

1. **For any list / rollup, use the renderer** — do not hand-format, so the output stays consistent:
   - Dashboard rollup: `python .skills/review/status.py`
   - A category: `python .skills/review/status.py investigations | a3s | kaizens | patterns | follow-ups`
   - The action queue: `python .skills/review/status.py open`
   - Due follow-ups: `python .skills/review/status.py due [--asof YYYY-MM-DD]`
   Present the script's output as-is (it already carries the standard ACI banner + sections).

2. **To filter** (by facility, state, quarter), run the relevant category view and narrow the rows in your reply — keep the same columns/visual the script uses. Don't invent a different layout.

3. **To open a specific artifact**, resolve its id against the right INDEX, then read the file and summarize it in the consistent shape (header line + the artifact's key sections). Cite the file path so the user can open it directly:
   - investigation → `data/investigations/{open|YYYY-Qn}/{id}.md`
   - A3 → `data/a3s/{open|closed/YYYY-Qn}/{id}.md`
   - Kaizen → `data/kaizens/{open|closed/YYYY-Qn}/{id}.md`
   - pattern → `data/patterns/{name}.md`

4. **If an id or filter returns nothing**, say so plainly and show the closest catalog (e.g. "no A3 by that id; here are the open A3s"). Never fabricate an artifact.

## Inputs and outputs

- **Reads:** `.skills/review/status.py`, the INDEX files under `data/`, and any specific artifact file the user names.
- **Writes:** nothing. `review` is strictly read-only — it never runs outcome calcs, opens/closes artifacts, or edits indexes.
- **Calls:** `python .skills/review/status.py <view>`.

## Anti-patterns

- **Do not run outcome calcs or edit anything.** Surfacing a stale recorded status is correct for `review`; *re-running* the check is `signal-detect`'s job, and *changing* an artifact is `close-loop`/`maintain`.
- **Do not duplicate the morning scan.** If the user actually wants "what should I look at today," hand off to `signal-detect`.
- **Do not hand-format catalogs.** Use `status.py` so every list looks the same; this is the whole point of the capability.
- **Do not fabricate.** If the index doesn't list it, it doesn't exist — say so.

## Verification

A review response either reproduces `status.py` output verbatim (for lists/rollups) or summarizes a real on-disk artifact with its file path. If the user could not re-run the same `status.py` command (or open the cited file) and see what you showed, the response is wrong.

## Note on rendered/shareable reports

`review` shows work *inside* the system. Producing a polished, self-contained document to share with someone *outside* it is the **`export`** skill (`.skills/export/SKILL.md`, engine `reports/render_html.py`) — it renders an A3 or Kaizen to consistently-structured, self-contained HTML under `reports/`. This is the "export this" hand-off the capability registry reserved: when a user wants to *send* an artifact to management (not just look at it), route to `export`. Boundary — if they want to **see/browse** work that's `review`; if they want a file to **share outside the system** that's `export`.
