# Beamer narrative (`docs/white-paper/ppt/presentation.tex`)

Slides consume **`output/did-cs-whitepaper/`** (`DID_WHITEPAPER_MODE=1`; `make run-did-pipeline-cs-whitepaper`). Rebuild the PDF with `make whitepaper-deck`.

| Block | Content | Key artefacts |
| ----- | ------- | ------------- |
| Introduction | Title, research question, staggered-DiD motivation | — |
| § Data and design | Outcome / treatment / eventual sample size | — |
| Geography | Matched panel map | `did_story_map.png` |
| § From raw data … | **Steps 1–5 (policy walkthrough)** | `data_funnel.png`, `tables/tab_data_funnel.tex`, `tables/tab_cohort_descriptive.tex`, `did_descriptive_cohort_stats.csv` |
| Adoption & trends | Adoption + parallel rents | `did_adoption_curve.png`, `did_parallel_trends.png` |
| § Estimator | CS vs TWFE intuition | — |
| § Results | Baseline CS, CS w/ controls, ATT table, cohort panels, explainer, TWFE vs CS | `did_callaway_santanna*.png`, cohort dynamics PNGs, comparison plot |
| § SUTVA | Donut + dose + honest pretrends | `sutva_*`, `tables/tab_honest_pretrends.tex` |
| § Takeaways | Summary + references | `literature/references.bib` |

**New outputs (data-funnel story):**

| File | Role |
|------|------|
| `did_descriptive_cohort_stats.csv` | Per prohibition-cohort means (from `DIDDescriptiveAnalyzer`) |
| `data_funnel.png` | Three-panel tract-count graphic |
| `tables/tab_data_funnel.tex` | Booktabs stages A/B/C |
| `tables/tab_cohort_descriptive.tex` | Cohort table for Step 4 |

If PNGs or `.tex` snippets are missing, placeholders still compile via `\WPFig` / `\WPInput`.
