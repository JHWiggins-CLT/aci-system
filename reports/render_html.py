#!/usr/bin/env python3
"""render_html.py — render ACI A3 / Kaizen artifacts (and combined investigation
bundles) to self-contained, management-shareable HTML with a fixed structure.

This is the "rendered / shareable export" capability reserved in
`onboarding_design.md` §5.6 and in `review`'s hand-off note: it turns the
markdown artifacts the CI loop produces into polished, single-file HTML
documents you can hand to someone *outside* the system (email, print, deck).

Two output shapes, both with a fixed structure so the shape never varies even as
content does:

  * **Per-artifact** — one HTML file per A3 or Kaizen. Every A3 renders with the
    same 8-section skeleton; every Kaizen with the same 4-section skeleton. A
    missing section renders as a labelled placeholder so the skeleton is always
    complete.
  * **Bundle** — one HTML file per investigation that ties together the source
    investigation + every A3/Kaizen it produced + the outcome (follow-up)
    history, in a fixed part order: At a glance → Investigation → A3s → Kaizens →
    Outcome history. This is the "one report" management asks for.

Design constraints (per ACI's model, onboarding_design.md §5.4): stdlib only;
reads markdown under `data/`, writes HTML under `reports/` (outside `data/`),
never mutating the canonical artifact tree; model-agnostic; deterministic.

Usage:
  python reports/render_html.py data/a3s/open/<id>.md            # one artifact
  python reports/render_html.py data/a3s/open/<id>.md -o out.html
  python reports/render_html.py --all                            # per-artifact + bundles + index
  python reports/render_html.py --all --state open               # only open artifacts
  python reports/render_html.py --bundle <investigation_id>      # one combined bundle report
  python reports/render_html.py --all-bundles                    # every bundle + index
  python reports/render_html.py --all --out-dir reports          # default out dir
"""

from __future__ import annotations

import argparse
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

# Canonical section order per artifact type. Rendering always follows this order
# so every A3 is structurally identical and every Kaizen is structurally
# identical, independent of the source file's ordering or any omitted section.
A3_SECTIONS = [
    "Current state", "Target state", "Root cause", "Countermeasures",
    "Plan", "Follow-up schedule", "Lessons learned", "Closing",
]
KAIZEN_SECTIONS = ["Observation", "Change", "Tracking", "Outcome"]

TYPE_SPEC = {
    "a3": {"label": "A3", "sections": A3_SECTIONS},
    "kaizen": {"label": "Kaizen", "sections": KAIZEN_SECTIONS},
}

