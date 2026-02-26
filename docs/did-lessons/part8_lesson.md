# Part 8: Callaway-Sant'Anna Pipeline (run-did-pipeline-cs)

## Introduction

In Part 7 you built trend matching to improve comparability of treated and control tracts. Standard TWFE can still be biased when treatment effects are **heterogeneous** across cohorts or over time: TWFE implicitly uses already-treated units as controls and can attach negative weights to some treatment effects, producing misleading averages.

The **Callaway-Sant'Anna (2020)** estimator avoids that by estimating group-time ATTs first (each cohort × time cell), then aggregating with transparent weights. This lesson documents the **run-did-pipeline-cs** pipeline: trend-matched data, TWFE event study, and CS event study on the same sample, with side-by-side comparison.

---

## When to Use Callaway-Sant'Anna

Use the CS pipeline when:

- **Treatment is staggered** — tracts are treated at different times (as with STR prohibition).
- **Effects may be heterogeneous** — by cohort (early vs. late adopters), by time since treatment, or by calendar time.
- You want **interpretable ATTs** — CS estimates are always weighted averages of treatment effects on the treated; TWFE can mix in negative weights when effects differ.

**Key difference:** CS uses only **never-treated** (or not-yet-treated) units as controls. TWFE uses everyone, including already-treated units, which can bias the single coefficient when effects vary.

---

## Pipeline Overview

The script `src/housing/scripts/did_pipeline_callaway_santanna.py` runs:

1. **Data load** — Boundaries, STR prohibitions, ZORI rental panel (same as main DiD pipeline).
2. **Data prep** — Zip–tract crosswalk, zip-to-tract panel, tract prohibition dates, treatment indicator → `did_panel`.
3. **Trend matching** — Restrict to matched treated + control tracts (pre-treatment slope matching) → updated `did_panel`.
4. **Descriptive analysis** — On the matched sample.
5. **TWFE event study** — On the matched sample; outputs `event_study_coefficients`, event study plot.
6. **Callaway-Sant'Anna** — Group-time ATTs on the matched sample, aggregated to event study and overall ATT.
7. **Visualizations** — CS event study plot, TWFE vs CS side-by-side, CS–TWFE difference plot, cohort dynamics, comparison table.

All analysis after trend matching uses the **same matched sample**, so TWFE and CS are comparable.

---

## How to Run

From the project root, with local data in `data/` (or `DATA_DIR` set):

```bash
make run-did-pipeline-cs
```

This runs:

```bash
docker compose run --rm $(mount_data) $(project_name) uv run python src/housing/scripts/did_pipeline_callaway_santanna.py
```

**Preflight:** The script checks that the tract shapefile and ZORI CSV exist under `DATA_DIR` (default `/project/data`). If either is missing, it raises `FileNotFoundError` with a clear message.

---

## Execution Order

The pipeline uses an explicit execution order so that trend matching runs **before** both TWFE and CS:

```
zip_boundaries → tract_boundaries → zip_tract_crosswalk
→ str_prohibition_data → rental_panel_data → zip_to_tract_panel
→ tract_prohibition_dates → treatment_indicator
→ trend_matching
→ did_descriptive_analysis → event_study_analysis → event_study_visualization
→ callaway_santanna_analysis → callaway_santanna_visualizer → cs_comparison_visualizer
```

`TrendMatchingProcessor` overwrites `did_panel` in context with the matched panel, so every component after it (descriptive, TWFE, CS) uses the matched sample.

---

## Key Components

| Component | Role |
|-----------|------|
| `TrendMatchingProcessor` | Match treated tracts to never-treated by pre-treatment rent slope; replace `did_panel` with matched sample. |
| `EventStudyAnalyzer` | TWFE event study (relative time dummies, entity & time FEs) on matched panel. |
| `CallawaySantAnnaAnalyzer` | Estimate ATT(g,t) per cohort × time, aggregate to event study and overall ATT. |
| `CallawaySantAnnaVisualizer` | CS event study plot, TWFE vs CS side-by-side, difference plot, cohort dynamics. |
| `CallawaySantAnnaComparisonVisualizer` | Builds `did_twfe_cs_comparison_table.csv` from CS and TWFE estimates. |

---

## Outputs (output/did-cs/)

| File | Description |
|------|-------------|
| `tract_prohibition_dates.csv` | Tract-level first prohibition date. |
| `did_panel_data.csv` | Full panel (before matching); written by TreatmentIndicatorProcessor. |
| `event_study_coefficients.csv` | TWFE relative-time coefficients (matched sample). |
| `event_study_plot.png` | TWFE event study figure (matched sample). |
| `did_callaway_santanna_event_study.png` | CS event study (ATT by months since treatment). |
| `did_twfe_vs_cs_comparison.png` | Side-by-side TWFE vs CS event study. |
| `did_cs_twfe_difference.png` | Difference (CS − TWFE) by relative time. |
| `did_cohort_dynamics.png` | Cohort-specific dynamic effects. |
| `did_twfe_cs_comparison_table.csv` | Table of rel_time, CS_ATT, TWFE_Coef, differences. |

The TWFE event study plot omits the reference period (k = −1) so both panels in the comparison use the same relative-time bins.

---

## Interpreting the Results

1. **CS event study** — Pre-treatment ATTs should be near zero if parallel trends holds in the matched sample. Post-treatment ATTs show how the effect evolves over time.
2. **TWFE vs CS comparison** — If the two lines diverge, especially post-treatment, TWFE is likely biased by heterogeneity (e.g. negative weights). The difference plot highlights where that bias is largest.
3. **Overall ATT** — Printed in the log and on the CS plot; this is the (weighted) average treatment effect on the treated across post-treatment periods.
4. **Cohort dynamics** — Show whether early vs. late adopters have different effect profiles.

---

## Deliverable

1. Run `make run-did-pipeline-cs` successfully with local data.
2. Inspect `output/did-cs/`: event study plots, comparison table, cohort dynamics.
3. In 1–2 paragraphs: How do TWFE and CS estimates compare? Do pre-treatment CS coefficients support parallel trends in the matched sample? What do you conclude about the effect of STR prohibition on rents?

---

## Next Steps

Part 9 brings everything together into the final report and presentation, including how to present the TWFE vs CS comparison and the role of trend matching in your design.
