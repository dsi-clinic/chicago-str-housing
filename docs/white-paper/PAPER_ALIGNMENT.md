# Paper alignment: Tim `str-paper` (Jekyll) vs LaTeX `white-paper`

Tim's live reference: [STR_PROHIBITION_PAPER](https://dsi-clinic.github.io/chicago-str-housing/str-paper/STR_PROHIBITION_PAPER/) (`controls` branch, `docs/str-paper/`).

Our authoritative draft: [`docs/white-paper/main.tex`](main.tex) (policy brief). Refresh this table when either pipeline outputs or the Jekyll doc change.

| Section | Tim (`str-paper`) | Ours (`white-paper`) | Action |
|---------|-------------------|----------------------|--------|
| Abstract / headline ATT | ~$6.13/mo, bootstrap CI, demand-side framing | Full-panel CS first; matched + residualized as robustness; conservative pre-trends | Reconcile numbers after merge runs on `AFC/reconcile-paper` |
| Data §3 | ZIP-area interpolation; ~110k obs | Tract crosswalk + lineage funnel (`did_descriptive_sample_lineage.csv`) | Updated in [`sections/03_data.tex`](sections/03_data.tex) |
| Methods §4 | k-NN on **slope only**; tract-cluster bootstrap B=1000; Wald pretrend | **Slope + avg pre-rent** matching; full-panel CS before match; CS w/ controls residualized | Updated in [`sections/04_methods.tex`](sections/04_methods.tex); cite Tim bootstrap as sensitivity |
| Results §5 | Strong positive ATT; subgroup + spillover panels | Naive TWFE → full-panel CS → matched CS → residualized CS (non-comparable scale) | Updated in [`sections/05_results.tex`](sections/05_results.tex) |
| Limitations | Spillover as conservative bound | Matching + pre-trend caveats; threshold/k sweeps | [`sections/06_limitations.tex`](sections/06_limitations.tex) + [`docs/robustness/`](../robustness/) |
| Companion UI | Jekyll site figures | Next.js dashboard on branch [`AFC/dashboard`](https://github.com/dsi-clinic/chicago-str-housing/tree/AFC/dashboard) | Not on `main`; see [`docs/PREFERRED_SPEC.md`](../PREFERRED_SPEC.md) |

## Estimator ladder (both narratives, after reconcile)

1. **Naive / TWFE** — full matched panel, conventional event study (heterogeneity-sensitive).
2. **Preferred headline** — **full-panel Callaway–Sant'Anna** ATT (all tracts with rent data).
3. **Robustness** — trend-matched sample CS; threshold vs binary (`DID_TREATMENT_MODE`); k sweep; percentile sweep.
4. **Residualized CS w/ controls** — ACS + tract linear trends; **not** comparable in level to raw rent ATTs.

## Figure / table sources

| Artifact | Pipeline output (default) |
|----------|---------------------------|
| Full-panel CS event study | `did_callaway_santanna_event_study_full_panel.png` |
| Matched CS event study | `did_callaway_santanna_event_study.png` |
| CS w/ controls | `did_callaway_santanna_event_study_with_controls.png` |
| Bootstrap meta | `cs_tract_bootstrap_meta.csv` (when `CS_BOOTSTRAP_REPS` set) |
| Wald pretrend | `cs_pre_trend_joint_test_aggregate.csv` |
| k / percentile sweeps | `docs/robustness/*_sweep_summary.csv` |
