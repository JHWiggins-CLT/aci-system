#!/usr/bin/env python3
"""render_html.py — render ACI A3 / Kaizen artifacts (and combined investigation
bundles) into management-facing, self-contained HTML reports.

This is the "rendered / shareable export" capability (onboarding_design.md §5.6).
It turns the CI loop's markdown artifacts into a polished, single-file report you
can hand to management — focused on what they care about, not the systems detail:

    The situation  →  What we found  →  What we did  →  Where it stands

Design choices that make it management-grade:

  * **Executive synthesis, fixed structure.** Each report is reorganised under the
    headings above (every A3 the same, every Kaizen the same, every bundle the
    same). Content varies; the shape does not.
  * **No systems jargon.** Calc/bash commands, file paths, artifact IDs, internal
    procedure/phase references are stripped; metric variable names are humanised
    (`cph` → throughput, `headcount_new` → new-hire headcount). Numbers are kept.
  * **Graphs where relevant.** The driving metric's daily trend is drawn as an
    inline SVG chart from the real metric data — baseline, dip/spike, recovery,
    with the target line and the signal date marked. No plotting library, no
    external image: the SVG is inline, so the file stays self-contained.
  * **Self-contained.** Each `.html` inlines its own CSS + SVG — emailable,
    printable, no external assets.

Constraints (ACI model, onboarding_design.md §5.4): stdlib only; reads markdown +
CSV under `data/`, writes HTML under `reports/` (outside `data/`), never mutating
the canonical tree; deterministic; model-agnostic.

Usage:
  python reports/render_html.py data/a3s/open/<id>.md            # one artifact
  python reports/render_html.py data/a3s/open/<id>.md -o out.html
  python reports/render_html.py --bundle <investigation_id>      # combined report
  python reports/render_html.py --all                            # everything + index
  python reports/render_html.py --all --state open               # only open artifacts
  python reports/render_html.py --all-bundles                    # every bundle + index
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# Data root is overridable (ACI_DATA_DIR) so the renderer can be pointed at any
# canonical tree — used by the test suite to render against a hermetic fixture.
DATA = Path(os.environ.get("ACI_DATA_DIR") or (REPO / "data"))
DEFAULT_OUT = REPO / "reports"

TYPE_LABEL = {"a3": "A3", "kaizen": "Kaizen"}

INDEXES = {
    "investigations": (lambda: DATA / "investigations/INDEX.md", "## Investigations"),
    "a3s": (lambda: DATA / "a3s/INDEX.md", "## A3s"),
    "kaizens": (lambda: DATA / "kaizens/INDEX.md", "## Kaizens"),
    "follow-ups": (lambda: DATA / "follow_ups/INDEX.md", "## Rows"),
}

# signal_type -> (metric family, csv column, human label, unit)
SIGNAL_METRIC = {
    "throughput_drop": ("operational", "cph", "Throughput", "cases/hr"),
    "damage_spike": ("exceptions", "damage", "Damage", "units/day"),
    "error_spike": ("operational", "error_rate", "Error rate", "%"),
}

# Humanise the system's metric variable names for a non-technical reader.
METRIC_HUMAN = {
    "cph": "throughput", "mispick": "mispicks", "mispicks": "mispicks",
    "damage": "damage", "error_rate": "error rate", "missort": "missorts",
    "lost": "lost units", "late_pick": "late picks", "headcount_new": "new-hire headcount",
    "conveyor_down_m": "conveyor downtime", "mhe_down_m": "equipment downtime",
    "wms_incidents": "WMS incidents", "scanner_faults": "scanner faults",
    "inbound_units": "inbound volume", "order_mix_complex": "complex-order mix",
    "hours_run": "run hours", "units": "units",
}


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    fm = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm, text[end + len("\n---\n"):]


def strip_html_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def parse_artifact(text: str) -> dict:
    fm, body = split_frontmatter(text)
    lines = body.splitlines()
    title, title_idx = "", None
    for i, line in enumerate(lines):
        m = re.match(r"^#\s+(.*)$", line)
        if m:
            title, title_idx = m.group(1).strip(), i
            break
    meta: list[tuple[str, str]] = []
    sections: list[tuple[str, list[str]]] = []
    cur_h, cur_c = None, []
    for line in lines[(title_idx + 1) if title_idx is not None else 0:]:
        h = re.match(r"^##\s+(.*)$", line)
        if h:
            if cur_h is not None:
                sections.append((cur_h, cur_c))
            cur_h, cur_c = h.group(1).strip(), []
            continue
        if cur_h is None:
            fld = re.match(r"^\*\*(.+?):\*\*\s*(.*)$", line.strip())
            if fld:
                meta.append((fld.group(1).strip(), fld.group(2).strip()))
            continue
        cur_c.append(line)
    if cur_h is not None:
        sections.append((cur_h, cur_c))
    return {"frontmatter": fm, "title": title, "meta": meta, "sections": sections}


def detect_type(parsed: dict) -> str:
    title = parsed["title"].lower()
    fm = parsed["frontmatter"]
    keys = {k.lower() for k, _ in parsed["meta"]}
    mp = {k.lower(): v for k, v in parsed["meta"]}
    if title.startswith("a3:") or "a3_id" in fm or "a3 id" in keys:
        return "a3"
    if title.startswith("kaizen:") or "kaizen_id" in fm or "kaizen id" in keys:
        return "kaizen"
    ident = mp.get("a3 id") or mp.get("kaizen id") or fm.get("a3_id") or fm.get("kaizen_id") or ""
    if ident.startswith("a3-"):
        return "a3"
    if ident.startswith("k-"):
        return "kaizen"
    raise ValueError("could not determine artifact type (not an A3 or Kaizen)")


def display_title(title: str) -> str:
    return re.sub(r"^(A3|Kaizen):\s*", "", title).strip()


def meta_value(parsed: dict, *names: str) -> str:
    lower = {k.lower(): v for k, v in parsed["meta"]}
    for n in names:
        if lower.get(n.lower()):
            return lower[n.lower()]
    fm = parsed["frontmatter"]
    for n in names:
        key = n.lower().replace(" ", "_")
        if fm.get(key):
            return fm[key]
    return ""


def grab_field(text: str, name: str) -> str:
    m = re.search(rf"^\*\*{re.escape(name)}:\*\*\s*(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


def section_lines(parsed: dict, name: str) -> list[str]:
    for h, c in parsed["sections"]:
        if h.strip().lower() == name.lower():
            return c
    return []


def is_placeholder(lines: list[str]) -> bool:
    txt = " ".join(l.strip() for l in lines).strip()
    return (not txt) or bool(re.fullmatch(r"\*[^*].*\*", txt) and
                             re.search(r"fill|at close|auto-populat", txt, re.I))


# --------------------------------------------------------------------------- #
# Jargon stripping (commands, paths, IDs, variable names)
# --------------------------------------------------------------------------- #
_CMD_SPAN = (r"`(?:bash|python|sh)\b[^`]*`|`[^`]*\bcalc/[^`]*`|`[^`]*\.sh\b[^`]*`")
_PATH = re.compile(r"`?\b(?:data|calc|conversion|config|investigations|patterns|kaizens|"
                   r"a3s|maintain|\.skills|follow_ups|simulate|reports)/[\w./*<>-]*`?")
_FILE = re.compile(r"`?\b[\w.-]+\.(?:md|csv|py|sh|ya?ml|json)\b`?")
_ID = re.compile(r"`?\b(?:a3|k)-\d{4}-\d{2}-[\w-]+`?|\b\d{4}-\d{2}-\d{2}_[\w-]+\b")


def _tidy(md: str) -> str:
    md = re.sub(r"\(\s*[);,]*\s*\)", "", md)              # empty / debris parens
    md = re.sub(r"\s*[—–-]\s*([.;,)])", r"\1", md)        # dangling dash before punct
    md = re.sub(r"\s*[—–]\s*$", "", md, flags=re.M)       # trailing dash
    md = re.sub(r"[ \t]{2,}", " ", md)
    md = re.sub(r"\s+([,.;:)])", r"\1", md)
    md = re.sub(r"([(])\s+", r"\1", md)
    md = re.sub(r"\(\s*\)", "", md)
    md = re.sub(r"^[ \t,;:—–-]+", "", md, flags=re.M)     # leading debris per line
    md = re.sub(r"[ \t]+$", "", md, flags=re.M)
    return md


def _strip_commands(md: str) -> str:
    md = re.sub(rf"(?:{_CMD_SPAN})\s*(?:→|->)\s*", "", md)
    md = re.sub(rf"\s*(?:,\s*)?(?:as\s+)?"
                rf"(?:confirmed|verified|measured|shown|ranked|ranks|per|via|by|see|from|and)\s+"
                rf"(?:{_CMD_SPAN})", "", md, flags=re.I)
    md = re.sub(_CMD_SPAN, "", md)
    return md


def _humanise_metrics(md: str) -> str:
    def code(m):
        inner = m.group(1).strip()
        return METRIC_HUMAN.get(inner, inner.replace("_", " "))
    md = re.sub(r"`([^`]+)`", code, md)                  # de-code, humanising metrics
    for k, v in METRIC_HUMAN.items():
        if "_" in k:
            md = re.sub(rf"\b{re.escape(k)}\b", v, md)
    # KPI acronym: "cph" as a metric -> throughput; as a unit after a number -> cases/hr
    def cph(m):
        pre = md[max(0, m.start() - 12):m.start()]
        return "cases/hr" if re.search(r"\d\s*$", pre) else "throughput"
    md = re.sub(r"\bcph\b", cph, md, flags=re.I)
    return md


def humanise_metric_label(s: str) -> str:
    """Token-level humanise for the outcome table's metric column."""
    s = re.sub(r"[A-Za-z_]+", lambda m: METRIC_HUMAN.get(m.group(0).lower(), m.group(0)), s)
    return s.replace("~", " vs ")