INDEXES = {
    "investigations": (DATA / "investigations/INDEX.md", "## Investigations"),
    "a3s": (DATA / "a3s/INDEX.md", "## A3s"),
    "kaizens": (DATA / "kaizens/INDEX.md", "## Kaizens"),
    "follow-ups": (DATA / "follow_ups/INDEX.md", "## Rows"),
}


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def split_frontmatter(text: str) -> tuple[dict, str]:
    """Strip an optional leading `--- ... ---` YAML block. Returns (dict, body)."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    block = text[4:end]
    body = text[end + len("\n---\n"):]
    fm = {}
    for line in block.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm, body


def strip_html_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def parse_artifact(text: str) -> dict:
    """Parse a single-H1 markdown A3/Kaizen into title, metadata, and sections."""
    fm, body = split_frontmatter(text)
    lines = body.splitlines()

    title = ""
    title_idx = None
    for i, line in enumerate(lines):
        m = re.match(r"^#\s+(.*)$", line)
        if m:
            title = m.group(1).strip()
            title_idx = i
            break

    meta: list[tuple[str, str]] = []
    sections: list[tuple[str, list[str]]] = []
    cur_heading = None
    cur_content: list[str] = []
    start = (title_idx + 1) if title_idx is not None else 0

    for line in lines[start:]:
        h = re.match(r"^##\s+(.*)$", line)
        if h:
            if cur_heading is not None:
                sections.append((cur_heading, cur_content))
            cur_heading = h.group(1).strip()
            cur_content = []
            continue
        if cur_heading is None:
            fld = re.match(r"^\*\*(.+?):\*\*\s*(.*)$", line.strip())
            if fld:
                meta.append((fld.group(1).strip(), fld.group(2).strip()))
            continue
        cur_content.append(line)
    if cur_heading is not None:
        sections.append((cur_heading, cur_content))

    return {"frontmatter": fm, "title": title, "meta": meta, "sections": sections}


def detect_type(parsed: dict) -> str:
    """Return 'a3' or 'kaizen' (raises if neither can be determined)."""
    title = parsed["title"].lower()
    fm = parsed["frontmatter"]
    meta_keys = {k.lower() for k, _ in parsed["meta"]}
    meta_map = {k.lower(): v for k, v in parsed["meta"]}

    if title.startswith("a3:") or "a3_id" in fm or "a3 id" in meta_keys:
        return "a3"
    if title.startswith("kaizen:") or "kaizen_id" in fm or "kaizen id" in meta_keys:
        return "kaizen"
    ident = (meta_map.get("a3 id") or meta_map.get("kaizen id")
             or fm.get("a3_id") or fm.get("kaizen_id") or "")
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
        if n.lower() in lower and lower[n.lower()]:
            return lower[n.lower()]
    fm = parsed["frontmatter"]
    for n in names:
        key = n.lower().replace(" ", "_")
        if key in fm and fm[key]:
            return fm[key]
    return ""


def grab_field(text: str, name: str) -> str:
    """Pull a `**Name:** value` bold field from anywhere in a markdown body."""
    m = re.search(rf"^\*\*{re.escape(name)}:\*\*\s*(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


# --------------------------------------------------------------------------- #
# Markdown -> HTML (small, self-contained subset)
# --------------------------------------------------------------------------- #
_HR = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")
_UL = re.compile(r"^\s*[-*]\s+")
_OL = re.compile(r"^\s*\d+\.\s+")
_HEAD = re.compile(r"^(#{1,6})\s+(.*)$")


def _inline(text: str) -> str:
    """Inline markdown -> HTML. Underscores are left literal (snake_case-safe)."""
    out = []
    for part in re.split(r"(`[^`]+`)", text):
        if len(part) >= 2 and part.startswith("`") and part.endswith("`"):
            out.append(f"<code>{html.escape(part[1:-1])}</code>")
        else:
            s = html.escape(part)
            s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                       lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', s)
            s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
            s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
            out.append(s)
    return "".join(out)


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
        tds = "".join(f"<td>{_inline(c)}</td>" for c in cs[:len(header)])
        trs.append(f"<tr>{tds}</tr>")
    return (f"<table><thead><tr>{th}</tr></thead>"
            f"<tbody>{''.join(trs)}</tbody></table>")


def md_to_html(md: str, demote: int = 2) -> str:
    """Render a markdown subset. `demote` shifts heading levels (so embedded
    documents nest under the surrounding structure)."""
    lines = md.splitlines()
    n = len(lines)
    blocks: list[str] = []
    i = 0
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
            blocks.append("<ul>" + "".join(f"<li>{_inline(it)}</li>" for it in items) + "</ul>")
            continue
        if _OL.match(lines[i]):
            items = []
            while i < n and _OL.match(lines[i]):
                items.append(re.sub(r"^\s*\d+\.\s+", "", lines[i]).strip())
                i += 1
            blocks.append("<ol>" + "".join(f"<li>{_inline(it)}</li>" for it in items) + "</ol>")
            continue
        if s.startswith(">"):
            quote = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            blocks.append(f"<blockquote>{md_to_html(chr(10).join(quote), demote)}</blockquote>")
            continue
        h = _HEAD.match(s)
        if h:
            lvl = min(6, len(h.group(1)) + demote)
            blocks.append(f"<h{lvl}>{_inline(h.group(2).strip())}</h{lvl}>")
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


def parse_md_table(path: Path, heading: str) -> list[dict]:
    """Return the rows of the markdown table under `heading` as dicts."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == heading)
    except StopIteration:
        return []
    header = None
    rows = []
    seen_sep = False
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
# HTML assembly
# --------------------------------------------------------------------------- #
CSS = """
:root{--ink:#1f2733;--muted:#5b6776;--line:#e2e8f0;--bg:#eef2f6;--card:#fff;
--accent:#2456a6;--a3:#2456a6;--kaizen:#0f8a7e;--inv:#5b6776;--bundle:#6b3fa0;
--open:#b9770f;--closed:#1f8a4c;--soft:#f6f9fc;--pass:#1f8a4c;--fail:#c0392b;}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
.wrap{max-width:900px;margin:32px auto;padding:0 20px;}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
box-shadow:0 1px 3px rgba(16,32,64,.06);overflow:hidden;}
.topbar{background:var(--accent);color:#fff;font-weight:600;letter-spacing:.04em;
font-size:13px;padding:8px 28px;text-transform:uppercase;}
header{padding:26px 28px 18px;border-bottom:1px solid var(--line);}
.badges{display:flex;gap:8px;align-items:center;margin-bottom:10px;flex-wrap:wrap;}
.badge{font-size:12px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;
color:#fff;border-radius:6px;padding:3px 9px;}
.badge.a3{background:var(--a3);}
.badge.kaizen{background:var(--kaizen);}
.badge.inv{background:var(--inv);}
.badge.bundle{background:var(--bundle);}
.pill{font-size:12px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;
border-radius:999px;padding:3px 11px;border:1px solid currentColor;}
.pill.open{color:var(--open);}
.pill.closed{color:var(--closed);}
.pill.other{color:var(--muted);}
h1{font-size:23px;line-height:1.3;margin:4px 0 0;}
.meta{display:grid;grid-template-columns:max-content 1fr;gap:6px 18px;
margin:18px 28px 4px;font-size:14px;}
.meta dt{color:var(--muted);font-weight:600;}
.meta dd{margin:0;}
section{padding:6px 28px 4px;}
section h2{font-size:16px;text-transform:uppercase;letter-spacing:.04em;color:var(--accent);
border-bottom:2px solid var(--line);padding-bottom:6px;margin:24px 0 10px;}
section.extra h2{color:var(--muted);}
section p{margin:10px 0;}
.placeholder{color:var(--muted);font-style:italic;}
code{background:var(--soft);border:1px solid var(--line);border-radius:4px;
padding:1px 5px;font:13px/1.5 "SF Mono",Menlo,Consolas,monospace;}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px;}
th,td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top;}
thead th{background:var(--soft);}
blockquote{border-left:3px solid var(--accent);background:var(--soft);
margin:12px 0;padding:8px 16px;color:var(--muted);}
ul,ol{margin:10px 0;padding-left:24px;}
li{margin:4px 0;}
footer{padding:16px 28px 24px;color:var(--muted);font-size:12px;border-top:1px solid var(--line);}
a{color:var(--accent);}
/* bundle: nested artifact/investigation blocks */
.summary dl.meta{margin:14px 28px;}
.embed{margin:14px 28px;border:1px solid var(--line);border-left:4px solid var(--accent);
border-radius:10px;background:#fcfdff;padding:2px 18px 12px;}
.embed.kaizen{border-left-color:var(--kaizen);}
.embed.inv{border-left-color:var(--inv);}
.embed>h2.embed-h{font-size:18px;text-transform:none;letter-spacing:0;color:var(--ink);
border:none;display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:14px 0 4px;padding:0;}
.embed .meta{margin:10px 0;}
.embed section{padding:2px 0;}
.embed section h3{font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:var(--accent);
border-bottom:1px solid var(--line);padding-bottom:4px;margin:16px 0 6px;}
.embed section.extra h3{color:var(--muted);}
.embed h3,.embed h4,.embed h5{margin:14px 0 6px;}
.status-pass{color:var(--pass);font-weight:700;}
.status-fail{color:var(--fail);font-weight:700;}
.index-list{list-style:none;padding:0;margin:0;}
.index-list li{border-bottom:1px solid var(--line);padding:14px 0;}
.index-list li:last-child{border-bottom:none;}
.index-list .t{font-weight:600;}
.index-list .sub{color:var(--muted);font-size:13px;margin-top:3px;}
@media print{body{background:#fff;}.wrap{margin:0;max-width:none;padding:0;}
.card{border:none;box-shadow:none;border-radius:0;}.embed{break-inside:avoid;}}
"""


