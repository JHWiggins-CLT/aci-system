# reports — management HTML reports

The "rendered / shareable export" capability (`onboarding_design.md` §5.6): it
turns the CI loop's A3/Kaizen/investigation markdown into polished, self-contained
HTML **written for management** — what was identified, what we found, what we did,
and where it stands. Email it, print it, drop it in a deck.

It is the counterpart to `review`: `review` shows work *inside* the system
(a read-only catalog for the operator); these reports are made to *leave* the
system. The `export` skill (`.skills/export/SKILL.md`) is the operator front door;
`render_html.py` is the engine.

## Two output shapes

- **Per-artifact** — one report per A3 or Kaizen.
- **Bundle** — one report per investigation, telling the whole story: the source
  investigation + every A3/Kaizen it produced + the outcome (follow-up) history,
  with the immediate **facility fix** and the **systemic fix** framed separately.

## What makes it management-grade

1. **Executive synthesis, fixed structure.** Every report is organised under the
   same headings — **The situation → What we found → What we did → Where it
   stands** (Kaizens omit "What we found"). Content varies; the shape does not, so
   every A3 reads the same, every Kaizen reads the same, every bundle reads the same.
2. **No systems jargon.** Calc/bash commands, file paths, artifact IDs, and
   internal procedure/phase references are stripped; metric variable names are
   humanised (`cph` → throughput, `headcount_new` → new-hire headcount). The
   numbers and findings are kept; the exact commands stay in the source `.md`.
3. **Graphs where relevant.** The driving metric's daily trend is drawn as an
   inline **SVG** chart from the real metric data — baseline, dip/spike, recovery,
   with the target line and the signal date marked. No plotting library, no
   external image file.
4. **Self-contained.** Each `.html` inlines its own CSS and SVG — no external
   assets, print-friendly. One file you can share as-is.

## Usage

```bash
# One artifact -> reports/<id>.html
python reports/render_html.py data/a3s/open/a3-2026-05-network-trainer-coverage.md

# The whole story for an investigation (investigation + A3s + Kaizens + outcomes + chart)
python reports/render_html.py --bundle 2026-03-15_dal-02_throughput_drop

# Everything (per-artifact + every bundle) + an index.html landing page
python reports/render_html.py --all

# Only open / only closed artifacts; bundles only
python reports/render_html.py --all --state open
python reports/render_html.py --all-bundles
```

`ACI_DATA_DIR` overrides the data root (default `data/`) — used by the test suite
to render against a hermetic fixture; rarely needed otherwise.

## Notes

- **stdlib only** — the SVG charts are emitted directly; no third-party library.
- **Read-only with respect to `data/`** — rendering never changes the source.
- **Output, not source** — generated HTML lives here under `reports/` and is
  gitignored. The committed capability is `render_html.py` + this README + the
  `export` skill.
