#!/usr/bin/env python3
"""
reconcile.py — Synchronize .skills/MANIFEST.yaml with on-disk SKILL.md files.

Walks the .skills/ tree, parses the frontmatter of every SKILL.md, and updates
the manifest. Detects drift via SHA-256 content hashes.

Behavior:
  - New skills on disk but missing from manifest are ADDED.
  - Skills in the manifest but missing from disk are FLAGGED (not removed
    without the --prune flag).
  - Skills present in both but with mismatched content hash have their
    manifest entry REGENERATED from the on-disk frontmatter. Disk wins.
  - Malformed SKILL.md frontmatter is WARNED and SKIPPED.

Usage:
  python .skills/.meta/reconcile.py            # report and apply changes
  python .skills/.meta/reconcile.py --dry-run  # report only, no changes
  python .skills/.meta/reconcile.py --prune    # also remove manifest entries
                                                 whose SKILL.md is missing

This script uses only the Python standard library. No pip install required.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# --------------------------------------------------------------------------
# Locate the .skills/ directory relative to this script.
# This script lives at .skills/.meta/reconcile.py, so .skills/ is its parent's
# parent. Resolving symlinks lets the script be invoked from anywhere.
# --------------------------------------------------------------------------

SCRIPT_PATH = Path(__file__).resolve()
SKILLS_ROOT = SCRIPT_PATH.parent.parent  # .skills/.meta/ -> .skills/
MANIFEST_PATH = SKILLS_ROOT / "MANIFEST.yaml"


# --------------------------------------------------------------------------
# Data classes for skill entries.
# --------------------------------------------------------------------------

@dataclass
class SkillEntry:
    name: str
    path: str  # relative to .skills/
    description: str
    triggers: list[str] = field(default_factory=list)
    content_hash: str = ""


# --------------------------------------------------------------------------
# Minimal YAML reader/writer.
#
# The manifest has a known, fixed shape. A full YAML parser is overkill and
# would add a dependency. Frontmatter parsing is similarly constrained — keys
# we expect are `name`, `description`, `triggers`. We support both scalar
# values and the YAML `>` folded-block syntax for description. Triggers are
# always a flow- or block-style list of strings.
#
# If a SKILL.md uses YAML constructs outside this small set, the parser will
# warn and skip the file rather than producing wrong output.
# --------------------------------------------------------------------------

def parse_frontmatter(text: str) -> Optional[dict]:
    """Parse the YAML frontmatter block from a SKILL.md.

    Returns a dict with keys `name`, `description`, `triggers` (list of str),
    or None if the file has no frontmatter block or it's malformed.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None

    end_index = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_index = i
            break
    if end_index is None:
        return None  # unterminated frontmatter

    fm_lines = lines[1:end_index]
    return _parse_yaml_dict(fm_lines)


def _parse_yaml_dict(lines: list[str]) -> Optional[dict]:
    """Parse a small subset of YAML: top-level scalar keys, folded scalars,
    and block-style string lists. No nested mappings."""
    result: dict = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip()
        if not stripped or stripped.lstrip().startswith("#"):
            i += 1
            continue

        if ":" not in line:
            # Stray line — refuse to parse rather than guess.
            return None

        key, _, value_part = line.partition(":")
        key = key.strip()
        value_part = value_part.strip()

        if value_part == ">" or value_part == "|" or value_part == ">-":
            # Folded scalar. Collect subsequent indented lines.
            block_lines = []
            i += 1
            while i < len(lines) and (lines[i].startswith(" ") or lines[i] == ""):
                block_lines.append(lines[i].strip())
                i += 1
            # Join folded-block lines with a space (close enough for our purposes).
            result[key] = " ".join(filter(None, block_lines))
            continue

        if value_part == "":
            # Possibly a block list on the following lines.
            list_items = []
            i += 1
            while i < len(lines) and lines[i].lstrip().startswith("-"):
                item = lines[i].lstrip()[1:].strip()
                # Strip surrounding quotes if present.
                if (item.startswith('"') and item.endswith('"')) or \
                   (item.startswith("'") and item.endswith("'")):
                    item = item[1:-1]
                list_items.append(item)
                i += 1
            result[key] = list_items
            continue

        # Scalar value on the same line. Strip surrounding quotes.
        if (value_part.startswith('"') and value_part.endswith('"')) or \
           (value_part.startswith("'") and value_part.endswith("'")):
            value_part = value_part[1:-1]
        result[key] = value_part
        i += 1

    return result


