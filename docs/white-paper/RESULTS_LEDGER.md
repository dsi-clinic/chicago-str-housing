# Results ledger (fresh run)

**Run:** `make run-did-pipeline-cs-whitepaper-both-local` (Docker, `/tmp/chicago_did_data`)  
**Outputs:** `output/did-cs-whitepaper-threshold/`, `output/did-cs-whitepaper-binary/`  
**Date:** 2026-05-27

## Headline ATTs — intensity threshold (rent index, $/month unless noted)

| Estimator | ATT | SE | Notes |
|-----------|-----|-----|-------|
| CS full-panel | **+20.65** | 0.35 | Before matching; primary dynamic figure |
| CS matched (k=3, 5-feature) | **+5.46** | 0.39 | 274 treated + 176 controls |
| CS w/ controls (linear detrend) | **−87.80** | 0.56 | Residualized scale — not rent dollars |
| CS w/ controls (quadratic detrend) | **−1046.61** | 4.70 | Appendix only |

## Cohort pooled ATTs (threshold, matched CS)

See `output/did-cs-whitepaper-threshold/tables/tab_cohort_att.tex` and `did_cs_att_summary.csv`.

| Cohort | n | ATT ($/mo) | Pre-violations (of 11) | Clean? |
|--------|---|-----------|------------------------|--------|
| 2019-10 | 13 | **+6.0** | 2 | Yes |
| 2016-07 | 62 | +12.9 | 11 | No |
| 2016-08 | 83 | +5.6 | 9 | No |

## Cohort pooled ATTs (binary, matched CS)

See `output/did-cs-whitepaper-binary/tables/tab_cohort_att.tex`.

| Cohort | n | ATT ($/mo) | Pre-violations | Clean? |
|--------|---|-----------|----------------|--------|
| **2019-10** | 39 | +6.3 | 0 | Yes |

## Calendar-month demean diagnostic

See `docs/robustness/SEASONALITY_DIAGNOSTIC.md`.

| Spec | Matched ATT | 2019-10 pre-violations |
|------|-------------|------------------------|
| Raw | +5.46 | 2 |
| Month demeaned | +5.46 | 2 |

**Decision:** Do not adopt month-FE in headline spec (no pretrend improvement).

## Full-panel pre-trend V-shape

Joint Wald on pre-periods: **p < 0.001**; minimum near **−$16/mo** at t=−8.

## Key figures

- `output/did-cs-whitepaper-threshold/did_callaway_santanna_event_study_full_panel.png`
- `output/did-cs-whitepaper-threshold/did_cohort_dynamics.png`
- `output/did-cs-whitepaper-threshold/tables/tab_cohort_att.tex`
- `docs/robustness/figures/did_cohort_dynamics_seasonality_compare.png`
