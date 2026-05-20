# Follow-Ups Index

Flat directory of scheduled outcome checks for every open A3 and Kaizen. Every artifact in `data/a3s/open/` or `data/kaizens/open/` must have at least one row here — the close-loop procedures enforce this gate.

The signal-detect skill scans this file daily and surfaces any row where `follow_up_date ≤ today` and `status = pending`. The outcome calc named in the `calc_invocation` column is the mechanical verification; the status column carries the result once the calc has fired.

## Schema

| Column | Meaning |
|--------|---------|
| artifact_id | Kaizen or A3 id |
| follow_up_date | Date the check fires |
| target_metric | Metric being verified |
| target_value | Target the metric must reach |
| direction | `>=` (rise) or `<=` (fall) |
| calc_invocation | Exact command to run for the check |
| status | pending / PASS / FAIL / NO DATA |
| last_run | Date the check last fired (blank if never) |

## Rows

| artifact_id | follow_up_date | target_metric | target_value | direction | calc_invocation | status | last_run |
|-------------|----------------|---------------|--------------|-----------|------------------|--------|----------|
| k-2026-05-dal-02-trainer-ratio | 2026-05-15 | cph | 138 | >= | `bash calc/outcome/follow_up_check.sh dal-02 cph --target 138 --by 2026-05-15 --window-days 14` | PASS (140.81) | 2026-05-18 |
| k-2026-05-dal-02-trainer-ratio | 2026-06-17 | cph | 138 | >= | `bash calc/outcome/follow_up_check.sh dal-02 cph --target 138 --by 2026-06-17 --window-days 14` | pending | |
| k-2026-05-dal-02-trainer-ratio | 2026-07-17 | cph | 138 | >= | `bash calc/outcome/follow_up_check.sh dal-02 cph --target 138 --by 2026-07-17 --window-days 14` | pending | |
| k-2026-05-dal-02-trainer-ratio | 2026-08-17 | cph | 138 | >= | `bash calc/outcome/follow_up_check.sh dal-02 cph --target 138 --by 2026-08-17 --window-days 14` | pending | |
| k-2026-05-chr-03-bin-relocation | 2026-06-19 | damage | 18 | <= | `bash calc/outcome/follow_up_check.sh chr-03 damage --max 18 --by 2026-06-19 --family exceptions --window-days 14` | pending | |
| k-2026-05-chr-03-bin-relocation | 2026-07-19 | damage | 18 | <= | `bash calc/outcome/follow_up_check.sh chr-03 damage --max 18 --by 2026-07-19 --family exceptions --window-days 14` | pending | |
| a3-2026-05-network-trainer-coverage | 2026-06-15 | cph | 138 | >= | `bash calc/outcome/follow_up_check.sh dal-02 cph --target 138 --by 2026-06-15 --window-days 14` | pending | |
| a3-2026-05-network-trainer-coverage | 2026-06-15 | cph~headcount_new (ral-02) | -0.35 | >= | `bash calc/diagnostic/correlate.sh ral-02 cph headcount_new` | pending | |
