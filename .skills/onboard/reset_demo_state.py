#!/usr/bin/env python3
"""reset_demo_state.py — clear demo CI history so a production deployment starts empty.

Removes the demo investigations, Kaizens, A3s, and pattern files, and resets the
investigations / a3s / patterns / follow_ups INDEX files to header-only (schema
preserved, data rows dropped). It deliberately does NOT touch:
  - metrics/events  → replaced by the production conversion adapter
  - facilities      → replaced during the add_facility setup step
  - the schema, calcs, skills, or templates

Mode-aware: refuses to run when the deployment mode is `production` unless --force
is given, so it can never silently destroy real investigation history.

Usage:
  python .skills/onboard/reset_demo_state.py            # perform the reset
  python .skills/onboard/reset_demo_state.py --dry-run  # preview only
  python .skills/onboard/reset_demo_state.py --force     # allow in production mode
  python .skills/onboard/reset_demo_state.py --root /tmp/data_copy   # operate on another tree
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = REPO_ROOT / "data"
DEPLOYMENT_FILE = REPO_ROOT / "config" / "deployment.yaml"

# (glob relative to data root, keep-predicate) — files to remove.
REMOVE_GLOBS = [
    ("investigations/**/*.md", lambda p: p.name == "INDEX.md"),
    ("kaizens/**/*.md", lambda p: False),
    ("a3s/**/*.md", lambda p: p.name == "INDEX.md"),
    ("patterns/*.md", lambda p: p.name == "INDEX.md"),
]

# (index path relative to data root, the data-section heading to clear after).
RESET_INDEXES = [
    ("investigations/INDEX.md", "## Investigations"),
    ("a3s/INDEX.md", "## A3s"),
    ("patterns/INDEX.md", "## Patterns"),
    ("follow_ups/INDEX.md", "## Rows"),
]


def current_mode() -> str:
    try:
        text = DEPLOYMENT_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "unset"
    for line in text.splitlines():
        m = re.match(r"^\s*mode:\s*(.*)$", line)
        if m:
            toks = m.group(1).split()
            return toks[0] if toks and not toks[0].startswith("#") else "unset"
    return "unset"


def reset_index(path: Path, heading: str, dry_run: bool) -> bool:
    """Keep everything through the heading + the table header/separator; drop data rows."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return False
    try:
        h = next(i for i, l in enumerate(lines) if l.strip() == heading)
    except StopIteration:
        return False
    out = lines[: h + 1]
    table_kept = 0
    dropped = 0
    for l in lines[h + 1:]:
        if l.lstrip().startswith("|"):
            if table_kept < 2:  # header row + separator row
                out.append(l)
                table_kept += 1
            else:
                dropped += 1
        else:
            out.append(l)
    if dropped and not dry_run:
        path.write_text("\n".join(out).rstrip("\n") + "\n", encoding="utf-8")
    return dropped > 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Clear demo CI history for a production start.")
    ap.add_argument("--root", type=Path, default=DEFAULT_DATA, help="data root (default: ./data)")
    ap.add_argument("--dry-run", action="store_true", help="preview without changing anything")
    ap.add_argument("--force", action="store_true", help="allow even in production mode")
    args = ap.parse_args(argv)

    root: Path = args.root
    if not root.is_dir():
        print(f"error: data root not found: {root}", file=sys.stderr)
        return 2

    mode = current_mode()
    if mode == "production" and not args.force and not args.dry_run:
        print("refusing to reset in production mode without --force "
              "(this would delete real investigation history). "
              "Use --dry-run to preview, or --force to proceed.", file=sys.stderr)
        return 3

    tag = "[dry-run] would remove" if args.dry_run else "removed"
    removed = 0
    for glob, keep in REMOVE_GLOBS:
        for p in sorted(root.glob(glob)):
            if p.is_file() and not keep(p):
                print(f"  {tag}: {p.relative_to(root)}")
                if not args.dry_run:
                    p.unlink()
                removed += 1

    tag2 = "[dry-run] would reset" if args.dry_run else "reset"
    reset = 0
    for rel, heading in RESET_INDEXES:
        if reset_index(root / rel, heading, args.dry_run):
            print(f"  {tag2}: {rel} (data rows cleared)")
            reset += 1

    verb = "Would clear" if args.dry_run else "Cleared"
    print(f"\n{verb} {removed} demo artifact file(s) and {reset} index file(s). "
          f"(mode={mode}; metrics/events/facilities untouched)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
