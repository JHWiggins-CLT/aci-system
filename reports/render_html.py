#!/usr/bin/env python3
"""render_html.py — render ACI A3 / Kaizen markdown artifacts to self-contained,
management-shareable HTML with a fixed per-type structure.

This is the "rendered / shareable export" capability reserved in
`onboarding_design.md` §5.6 and in `review`'s hand-off note: it turns the
markdown artifacts the CI loop produces into a polished, single-file HTML
document you can hand to someone *outside* the system (email it, print it,
drop it in a deck appendix).

Two guarantees make it useful for management reporting:

  1. **Consistent structure.** Every A3 renders with the same header card and
     the same section order; every Kaizen does too. Content varies per artifact;
     the shape never does. Sections are emitted in a canonical order regardless
     of how the source file is ordered, and a missing section renders as a
     labelled placeholder so the skeleton is always complete.
  2. **Self-contained output.** Each HTML file inlines its own CSS — no external
     assets, no network, no build step. One file you can share or print as-is.

Design constraints (per ACI's model, onboarding_design.md §5.4):
  - stdlib only (no third-party dependencies);
  - reads markdown under `data/`, writes HTML under `reports/` (outside `data/`),
    never mutating the canonical artifact tree;
  - model-agnostic, deterministic.

Usage:
  python reports/render_html.py data/a3s/open/<id>.md          # one artifact
  python reports/render_html.py data/a3s/open/<id>.md -o out.html
  python reports/render_html.py --all                          # every A3 + Kaizen
  python reports/render_html.py --all --state open             # only open ones
  python reports/render_html.py --all --out-dir reports        # default out dir
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
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


def parse_artifact(text: str) -> dict:
    """Parse a markdown A3/Kaizen into title, metadata fields, and sections."""
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
    ident = meta_map.get("a3 id") or meta_map.get("kaizen id") or fm.get("a3_id") or fm.get("kaizen_id") or ""
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
    return (f'<table><thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table>')


def md_to_html(md: str) -> str:
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
            blocks.append(f"<blockquote>{md_to_html(chr(10).join(quote))}</blockquote>")
            continue
        h = _HEAD.match(s)
        if h:
            lvl = min(6, len(h.group(1)) + 2)
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


# --------------------------------------------------------------------------- #
# HTML assembly
# --------------------------------------------------------------------------- #
CSS = """
:root{--ink:#1f2733;--muted:#5b6776;--line:#e2e8f0;--bg:#eef2f6;--card:#fff;
--accent:#2456a6;--a3:#2456a6;--kaizen:#0f8a7e;--open:#b9770f;--closed:#1f8a4c;--soft:#f6f9fc;}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
.wrap{max-width:880px;margin:32px auto;padding:0 20px;}
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
.index-list{list-style:none;padding:0;margin:0;}
.index-list li{border-bottom:1px solid var(--line);padding:14px 0;}
.index-list li:last-child{border-bottom:none;}
.index-list .t{font-weight:600;}
.index-list .sub{color:var(--muted);font-size:13px;margin-top:3px;}
@media print{body{background:#fff;}.wrap{margin:0;max-width:none;padding:0;}
.card{border:none;box-shadow:none;border-radius:0;}}
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


def render_artifact(text: str) -> tuple[str, str, str]:
    """Render one artifact. Returns (html_doc, artifact_id, artifact_type)."""
    parsed = parse_artifact(text)
    atype = detect_type(parsed)
    spec = TYPE_SPEC[atype]
    label = spec["label"]

    ident = meta_value(parsed, f"{label} ID", "a3_id", "kaizen_id") or "(unknown id)"
    state = meta_value(parsed, "State") or parsed["frontmatter"].get("state", "")
    title = display_title(parsed["title"])

    pill = (f'<span class="pill {_state_class(state)}">{html.escape(state)}</span>'
            if state else "")
    head = (
        f'<header>\n<div class="badges"><span class="badge {atype}">{label}</span>{pill}</div>\n'
        f"<h1>{_inline(title)}</h1>\n</header>"
    )

    meta_rows = "".join(
        f"<dt>{html.escape(k)}</dt><dd>{_inline(v)}</dd>"
        for k, v in parsed["meta"] if v
    )
    meta_block = f'<dl class="meta">{meta_rows}</dl>' if meta_rows else ""

    found = {h.strip().lower(): c for h, c in parsed["sections"]}
    used = set()
    body_sections = []
    for name in spec["sections"]:
        key = name.lower()
        used.add(key)
        content = found.get(key)
        rendered = md_to_html("\n".join(content)).strip() if content else ""
        if not rendered:
            rendered = '<p class="placeholder">Not yet recorded.</p>'
        body_sections.append(f"<section>\n<h2>{html.escape(name)}</h2>\n{rendered}\n</section>")

    for h, c in parsed["sections"]:
        if h.strip().lower() in used:
            continue
        rendered = md_to_html("\n".join(c)).strip() or '<p class="placeholder">Not yet recorded.</p>'
        body_sections.append(
            f'<section class="extra">\n<h2>{html.escape(h.strip())}</h2>\n{rendered}\n</section>')

    foot = (f'<footer>{label} · <code>{html.escape(ident)}</code> — '
            f"rendered by the ACI export capability on {dt.date.today().isoformat()}. "
            "Generated from the source markdown artifact; structure is fixed per type so "
            "every A3 and every Kaizen reads the same.</footer>")

    body = (f'<div class="card">\n<div class="topbar">ACI · Continuous Improvement</div>\n'
            f'{head}\n{meta_block}\n{"".join(body_sections)}\n{foot}\n</div>')
    return _page(f"{label}: {title}", body), ident, atype


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
            if state != "all":
                in_state = f"/{state}/" in str(p.as_posix())
                if not in_state:
                    continue
            found.append(p)
    return found


def render_index(entries: list[dict]) -> str:
    a3 = [e for e in entries if e["type"] == "a3"]
    kz = [e for e in entries if e["type"] == "kaizen"]

    def block(title: str, items: list[dict]) -> str:
        if not items:
            return f'<section><h2>{title} (0)</h2><p class="placeholder">None.</p></section>'
        lis = []
        for e in items:
            sub = " · ".join(x for x in (e.get("state"), e.get("owner"),
                                         (f"opened {e['opened']}" if e.get("opened") else "")) if x)
            lis.append(
                f'<li><div class="t"><a href="{html.escape(e["file"])}">{_inline(e["title"])}</a></div>'
                f'<div class="sub"><code>{html.escape(e["id"])}</code>'
                f'{(" — " + _inline(sub)) if sub else ""}</div></li>')
        return (f'<section><h2>{title} ({len(items)})</h2>'
                f'<ul class="index-list">{"".join(lis)}</ul></section>')

    body = (
        '<div class="card">\n<div class="topbar">ACI · Continuous Improvement</div>\n'
        '<header><div class="badges"><span class="badge a3">Reports</span></div>'
        '<h1>Improvement artifact reports</h1></header>\n'
        f'{block("A3s", a3)}\n{block("Kaizens", kz)}\n'
        f'<footer>{len(entries)} artifact(s) rendered by the ACI export capability on '
        f'{dt.date.today().isoformat()}.</footer>\n</div>')
    return _page("ACI · Improvement artifact reports", body)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Render ACI A3/Kaizen markdown to shareable, consistently-structured HTML.")
    ap.add_argument("source", nargs="?", help="path to a single A3/Kaizen .md file")
    ap.add_argument("--all", action="store_true",
                    help="render every A3 and Kaizen under data/ plus an index.html")
    ap.add_argument("--state", choices=["open", "closed", "all"], default="all",
                    help="with --all: which artifacts to render (default: all)")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT),
                    help="output directory for --all (default: reports/)")
    ap.add_argument("-o", "--output", help="output path for a single source file")
    args = ap.parse_args(argv)

    if not args.all and not args.source:
        ap.error("give a source .md file, or --all")

    if args.source and not args.all:
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

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for p in discover(args.state):
        try:
            text = p.read_text(encoding="utf-8")
            doc, ident, atype = render_artifact(text)
        except (OSError, ValueError) as e:
            print(f"skip {p}: {e}")
            continue
        out = out_dir / f"{ident}.html"
        out.write_text(doc, encoding="utf-8")
        parsed = parse_artifact(text)
        entries.append({
            "type": atype, "id": ident, "file": out.name,
            "title": display_title(parsed["title"]),
            "state": meta_value(parsed, "State"),
            "owner": meta_value(parsed, "Owner"),
            "opened": meta_value(parsed, "Opened"),
        })
        print(f"wrote {out}")
    if entries:
        idx = out_dir / "index.html"
        idx.write_text(render_index(entries), encoding="utf-8")
        print(f"wrote {idx}  ({len(entries)} artifact(s))")
    else:
        print("no artifacts found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