def write_manifest(skills: list[SkillEntry], path: Path) -> None:
    """Write the manifest in a stable, human-readable form.

    Skills are sorted by name for deterministic diffs.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "version: 1",
        f"generated_at: {now}",
        "skills:",
    ]

    for s in sorted(skills, key=lambda x: x.name):
        lines.append(f"  - name: {s.name}")
        lines.append(f"    path: {s.path}")
        lines.append(f"    description: >")
        # Wrap description at ~70 chars for readability. Indent two spaces past
        # the description key.
        for chunk in _wrap_for_block(s.description, width=70, indent="      "):
            lines.append(chunk)
        if s.triggers:
            lines.append(f"    triggers:")
            for t in s.triggers:
                # Use single-quoted form for safety against special chars.
                escaped = t.replace("'", "''")
                lines.append(f"      - '{escaped}'")
        else:
            lines.append(f"    triggers: []")
        lines.append(f"    content_hash: {s.content_hash}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _wrap_for_block(text: str, width: int, indent: str) -> list[str]:
    """Greedy word wrap with a fixed indent prefix."""
    words = text.split()
    if not words:
        return [indent]
    out: list[str] = []
    current = indent
    for word in words:
        if len(current) + len(word) + 1 > len(indent) + width and current.strip():
            out.append(current.rstrip())
            current = indent + word
        else:
            current = (current + " " + word) if current.strip() else (current + word)
    if current.strip():
        out.append(current.rstrip())
    return out


def read_manifest(path: Path) -> list[SkillEntry]:
    """Read the existing manifest. Returns an empty list if it doesn't exist
    or is malformed."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    return _parse_manifest_skills(text)


def _parse_manifest_skills(text: str) -> list[SkillEntry]:
    """Parse the skills: list out of the manifest. Tolerant of formatting
    variations but assumes the structure write_manifest produces."""
    lines = text.split("\n")
    skills: list[SkillEntry] = []
    i = 0
    # Find the `skills:` line.
    while i < len(lines) and not lines[i].startswith("skills:"):
        i += 1
    i += 1

    current: Optional[dict] = None
    current_field: Optional[str] = None

    def finalize(entry: dict):
        if entry.get("name"):
            skills.append(SkillEntry(
                name=entry.get("name", ""),
                path=entry.get("path", ""),
                description=entry.get("description", ""),
                triggers=entry.get("triggers", []),
                content_hash=entry.get("content_hash", ""),
            ))

    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip()
        if not stripped:
            i += 1
            continue
        if stripped.startswith("  - name:"):
            if current is not None:
                finalize(current)
            current = {"triggers": []}
            current["name"] = stripped.split(":", 1)[1].strip()
            current_field = None
        elif stripped.startswith("    path:") and current is not None:
            current["path"] = stripped.split(":", 1)[1].strip()
            current_field = None
        elif stripped.startswith("    description:") and current is not None:
            value = stripped.split(":", 1)[1].strip()
            if value in (">", "|", ">-"):
                # Collect folded-block lines.
                current["description"] = ""
                current_field = "description"
            else:
                current["description"] = value
                current_field = None
        elif stripped.startswith("    triggers:") and current is not None:
            value = stripped.split(":", 1)[1].strip()
            if value == "[]":
                current["triggers"] = []
                current_field = None
            else:
                current_field = "triggers"
                current["triggers"] = []
        elif stripped.startswith("    content_hash:") and current is not None:
            current["content_hash"] = stripped.split(":", 1)[1].strip()
            current_field = None
        elif current_field == "description" and stripped.startswith("      ") \
                and current is not None:
            existing = current.get("description", "")
            chunk = stripped.strip()
            current["description"] = (existing + " " + chunk).strip() \
                if existing else chunk
        elif current_field == "triggers" and stripped.lstrip().startswith("- ") \
                and current is not None:
            item = stripped.lstrip()[1:].strip()
            if (item.startswith("'") and item.endswith("'")):
                item = item[1:-1].replace("''", "'")
            elif (item.startswith('"') and item.endswith('"')):
                item = item[1:-1]
            current["triggers"].append(item)
        i += 1

    if current is not None:
        finalize(current)
    return skills


# --------------------------------------------------------------------------
# Skill discovery on disk.
# --------------------------------------------------------------------------

