# Part 9: Final Report & Presentation

## Introduction

You've built a complete DiD analysis pipeline: data prep, trend matching (Part 7), and the Callaway-Sant'Anna pipeline with TWFE vs CS comparison (Part 8). Now it's time to synthesize everything into a professional report and presentation that communicates your findings clearly—including your preferred estimate (e.g. CS on the matched sample), the event study, and the TWFE vs CS comparison.

---

## Report Structure

### 1. Introduction

Research question, why it matters, preview of findings, roadmap.

### 2. Background & Data

STR prohibition policy in Chicago; data sources (Zillow ZORI, Chicago Open Data STR prohibitions); panel construction; summary statistics (N tracts, N months, mean rent, treated vs. control).

### 3. Methods

DiD identification strategy; parallel trends (and how you assess it). Trend matching (Part 7); TWFE and Callaway-Sant'Anna (2020) on the same matched sample. Model specification (TWFE equation; CS as ATT(g,t) then aggregated); standard errors; event study and pre-trend test (CS pre-treatment coefficients).

### 4. Results

Preferred estimate (CS overall ATT from matched sample); TWFE for comparison. CS event study plot; TWFE vs CS comparison; pre-trends; dynamic pattern. Optional: cohort dynamics, robustness if you ran other pipelines.

### 5. Discussion

Summary of findings; limitations (parallel trends, external validity, measurement); policy implications and caveats.

### 6. Conclusion

Main finding, key contribution, future research directions.

---

## Key Tables and Figures

Your report should include:

| Item | Description |
|------|-------------|
| Table 1 | Summary statistics (treated vs. control; can use matched sample) |
| Table 2 | Main DiD results: CS overall ATT, and optionally TWFE for comparison |
| Table 3 | TWFE vs CS comparison table (e.g. from `did_twfe_cs_comparison_table.csv`) or robustness checks |
| Figure 1 | Adoption curve or treatment timing (if available from descriptive outputs) |
| Figure 2 | Parallel trends (avg rent by group over time) or pre-trend discussion |
| Figure 3 | **CS event study plot** (main dynamic effects; from `did_callaway_santanna_event_study.png`) |
| Figure 4 | TWFE vs CS side-by-side or difference plot (from `did_twfe_vs_cs_comparison.png` or `did_cs_twfe_difference.png`) |

---

## Presentation Structure

1. Title slide
2. Motivation
3. Research question
4. Data
5. Identification
6. Parallel trends
7. Main result (CS overall ATT; TWFE if contrasting)
8. Event study (CS plot; pre-trends)
9. TWFE vs CS
10. Robustness / design (trend matching; other checks)
11. Limitations
12. Conclusion
13. Questions / backup

---

## Deliverables Checklist

- [ ] Final report (PDF)
- [ ] Presentation slides
- [ ] All code organized in `src/housing/components/`
- [ ] Output files from **run-did-pipeline-cs** in `output/did-cs/`:
  - [ ] `did_panel_data.csv`
  - [ ] `tract_prohibition_dates.csv`
  - [ ] `event_study_coefficients.csv` (TWFE, matched sample)
  - [ ] `event_study_plot.png` (TWFE event study, matched sample)
  - [ ] `did_callaway_santanna_event_study.png` (CS event study)
  - [ ] `did_twfe_vs_cs_comparison.png` (side-by-side)
  - [ ] `did_cs_twfe_difference.png` (difference plot)
  - [ ] `did_cohort_dynamics.png` (optional)
  - [ ] `did_twfe_cs_comparison_table.csv`
- [ ] Any additional outputs from main DiD or covariates pipeline if discussed in the report

---

## Final Reflection

You've completed a full causal inference project:

1. **Understood** the research question and why correlation ≠ causation
2. **Built** panel data infrastructure from raw sources
3. **Created** treatment indicators from policy data
4. **Explored** the data through descriptive analysis
5. **Estimated** causal effects using TWFE
6. **Tested** assumptions with event study analysis
7. **Addressed** parallel trends concerns with trend matching (Part 7)
8. **Ran** the Callaway-Sant'Anna pipeline (Part 8): trend-matched sample, TWFE and CS side by side, and compared the two estimators
9. **Communicated** findings in a professional report and presentation

These skills—causal thinking, data engineering, statistical analysis, and communication—transfer to any empirical research project.
