# Beamer narrative (`docs/white-paper/ppt/presentation.tex`)

Slides consume **`output/did-cs-whitepaper/`** (`DID_WHITEPAPER_MODE=1`; `make run-did-pipeline-cs-whitepaper`). Rebuild the PDF with `make whitepaper-deck`.

| Block | Content | Key artefacts |
| ----- | ------- | ------------- |
| Introduction | Title, research question, **naive → preferred ladder** | — |
| § Data and design | Outcome / treatment / sample funnel | `data_funnel.png`, lineage CSVs |
| § Naive benchmark | TWFE on matched panel (heterogeneity caveat) | `did_twfe_vs_cs_comparison.png` |
| § Preferred headline | **Full-panel CS ATT** before matching | `did_callaway_santanna_event_study_full_panel.png`, `tables/tab_*.tex` |
| § Robustness | Matched CS, k / percentile sweeps, threshold vs binary | `docs/robustness/*`, Love plot |
| § Residualized CS | ACS + tract trends (non-comparable scale) | `did_callaway_santanna_event_study_with_controls.png` |
| § SUTVA / pretrends | Donut, dose, Wald / honest pretrends | `sutva_*`, bootstrap CSVs when run |
| § Takeaways | Summary + references | `literature/references.bib` |

Lock defaults in [`docs/PREFERRED_SPEC.md`](../PREFERRED_SPEC.md); divergence vs Tim's Jekyll paper in [`PAPER_ALIGNMENT.md`](PAPER_ALIGNMENT.md).

**New outputs (data-funnel story):**

| File | Role |
|------|------|
| `did_descriptive_cohort_stats.csv` | Per prohibition-cohort means (from `DIDDescriptiveAnalyzer`) |
| `data_funnel.png` | Three-panel tract-count graphic |
| `tables/tab_data_funnel.tex` | Booktabs stages A/B/C |
| `tables/tab_cohort_descriptive.tex` | Cohort table for Step 4 |

If PNGs or `.tex` snippets are missing, placeholders still compile via `\WPFig` / `\WPInput`.