def clean(md: str) -> str:
    """Full management cleanup: commands, paths, files, IDs, variable names, refs."""
    md = _strip_commands(md)
    md = _PATH.sub("", md)
    md = _FILE.sub("", md)
    md = _ID.sub("", md)
    md = re.sub(r"\(?\bPhase\s*\d+\b[^)]*\)?", "", md, flags=re.I)
    md = _humanise_metrics(md)
    return _tidy(md)


# --------------------------------------------------------------------------- #
# Markdown -> HTML (small subset)
# --------------------------------------------------------------------------- #
_HR = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")
_UL = re.compile(r"^\s*[-*]\s+")
_OL = re.compile(r"^\s*\d+\.\s+")
_HEAD = re.compile(r"^(#{1,6})\s+(.*)$")


def _inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                  lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    return text


def _cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def _render_table(rows: list[str]) -> str:
    if not rows:
        return ""
    header = _cells(rows[0])
    body = rows[1:]
    if body and set("".join(_cells(body[0]))) <= set("-: "):
        body = body[1:]
    th = "".join(f"<th>{_inline(c)}</th>" for c in header)
    trs = []
    for r in body:
        cs = _cells(r)
        cs += [""] * (len(header) - len(cs))
        trs.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cs[:len(header)]) + "</tr>")
    return f"<table><thead><tr>{th}</tr></thead><tbody>{''.join(trs)}</tbody></table>"