def _state_class(state: str) -> str:
    s = state.lower()
    if "open" in s:
        return "open"
    if "closed" in s or "close" in s:
        return "closed"
    return "other"


def _page(title: str, body: str) -> str:
    return (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{html.escape(title)}</title>\n<style>{CSS}</style>\n</head>\n"
        f"<body>\n<div class=\"wrap\">\n{body}\n</div>\n</body>\n</html>\n"
    )


def _meta_grid(meta: list[tuple[str, str]]) -> str:
    rows = "".join(f"<dt>{html.escape(k)}</dt><dd>{_inline(v)}</dd>"
                   for k, v in meta if v)
    return f'<dl class="meta">{rows}</dl>' if rows else ""


def _render_sections(parsed: dict, spec: dict, level: int = 2) -> str:
    """Canonical sections in fixed order (missing -> placeholder), then any extras."""
    found = {h.strip().lower(): c for h, c in parsed["sections"]}
    used = set()
    out = []
    for name in spec["sections"]:
        used.add(name.lower())
        content = found.get(name.lower())
        rendered = md_to_html("\n".join(content), demote=level).strip() if content else ""
        if not rendered:
            rendered = '<p class="placeholder">Not yet recorded.</p>'
        out.append(f"<section>\n<h{level}>{html.escape(name)}</h{level}>\n{rendered}\n</section>")
    for h, c in parsed["sections"]:
        if h.strip().lower() in used:
            continue
        rendered = md_to_html("\n".join(c), demote=level).strip() or \
            '<p class="placeholder">Not yet recorded.</p>'
        out.append(f'<section class="extra">\n<h{level}>{html.escape(h.strip())}</h{level}>\n'
                   f"{rendered}\n</section>")
    return "".join(out)


