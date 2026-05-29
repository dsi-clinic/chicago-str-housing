## Summary

Reviewer / advisor feedback: the **paper** should open with **naive, simpler results** before layering the preferred (richer) specification. Readers need a clear ladder: what you see with minimal assumptions → what changes once you add the locked-in design.

## Scope

- **White paper / policy brief** narrative ([`docs/white-paper/`](docs/white-paper/)): reorder or add an early subsection (e.g. intro or short “baseline” section) that presents:
  - simplest defensible estimate readers expect (e.g. TWFE or pooled pre-post contrast on full panel, clearly labeled);
  - then **preferred** specification: matched sample + Callaway–Sant’Anna (and CS with controls as appropriate per [`docs/CS_WITH_CONTROLS.md`](docs/CS_WITH_CONTROLS.md)).
- Cross-reference **locked preferred spec** in one place (see companion issue on documenting `k`, threshold percentile, `DID_TREATMENT_MODE`).

## Acceptance criteria

- [ ] Intro / early section explicitly states “simple → preferred” logic in prose.
- [ ] Tables/figures for naive vs preferred are clearly captioned (no conflation of residualized vs level scales).
- [ ] [`docs/white-paper/STORY_OUTLINE.md`](docs/white-paper/STORY_OUTLINE.md) updated if slide/paper structure changes.

## Out of scope

- New estimators beyond what the pipeline already produces (unless needed to define “naive”).