def md_to_html(md: str, demote: int = 2) -> str:
    lines = md.splitlines()
    n, i, blocks = len(lines), 0, []
    while i < n:
        s = lines[i].strip()
        if s == "" or _HR.match(s):
            i += 1
            continue
        if s.startswith("|"):
            tbl = []
            while i < n and lines[i].strip().startswith("|"):
                tbl.append(lines[i].strip())
                i += 1
            blocks.append(_render_table(tbl))
            continue
        if _UL.match(lines[i]):
            items = []
            while i < n and _UL.match(lines[i]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[i]).strip())
                i += 1
            blocks.append("<ul>" + "".join(f"<li>{_inline(x)}</li>" for x in items) + "</ul>")
            continue
        if _OL.match(lines[i]):
            items = []
            while i < n and _OL.match(lines[i]):
                items.append(re.sub(r"^\s*\d+\.\s+", "", lines[i]).strip())
                i += 1
            blocks.append("<ol>" + "".join(f"<li>{_inline(x)}</li>" for x in items) + "</ol>")
            continue
        if s.startswith(">"):
            q = []
            while i < n and lines[i].strip().startswith(">"):
                q.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            blocks.append(f"<blockquote>{md_to_html(chr(10).join(q), demote)}</blockquote>")
            continue
        h = _HEAD.match(s)
        if h:
            blocks.append(f"<h{min(6, len(h.group(1)) + demote)}>{_inline(h.group(2).strip())}"
                          f"</h{min(6, len(h.group(1)) + demote)}>")
            i += 1
            continue
        para = []
        while i < n:
            cs = lines[i].strip()
            if (cs == "" or _HR.match(cs) or cs.startswith("|") or _UL.match(lines[i])
                    or _OL.match(lines[i]) or cs.startswith(">") or _HEAD.match(cs)):
                break
            para.append(cs)
            i += 1
        blocks.append(f"<p>{_inline(' '.join(para))}</p>")
    return "\n".join(blocks)


def block_html(lines: list[str], demote: int = 3) -> str:
    out = md_to_html(clean("\n".join(lines)), demote=demote).strip()
    return out or '<p class="muted">Not yet recorded.</p>'


def parse_md_table(path: Path, heading: str) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == heading)
    except StopIteration:
        return []
    header, rows, seen_sep = None, [], False
    for l in lines[start + 1:]:
        s = l.strip()
        if s.startswith("##") and header is not None:
            break
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if not seen_sep and set("".join(cells)) <= set("-: "):
            seen_sep = True
            continue
        rows.append(dict(zip(header, cells)))
    return rows


# --------------------------------------------------------------------------- #
# Extraction helpers (pull the management-relevant lead of a section)
# --------------------------------------------------------------------------- #
def lead_block(lines: list[str]) -> list[str]:
    """Intro paragraph + first list, stopping before tables, sub-headings, or the
    'Why this is an A3' / 'Scope evidence' rationale blocks."""
    out = []
    for l in lines:
        s = l.strip()
        if s.startswith("|") or s.startswith("##"):
            break
        if re.match(r"^\*\*(Why|Scope evidence|Why this)", s):
            break
        out.append(l)
    return out


def bullets_drop(lines: list[str], drop_leads=()) -> list[str]:
    """List items, dropping those whose bold lead matches drop_leads."""
    out = []
    for l in lines:
        s = l.strip()
        if _UL.match(l) or _OL.match(l):
            lead = re.match(r"^\s*(?:[-*]|\d+\.)\s+\*\*(.+?)[:.]?\*\*", l)
            if lead and any(lead.group(1).lower().startswith(d.lower()) for d in drop_leads):
                continue
            out.append(l)
        elif not s:
            out.append(l)
    return out


# --------------------------------------------------------------------------- #
# Metric series + inline SVG chart
# --------------------------------------------------------------------------- #
def metric_series(facility: str, signal_type: str):
    fam, col, label, unit = SIGNAL_METRIC.get(
        signal_type, ("operational", "cph", "Throughput", "cases/hr"))
    path = DATA / "metrics" / fam / f"{facility}.csv"
    try:
        with path.open(encoding="utf-8") as fh:
            series = []
            for row in csv.DictReader(fh):
                d, v = row.get("date"), row.get(col)
                if d and v not in (None, ""):
                    try:
                        series.append((d, float(v)))
                    except ValueError:
                        pass
    except OSError:
        return None
    return (label, unit, col, series) if len(series) >= 2 else None


