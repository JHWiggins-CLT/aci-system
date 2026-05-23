# reports — shareable HTML export

The **rendered / shareable export** capability (`onboarding_design.md` §5.6,
"capability D"): it turns the A3 and Kaizen markdown artifacts the CI loop
produces into polished, self-contained HTML you can hand to someone *outside*
the system — email it to management, print it, drop it in a deck appendix.

It is the counterpart to `review`: `review` shows work *inside* the system
(a read-only catalog for the operator); `export` produces a document to *leave*
the system. The `export` skill (`.skills/export/SKILL.md`) is the operator-facing
front door; `render_html.py` is the engine.

## Two output shapes

- **Per-artifact** — one HTML file per A3 or Kaizen.
- **Bundle** — one HTML file per investigation, tying together the source
  investigation + every A3/Kaizen it produced + the outcome (follow-up) history,
  as one self-contained report. Fixed part order: **At a glance → Investigation →
  A3s → Kaizens → Outcome history.** This is the "give management the whole
  story" report.

## Two guarantees

1. **Consistent structure.** Every A3 renders with the same skeleton; every
   Kaizen does too; every bundle uses the same part order. Content varies; the
   shape never does. Sections are emitted in a canonical order regardless of the
   source file's ordering, and a missing section renders as a labelled
   placeholder so the skeleton is always complete.
   - A3: Current state → Target state → Root cause → Countermeasures → Plan →
     Follow-up schedule → Lessons learned → Closing
   - Kaizen: Observation → Change → Tracking → Outcome
2. **Self-contained output.** Each `.html` file inlines its own CSS — no external
   assets, no network, no build step, print-friendly. One file you can share as-is.
3. **Audience-appropriate.** The calc/bash command invocations woven through the
   source markdown (the operator's reproducibility) are **hidden** in the rendered
   report — the result of a command is kept (`… → 128.10` becomes `128.10`), the
   command itself is dropped, and command-only table columns (e.g. "Calc
   invocation") are removed. Management sees the findings, not the plumbing; the
   exact commands still live in the source `.md` for anyone who needs to reproduce.

## Usage

```bash
# One artifact -> reports/<id>.html
python reports/render_html.py data/a3s/open/a3-2026-05-network-trainer-coverage.md

# A specific output path
python reports/render_html.py data/kaizens/open/k-2026-05-dal-02-trainer-ratio.md -o /tmp/k.html

# A combined investigation bundle (investigation + A3s + Kaizens + outcomes)
python reports/render_html.py --bundle 2026-03-15_dal-02_throughput_drop

# Everything (per-artifact + every bundle) + an index.html landing page
python reports/render_html.py --all

# Only open (or only closed) artifacts; bundles only
python reports/render_html.py --all --state open
python reports/render_html.py --all-bundles
```

`ACI_DATA_DIR` overrides the data root (default `data/`) — used by the test suite
to render against a hermetic fixture; rarely needed otherwise.

## Design notes

- **stdlib only.** No third-party dependencies — the engine emits HTML directly.
  An export that needed a library (PDF, slides) would follow §5.4: optional,
  isolated to its capability, checked at enable-time, graceful degrade.
- **Read-only with respect to `data/`.** Rendering a view never changes the source
  artifact, its INDEX, or its state.
- **Output, not source.** Generated HTML lives here under `reports/` (outside the
  canonical `data/` tree) and is gitignored. The committed capability is
  `render_html.py` + this README + the `export` skill.
