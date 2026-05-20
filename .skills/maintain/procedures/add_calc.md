# Procedure: Add a calc

## When to use

An investigation needed a number that no existing calc produces, and you had to compute it by hand (inline awk, a one-off Python snippet, mental arithmetic). That friction is the signal to add a calc — the architecture's rule is "no improvised arithmetic anywhere," so a recurring question becomes a calc rather than a habit.

Do NOT add a calc speculatively ("this might be useful someday"). Add it when a real investigation hit the gap. The calc library stays small and every entry has a caller.

## Prerequisites

- **A concrete question** the calc answers, phrased as "what is X for facility F over window T." If you can't phrase it that tightly, the calc's scope isn't clear yet.
- **The metric already exists in the schema.** Run `col_for <family> <metric>` (sourced from `calc/lib/_schema_v1.sh`) to confirm it resolves. If it doesn't, you need `bump_schema.md` first — adding a calc against a non-existent column is a silent failure waiting to happen.
- **A decided output format.** One number? A `label | value` line? A header plus rows? Decide before writing — the format is the contract the golden test locks and skills parse.
- **A way to compute the expected value independently** (by hand, in Python, or from a known fixture). The golden test must not be the calc validating itself.

## Steps

1. **Pick the family directory and name.** Family is one of `descriptive/` (single-variable aggregation), `diagnostic/` (multi-variable / "why"), `comparative/` (cross-facility), `outcome/` (did-it-work). Name is `verb_noun.sh`, lowercase, matching the existing set (`avg.sh`, `change_drivers.sh`, `peer_benchmark.sh`, `follow_up_check.sh`).

2. **Copy the nearest existing calc as a skeleton — do not start from a blank file.** The closest analog carries every convention you must keep:
   - `#!/usr/bin/env bash` + a header comment block: `Family:`, `Question answered:`, `Schema:`, `Usage:`, `Output:`, `Exit codes:` (0 success; 1 bad args; 2 data file not found).
   - `set -euo pipefail` then `source "$(dirname "$0")/../lib/_schema_v1.sh"`.
   - Facility ID as the first positional arg (except network-scope calcs); `--start`/`--end` for windowing where it makes sense.
   - For a single-family calc, mirror `avg.sh`/`worst_day.sh` (a `--family` flag, default `operational`). For a multi-family calc, mirror `change_drivers.sh`/`correlate.sh`.

3. **Resolve columns through `col_for()`, never by hardcoding a position.** `COL=$(col_for "$FAMILY" "$METRIC") || { echo "Unknown metric '$METRIC' in family '$FAMILY'" >&2; exit 1; }`. Hardcoding `$4` couples the calc to schema v1's layout and breaks silently on a schema bump. (Older calcs predate `col_for` and inline a `case` block — do not copy that; use the resolver.)

4. **Keep the zero-safe numeric filter in the awk body.** Reject blanks and non-numerics, but NOT legitimate zeros (a shutdown day is `cph=0`, not missing data): `$col !~ /^-?[0-9]+(\.[0-9]+)?$/ { next }`. Do **not** use `$col + 0 == 0 { next }` — that drops real zeros and biases every mean. This is a logged project decision (2026-05-19); honor it.

5. **Choose the `DATA_ROOT` convention to match the calc's reach.** A single-family calc defaults `DATA_ROOT="${DATA_ROOT:-data/metrics/${FAMILY}}"` and reads `${DATA_ROOT}/${FACILITY}.csv`. A multi-family calc defaults `DATA_ROOT="${DATA_ROOT:-data/metrics}"` and reads `${DATA_ROOT}/${fam}/${FACILITY}.csv`. The override exists so the golden runner can point at fixtures — keep it.

6. **Make the script executable AND record the bit in git.** `chmod +x calc/{family}/{name}.sh`, then stage with `git add --chmod=+x calc/{family}/{name}.sh`. The golden runner invokes calcs directly (`"$@"`, not `bash "$@"`), so a calc committed as mode 100644 fails with "Permission denied" on a fresh clone. This bit it us before (logged 2026-05-20) — do not skip the `--chmod=+x`.

7. **Write a golden test.**
   - Use an existing fixture in `calc/tests/golden/` if one has the right columns (`operational_dal-02.csv`, `exceptions_chr-test.csv`); otherwise add a small, hand-traceable fixture.
   - **Compute the expected value independently** (Python, or arithmetic you can write in a comment), then write it to `calc/tests/expected/{test_name}.txt`. Never paste the calc's own output in as "expected" without an independent check — that locks in bugs.
   - Add a `run_test` line in `calc/tests/run.sh`. Set `DATA_ROOT` on that line to the fixture root the calc expects (family dir vs `metrics/` root, per step 5).

8. **Run `bash calc/tests/run.sh`.** All tests must pass, including the existing ones. If a prior test changed output, you broke something — investigate, don't relock.

9. **Add a `verify.sh` check against the live dataset.** Pick the section that fits (descriptive → 7, exceptions → 8, diagnostic → 5) and assert a value you can independently confirm against an embedded scenario (e.g. the dal-02 dip or chr-03 spike). Run `bash verify.sh` — it must stay all-green.

10. **Update `calc/README.md`** — add a row to the right family table with the calc name, the question it answers, and a real example invocation. Remove any `*(to be built)*` marker if you just built a previously-listed calc.

## Verification

The procedure completed only if all of the following hold:

- `calc/{family}/{name}.sh` exists, is executable (`ls -l` shows `x`; `git ls-files -s` shows mode `100755`), and runs against the live dataset without error.
- At least one golden test covers it and `bash calc/tests/run.sh` exits 0.
- At least one `verify.sh` assertion exercises it and `bash verify.sh` exits 0.
- `calc/README.md` lists it with a usage example.
- The expected value in the golden was derived independently of the calc.

If any is missing, report the partial state — the calc is not "added" until its tests lock it.

## Common mistakes

- **Hardcoding a column index instead of using `col_for()`.** Works today, breaks silently on the next schema bump.
- **Letting the calc generate its own golden.** If you `./calc.sh ... > expected.txt`, the test only proves the output is stable, not correct. Derive the expected value some other way at least once.
- **Dropping legitimate zeros** with the `+0 == 0` filter. Use the numeric-regex filter.
- **Forgetting `git add --chmod=+x`.** The calc runs fine in your tree (you `chmod`'d it) but is broken for everyone who clones. Verify with `git ls-files -s`.
- **Pointing the golden's `DATA_ROOT` at the wrong level.** A multi-family calc needs the `metrics/` root; a single-family calc needs the `metrics/{family}` dir. Mismatched, the test gets "file not found."
- **Adding a calc no investigation asked for.** Every calc must have a caller. If nothing needs it yet, write the question down in the tracker and wait.