def discover_skills_on_disk(skills_root: Path) -> tuple[list[SkillEntry], list[tuple[Path, str]]]:
    """Walk the skills directory and parse every SKILL.md.

    Returns (entries, warnings). Warnings are (path, reason) tuples for files
    that couldn't be parsed cleanly.
    """
    entries: list[SkillEntry] = []
    warnings: list[tuple[Path, str]] = []

    for skill_md in sorted(skills_root.rglob("SKILL.md")):
        # Skip anything inside dot-prefixed directories (e.g. .meta/, .git/).
        rel_parts = skill_md.relative_to(skills_root).parts
        if any(part.startswith(".") for part in rel_parts):
            continue

        text = skill_md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if fm is None:
            warnings.append((skill_md, "no valid frontmatter block"))
            continue
        if "name" not in fm or "description" not in fm:
            warnings.append((skill_md, "frontmatter missing required fields (name, description)"))
            continue

        # Always emit POSIX separators so the manifest is identical on every OS
        # (the project targets model/platform-agnostic use; .gitattributes forces LF).
        rel_path = skill_md.relative_to(skills_root).as_posix()
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        entries.append(SkillEntry(
            name=fm["name"],
            path=rel_path,
            description=fm["description"],
            triggers=fm.get("triggers", []) or [],
            content_hash=content_hash,
        ))

    return entries, warnings


# --------------------------------------------------------------------------
# Diff and reconciliation logic.
# --------------------------------------------------------------------------

def reconcile(on_disk: list[SkillEntry],
              in_manifest: list[SkillEntry]) -> tuple[list[SkillEntry], dict]:
    """Compute the new manifest entries and a report of changes.

    Returns (new_entries, report). The report has keys:
      added: list of names
      drifted: list of names (manifest description/hash didn't match disk)
      missing_from_disk: list of names (in manifest, no SKILL.md found)
      unchanged: list of names
    """
    disk_by_name = {s.name: s for s in on_disk}
    mfst_by_name = {s.name: s for s in in_manifest}

    added: list[str] = []
    drifted: list[str] = []
    missing_from_disk: list[str] = []
    unchanged: list[str] = []

    new_entries: list[SkillEntry] = []

    for name, disk_entry in disk_by_name.items():
        if name not in mfst_by_name:
            added.append(name)
            new_entries.append(disk_entry)
            continue
        mfst_entry = mfst_by_name[name]
        if mfst_entry.content_hash != disk_entry.content_hash:
            drifted.append(name)
            new_entries.append(disk_entry)  # disk wins
        else:
            unchanged.append(name)
            new_entries.append(disk_entry)

    for name in mfst_by_name:
        if name not in disk_by_name:
            missing_from_disk.append(name)

    return new_entries, {
        "added": sorted(added),
        "drifted": sorted(drifted),
        "missing_from_disk": sorted(missing_from_disk),
        "unchanged": sorted(unchanged),
    }


# --------------------------------------------------------------------------
# CLI.
# --------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Synchronize .skills/MANIFEST.yaml with on-disk SKILL.md files.",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Report changes but do not write the manifest.")
    parser.add_argument("--prune", action="store_true",
                        help="Also remove manifest entries whose SKILL.md is missing.")
    args = parser.parse_args()

    if not SKILLS_ROOT.exists():
        print(f"ERROR: skills directory not found at {SKILLS_ROOT}", file=sys.stderr)
        return 2

    on_disk, warnings = discover_skills_on_disk(SKILLS_ROOT)
    in_manifest = read_manifest(MANIFEST_PATH)
    new_entries, report = reconcile(on_disk, in_manifest)

    print(f"Skills directory: {SKILLS_ROOT}")
    print(f"Manifest:         {MANIFEST_PATH}")
    print(f"Found on disk:    {len(on_disk)}")
    print(f"In manifest:      {len(in_manifest)}")
    print()

    if warnings:
        print("WARNINGS:")
        for path, reason in warnings:
            print(f"  - {path}: {reason}")
        print()

    if report["added"]:
        print("ADDED (new on disk, will be added to manifest):")
        for n in report["added"]:
            print(f"  + {n}")
        print()
    if report["drifted"]:
        print("DRIFTED (content changed on disk, manifest will be regenerated):")
        for n in report["drifted"]:
            print(f"  ~ {n}")
        print()
    if report["missing_from_disk"]:
        action = "WILL BE REMOVED" if args.prune else "FLAGGED (rerun with --prune to remove)"
        print(f"MISSING FROM DISK ({action}):")
        for n in report["missing_from_disk"]:
            print(f"  - {n}")
        print()
    if not (report["added"] or report["drifted"] or report["missing_from_disk"]):
        print("No changes detected. Manifest is in sync.")
        return 0

    # Decide what to write.
    to_write = list(new_entries)
    if not args.prune:
        # Preserve missing-from-disk entries unchanged in the manifest.
        existing_by_name = {s.name: s for s in in_manifest}
        new_names = {s.name for s in to_write}
        for n in report["missing_from_disk"]:
            if n in existing_by_name and n not in new_names:
                to_write.append(existing_by_name[n])

    if args.dry_run:
        print("(--dry-run: manifest not written)")
        return 0

    write_manifest(to_write, MANIFEST_PATH)
    print(f"Manifest written: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