def render_artifact(text: str) -> tuple[str, str, str]:
    """Render one standalone artifact. Returns (html_doc, artifact_id, type)."""
    parsed = parse_artifact(text)
    atype = detect_type(parsed)
    spec = TYPE_SPEC[atype]
    label = spec["label"]

    ident = meta_value(parsed, f"{label} ID", "a3_id", "kaizen_id") or "(unknown id)"
    state = meta_value(parsed, "State") or parsed["frontmatter"].get("state", "")
    title = display_title(parsed["title"])

    pill = (f'<span class="pill {_state_class(state)}">{html.escape(state)}</span>'
            if state else "")
    head = (f'<header>\n<div class="badges"><span class="badge {atype}">{label}</span>{pill}</div>\n'
            f"<h1>{_inline(title)}</h1>\n</header>")
    foot = (f'<footer>{label} · <code>{html.escape(ident)}</code> — '
            f"rendered by the ACI export capability on {dt.date.today().isoformat()}. "
            "Structure is fixed per type so every A3 and every Kaizen reads the same.</footer>")
    body = (f'<div class="card">\n<div class="topbar">ACI · Continuous Improvement</div>\n'
            f'{head}\n{_meta_grid(parsed["meta"])}\n{_render_sections(parsed, spec, 2)}\n'
            f"{foot}\n</div>")
    return _page(f"{label}: {title}", body), ident, atype