def _mon(iso: str) -> str:
    try:
        return dt.date.fromisoformat(iso).strftime("%b")
    except ValueError:
        return iso


def svg_chart(series, label, unit, marker_date=None, target=None) -> str:
    if not series or len(series) < 2:
        return ""
    W, H, pl, pr, pt, pb = 700, 250, 56, 18, 30, 42
    ys = [v for _, v in series]
    lo, hi = min(ys), max(ys)
    if target is not None:
        lo, hi = min(lo, target), max(hi, target)
    span = (hi - lo) or 1
    lo, hi = lo - span * 0.12, hi + span * 0.12

    def X(i):
        return pl + (W - pl - pr) * (i / (len(series) - 1))

    def Y(v):
        return pt + (H - pt - pb) * (1 - (v - lo) / (hi - lo))

    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, (_, v) in enumerate(series))
    area = f"{pl},{Y(lo):.1f} " + pts + f" {X(len(series) - 1):.1f},{Y(lo):.1f}"
    parts = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" '
             f'aria-label="{html.escape(label)} trend">']
    # y gridlines + labels
    for frac in (0, 0.5, 1):
        val = hi - (hi - lo) * frac
        y = pt + (H - pt - pb) * frac
        parts.append(f'<line x1="{pl}" y1="{y:.1f}" x2="{W - pr}" y2="{y:.1f}" class="grid"/>')
        parts.append(f'<text x="{pl - 8}" y="{y + 4:.1f}" class="yl" text-anchor="end">'
                     f'{val:.0f}</text>')
    # target line
    if target is not None:
        ty = Y(target)
        parts.append(f'<line x1="{pl}" y1="{ty:.1f}" x2="{W - pr}" y2="{ty:.1f}" class="target"/>')
        parts.append(f'<text x="{W - pr}" y="{ty - 5:.1f}" class="tl" text-anchor="end">'
                     f'target {target:.0f}</text>')
    # signal-date marker
    if marker_date:
        idx = next((i for i, (d, _) in enumerate(series) if d >= marker_date), None)
        if idx is not None:
            mx = X(idx)
            parts.append(f'<line x1="{mx:.1f}" y1="{pt}" x2="{mx:.1f}" y2="{H - pb}" '
                         f'class="marker"/>')
            parts.append(f'<text x="{mx:.1f}" y="{pt - 8:.1f}" class="ml" text-anchor="middle">'
                         f'signal</text>')
    parts.append(f'<polygon points="{area}" class="area"/>')
    parts.append(f'<polyline points="{pts}" class="line"/>')
    # x labels: first / middle / last
    for i in (0, len(series) // 2, len(series) - 1):
        parts.append(f'<text x="{X(i):.1f}" y="{H - pb + 18:.1f}" class="xl" '
                     f'text-anchor="middle">{_mon(series[i][0])}</text>')
    parts.append(f'<text x="{pl}" y="16" class="cap">{html.escape(label)} '
                 f'({html.escape(unit)}), daily</text>')
    parts.append("</svg>")
    return f'<div class="chartwrap">{"".join(parts)}</div>'


# --------------------------------------------------------------------------- #
# HTML assembly
# --------------------------------------------------------------------------- #
CSS = """
:root{--ink:#1f2733;--muted:#5b6776;--line:#e2e8f0;--bg:#eef2f6;--card:#fff;
--accent:#2456a6;--a3:#2456a6;--kaizen:#0f8a7e;--bundle:#6b3fa0;--soft:#f6f9fc;
--ok:#1f8a4c;--warn:#b9770f;--bad:#c0392b;}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.62 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
.wrap{max-width:840px;margin:32px auto;padding:0 20px;}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
box-shadow:0 1px 3px rgba(16,32,64,.06);overflow:hidden;}
.topbar{background:var(--accent);color:#fff;font-weight:600;letter-spacing:.04em;
font-size:13px;padding:8px 30px;text-transform:uppercase;}
header{padding:26px 30px 20px;border-bottom:1px solid var(--line);}
.kicker{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
color:var(--muted);margin-bottom:6px;}
h1{font-size:25px;line-height:1.25;margin:0;}
.statusrow{display:flex;gap:8px;align-items:center;margin-top:14px;flex-wrap:wrap;}
.pill{font-size:12px;font-weight:700;letter-spacing:.03em;text-transform:uppercase;
border-radius:999px;padding:4px 12px;color:#fff;}
.pill.ok{background:var(--ok);}.pill.warn{background:var(--warn);}
.pill.bad{background:var(--bad);}.pill.info{background:var(--muted);}
.facts{display:flex;gap:26px;flex-wrap:wrap;margin-top:12px;font-size:14px;color:var(--muted);}
.facts b{color:var(--ink);font-weight:600;}
section{padding:8px 30px;}
section h2{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--accent);
border-bottom:2px solid var(--line);padding-bottom:6px;margin:26px 0 12px;}
section h2 .n{color:var(--muted);font-weight:600;}
section h3{font-size:15px;margin:18px 0 6px;}
p{margin:10px 0;}.muted{color:var(--muted);font-style:italic;}
ul,ol{margin:10px 0;padding-left:22px;}li{margin:6px 0;}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px;}
th,td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top;}
thead th{background:var(--soft);}
blockquote{border-left:3px solid var(--accent);background:var(--soft);margin:12px 0;
padding:8px 16px;color:var(--muted);}
.tag{display:inline-block;font-size:12px;font-weight:700;color:#fff;border-radius:6px;
padding:2px 8px;margin-right:6px;}
.tag.a3{background:var(--a3);}.tag.kaizen{background:var(--kaizen);}
.s-pass{color:var(--ok);font-weight:700;}.s-fail{color:var(--bad);font-weight:700;}
.chartwrap{margin:14px 30px;border:1px solid var(--line);border-radius:10px;background:#fff;
padding:8px;}
.chart{width:100%;height:auto;display:block;}
.chart .grid{stroke:#eef2f6;stroke-width:1;}
.chart .line{fill:none;stroke:var(--accent);stroke-width:2.4;}
.chart .area{fill:rgba(36,86,166,.08);stroke:none;}
.chart .target{stroke:var(--ok);stroke-width:1.4;stroke-dasharray:5 4;}
.chart .marker{stroke:var(--warn);stroke-width:1.4;stroke-dasharray:3 3;}
.chart text{font:12px -apple-system,Segoe UI,Roboto,sans-serif;fill:var(--muted);}
.chart .cap{fill:var(--ink);font-weight:600;}
.chart .tl{fill:var(--ok);}.chart .ml{fill:var(--warn);}
footer{padding:16px 30px 24px;color:var(--muted);font-size:12px;border-top:1px solid var(--line);}
a{color:var(--accent);}
.index-list{list-style:none;padding:0;margin:0;}
.index-list li{border-bottom:1px solid var(--line);padding:14px 0;}
.index-list li:last-child{border-bottom:none;}
.index-list .t{font-weight:600;}.index-list .sub{color:var(--muted);font-size:13px;margin-top:3px;}
@media print{body{background:#fff;}.wrap{margin:0;max-width:none;padding:0;}
.card{border:none;box-shadow:none;border-radius:0;}section{break-inside:avoid;}}
"""


def _page(title: str, body: str) -> str:
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"<title>{html.escape(title)}</title>\n<style>{CSS}</style>\n</head>\n"
            f"<body>\n<div class=\"wrap\">\n{body}\n</div>\n</body>\n</html>\n")


