#!/usr/bin/env python3
"""deployment.py — read/write the ACI deployment mode (slice 1 of onboarding).

Stdlib-only. The deployment mode is the first thing the skills protocol checks
(see .skills/README.md Step 0): an `unset` (or missing) config triggers the
first-run demo-vs-setup greeting; once set, the choice is sticky.

Usage:
  python config/deployment.py get   [--file PATH]          -> prints mode (unset if missing)
  python config/deployment.py set MODE [--file PATH] [--by WHO]
  python config/deployment.py show  [--file PATH]

MODE is one of: demo | production | unset

The live file (config/deployment.yaml) is gitignored; config/deployment.yaml.example
is the committed template the helper falls back to when creating a fresh file.
"""

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_FILE = HERE / "deployment.yaml"
EXAMPLE_FILE = HERE / "deployment.yaml.example"
VALID_MODES = ("unset", "demo", "production")
DYNAMIC_KEYS = ("mode", "chosen_at", "chosen_by")

# Fallback template used only if the .example is also missing.
_FALLBACK = """\
mode: unset
chosen_at:
chosen_by:
schema_version: v1
capabilities:
notes:
"""


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def get_mode(path: Path) -> str:
    """Return the current mode, or 'unset' if the file or key is absent."""
    text = _read_text(path)
    if text is None:
        return "unset"
    for line in text.splitlines():
        m = re.match(r"^\s*mode:\s*(.*)$", line)
        if m:
            tokens = m.group(1).split()
            if not tokens or tokens[0].startswith("#"):
                return "unset"
            return tokens[0]
    return "unset"


def set_mode(path: Path, mode: str, by: str) -> None:
    """Write `mode` (and chosen_at/chosen_by) into the config, creating it if needed."""
    if mode not in VALID_MODES:
        raise ValueError(f"invalid mode '{mode}' (use: {', '.join(VALID_MODES)})")

    base = _read_text(path)
    if base is None or not base.strip():
        # Missing OR empty/partial file: rebuild from the template so the
        # capabilities block and other keys are never silently dropped.
        base = _read_text(EXAMPLE_FILE) or _FALLBACK

    values = {
        "mode": mode,
        "chosen_at": dt.date.today().isoformat(),
        "chosen_by": by,
    }
    out, seen = [], set()
    for line in base.splitlines():
        m = re.match(r"^(\s*)([A-Za-z_]+):", line)
        key = m.group(2) if m else None
        if key in DYNAMIC_KEYS:
            out.append(f"{m.group(1)}{key}: {values[key]}")
            seen.add(key)
        else:
            out.append(line)
    for key in DYNAMIC_KEYS:
        if key not in seen:
            out.append(f"{key}: {values[key]}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Read/write the ACI deployment mode.")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("get", help="print the current mode")
    g.add_argument("--file", type=Path, default=DEFAULT_FILE)

    s = sub.add_parser("set", help="record a mode")
    s.add_argument("mode", choices=VALID_MODES)
    s.add_argument("--file", type=Path, default=DEFAULT_FILE)
    s.add_argument("--by", default="operator")

    sh = sub.add_parser("show", help="print the whole config")
    sh.add_argument("--file", type=Path, default=DEFAULT_FILE)

    args = p.parse_args(argv)

    if args.cmd == "get":
        print(get_mode(args.file))
    elif args.cmd == "set":
        set_mode(args.file, args.mode, args.by)
        print(get_mode(args.file))
    elif args.cmd == "show":
        text = _read_text(args.file)
        if text is None:
            print(f"(no config at {args.file}; mode is unset)")
        else:
            print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