def _embed_artifact(text: str) -> str:
    """Render an A3/Kaizen as a nested block inside a bundle (sections at h3)."""
    parsed = parse_artifact(text)
    atype = detect_type(parsed)
    spec = TYPE_SPEC[atype]
    label = spec["label"]
    ident = meta_value(parsed, f"{label} ID", "a3_id", "kaizen_id") or ""
    state = meta_value(parsed, "State") or parsed["frontmatter"].get("state", "")
    title = display_title(parsed["title"])
    pill = (f'<span class="pill {_state_class(state)}">{html.escape(state)}</span>'
            if state else "")
    return (f'<div class="embed {atype}">\n'
            f'<h2 class="embed-h"><span class="badge {atype}">{label}</span> '
            f"{_inline(title)} {pill}</h2>\n"
            f'{_meta_grid(parsed["meta"])}\n{_render_sections(parsed, spec, 3)}\n</div>')


# --------------------------------------------------------------------------- #
# Bundle (investigation + A3s + Kaizens + outcome history)
# --------------------------------------------------------------------------- #
def load_investigations() -> dict:
    out = {}
    for r in parse_md_table(*INDEXES["investigations"]):
        f = r.get("file", "")
        if not f:
            continue
        out[Path(f).stem] = {
            "file": DATA / "investigations" / f,
            "facility": r.get("facility", ""),
            "signal": r.get("signal", ""),
            "state": r.get("state", ""),
            "disposition": r.get("disposition", ""),
        }
    return out


def related_artifacts(inv_id: str) -> tuple[list[Path], list[Path]]:
    a3s = [DATA / "a3s" / r["file"] for r in parse_md_table(*INDEXES["a3s"])
           if r.get("source") == inv_id and r.get("file")]
    kz = [DATA / "kaizens" / r["file"] for r in parse_md_table(*INDEXES["kaizens"])
          if r.get("source") == inv_id and r.get("file")]
    return a3s, kz


def followups_for(ids: set[str]) -> list[dict]:
    return [r for r in parse_md_table(*INDEXES["follow-ups"])
            if r.get("artifact_id") in ids]


def _status_html(status: str) -> str:
    s = html.escape(status)
    if "PASS" in status:
        return f'<span class="status-pass">{s}</span>'
    if "FAIL" in status:
        return f'<span class="status-fail">{s}</span>'
    return s


def _outcome_table(rows: list[dict]) -> str:
    if not rows:
        return '<p class="placeholder">No follow-up checks recorded for this investigation’s artifacts.</p>'
    head = ("<tr><th>Artifact</th><th>Due</th><th>Metric</th><th>Target</th>"
            "<th>Status</th><th>Last run</th></tr>")
    trs = []
    for r in rows:
        tgt = " ".join(x for x in (r.get("direction", ""), r.get("target_value", "")) if x)
        trs.append(
            f"<tr><td><code>{html.escape(r.get('artifact_id',''))}</code></td>"
            f"<td>{html.escape(r.get('follow_up_date',''))}</td>"
            f"<td>{_inline(r.get('target_metric',''))}</td>"
            f"<td>{html.escape(tgt)}</td>"
            f"<td>{_status_html(r.get('status',''))}</td>"
            f"<td>{html.escape(r.get('last_run','') or '—')}</td></tr>")
    return f"<table><thead>{head}</thead><tbody>{''.join(trs)}</tbody></table>"


def render_investigation_embed(path: Path) -> str:
    fm, body = split_frontmatter(path.read_text(encoding="utf-8"))
    body = strip_html_comments(body)
    meta = []
    for k in ("facility", "signal_type", "signal_date", "state", "investigator",
              "disposition", "kaizen_id", "a3_id"):
        if fm.get(k):
            meta.append((k.replace("_", " ").title(), fm[k]))
    inv_id = fm.get("investigation_id", path.stem)
    return (f'<div class="embed inv">\n'
            f'<h2 class="embed-h"><span class="badge inv">Investigation</span> '
            f"<code>{html.escape(inv_id)}</code></h2>\n"
            f"{_meta_grid(meta)}\n{md_to_html(body, demote=3)}\n</div>")