def humanise_signal(sig: str) -> str:
    return sig.replace("_", " ") if sig else ""


def _humandate(iso: str) -> str:
    try:
        return dt.date.fromisoformat(iso).strftime("%-d %b %Y")
    except (ValueError, TypeError):
        return iso


def followups_for(ids: set[str]) -> list[dict]:
    getp, heading = INDEXES["follow-ups"]
    return [r for r in parse_md_table(getp(), heading) if r.get("artifact_id") in ids]


def outcome_status(fus: list[dict], state: str = "") -> tuple[str, str]:
    """Return (pill_class, sentence) describing where things stand."""
    npass = sum(1 for r in fus if "PASS" in r.get("status", ""))
    nfail = sum(1 for r in fus if "FAIL" in r.get("status", ""))
    npend = sum(1 for r in fus if r.get("status", "").lower().startswith("pending"))
    due = sorted(r.get("follow_up_date", "") for r in fus
                 if r.get("status", "").lower().startswith("pending") and r.get("follow_up_date"))
    bits = []
    if npass:
        bits.append(f"{npass} check{'s' if npass > 1 else ''} passed")
    if nfail:
        bits.append(f"{nfail} failed")
    if npend:
        bits.append(f"{npend} still pending")
    sentence = ("; ".join(bits) + ".") if bits else "No outcome checks scheduled yet."
    if due:
        sentence += f" Next review {_humandate(due[0])}."
    if nfail:
        pill = "bad"
    elif "resolv" in state.lower():
        pill = "ok"
    elif fus and npend == 0:
        pill = "ok"
    else:
        pill = "warn"
    return pill, sentence


def outcome_table(fus: list[dict]) -> str:
    if not fus:
        return '<p class="muted">No outcome checks recorded yet.</p>'
    head = "<tr><th>Item</th><th>Measure</th><th>Target</th><th>Due</th><th>Result</th></tr>"
    trs = []
    for r in fus:
        who = "A3" if r.get("artifact_id", "").startswith("a3-") else "Kaizen"
        metric = humanise_metric_label(r.get("target_metric", ""))
        tgt = " ".join(x for x in (r.get("direction", ""), r.get("target_value", "")) if x)
        st = r.get("status", "")
        cls = "s-pass" if "PASS" in st else ("s-fail" if "FAIL" in st else "")
        st_html = f'<span class="{cls}">{html.escape(st)}</span>' if cls else html.escape(st)
        trs.append(f"<tr><td>{who}</td><td>{_inline(metric)}</td><td>{html.escape(tgt)}</td>"
                   f"<td>{html.escape(_humandate(r.get('follow_up_date', '')))}</td>"
                   f"<td>{st_html}</td></tr>")
    return f"<table><thead>{head}</thead><tbody>{''.join(trs)}</tbody></table>"


