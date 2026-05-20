---
kaizen_id: k-2026-05-dal-02-trainer-ratio
title: dal-02 cohort onboarding trainer-ratio guardrail
opened: 2026-05-18
state: open
owner: Lisa Chen (ops manager, dal-02)
source_investigation: 2026-03-15_dal-02_throughput_drop
related_pattern: (none yet — pattern library pending Phase 6)
facility: dal-02
---

# Kaizen: dal-02 cohort onboarding trainer-ratio guardrail

**Kaizen ID:** k-2026-05-dal-02-trainer-ratio
**Opened:** 2026-05-18
**State:** open
**Owner:** Lisa Chen
**Source:** 2026-03-15_dal-02_throughput_drop
**Related pattern:** (none — flagged as seed for `cohort_overload_throughput_dip` after 2+ more cases)

---

## Observation

The dal-02 cohort of 6 new hires onboarded on 2026-03-02 produced a measurable throughput dip during week-1 of pick certification: `bash calc/descriptive/avg_cph.sh dal-02 --start 2026-03-08 --end 2026-03-22` returned 128.10 vs a February baseline of 141.82 (−9.68%). The mechanism — confirmed on the floor — was that the lead trainer was simultaneously covering a vacant night-shift lead role, stretching the trainer ratio from the nominal 1:4 to an effective 1:6 during certification. `bash calc/diagnostic/change_drivers.sh dal-02 --baseline 2026-02-01:2026-02-28 --comparison 2026-03-08:2026-03-22 --top 3` ranks mispick (+74.62%) and headcount_new (+54.83%) as the top two drivers by an order of magnitude — the cohort-overload signature.

## Change

When onboarding any cohort of more than 4 new hires at dal-02, the lead trainer is formally relieved of all secondary coverage duties (including night-shift escalation backup) for the duration of week-1 pick certification. The standard ratio target is 1:4 trainees per active trainer. Cohort onboardings exceeding 4 trainees require a pre-staffed second trainer with confirmed availability before week-1 certification begins. The trainer release is published to the dal-02 ops bulletin and enforced by the ops manager; informal dual-cover arrangements during certification are prohibited.

## Tracking

- **Baseline:** dal-02 CPH dipped 9.68% (141.82 → 128.10) during the 2026-03-08..2026-03-22 cohort window. Pattern: every cohort onboarding ≥5 trainees at dal-02 has historically required informal dual-cover, with no measurement of the resulting throughput cost until this investigation.

- **Target:** Through the week-1 certification of the next cohort onboarding (≥5 trainees), dal-02 CPH stays within 5% of the pre-cohort 30-day baseline. Concretely: if pre-cohort baseline is X, week-1 average CPH ≥ 0.95 × X.

- **Follow-up checks:**
  - **2026-05-15** (baseline-maintenance check, fired today as part of close-loop): `bash calc/outcome/follow_up_check.sh dal-02 cph --target 138 --by 2026-05-15 --window-days 14` → ACTUAL 140.81, RESULT PASS. Confirms facility is operating at target absent any cohort load.
  - **2026-06-17** (+30 days): `bash calc/outcome/follow_up_check.sh dal-02 cph --target 138 --by 2026-06-17 --window-days 14` — verifies steady-state operation through June. Pending (data not yet available; check fires automatically once the events log is current through that date).
  - **2026-07-17** (+60 days): same calc shape, `--by 2026-07-17`. Pending.
  - **2026-08-17** (+90 days): same calc shape, `--by 2026-08-17`. Pending.
  - **Cohort-event-triggered check** (date TBD): when the ops manager files the next cohort onboarding event, `bash calc/descriptive/avg_cph.sh dal-02 --start <cohort_week1_start> --end <cohort_week1_end>` compared against `--start <baseline_30d_start> --end <baseline_30d_end>`. PASS if comparison ≥ 0.95 × baseline. This is the real outcome check; the steady-state checks above exist to detect regressions outside cohort windows.

## Outcome

*Filled in at Kaizen close. Pending — no cohort onboarding has occurred since the policy took effect on 2026-05-18.*

- Did the metric hit the target?
- Was the change standardized (becomes SOP) or rolled back?
- Lessons that feed the pattern library — particularly: did the trainer release policy alone work, or did the second-trainer requirement also fire?

---

*This Kaizen is one half of a two-part response. The companion A3 — `a3-2026-05-network-trainer-coverage` (opened 2026-05-20) — addresses the systemic issue: training capacity is modeled as nominal availability but is actually shared with shift coverage across the network. This Kaizen handles dal-02; the A3 handles the architecture. The A3 opened with single-facility evidence (a 2026-05-20 `correlate.sh` sweep found the cohort-overload signature only at dal-02) and a peer-evidence gate at 2026-06-15 — the network-sync poll committed here is that gate. See `data/a3s/open/a3-2026-05-network-trainer-coverage.md`.*
