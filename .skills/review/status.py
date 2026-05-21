#!/usr/bin/env python3
"""status.py — read-only catalog/rollup renderer for the ACI artifact layer.

The single consistent presenter for "show me my work": it parses the INDEX
catalogs (investigations, A3s, Kaizens, patterns, follow-ups) and prints a fixed,
repeatable visual. The `review` skill calls it for listings; signal-detect reuses
the same look for its morning brief so the operator sees one consistent format.

Read-only: it never runs calcs or edits anything. It reads the recorded state in
the indexes (re-running outcome calcs is signal-detect's job).

Usage:
  python .skills/review/status.py                 # dashboard rollup (default)
  python .skills/review/status.py investigations   # list one category
  python .skills/review/status.py a3s | kaizens | patterns | follow-ups
  python .skills/review/status.py open             # the action queue (investigations/open/)
  python .skills/review/status.py due [--asof YYYY-MM-DD]   # follow-ups due on/before a date
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
WIDTH = 66

INDEXES = {
    "investigations": (DATA / "investigations/INDEX.md", "## Investigations"),
    "a3s":            (DATA / "a3s/INDEX.md",            "## A3s"),
    "kaizens":        (DATA / "kaizens/INDEX.md",        "## Kaizens"),
    "patterns":       (DATA / "patterns/INDEX.md",       "## Patterns"),
    "follow-ups":     (DATA / "follow_ups/INDEX.md",     "## Rows"),
}


def parse_index(path: Path, heading: str) -> list[dict]:
    """Return the data rows of the markdown table under `heading` as dicts."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
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
        if s.startswith("##"):
            break
        if not s.startswith("|"):
            if header is not None and s == "":
                continue
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


def banner(title: str) -> str:
    line = "=" * WIDTH
    return f"{line}\n ACI  ·  {title}  ·  {dt.date.today().isoformat()}\n{line}"


def section(name: str, count: int) -> str:
    return f"\n▸ {name} ({count})"


def _get(row: dict, *names: str) -> str:
    for n in names:
        if n in row and row[n]:
            return row[n]
    return ""


def list_investigations(rows, only_open=False):
    out = []
    for r in rows:
        f = _get(r, "file")
        is_open = f.startswith("open/")
        if only_open and not is_open:
            continue
        out.append(f"    {_get(r,'date'):<11} {_get(r,'facility'):<8} "
                   f"{_get(r,'signal'):<16} {_get(r,'state'):<13} "
                   f"→ {_get(r,'disposition') or '(pending)'}")
    return out


def list_a3s(rows):
    return [f"    {_get(r,'a3_id'):<40} {_get(r,'state'):<7} "
            f"open:{_get(r,'opened')}  next:{_get(r,'next_follow_up') or '—'}"
            for r in rows]


def list_kaizens(rows):
    return [f"    {_get(r,'kaizen_id'):<34} {_get(r,'state'):<7} "
            f"{_get(r,'facility'):<8} open:{_get(r,'opened')}  "
            f"next:{_get(r,'next_follow_up') or '—'}" for r in rows]


def list_patterns(rows):
    return [f"    {_get(r,'pattern'):<40} instances:{_get(r,'instances')}"
            for r in rows]


def list_followups(rows, asof=None):
    out = []
    for r in rows:
        d = _get(r, "follow_up_date")
        if asof and d and d > asof:
            continue
        flag = ""
        status = _get(r, "status")
        if asof and d and d <= asof and status.lower().startswith("pending"):
            flag = "  ⚠ DUE"
        out.append(f"    {d:<12} {_get(r,'artifact_id'):<38} "
                   f"{_get(r,'target_metric'):<14} {status}{flag}")
    return out