def _shell(kicker: str, title: str, pills: list[tuple[str, str]],
           facts: list[tuple[str, str]], body: str, foot: str) -> str:
    pill_html = "".join(f'<span class="pill {c}">{html.escape(t)}</span>' for c, t in pills)
    fact_html = "".join(f"<span><b>{html.escape(v)}</b> {html.escape(k)}</span>"
                        for k, v in facts if v)
    facts_div = f'<div class="facts">{fact_html}</div>' if fact_html else ""
    return (f'<div class="card">\n<div class="topbar">ACI · Continuous Improvement</div>\n'
            f'<header><div class="kicker">{html.escape(kicker)}</div>'
            f'<h1>{_inline(title)}</h1>'
            f'<div class="statusrow">{pill_html}</div>'
            f'{facts_div}'
            f'</header>\n{body}\n<footer>{foot}</footer>\n</div>')


def _section(title: str, inner: str) -> str:
    return f"<section><h2>{html.escape(title)}</h2>\n{inner}\n</section>"


# --------------------------------------------------------------------------- #
# Render a standalone artifact as a management report
# --------------------------------------------------------------------------- #
def _facility_of(parsed: dict, ident: str) -> str:
    fac = parsed["frontmatter"].get("facility", "")
    if fac:
        return fac
    m = (re.search(r"[a-z]{3}-\d{2}", ident)
         or re.search(r"[a-z]{3}-\d{2}", meta_value(parsed, "Source", "Source investigation")))
    return m.group(0) if m else ""


def render_artifact(text: str) -> tuple[str, str, str]:
    parsed = parse_artifact(text)
    atype = detect_type(parsed)
    label = TYPE_LABEL[atype]
    ident = meta_value(parsed, f"{label} ID", "a3_id", "kaizen_id") or "(unknown)"
    state = meta_value(parsed, "State") or parsed["frontmatter"].get("state", "")
    owner = meta_value(parsed, "Owner")
    opened = meta_value(parsed, "Opened")
    facility = _facility_of(parsed, ident)
    sig = parsed["frontmatter"].get("signal_type", "")
    title = clean(display_title(parsed["title"]))

    fus = followups_for({ident})
    pill, stands = outcome_status(fus, state)
    pills = [(pill, ("Open" if "open" in state.lower() else "Closed") if state else "Status")]

    # chart where relevant
    chart = ""
    if facility:
        ms = metric_series(facility, sig or "throughput_drop")
        if ms:
            mlabel, unit, col, series = ms
            tgt = next((float(r["target_value"]) for r in fus
                        if r.get("target_metric") == col and r.get("target_value", "").replace(".", "", 1).lstrip("-").isdigit()),
                       None)
            chart = svg_chart(series, mlabel, unit,
                              parsed["frontmatter"].get("signal_date"), tgt)

    parts = [chart]
    if atype == "a3":
        parts.append(_section("The situation", block_html(lead_block(section_lines(parsed, "Current state")))))
        parts.append(_section("What we found", block_html(
            bullets_drop(section_lines(parsed, "Root cause"), drop_leads=("Supporting evidence",)))))
        did = section_lines(parsed, "Countermeasures")
        parts.append(_section("What we did", block_html(did)))
        stands_lines = section_lines(parsed, "Closing")
        extra = "" if is_placeholder(stands_lines) else block_html(stands_lines)
        parts.append(_section("Where it stands", f"<p>{html.escape(stands)}</p>\n{extra}"))
    else:
        parts.append(_section("The situation", block_html(section_lines(parsed, "Observation"))))
        parts.append(_section("What we did", block_html(section_lines(parsed, "Change"))))
        tr = section_lines(parsed, "Tracking")
        oc = section_lines(parsed, "Outcome")
        extra = "" if is_placeholder(oc) else block_html(oc)
        parts.append(_section("Where it stands",
                              f"<p>{html.escape(stands)}</p>\n{block_html(tr)}\n{extra}"))

    facts = [("owner", owner), ("opened", _humandate(opened) if opened else ""),
             ("facility", facility), ("scope", meta_value(parsed, "Network applicability"))]
    foot = (f"Continuous-improvement {label} · {html.escape(facility or 'network')} · "
            f"prepared for management on {dt.date.today().strftime('%-d %b %Y')}.")
    body = "\n".join(p for p in parts if p)
    return _page(f"{label}: {title}", _shell(f"{label} report", title, pills, facts, body, foot)), ident, atype


# --------------------------------------------------------------------------- #
# Bundle (investigation + A3s + Kaizens + outcome) as one management report
# --------------------------------------------------------------------------- #
def load_investigations() -> dict:
    getp, heading = INDEXES["investigations"]
    out = {}
    for r in parse_md_table(getp(), heading):
        f = r.get("file", "")
        if f:
            out[Path(f).stem] = {"file": DATA / "investigations" / f,
                                 "facility": r.get("facility", ""), "signal": r.get("signal", ""),
                                 "state": r.get("state", ""), "disposition": r.get("disposition", "")}
    return out


