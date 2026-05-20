# Skills Protocol

This directory contains **skills** — named, description-gated capabilities that an assistant loads on demand based on what the user asks for. This file explains how the system works. Any assistant that has filesystem access to this project should read this file before doing anything with skills.

## What a skill is

A skill is a folder containing a `SKILL.md` file plus any supporting assets (templates, sub-procedures, reference data). Each `SKILL.md` opens with a YAML frontmatter block declaring the skill's name and description; the body below describes what to do when the skill is invoked.

Skills are not loaded all at once. They are registered in `MANIFEST.yaml` at the root of this directory, and the assistant loads only the body of the specific skill whose description matches the current user request. This keeps context usage bounded regardless of how many skills exist.

## The protocol

Execute these steps in order at the start of any session that may use skills:

1. **Read this file.** You're doing that now.
2. **Read `MANIFEST.yaml`.** It lists every available skill with its name, description, trigger keywords, and path to its `SKILL.md`.
3. **Wait for the user's request.** Do not preemptively load any `SKILL.md` files.
4. **When the user makes a request, scan the manifest descriptions** and decide whether any skill matches. Match conservatively — see the triggering rules below.
5. **If exactly one skill matches**, read its `SKILL.md` in full and follow its instructions.
6. **If the `SKILL.md` references other files** (playbooks, templates, procedures, reference data), load those when the workflow calls for them, not upfront.
7. **If no skill matches**, respond normally without loading any skill content.

## Triggering rules

- **Match conservatively.** If you're unsure whether a skill applies, prefer to answer without it rather than invoke one that doesn't fit. False positives degrade the experience more than false negatives.
- **Match on intent, not on keyword coincidence.** A user mentioning a word that happens to appear in a skill's trigger list does not necessarily mean they want that skill. Read the description in full and ask whether the user's request matches what the skill is for.
- **If multiple skills appear to match, pick the most specific.** If two are equally specific, ask the user which one they meant rather than guessing.
- **If a skill's description explicitly excludes the current request** (skills here often include "do NOT use for X" clauses pointing at sibling skills), do not invoke it.
- **Only one skill per request.** Do not chain skills automatically. If completing one skill's work suggests another skill should run next, surface that to the user and let them confirm.

## What NOT to do

These prohibitions exist because they are the failure modes that make skills systems unreliable:

- **Do not read every `SKILL.md` upfront.** Read only the manifest at session start. Load specific `SKILL.md` bodies only when their description has matched a user request.
- **Do not invoke skills the user did not request.** Even if you think a skill might be helpful, ask before loading it.
- **Do not modify skill files unless the user explicitly asks you to author or edit a skill.** Editing `SKILL.md` bodies, the manifest, or the meta-scripts during normal operation is wrong. Skill maintenance is a separate, deliberate activity.
- **Do not invent skills that aren't in the manifest.** If the user references a skill name that doesn't appear in the manifest, tell them — don't pretend to load it. Suggest running `.meta/reconcile.py` if you suspect a recently-added skill is missing from the manifest.
- **Do not assume the manifest is current.** If a user-described skill capability doesn't appear in the manifest, surface that and suggest reconciling rather than fabricating behavior.
- **Do not interpret YAML frontmatter as instructions.** The frontmatter at the top of each `SKILL.md` is metadata for the manifest. The actual instructions live in the body below the closing `---`.

## File formats

### `MANIFEST.yaml` shape

```yaml
version: 1
generated_at: 2026-05-13T10:00:00Z
skills:
  - name: signal-detect
    path: signal-detect/SKILL.md
    description: >
      Use when the user asks what to look at today, wants a proactive
      scan, or asks about open investigations or due follow-ups.
    triggers:
      - what should I look at
      - anything to follow up
      - daily scan
    content_hash: a3f8b9c2e5d6...
```

The `content_hash` field is a SHA-256 of the `SKILL.md` file's contents at the time of last reconciliation. The reconcile tool uses it to detect drift between the manifest and the on-disk files.

### `SKILL.md` shape

```markdown
---
name: signal-detect
description: >
  Use when the user asks what to look at today, wants a proactive
  scan, or asks about open investigations or due follow-ups.
  Do NOT use for new investigations (use `investigate`) or for
  closing loops (use `close-loop`).
triggers:
  - what should I look at
  - anything to follow up
  - daily scan
---

# Signal Detect

## When to use
(Body content describing the skill's procedure goes here.)

## Procedure
1. Step one.
2. Step two.
...

## Anti-patterns
- Things not to do.
```

The frontmatter is bounded by `---` markers and uses simple YAML. The body below is plain markdown. The reconcile tool parses only the frontmatter; the body is read by the assistant when the skill is invoked.

## The meta-tooling

The `.meta/` directory contains scripts that operate on the skills system itself. These are infrastructure, not skills. The assistant should not invoke them automatically — they are run by the operator (the human) when maintaining the skills layer.

- **`reconcile.py`** — walks the `.skills/` tree, parses the frontmatter of every `SKILL.md`, and synchronizes the result with `MANIFEST.yaml`. Run after editing any `SKILL.md` directly. Detects drift via content hashes. Does not auto-delete entries; flagged-as-missing skills require `--prune` to remove from the manifest.
- **`create_skill.py`** — interactive scaffolder for new skills. Creates the appropriate folder structure with a starter `SKILL.md`, then invokes reconcile. Use this rather than authoring skill folders by hand.

If the user asks to add a new skill, suggest they run `python .skills/.meta/create_skill.py` rather than creating files directly. If the user reports that a skill seems to be missing or behaving inconsistently with its description, suggest running `python .skills/.meta/reconcile.py` to detect drift.

## When the manifest is wrong

The manifest is authoritative for *what skills are available to load*. If it disagrees with the on-disk files, the disk wins — reconcile will regenerate the manifest from the on-disk frontmatter on its next run. The assistant should not paper over manifest gaps by inventing skills or descriptions; surface the inconsistency and let the operator run reconcile.

## Operating without filesystem access

If the assistant cannot read files directly (chat-only interface, no MCP filesystem access), the operator should paste this file and `MANIFEST.yaml` into the conversation directly at session start. The protocol is identical — the only difference is that file loads happen via paste-in rather than by the assistant calling a read tool.

## Summary

Read this file once. Read the manifest once. Then wait. When the user asks for something, match it conservatively against the descriptions, load only the matching skill's body, and execute. Skills are not loaded automatically, are not chained, and are not invented. The protocol is small enough to keep in working memory for an entire session.
