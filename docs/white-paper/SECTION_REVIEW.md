# Section-by-section review guide

**PDF:** [`main.pdf`](main.pdf) (built after `make run-did-pipeline-cs-whitepaper-both-local`)  
**Numbers ledger:** [`RESULTS_LEDGER.md`](RESULTS_LEDGER.md)  
**Figures root:** `output/did-cs-whitepaper-threshold/` (binary tables in `-binary/`)

---

## Abstract (`sections/00_abstract.tex`)

**Claims:** V-shaped pre-trends; full-panel ~$20.7/mo not identified as causal; residualized specs are sensitivity only.

**Verify:** `cs_pre_trend_joint_test_periods.csv` (min at t=−8); pipeline log full-panel ATT.

**Open:** Whether to add HonestDiD bounds in a future revision (current heuristic only).

---

## Introduction (`sections/01_intro.tex`)

**Claims:** Ladder starts with full-panel dynamics + PT challenge; matched/residualized are downstream.

**Figures:** None inline.

---

## Data (`sections/03_data.tex`)

**Claims:** ZORI smoothed/SA at source; five-feature matching; 842→450 tract attrition.

**Verify:** `did_descriptive_sample_lineage.csv`, `did_matching_diagnostics.csv`.

---

## Methods (`sections/04_methods.tex`)

**Claims:** Estimator ladder; robustness grids in `docs/robustness/`.

**Verify:** Matches `docs/PREFERRED_SPEC.md`.

---

## Results (`sections/05_results.tex`)

**Claims:** V-shape first; Table tab:main-att; matched +$5.5; residualized not rent-level.

| Figure | File |
|--------|------|
| Fig full-panel | `did_callaway_santanna_event_study_full_panel.png` |
| Fig matched | `did_callaway_santanna_event_study.png` |
| Fig cohorts | `did_cohort_dynamics.png` |
| Fig residualized | `did_callaway_santanna_event_study_with_controls.png` |
| Table main ATT | `output/did-cs-whitepaper-threshold/tables/tab_main_att.tex` |
| Table cohort ATT | `output/did-cs-whitepaper-threshold/tables/tab_cohort_att.tex` |
| Table cohort binary | `output/did-cs-whitepaper-binary/tables/tab_cohort_att.tex` |
| Seasonality | `docs/robustness/tables/seasonality_comparison.tex` |

**Reviewer focus:** Cohort 2019-10 is highlighted as cleanest sub-result; aggregate V-shape still dominates headline identification.

---

## Limitations (`sections/06_limitations.tex`)

**Claims:** PT violation; heuristic not HonestDiD; matching local estimand; ZORI/seasonality; detrending artifacts.

**Verify:** `honest_pretrends_summary.csv`, `pretrend_parallel_trends_regression_summary.csv`.

---

## Conclusion (`sections/07_conclusion.tex`)

**Claims:** Targeting finding is policy-relevant; rent effect not cleanly identified.

---

## After robustness sweeps complete

1. `make plot-robustness-sweeps`
2. Refresh `docs/robustness/ROBUSTNESS_FINDINGS.md` with new matched ATTs and SMDs
3. Update § `\ref{sec:results-robustness}` if grid numbers change materially
