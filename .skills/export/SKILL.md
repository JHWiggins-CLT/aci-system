---
name: export
description: >
  Use when the user wants to turn an existing A3 or Kaizen into a polished,
  self-contained document to SHARE with someone OUTSIDE the system — management,
  a sponsor, a peer facility — typically phrased as "export this A3 to HTML,"
  "render the Kaizen as a shareable report," "make this presentable for
  management," "send the dal-02 A3 to my director," "give me an HTML version
  of the open A3s," or "put together the whole dal-02 story (investigation + what
  we did + outcomes) as one report for management." Produces consistently-
  structured HTML — every A3 the same, every Kaizen the same, and a combined
  investigation BUNDLE (investigation + A3s + Kaizens + outcome history) the same
  — written to `reports/`. Do NOT use to BROWSE or list work
  inside the system (use `review`), to draft or close artifacts (use
  `close-loop`), for the daily scan (use `signal-detect`), or to edit the
  architecture (use `maintain`).
triggers:
  - 'export'
  - 'export to html'
  - 'render as html'
  - 'shareable report'
  - 'share with management'
  - 'send to my director'
  - 'presentable version'
  - 'html version of'
  - 'make this presentable'
  - 'the whole story as one report'
  - 'bundle the investigation'
---

# Export

## When to use

The user already has an A3 or Kaizen and wants a polished, self-contained file to
hand to someone **outside** the system — management, a sponsor, another facility.
This is the "rendered / shareable export" capability reserved in
`onboarding_design.md` §5.6 and in `review`'s hand-off note.

The boundary with `review`: `review` shows work *inside* the system (a read-only
catalog/dashboard for the operator). `export` produces a document to *leave* the
system — one shareable HTML file per artifact, with a fixed structure so every A3
reads the same and every Kaizen reads the same. If the user wants to look at
what's open or pull an artifact up on screen, that's `review`; if they want to
*send it to someone*, that's `export`.

## Procedure

1. **Identify the source artifact(s).** Resolve the id the user named against the
   right location (the `review` skill's resolution rules apply):
   - A3 → `data/a3s/{open|closed/YYYY-Qn}/{id}.md`
   - Kaizen → `data/kaizens/{open|closed/YYYY-Qn}/{id}.md`
   If the user asked for a group ("the open A3s," "everything"), use `--all`.

2. **Render with the engine** — do not hand-write HTML, so the output stays
   consistent. Two shapes:
   - **Per-artifact** (one A3/Kaizen → one file):
     - `python reports/render_html.py data/a3s/open/<id>.md`
     - specific path: `python reports/render_html.py <path>.md -o reports/<name>.html`
   - **Bundle** (an investigation + its A3(s) + Kaizen(s) + outcome history as
     one report — the "give management the whole story" shape):
     - `python reports/render_html.py --bundle <investigation_id>`
   - **Everything** (per-artifact + every bundle + an `index.html` landing page):
     - `python reports/render_html.py --all`
     - only open / only closed artifacts: `--all --state open`
     - bundles only: `python reports/render_html.py --all-bundles`

   Pick the shape from the ask: a single artifact to send → per-artifact; "the
   whole dal-02 story / the investigation and what we did about it" → `--bundle`;
   "everything for the review" → `--all`.

3. **Report where it landed.** Output goes to `reports/` (outside the canonical
   `data/` tree). Tell the user the file path(s); each HTML file is fully
   self-contained (inline CSS, no external assets), so it can be emailed,
   printed, or opened directly. `--all` / `--all-bundles` also write
   `reports/index.html` linking every rendered report.

4. **Do not edit the source.** Export is read-only with respect to `data/`. It
   renders a *view* of the artifact; it never changes the artifact, its INDEX, or
   its state. If the artifact's content is wrong, that is a `close-loop` /
   `maintain` job, not an export job.

## Inputs and outputs

- **Reads:** the named A3/Kaizen markdown file(s) under `data/`.
- **Writes:** self-contained `.html` file(s) under `reports/` only. Generated
  HTML is gitignored (it is output, not source); the renderer and this skill are
  the committed capability.
- **Audience cleanup:** the render hides calc/bash command invocations (keeping
  their results) and drops command-only table columns, so the shared report shows
  findings, not plumbing. The exact commands remain in the source `.md`.
- **Calls:** `python reports/render_html.py <source.md | --bundle ID | --all> [options]`.
- **Dependencies:** none beyond the Python standard library (the engine emits
  HTML directly), so this capability degrades to "always available" — there is no
  optional library to install. A capability that needed one (PDF, slides) would
  follow `onboarding_design.md` §5.4: optional, isolated, checked at enable-time.

## Anti-patterns

- **Do not hand-format HTML.** Use `render_html.py` so every A3 and every Kaizen
  comes out structurally identical — that consistency is the whole point.
- **Do not mutate `data/`.** Export never opens, closes, or re-indexes an
  artifact; it only renders one. Changing content is `close-loop`/`maintain`.
- **Do not use this to browse.** "Show me the open Kaizens" is `review`. Export is
  for producing a file to send to someone outside the system.
- **Do not fabricate an artifact.** If the id doesn't resolve, say so (and offer
  `review` to find the right id) — never invent content to render.

## Verification

A correct export run prints the path of each HTML file it wrote under `reports/`,
the source `data/` artifact is unchanged, and opening the file shows the fixed
structure:
- **Per-artifact** — A3: Current state → Target state → Root cause →
  Countermeasures → Plan → Follow-up schedule → Lessons learned → Closing;
  Kaizen: Observation → Change → Tracking → Outcome. Any unfilled section shows
  as a labelled placeholder rather than being dropped.
- **Bundle** — fixed part order: At a glance → Investigation → A3(s) → Kaizen(s)
  → Outcome history, where the embedded A3s/Kaizens keep their per-type skeleton
  and the outcome history is the follow-up rows for the bundle's artifacts.
