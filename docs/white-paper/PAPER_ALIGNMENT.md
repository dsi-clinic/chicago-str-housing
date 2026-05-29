# Paper alignment: Tim `str-paper` (Jekyll) vs LaTeX `white-paper`

Tim's live reference: [STR_PROHIBITION_PAPER](https://dsi-clinic.github.io/chicago-str-housing/str-paper/STR_PROHIBITION_PAPER/) (`controls` branch, `docs/str-paper/`).

Our authoritative draft: [`docs/white-paper/main.tex`](main.tex) (policy brief). Refresh this table when either pipeline outputs or the Jekyll doc change.

| Section | Tim (`str-paper`) | Ours (`white-paper`) | Action |
|---------|-------------------|----------------------|--------|
| Abstract / headline ATT | ~$6.13/mo, bootstrap CI, demand-side framing | **PT violation first**; full-panel ~$20.7/mo with caveats; matched ~$5.5/mo; no residualized headline | **Aligned** — [`RESULTS_LEDGER.md`](RESULTS_LEDGER.md) |
| Data §3 | ZIP-area interpolation; ~110k obs | Tract crosswalk + five-feature matching + lineage funnel | [`sections/03_data.tex`](sections/03_data.tex) |
| Methods §4 | k-NN on **slope only**; tract-cluster bootstrap B=1000; Wald pretrend | **Five-feature** k-NN; full-panel CS before match; CS w/ controls residualized | [`sections/04_methods.tex`](sections/04_methods.tex) |
| Results §5 | Strong positive ATT; subgroup + spillover panels | **V-shape event study first** → ATT table → matched → cohorts → residualized appendix | [`sections/05_results.tex`](sections/05_results.tex); [`SECTION_REVIEW.md`](SECTION_REVIEW.md) |
| Limitations | Spillover as conservative bound | PT violation + matching + ZORI/seasonality + detrending artifacts | [`sections/06_limitations.tex`](sections/06_limitations.tex) |
| Companion UI | Jekyll site figures | Next.js dashboard on [`AFC/dashboard`](https://github.com/dsi-clinic/chicago-str-housing/tree/AFC/dashboard) | Not on `main` |

## Estimator ladder (ours, post fresh run)

1. **Full-panel CS event study** — show V-shape; joint pre-trend Wald rejects flat null.
2. **Pooled ATTs** — full-panel ~$20.7/mo; matched ~$5.5/mo (k=3, five features); interpret with PT caveats.
3. **Robustness grids** — `docs/robustness/` (regenerate via `make run-robustness-sweeps-local`).
4. **Residualized CS** — appendix only; not rent-comparable.

## Figure / table sources (whitepaper run)

| Artifact | Path |
|----------|------|
| Full-panel CS event study | `output/did-cs-whitepaper-threshold/did_callaway_santanna_event_study_full_panel.png` |
| Matched CS event study | `output/did-cs-whitepaper-threshold/did_callaway_santanna_event_study.png` |
| Cohort ATT table (threshold) | `output/did-cs-whitepaper-threshold/tables/tab_cohort_att.tex` |
| Cohort ATT table (binary) | `output/did-cs-whitepaper-binary/tables/tab_cohort_att.tex` |
| Seasonality diagnostic | `docs/robustness/SEASONALITY_DIAGNOSTIC.md` |
| k / percentile sweeps | `docs/robustness/*_sweep_summary.csv` |