def build_bundle(inv_id: str) -> tuple[str, str] | None:
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
    art_ids = set()
    for p in a3_paths + kz_paths:
        try:
            pp = parse_artifact(p.read_text(encoding="utf-8"))
            art_ids.add(meta_value(pp, "A3 ID", "Kaizen ID", "a3_id", "kaizen_id"))
        except OSError:
            pass
    fus = followups_for(art_ids)

    inv_text = inv_path.read_text(encoding="utf-8")
    fac = inv.get("facility", "") or grab_field(inv_text, "")
    signal = inv.get("signal", "")
    title = " · ".join(x for x in (fac, signal) if x) or inv_id
    signal_detail = grab_field(inv_text, "Signal")

    # At a glance (composed only from data on disk; nothing fabricated)
    n = len(fus)
    npass = sum(1 for r in fus if "PASS" in r.get("status", ""))
    nfail = sum(1 for r in fus if "FAIL" in r.get("status", ""))
    npend = sum(1 for r in fus if r.get("status", "").lower().startswith("pending"))
    due = sorted(r.get("follow_up_date", "") for r in fus
                 if r.get("status", "").lower().startswith("pending") and r.get("follow_up_date"))
    next_due = due[0] if due else ""
    outcome = (f"{n} check(s): {npass} PASS, {npend} pending"
               + (f", {nfail} FAIL" if nfail else "")) if n else "none recorded"
    art_lines = []
    for p in a3_paths:
        pp = parse_artifact(p.read_text(encoding="utf-8"))
        art_lines.append(f"A3 · {display_title(pp['title'])}")
    for p in kz_paths:
        pp = parse_artifact(p.read_text(encoding="utf-8"))
        art_lines.append(f"Kaizen · {display_title(pp['title'])}")

    glance = [
        ("Facility", fac),
        ("Signal", f"{signal}" + (f" · {signal_detail}" if signal_detail else "")),
        ("Investigation state", inv.get("state", "")),
        ("Disposition", inv.get("disposition", "")),
        ("Artifacts", " ; ".join(art_lines) if art_lines else "none"),
        ("Outcome to date", outcome),
        ("Next check due", next_due or "—"),
    ]

    parts = [f'<div class="card">\n<div class="topbar">ACI · Continuous Improvement</div>']
    parts.append('<header>\n<div class="badges"><span class="badge bundle">Bundle</span></div>\n'
                 f"<h1>{_inline(title)}</h1>\n</header>")
    parts.append(f'<section class="summary"><h2>At a glance</h2>{_meta_grid(glance)}</section>')
    parts.append(render_investigation_embed(inv_path))
    for p in a3_paths:
        parts.append(f"<section><h2>A3</h2>{_embed_artifact(p.read_text(encoding='utf-8'))}</section>")
    for p in kz_paths:
        parts.append(f"<section><h2>Kaizen</h2>{_embed_artifact(p.read_text(encoding='utf-8'))}</section>")
    parts.append(f"<section><h2>Outcome history</h2>{_outcome_table(fus)}</section>")
    parts.append(f'<footer>Investigation bundle · <code>{html.escape(inv_id)}</code> — '
                 f"rendered by the ACI export capability on {dt.date.today().isoformat()}. "
                 "Bundle structure is fixed: At a glance → Investigation → A3s → Kaizens → "
                 "Outcome history.</footer>\n</div>")
    return _page(f"Bundle: {title}", "\n".join(parts)), inv_id