def related_artifacts(inv_id: str) -> tuple[list[Path], list[Path]]:
    ga, ha = INDEXES["a3s"]
    gk, hk = INDEXES["kaizens"]
    a3 = [DATA / "a3s" / r["file"] for r in parse_md_table(ga(), ha)
          if r.get("source") == inv_id and r.get("file")]
    kz = [DATA / "kaizens" / r["file"] for r in parse_md_table(gk(), hk)
          if r.get("source") == inv_id and r.get("file")]
    return a3, kz


def build_bundle(inv_id: str):
    invs = load_investigations()
    inv = invs.get(inv_id)
    inv_path = inv["file"] if inv else None
    if inv_path is None or not inv_path.exists():
        hits = list((DATA / "investigations").rglob(f"{inv_id}.md"))
        if not hits:
            return None
        inv_path = hits[0]
        inv = inv or {"facility": "", "signal": "", "state": "", "disposition": ""}

    a3_paths, kz_paths = related_artifacts(inv_id)
    a3s = [parse_artifact(p.read_text(encoding="utf-8")) for p in a3_paths]
    kzs = [parse_artifact(p.read_text(encoding="utf-8")) for p in kz_paths]
    art_ids = {meta_value(p, "A3 ID", "Kaizen ID", "a3_id", "kaizen_id")
               for p in a3s + kzs}
    fus = followups_for(art_ids)

    fm, inv_body = split_frontmatter(inv_path.read_text(encoding="utf-8"))
    facility = inv.get("facility") or fm.get("facility", "")
    signal = inv.get("signal") or fm.get("signal_type", "")
    signal_date = fm.get("signal_date", "")
    signal_detail = grab_field(inv_body, "Signal")
    title = f"{facility} — {humanise_signal(signal)}".strip(" —")
    if signal_date:
        title += f", {_mon(signal_date)} {signal_date[:4]}"

    pill, stands = outcome_status(fus, inv.get("state", ""))

    # chart
    chart = ""
    ms = metric_series(facility, signal)
    if ms:
        mlabel, unit, col, series = ms
        tgt = next((float(r["target_value"]) for r in fus
                    if r.get("target_metric") == col and r.get("target_value", "").replace(".", "", 1).lstrip("-").isdigit()),
                   None)
        chart = svg_chart(series, mlabel, unit, signal_date, tgt)

    # The situation
    situation = (f"<p>{_inline(clean(signal_detail))}</p>" if signal_detail
                 else block_html(lead_block(section_lines(a3s[0], "Current state"))) if a3s
                 else block_html(section_lines(kzs[0], "Observation")) if kzs
                 else '<p class="muted">Not recorded.</p>')

    # What we found
    if a3s:
        found = block_html(bullets_drop(section_lines(a3s[0], "Root cause"),
                                        drop_leads=("Supporting evidence",)))
    elif kzs:
        found = block_html(section_lines(kzs[0], "Observation"))
    else:
        found = '<p class="muted">Not recorded.</p>'

    # What we did — facility fix (Kaizen) + systemic fix (A3)
    did_parts = []
    for p in kzs:
        did_parts.append('<h3><span class="tag kaizen">Facility fix</span> '
                         f'{_inline(clean(display_title(p["title"])))}</h3>'
                         + block_html(section_lines(p, "Change")))
    for p in a3s:
        did_parts.append('<h3><span class="tag a3">Systemic fix</span> '
                         f'{_inline(clean(display_title(p["title"])))}</h3>'
                         + block_html(section_lines(p, "Countermeasures")))
    did = "\n".join(did_parts) or '<p class="muted">Not recorded.</p>'

    # Where it stands
    stands_html = f"<p>{html.escape(stands)}</p>\n{outcome_table(fus)}"

    parts = [chart,
             _section("The situation", situation),
             _section("What we found", found),
             _section("What we did", did),
             _section("Where it stands", stands_html)]
    facts = [("facility", facility),
             ("owner", meta_value(a3s[0], "Owner") if a3s else (meta_value(kzs[0], "Owner") if kzs else "")),
             ("identified", _humandate(signal_date) if signal_date else "")]
    foot = (f"Continuous-improvement report · {html.escape(facility or 'network')} · "
            f"prepared for management on {dt.date.today().strftime('%-d %b %Y')}.")
    body = _shell("Improvement report", title, [(pill, _status_word(pill))], facts,
                  "\n".join(p for p in parts if p), foot)
    return _page(f"Improvement report: {title}", body), inv_id


def _status_word(pill: str) -> str:
    return {"ok": "Resolved / on track", "warn": "In progress", "bad": "Needs attention",
            "info": "Status"}.get(pill, "Status")


def bundle_ids() -> list[str]:
    ids = set()
    for key in ("a3s", "kaizens"):
        getp, heading = INDEXES[key]
        for r in parse_md_table(getp(), heading):
            if r.get("source"):
                ids.add(r["source"])
    invs = load_investigations()
    return sorted(i for i in ids if i in invs or list((DATA / "investigations").rglob(f"{i}.md")))


