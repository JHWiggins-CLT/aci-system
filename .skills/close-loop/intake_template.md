# Floor Feedback Intake

**Investigation ID:** {investigation_id}
**Floor visit:** {start_date} to {end_date}
**Visited by:** {name}
**Floor contacts:** {names + roles}
**Intake recorded:** {date}

---

## 1. Hypothesis disposition

For each hypothesis from the brief, mark its status and cite floor evidence.

### Hypothesis A — {label}

- **Status:** {CONFIRMED | RULED OUT | INCONCLUSIVE}
- **Floor evidence:**
  - {bullet list of specific observations, quotes, contacts who said what}
- **Strength:** {STRONG | MODERATE | WEAK} — {reason}

{Repeat per hypothesis from the brief.}

---

## 2. What the data missed

Facts the floor knew that the data didn't show.

- {bullet list, one per item}

---

## 3. Surprises

Things that contradicted or extended expectations.

- {bullet list}

---

## 4. New questions raised

Things this visit couldn't answer that might need follow-up.

- {bullet list}

---

## 5. Floor-attributed observations to log

Items to add to the events log or as candidate schema additions.

- events/{facility}.csv: Add `{date}, {facility}, {event_type}, "{description}", floor-intake-{intake_date}`
- Candidate new metric: {description, flagged for `bump_schema.md` discussion}

---

## 6. Disposition

What happens next. Multi-select if sequenced.

- [ ] Close as resolved — signal was a one-off
- [ ] Close as monitoring — watch for recurrence
- [ ] Open A3 — systemic, structured root-cause work
- [ ] Open Kaizen — quick targeted change
- [ ] Re-open as investigation — brief was wrong
- [ ] Escalate — outside CI scope

**Rationale:** {1-3 sentences on why this disposition vs alternatives}

**Suggested A3 scope (if A3):** {problem statement, initial facility, network applicability}

**Suggested Kaizen scope (if Kaizen):** {specific change, owner, target metric, target date}

---

## 7. Pattern feedback

If this investigation matched a pattern from `patterns/INDEX.md`:

- **Matched pattern:** {patterns/{file}.md, match score from brief}
- **Confirmed pattern elements:** {what held}
- **Refuted pattern elements:** {what didn't hold, if any}
- **New element to add to pattern:** {extension worth capturing}
- **Suggested pattern update:** {specific revision proposed}

---

## 8. Follow-up commitments

Things committed to during the visit.

- {bullet list with date, person, what was promised}

---

*This intake is walked conversationally by the `close-loop` skill — not filled out as a form. The structured fields exist so the diagnostic value of the floor visit doesn't evaporate into prose; the conversation is what makes the structure feel natural rather than bureaucratic.*
