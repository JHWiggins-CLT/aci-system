#!/usr/bin/env python3
"""
create_skill.py — Scaffold a new skill folder with starter SKILL.md.

Prompts the operator for a skill name, description, and triggers. Creates the
folder structure under .skills/{name}/, writes a starter SKILL.md with valid
frontmatter and section headers, then invokes reconcile.py to register the
skill in MANIFEST.yaml.

Usage:
  python .skills/.meta/create_skill.py
  python .skills/.meta/create_skill.py --name my-skill --description "..." \\
      --trigger "phrase one" --trigger "phrase two"

Non-interactive mode requires --name and --description. Triggers are optional.

This script uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from textwrap import dedent


SCRIPT_PATH = Path(__file__).resolve()
SKILLS_ROOT = SCRIPT_PATH.parent.parent
RECONCILE_SCRIPT = SCRIPT_PATH.parent / "reconcile.py"


SKILL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,49}$")


SKILL_MD_TEMPLATE = dedent("""\
    ---
    name: {name}
    description: >
      {description}
    triggers:
    {triggers}
    ---

    # {title}

    ## When to use

    {when_to_use}

    ## Procedure

    1. (Step one. Describe the first concrete action this skill should take when invoked.)
    2. (Step two.)
    3. (Step three.)

    ## Inputs and outputs

    - **Reads:** (list files this skill reads from)
    - **Writes:** (list files this skill produces or modifies)
    - **Calls:** (list any calcs, scripts, or other skills this skill invokes)

    ## Anti-patterns

    - (List things this skill should NOT do.)
    - (Especially: explicitly call out other skills it might be confused with.)

    ## Variants and edge cases

    (Describe any common variations on the procedure, or edge cases the operator should know about.)

    ## Verification

    (Describe how to confirm this skill executed correctly. What artifact should exist? What should it contain?)
""")


def prompt(label: str, *, required: bool = True, default: str | None = None) -> str:
    """Prompt the operator interactively. Returns the entered value."""
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default is not None:
            return default
        if not required:
            return ""
        print("  (required)")


def prompt_triggers() -> list[str]:
    """Prompt for trigger phrases one at a time. Empty line ends the list."""
    print("Enter trigger phrases one at a time. Empty line to finish.")
    triggers: list[str] = []
    while True:
        value = input(f"  trigger {len(triggers) + 1}: ").strip()
        if not value:
            return triggers
        triggers.append(value)


def validate_name(name: str) -> None:
    if not SKILL_NAME_PATTERN.match(name):
        raise ValueError(
            f"Invalid skill name {name!r}. "
            "Must be lowercase letters, digits, and hyphens; "
            "start with a letter; 2-50 characters."
        )


def format_triggers_block(triggers: list[str]) -> str:
    if not triggers:
        return "  []"
    lines = []
    for t in triggers:
        escaped = t.replace("'", "''")
        lines.append(f"  - '{escaped}'")
    return "\n".join(lines)


def title_from_name(name: str) -> str:
    """Turn `signal-detect` into `Signal Detect`."""
    return " ".join(word.capitalize() for word in name.split("-"))


def create_skill(name: str, description: str, triggers: list[str]) -> Path:
    validate_name(name)

    skill_dir = SKILLS_ROOT / name
    if skill_dir.exists():
        raise FileExistsError(f"Skill directory already exists: {skill_dir}")

    skill_dir.mkdir(parents=True)
    skill_md_path = skill_dir / "SKILL.md"

    content = SKILL_MD_TEMPLATE.format(
        name=name,
        description=description,
        triggers=format_triggers_block(triggers),
        title=title_from_name(name),
        when_to_use=("(Briefly describe the user-request scenario that should "
                     "trigger this skill. Be specific about what does and does "
                     "not count.)"),
    )
    skill_md_path.write_text(content, encoding="utf-8")
    return skill_md_path


def run_reconcile() -> int:
    if not RECONCILE_SCRIPT.exists():
        print(f"WARNING: reconcile script not found at {RECONCILE_SCRIPT}; "
              "skipping registration. Run reconcile manually after this.",
              file=sys.stderr)
        return 0
    print()
    print("Running reconcile to register the new skill...")
    result = subprocess.run(
        [sys.executable, str(RECONCILE_SCRIPT)],
        check=False,
    )
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold a new skill folder with a starter SKILL.md.",
    )
    parser.add_argument("--name", help="Skill name (lowercase, hyphens, no spaces).")
    parser.add_argument("--description",
                        help="One-paragraph description of what this skill does.")
    parser.add_argument("--trigger", action="append", default=[],
                        help="Trigger phrase. May be passed multiple times.")
    args = parser.parse_args()

    interactive = args.name is None or args.description is None

    if interactive:
        print("Creating a new skill. Press Ctrl+C to cancel.")
        print()
        if args.name is None:
            print("Skill name: lowercase, hyphens, no spaces. Example: signal-detect")
            args.name = prompt("name")
        if args.description is None:
            print("Description: one paragraph explaining what this skill does and when to use it.")
            print("This is what other models will read to decide whether to invoke the skill.")
            args.description = prompt("description")
        if not args.trigger:
            args.trigger = prompt_triggers()

    try:
        skill_md_path = create_skill(args.name, args.description, args.trigger)
    except (ValueError, FileExistsError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    print()
    print(f"Created: {skill_md_path}")
    print()
    print("Next steps:")
    print(f"  1. Open {skill_md_path} and fill in the body sections.")
    print(f"  2. Add any supporting files (templates, procedures) to the skill folder.")
    print(f"  3. Re-run reconcile if you change the frontmatter after this initial scaffold.")

    return run_reconcile()


if __name__ == "__main__":
    sys.exit(main())