# --------------------------------------------------------------------------- #
# Discovery + index
# --------------------------------------------------------------------------- #
def discover(state: str = "all") -> list[Path]:
    found = []
    for sub in ("a3s", "kaizens"):
        base = DATA / sub
        if not base.exists():
            continue
        for p in sorted(base.rglob("*.md")):
            if p.name == "INDEX.md":
                continue
            if state != "all" and f"/{state}/" not in p.as_posix():
                continue
            found.append(p)
    return found


def render_index(entries: list[dict]) -> str:
    def block(title, items):
        if not items:
            return f'<section><h2>{title} (0)</h2><p class="muted">None.</p></section>'
        lis = []
        for e in items:
            sub = " · ".join(x for x in (e.get("sub"), e.get("owner")) if x)
            sub_div = f'<div class="sub">{_inline(sub)}</div>' if sub else ""
            lis.append(f'<li><div class="t"><a href="{html.escape(e["file"])}">'
                       f'{_inline(e["title"])}</a></div>{sub_div}</li>')
        return f'<section><h2>{title} ({len(items)})</h2><ul class="index-list">{"".join(lis)}</ul></section>'

    bd = [e for e in entries if e["type"] == "bundle"]
    a3 = [e for e in entries if e["type"] == "a3"]
    kz = [e for e in entries if e["type"] == "kaizen"]
    body = ('<div class="card">\n<div class="topbar">ACI · Continuous Improvement</div>\n'
            '<header><div class="kicker">Management reports</div>'
            '<h1>Continuous-improvement reports</h1></header>\n'
            f'{block("Improvement reports (full story)", bd)}\n'
            f'{block("A3s", a3)}\n{block("Kaizens", kz)}\n'
            f'<footer>{len(entries)} report(s) · prepared on '
            f'{dt.date.today().strftime("%-d %b %Y")}.</footer>\n</div>')
    return _page("ACI · Continuous-improvement reports", body)


def _entry(text: str, fname: str) -> dict:
    parsed = parse_artifact(text)
    atype = detect_type(parsed)
    label = TYPE_LABEL[atype]
    return {"type": atype, "file": fname,
            "title": clean(display_title(parsed["title"])),
            "owner": meta_value(parsed, "Owner"),
            "sub": ("Open" if "open" in (meta_value(parsed, "State")).lower() else "Closed")}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Render ACI artifacts to management-facing HTML reports.")
    ap.add_argument("source", nargs="?", help="path to a single A3/Kaizen .md file")
    ap.add_argument("--all", action="store_true",
                    help="render every A3 + Kaizen + every bundle, plus an index.html")
    ap.add_argument("--bundle", metavar="INVESTIGATION_ID", help="render one combined report")
    ap.add_argument("--all-bundles", action="store_true",
                    help="render every investigation bundle plus an index.html")
    ap.add_argument("--state", choices=["open", "closed", "all"], default="all")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT))
    ap.add_argument("-o", "--output")
    args = ap.parse_args(argv)

    if not (args.all or args.all_bundles or args.bundle or args.source):
        ap.error("give a source .md file, --bundle ID, --all-bundles, or --all")

    if args.bundle and not (args.all or args.all_bundles):
        result = build_bundle(args.bundle)
        if result is None:
            print(f"error: no investigation found for id '{args.bundle}'")
            return 1
        doc, ident = result
        out = Path(args.output) if args.output else DEFAULT_OUT / f"bundle-{ident}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(doc, encoding="utf-8")
        print(f"wrote {out}")
        return 0

    if args.source and not (args.all or args.all_bundles):
        try:
            doc, ident, _ = render_artifact(Path(args.source).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"error: {e}")
            return 1
        out = Path(args.output) if args.output else DEFAULT_OUT / f"{ident}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(doc, encoding="utf-8")
        print(f"wrote {out}")
        return 0

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    if args.all:
        for p in discover(args.state):
            try:
                text = p.read_text(encoding="utf-8")
                doc, ident, _ = render_artifact(text)
            except (OSError, ValueError) as e:
                print(f"skip {p}: {e}")
                continue
            (out_dir / f"{ident}.html").write_text(doc, encoding="utf-8")
            entries.append(_entry(text, f"{ident}.html"))
            print(f"wrote {out_dir / f'{ident}.html'}")
    if args.all or args.all_bundles:
        invs = load_investigations()
        for inv_id in bundle_ids():
            result = build_bundle(inv_id)
            if result is None:
                continue
            doc, ident = result
            fname = f"bundle-{ident}.html"
            (out_dir / fname).write_text(doc, encoding="utf-8")
            inv = invs.get(ident, {})
            entries.append({"type": "bundle", "file": fname,
                            "title": (f"{inv.get('facility', '')} — "
                                      f"{humanise_signal(inv.get('signal', ''))}").strip(" —") or ident,
                            "sub": "Full story", "owner": ""})
            print(f"wrote {out_dir / fname}")
    if entries:
        (out_dir / "index.html").write_text(render_index(entries), encoding="utf-8")
        print(f"wrote {out_dir / 'index.html'}  ({len(entries)} report(s))")
    else:
        print("no artifacts found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