def cmd_dashboard():
    inv = parse_index(*INDEXES["investigations"])
    a3 = parse_index(*INDEXES["a3s"])
    kz = parse_index(*INDEXES["kaizens"])
    pat = parse_index(*INDEXES["patterns"])
    fu = parse_index(*INDEXES["follow-ups"])
    today = dt.date.today().isoformat()

    print(banner("Status dashboard"))

    open_inv = [r for r in inv if _get(r, "file").startswith("open/")]
    by_state = {}
    for r in inv:
        by_state[_get(r, "state")] = by_state.get(_get(r, "state"), 0) + 1
    print(section("Investigations", len(inv)))
    print(f"    open queue (need action): {len(open_inv)}")
    for st, n in sorted(by_state.items()):
        print(f"    {st:<14} {n}")

    print(section("Improvement artifacts", len(a3) + len(kz)))
    print(f"    A3s:     {sum(1 for r in a3 if _get(r,'state')=='open')} open / {len(a3)} total")
    print(f"    Kaizens: {sum(1 for r in kz if _get(r,'state')=='open')} open / {len(kz)} total")
    print(f"    Patterns: {len(pat)}")

    due = [r for r in fu if _get(r, "follow_up_date") and _get(r, "follow_up_date") <= today]
    overdue = [r for r in due if _get(r, "status").lower().startswith("pending")]
    print(section("Follow-ups", len(fu)))
    print(f"    due on/before {today}: {len(due)}   (still pending: {len(overdue)})")
    print(f"    PASS: {sum(1 for r in fu if 'PASS' in _get(r,'status'))}   "
          f"FAIL: {sum(1 for r in fu if 'FAIL' in _get(r,'status'))}   "
          f"pending: {sum(1 for r in fu if _get(r,'status').lower().startswith('pending'))}")
    print()
    print("  (use: status.py <investigations|a3s|kaizens|patterns|follow-ups|open|due>)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="ACI artifact catalog/rollup (read-only).")
    ap.add_argument("view", nargs="?", default="dashboard",
                    choices=["dashboard", "investigations", "a3s", "kaizens",
                             "patterns", "follow-ups", "open", "due", "brief"])
    ap.add_argument("--asof", default=dt.date.today().isoformat(),
                    help="reference date for 'due' (default: today)")
    args = ap.parse_args(argv)

    if args.view == "dashboard":
        cmd_dashboard()
        return 0
    if args.view == "brief":
        # The OPEN + DUE sections of the morning brief, rendered WITHOUT a banner
        # so signal-detect can slot them under the single "Morning brief" banner
        # (after its live NEW-signals section). See
        # .skills/signal-detect/morning_brief_template.md.
        inv_open = list_investigations(parse_index(*INDEXES["investigations"]), only_open=True)
        print(section("OPEN investigations", len(inv_open)))
        print("\n".join(inv_open) if inv_open else "    (queue clear)")
        due = list_followups(parse_index(*INDEXES["follow-ups"]), asof=args.asof)
        print(section("DUE follow-ups", len(due)))
        print("\n".join(due) if due else "    (none due)")
        print("\n  (signal-detect: re-run each pending DUE check's calc and "
              "annotate PASS/FAIL/NO DATA inline)")
        return 0
    if args.view == "open":
        rows = list_investigations(parse_index(*INDEXES["investigations"]), only_open=True)
        print(banner("Open investigations (action queue)"))
        print(section("Open", len(rows)))
        print("\n".join(rows) if rows else "    (queue clear)")
        return 0
    if args.view == "due":
        rows = list_followups(parse_index(*INDEXES["follow-ups"]), asof=args.asof)
        print(banner(f"Follow-ups due on/before {args.asof}"))
        print(section("Due", len(rows)))
        print("\n".join(rows) if rows else "    (none due)")
        return 0

    renderers = {
        "investigations": list_investigations,
        "a3s": list_a3s, "kaizens": list_kaizens,
        "patterns": list_patterns, "follow-ups": list_followups,
    }
    rows = parse_index(*INDEXES[args.view])
    body = renderers[args.view](rows)
    print(banner(args.view.replace("-", " ").title()))
    print(section(args.view.replace("-", " ").title(), len(body)))
    print("\n".join(body) if body else "    (none)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