def bundle_ids() -> list[str]:
    """Investigation ids that have at least one A3 or Kaizen sourced from them."""
    ids = set()
    for key in ("a3s", "kaizens"):
        for r in parse_md_table(*INDEXES[key]):
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
    def block(title: str, items: list[dict]) -> str:
        if not items:
            return f'<section><h2>{title} (0)</h2><p class="placeholder">None.</p></section>'
        lis = []
        for e in items:
            sub = " · ".join(x for x in (e.get("state"), e.get("owner"),
                                         (f"opened {e['opened']}" if e.get("opened") else ""),
                                         e.get("subtitle")) if x)
            lis.append(
                f'<li><div class="t"><a href="{html.escape(e["file"])}">{_inline(e["title"])}</a></div>'
                f'<div class="sub"><code>{html.escape(e["id"])}</code>'
                f'{(" — " + _inline(sub)) if sub else ""}</div></li>')
        return (f'<section><h2>{title} ({len(items)})</h2>'
                f'<ul class="index-list">{"".join(lis)}</ul></section>')

    a3 = [e for e in entries if e["type"] == "a3"]
    kz = [e for e in entries if e["type"] == "kaizen"]
    bd = [e for e in entries if e["type"] == "bundle"]
    body = (
        '<div class="card">\n<div class="topbar">ACI · Continuous Improvement</div>\n'
        '<header><div class="badges"><span class="badge bundle">Reports</span></div>'
        '<h1>Improvement artifact reports</h1></header>\n'
        f'{block("Investigation bundles", bd)}\n{block("A3s", a3)}\n{block("Kaizens", kz)}\n'
        f'<footer>{len(entries)} report(s) rendered by the ACI export capability on '
        f'{dt.date.today().isoformat()}.</footer>\n</div>')
    return _page("ACI · Improvement artifact reports", body)


def _artifact_entry(text: str, fname: str) -> dict:
    parsed = parse_artifact(text)
    atype = detect_type(parsed)
    label = TYPE_SPEC[atype]["label"]
    return {
        "type": atype, "file": fname,
        "id": meta_value(parsed, f"{label} ID", "a3_id", "kaizen_id"),
        "title": display_title(parsed["title"]),
        "state": meta_value(parsed, "State"),
        "owner": meta_value(parsed, "Owner"),
        "opened": meta_value(parsed, "Opened"),
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Render ACI A3/Kaizen markdown (and investigation bundles) to shareable HTML.")
    ap.add_argument("source", nargs="?", help="path to a single A3/Kaizen .md file")
    ap.add_argument("--all", action="store_true",
                    help="render every A3 + Kaizen + every bundle, plus an index.html")
    ap.add_argument("--bundle", metavar="INVESTIGATION_ID",
                    help="render one combined investigation bundle report")
    ap.add_argument("--all-bundles", action="store_true",
                    help="render every investigation bundle plus an index.html")
    ap.add_argument("--state", choices=["open", "closed", "all"], default="all",
                    help="with --all: which artifacts to render (default: all)")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT),
                    help="output directory for --all/--all-bundles (default: reports/)")
    ap.add_argument("-o", "--output", help="output path for a single source / bundle")
    args = ap.parse_args(argv)

    if not (args.all or args.all_bundles or args.bundle or args.source):
        ap.error("give a source .md file, --bundle ID, --all-bundles, or --all")

    # Single bundle
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

    # Single artifact
    if args.source and not (args.all or args.all_bundles):
        src = Path(args.source)
        try:
            doc, ident, _ = render_artifact(src.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"error: {e}")
            return 1
        out = Path(args.output) if args.output else DEFAULT_OUT / f"{ident}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(doc, encoding="utf-8")
        print(f"wrote {out}")
        return 0

    # Batch (--all and/or --all-bundles)
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
            e = _artifact_entry(text, f"{ident}.html")
            entries.append(e)
            print(f"wrote {out_dir / f'{ident}.html'}")

    if args.all or args.all_bundles:
        for inv_id in bundle_ids():
            result = build_bundle(inv_id)
            if result is None:
                continue
            doc, ident = result
            fname = f"bundle-{ident}.html"
            (out_dir / fname).write_text(doc, encoding="utf-8")
            inv = load_investigations().get(ident, {})
            entries.append({
                "type": "bundle", "id": ident, "file": fname,
                "title": " · ".join(x for x in (inv.get("facility", ""), inv.get("signal", "")) if x) or ident,
                "subtitle": inv.get("state", ""),
            })
            print(f"wrote {out_dir / fname}")

    if entries:
        (out_dir / "index.html").write_text(render_index(entries), encoding="utf-8")
        print(f"wrote {out_dir / 'index.html'}  ({len(entries)} report(s))")
    else:
        print("no artifacts found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
