## Summary

**Robustness (intensity):** under **threshold** treatment, [`TreatmentThresholdProcessor`](src/housing/components/processors/treatment_threshold.py) uses a **calendar-year percentile** of tract-level restricted-unit share (default **`percentile=0.25`**). Sweep **alternative percentiles** (and/or document alternative intensity rules) to show **sensitivity of results** to how “high intensity” is defined.

## Motivation

Advisor feedback: changing the threshold rule should show how **treated-set composition** and **estimated effects** move—readers will ask whether findings hinge on a single cutoff.

## Implementation ideas

- Parameterize `TreatmentThresholdProcessor(..., percentile=...)` from env e.g. `DID_THRESHOLD_PERCENTILE` (float 0–1) in [`did_pipeline_callaway_santanna.py`](src/housing/scripts/did_pipeline_callaway_santanna.py), **or** batch script that loops percentiles and sets `DID_CS_OUTPUT_DIR` per run.
- Keep **`DID_TREATMENT_MODE=threshold`** for this sweep; compare to **binary** separately ([`docs/DID_CS_RUNBOOK.md`](docs/DID_CS_RUNBOOK.md)).
- Log / export: n treated tracts, adoption curve, CS overall ATT + key event-study points per percentile.

## Acceptance criteria

- [ ] Grid of percentiles documented (e.g. 0.10, 0.15, 0.25, 0.33, 0.50—or range agreed with team).
- [ ] Appendix figure/table: percentile vs main estimate (and sample size).
- [ ] Short prose in limitations if estimates are highly sensitive.

## Out of scope

- Replacing the economic definition of “intensity” (e.g. alternative to share × ACS units) unless scoped in a follow-up issue.
