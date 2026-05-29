# Robustness Decisions: Sweep Results and Design Choices

**Date:** 2026-05-27  
**Status:** Active  
**Related files:** `docs/robustness/ROBUSTNESS_FINDINGS.md`, `docs/methodology/PARALLEL_TRENDS_ANALYSIS.md`, `docs/PREFERRED_SPEC.md`

---

## Summary

Two robustness sweeps (Issues #81, #82) are complete. The key finding is that the **full-panel CS ATT is stable across all parameter variations** (~$20/month), while the matched CS ATT is moderately sensitive to k and the threshold percentile. The residualized CS ATT is consistently large-negative across all specifications — this is a detrending artifact, not a stable finding (see `PARALLEL_TRENDS_ANALYSIS.md`).

This document records: (1) what each sweep found, (2) the preferred specification decisions, and (3) additional matching improvements made in response to the V-shaped pre-trend diagnosis.

---

## Issue #81: k-Neighbors Sensitivity Sweep (COMPLETE)

**Motivation:** The number of matched control units (k) affects control pool size, control reuse, and matched-sample ATT magnitudes. Showing stability across k demonstrates the matched-sample result is not cherry-picked.

**Results (threshold = 0.25, all runs):**

| k | Treated | Controls | Max reuse | Full-panel CS ATT | Matched CS ATT | Residualized ATT |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 274 | 84  | 24 | $20.65 | $2.45  | −$58.27 |
| 2 | 274 | 139 | 29 | $20.65 | $3.46  | −$82.27 |
| **3** | **274** | **179** | **30** | **$20.65** | **$4.60**  | **−$86.20** |
| 4 | 274 | 214 | 41 | $20.65 | $5.72  | −$87.58 |
| 5 | 274 | 247 | 42 | $20.65 | $6.77  | −$89.73 |

**Findings:**
- Full-panel CS ATT: **perfectly stable** at $20.65 across all k (k does not affect this estimator)
- Matched CS ATT: **grows with k** ($2.45→$6.77), reflecting more lenient matching pulling in less-similar controls at higher k
- Residualized ATT: consistently large-negative (−$58 to −$90) — a detrending artifact, not a meaningful pattern
- Max control reuse reaches 41–42 at k=4,5, which is high. Preferred k=3 keeps max reuse at 30.

**Decision: k=3 is the preferred specification** (per `PREFERRED_SPEC.md`). It balances:
- Enough control diversity to avoid over-reliance on any single control tract
- Tight enough matching to avoid including very different tracts
- Max control reuse of 30 (vs 41+ at k=4,5)

---

## Issue #82: Threshold Percentile Sensitivity Sweep (COMPLETE)

**Motivation:** The treatment definition (whether a tract counts as "treated" in a given month) depends on whether the share of restricted units exceeds the 25th percentile of all active prohibition tracts that year. The choice of 0.25 is somewhat arbitrary; showing results across 0.10–0.50 demonstrates robustness.

**Results (k=3, all runs):**

| Percentile | Treated | Controls | Max reuse | Full-panel CS ATT | Matched CS ATT | Residualized ATT |
|---|---:|---:|---:|---:|---:|---:|
| 0.10 | 329 | 177 | 46 | $20.87 | $9.37  | −$70.45 |
| 0.15 | 311 | 173 | 41 | $20.18 | $8.02  | −$75.16 |
| **0.25** | **274** | **179** | **30** | **$20.65** | **$4.60**  | **−$86.20** |
| 0.33 | 245 | 164 | 30 | $21.16 | $4.00  | −$73.89 |
| 0.50 | 183 | 150 | 28 | $19.83 | $3.65  | −$87.82 |

**Findings:**
- Full-panel CS ATT: **stable** across all thresholds ($19.83–$21.16) — direction and magnitude robust
- Matched CS ATT: **sensitive** to threshold (0.10: $9.37 → 0.50: $3.65). Higher threshold = fewer treated tracts = more restrictive definition = smaller matched ATT
- The matched ATT decline at stricter thresholds reflects that the most intensive STR prohibition tracts show less effect — consistent with diminishing returns at higher prohibition intensity
- Residualized ATT: consistently negative across all thresholds — confirms this is a detrending artifact not driven by the specific threshold

**Decision: 0.25 is the preferred threshold** (per `PREFERRED_SPEC.md`). It represents the middle of the distribution of prohibition intensity — requiring that a tract has more restrictions than the bottom quartile of all active prohibition tracts. It is neither permissive (0.10, which includes nearly every tract with any prohibitions) nor restrictive (0.50, which halves the treated sample).

---

## Matching Feature Improvement (2026-05-27)

**Problem:** The existing 2-feature matching (slope + avg_pre_rent) cannot distinguish a V-shaped pre-treatment trajectory from a flat one. Two tracts can have identical pre-trend slope and mean but completely different trajectory shapes. With current SMD of 1.357 on slope and 0.683 on rent (materially imbalanced after matching), the matched sample has poor pre-treatment comparability.

**Root cause:** The V-shaped pre-trend (treated tracts diverging from controls then reconverging pre-treatment) means standard slope-based matching misses the curvature that drives the parallel trends violation.

**Solution:** Add 3-horizon lagged rent levels to the matching feature set, computed relative to the global first treatment month:
- `rent_lag_1` — rent 1 month before first treatment
- `rent_lag_6` — rent 6 months before first treatment  
- `rent_lag_12` — rent 12 months before first treatment

**New default feature set (5 features):**
```python
matching_features = ("pre_trend_slope", "avg_pre_rent", "rent_lag_1", "rent_lag_6", "rent_lag_12")
```

All features standardized by `StandardScaler` before k-NN (existing behavior).

**Code changes:**
- `src/housing/components/processors/trend_matching.py`: added `_rent_at_month()` static method; updated `_calculate_pre_trends()` to compute lag values; updated default `matching_features`
- `src/housing/did_spec.py`: added `DID_TREND_MATCH_CALIPER` constant and `resolve_trend_match_caliper()` resolver

**Expected outcome:** Lower SMD on slope (target < 0.5, down from 1.357) because matched controls will now more closely replicate the 3-point trajectory shape of treated tracts.

**To verify:** Run `python src/housing/scripts/run_robustness_sweeps_fast.py` and check updated `docs/robustness/k_neighbors_sweep_summary.csv` for improved SMD diagnostics.

---

## Nonlinear Detrending (Appendix Only)

**Problem:** The residualized CS with linear tract trends produces negative ATTs that are a functional form artifact (see `PARALLEL_TRENDS_ANALYSIS.md` §3). The question is whether quadratic detrending corrects this.

**Solution:** Added `detrend_order=2` parameter to `CallawaySantAnnaWithControlsAnalyzer`. In whitepaper mode, the pipeline now runs a second instance with quadratic trends as an **appendix sensitivity spec**.

**What to expect:** The quadratic detrend ATT should be less negative (moving toward zero or positive) compared to the linear detrend, confirming the sign flip under linear detrending is a misspecification artifact.

**Paper placement:**
- Linear detrend: footnote or appendix, with explicit explanation of why the sign flip occurs
- Quadratic detrend: appendix sensitivity figure (`did_callaway_santanna_event_study_quadratic_detrend.png`)
- Neither should appear in the main results table

**Code changes:**
- `src/housing/components/analyzers/callaway_santanna_with_controls.py`: added `detrend_order` parameter and quadratic term in `_residualize_outcome`
- `src/housing/scripts/did_pipeline_callaway_santanna.py`: registered quadratic spec + visualizer in whitepaper mode; added to execution order

---

## Preferred Specification Summary

| Layer | Setting | Rationale |
|-------|---------|-----------|
| Estimator | Full-panel CS (nevertreated, min_cohort_size=5) | Primary; not restricted by matching |
| Treatment mode | Threshold at 0.25 percentile | Middle-of-distribution intensity definition |
| k_neighbors | 3 | Balances pool size and control reuse |
| Matching features | slope + avg_rent + 3 lagged levels | Captures trajectory shape, not just slope/mean |
| Matching caliper | None (env: DID_MATCH_CALIPER) | Conservative default; set via env var if needed |
| Residualized CS | Linear detrend → appendix/footnote | Artifact of linear trend misspecification |
| Quadratic detrend | Appendix sensitivity only | Validates sign flip is a detrending artifact |
