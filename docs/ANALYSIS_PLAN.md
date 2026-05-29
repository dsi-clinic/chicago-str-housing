# Analysis Plan: Parallel Trends Response + Robustness Hardening

**Date:** 2026-05-27  
**Status:** Implementation in progress  
**For:** Cursor agents, collaborators, and paper reviewers  
**Background:** `docs/methodology/PARALLEL_TRENDS_ANALYSIS.md`, `docs/methodology/ROBUSTNESS_DECISIONS.md`

---

## Why This Plan Exists

The full-panel Callaway-Sant'Anna event study revealed a **V-shaped parallel trends violation**: the pre-treatment CS ATT dips to −$16 at t=−8 then recovers to $0 at t=−1. All pre-period estimates are statistically significant (SE ~$1–2). This creates two problems:

1. The **raw CS ATT is likely upward-biased** (the positive post-treatment effect mirrors the pre-trend continuation).
2. The **residualized CS ATT inverts to large-negative** (linear detrending misfits the nonlinear pre-period).

Two robustness sweeps (Issues #81, #82) are already complete in `docs/robustness/`. This plan addresses the remaining gaps.

---

## What Is Already Done (Do Not Re-Implement)

| Item | Location |
|------|----------|
| k-sweep (k=1..5) | `docs/robustness/k_neighbors_sweep_summary.csv` + figures |
| Threshold sweep (0.10..0.50) | `docs/robustness/threshold_percentile_sweep_summary.csv` + figures |
| Preferred specification | `docs/PREFERRED_SPEC.md` |
| Pre-trend violation diagnosis | `docs/PRETREND_VIOLATIONS_AND_FIXES.md` |
| Current findings narrative | `docs/DID_RESULTS_STORY.md` |

---

## Work Item 1 — Improved Matching Features ✅ DONE

**Problem:** 2-feature matching (slope + avg_pre_rent) cannot distinguish a V-shaped from a flat pre-trend. Current SMD on slope = 1.357 (materially imbalanced).

**Solution:** Add 3-horizon lagged rent levels (1, 6, 12 months before global first treatment) to matching features.

**New default feature set:**
```python
matching_features = ("pre_trend_slope", "avg_pre_rent", "rent_lag_1", "rent_lag_6", "rent_lag_12")
```

**Changes made:**
- `src/housing/components/processors/trend_matching.py`:
  - Added `_rent_at_month()` static method for lag lookup with year-month matching
  - Updated `_calculate_pre_trends()` to compute `rent_lag_1`, `rent_lag_6`, `rent_lag_12`
  - Updated default `matching_features` tuple (5 features instead of 2)
  - Updated docstrings
- `src/housing/did_spec.py`:
  - Added `DID_TREND_MATCH_CALIPER: Final[float | None] = None`
  - Added `resolve_trend_match_caliper()` resolver (env var: `DID_MATCH_CALIPER`)

**To verify:**
```bash
export PYTHONPATH=src DATA_DIR=$(pwd)/data
python src/housing/scripts/run_robustness_sweeps_fast.py
```
Check: `docs/robustness/k_neighbors_sweep_summary.csv` updated; slope SMD should be lower than 1.357.

---

## Work Item 2 — Quadratic Detrending (Appendix) ✅ DONE

**Problem:** Linear tract-specific trends over-correct the V-shaped pre-period, producing large negative ATTs that are a detrending artifact. Adding t² terms would better fit the curvature.

**Changes made:**
- `src/housing/components/analyzers/callaway_santanna_with_controls.py`:
  - Added `detrend_order: int = 1` parameter (`__init__`, line ~64)
  - In `_residualize_outcome`: when `detrend_order >= 2`, adds `tract_i_trend_sq` columns (t² interactions) to design matrix
  - Output context keys now include name-based suffix so quadratic instance writes to distinct keys
- `src/housing/scripts/did_pipeline_callaway_santanna.py`:
  - Whitepaper mode only: registers `CallawaySantAnnaWithControlsAnalyzer(detrend_order=2)` with name `callaway_santanna_with_controls_quadratic`
  - Registers `CallawaySantAnnaVisualizer(context_suffix="_with_controls_quadratic", output_suffix="_quadratic_detrend")`
  - Both added to `wp_order_suffix` execution order
  - Logs quadratic ATT in `_print_summary` with comparison to linear ATT

**To verify:**
```bash
make run-did-pipeline-cs-whitepaper
# or:
export PYTHONPATH=src DATA_DIR=$(pwd)/data DID_WHITEPAPER_MODE=1
python src/housing/scripts/did_pipeline_callaway_santanna.py
```
Check: `output/did-cs-whitepaper/did_callaway_santanna_event_study_quadratic_detrend.png` exists. Quadratic ATT in pipeline log should be less negative than linear ATT.

---

## Work Item 3 — Documentation ✅ DONE

| File | Status | Contents |
|------|--------|----------|
| `docs/methodology/PARALLEL_TRENDS_ANALYSIS.md` | ✅ Created | Full V-shape diagnosis, economic interpretation, what can/cannot be claimed, paper narrative guidance |
| `docs/methodology/ROBUSTNESS_DECISIONS.md` | ✅ Created | k-sweep and threshold sweep results + decisions, matching improvement rationale, quadratic detrend placement |
| `docs/robustness/ROBUSTNESS_FINDINGS.md` | ✅ Updated | Added "Why the residualized ATT is always negative" section with quantitative mechanism |
| `docs/ANALYSIS_PLAN.md` | ✅ This file | Implementation plan for Cursor/collaborators |

---

## Work Item 4 — Paper Section Updates (Pending)

These should be done after running the pipeline with the improved matching to have updated figures and SMD numbers.

### `docs/white-paper/sections/05_results.tex`
- Move the event study figure (`did_callaway_santanna_event_study_full_panel.png`) to the **top** of the results section
- Add 1–2 sentences characterizing the V-shape: "Pre-treatment estimates diverge significantly from zero (max ~$16/month at t=−8), with treated tracts showing higher baseline rent growth rates consistent with pre-existing gentrification pressure in areas where the ordinance was applied."
- ATT tables come **after** the event study discussion
- Add subsection "Sensitivity to detrending assumption" pointing to the appendix quadratic figure

### `docs/white-paper/sections/06_limitations.tex`
- Add explicit parallel trends language: "The pre-treatment event study reveals a non-parallel trend between treated and never-treated tracts (max deviation ~$16/month at t=−8, p<0.001). Under the Rambachan & Roth (2023) smoothness bound M=2, the identified set for the average ATT spans [fill from HonestDiD output]. We interpret results as consistent with bounded positive effects rather than a precise point estimate."
- Reference `docs/methodology/PARALLEL_TRENDS_ANALYSIS.md`

### `docs/white-paper/sections/00_abstract.tex`
- Remove the stale specific point estimate (−$2.95 or any such number)
- Replace with bounded/sensitivity language

---

## File Change Summary

| File | Change | Status |
|------|--------|--------|
| `src/housing/components/processors/trend_matching.py` | Add 3 lag features + caliper env | ✅ Done |
| `src/housing/did_spec.py` | Add caliper constant + resolver | ✅ Done |
| `src/housing/components/analyzers/callaway_santanna_with_controls.py` | Add `detrend_order` + quadratic term | ✅ Done |
| `src/housing/scripts/did_pipeline_callaway_santanna.py` | Register quadratic spec in whitepaper mode | ✅ Done |
| `docs/methodology/PARALLEL_TRENDS_ANALYSIS.md` | New — full diagnosis | ✅ Done |
| `docs/methodology/ROBUSTNESS_DECISIONS.md` | New — sweep decisions | ✅ Done |
| `docs/robustness/ROBUSTNESS_FINDINGS.md` | Updated — V-shape mechanism section | ✅ Done |
| `docs/ANALYSIS_PLAN.md` | New — this file | ✅ Done |
| `docs/white-paper/sections/05_results.tex` | Restructure — lead with event study | ⏳ Pending (after pipeline run) |
| `docs/white-paper/sections/06_limitations.tex` | Add parallel trends + HonestDiD language | ⏳ Pending (after pipeline run) |
| `docs/white-paper/sections/00_abstract.tex` | Remove stale point estimate | ⏳ Pending |

---

## Verification Sequence

```bash
# 1. Verify improved matching
export PYTHONPATH=src DATA_DIR=$(pwd)/data
python src/housing/scripts/run_robustness_sweeps_fast.py
# Expected: docs/robustness/ CSVs updated, slope SMD < 0.5

# 2. Verify quadratic detrend output
make run-did-pipeline-cs-whitepaper
# Expected: output/did-cs-whitepaper/did_callaway_santanna_event_study_quadratic_detrend.png
# Expected: linear spec PNG still generated unchanged
# Expected: pipeline log shows "quadratic ATT > linear ATT" (less negative)

# 3. Run tests
make test
```
