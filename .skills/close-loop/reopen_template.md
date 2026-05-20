# Floor Feedback Intake — Re-open

For investigations where the floor visit contradicted the brief enough that the investigation needs to start over with new context. The re-opened investigation gets a new ID and a `supersedes` reference back to the original.

**Original investigation ID:** {original_investigation_id}
**New investigation ID:** {new_investigation_id}
**Floor visit:** {start_date} to {end_date}
**Visited by:** {name}
**Floor contacts:** {names + roles}
**Intake recorded:** {date}

---

## What was wrong with the original brief

Be specific. The next investigation needs to know which assumptions to discard.

- **Hypothesis that pulled the brief in the wrong direction:** {which one, and why was the floor evidence so contradictory}
- **Data that turned out to be misleading:** {which calc results pointed wrong, and why}
- **Floor context the brief lacked:** {what the floor knew that, had it been in the brief, would have changed the hypotheses}

---

## New starting point for the re-opened investigation

What does the next investigation know now that the original didn't?

- **Confirmed floor observations:** {what is now known to be true}
- **Ruled out causes:** {what the floor visit clearly eliminated}
- **New suspected mechanism:** {if the floor visit suggested a different cause, name it}
- **Data that should be re-pulled:** {which calcs the next investigation should run with different parameters or against different time windows}

---

## Floor-attributed observations to log

Even a re-open generates events worth logging.

- events/{facility}.csv: Add `{date}, {facility}, {event_type}, "{description}", floor-intake-{intake_date}`

---

## Disposition

- [x] Re-open as new investigation — {new_investigation_id} with `supersedes: {original_investigation_id}` in frontmatter
- [ ] Set original investigation state to `superseded` (with `superseded_by: {new_investigation_id}` in frontmatter) and move to `data/investigations/YYYY-Qn/`

---

*The re-open path is not a failure mode — it's the architecture working correctly. Briefs are sometimes wrong; this template captures **what was wrong** in a structured way so the next investigation benefits from the learning rather than restarting from zero. Discarding the original investigation silently loses that information.*
