# DiD pipeline runbook — Callaway & Sant’Anna (`did_pipeline_callaway_santanna`)

## One-command run (local repo)

From the repository root, with tract shapefile + ZORI CSV under `./data`:

```bash
export DATA_DIR="$(pwd)/data"
export PYTHONPATH="src:${PYTHONPATH}"
# Optional: persist outputs elsewhere
# export DID_CS_OUTPUT_DIR="$(pwd)/output/did-cs"

python -m housing.scripts.did_pipeline_callaway_santanna
```

If you use Python from the project virtual environment, substitute `python` with `.venv/bin/python` (paths vary).

## Prerequisites

- `./data/tl_2023_17_tract/tl_2023_17_tract.shp` (and `.dbf`, `.shx`, `.prj`, …).
- `./data/Zip_zori_uc_sfrcondomfr_sm_month.csv` (monthly ZIP-level rents).
- Network on first run for Chicago Data Portal API loads (ZIP, STR, city boundaries) unless cached under `DATA_DIR/.cache/`.
- `CENSUS_API_KEY` recommended for ACS covariates in `DIDCovariateProcessor`; the pipeline proceeds if the key is absent but covariates may degrade.

Avoid running with the project folder on flaky cloud-sync mounts; GDAL shapefile locks can yield Errno 35 (see pipeline preflight messages).

## Key hyperparameters (current script defaults)

Registered in [`src/housing/scripts/did_pipeline_callaway_santanna.py`](../src/housing/scripts/did_pipeline_callaway_santanna.py).

| Stage | Setting | Typical value |
| --- | --- | --- |
| Trend matching | `k_neighbors`, `min_pre_periods` | `3`, `6` |
| TWFE event study | `pre_periods`, `post_periods` | `12`, `36` |
| Callaway–Sant’Anna | `comparison_group`, `anticipation`, `min_cohort_size` | `"nevertreated"`, `0`, `5` |
| CS with controls | `comparison_group`, `anticipation`, `min_cohort_size`, `include_covariates`, `include_tract_trends`, `estimation_method` | same as baseline CS, `True`, `True`, `"dr"` |

Implementation details for residualization, covariates, and tract-linear trends mirror [`docs/CS_WITH_CONTROLS.md`](CS_WITH_CONTROLS.md) and [`callaway_santanna_with_controls.py`](../src/housing/components/analyzers/callaway_santanna_with_controls.py).

## Slide-oriented outputs (`DID_CS_OUTPUT_DIR`)

After a successful run **all** CSV/PNG artefacts for temporal dynamics, geography, descriptive balance, parallel-trends regression summary, TWFE vs CS comparisons, and main CS figures live alongside each other:

- Dynamics: `did_adoption_curve.png`, `did_parallel_trends.png`, `did_diagnostic_analysis.png`; `did_trends_*.csv`
- Diagnostics: `pretrend_*.csv`
- Geography: `did_spatial_sample*.png`, `did_spatial_sample_tract_table.csv`
- Primary estimates: `did_callaway_santanna_event_study.png`, `did_callaway_santanna_event_study_with_controls.png`, `did_twfe_vs_cs_comparison.png`, `did_cs_twfe_difference.png`, `did_cohort_dynamics.png`, `did_twfe_cs_comparison_table.csv`

Stable filenames are intended for Beamer under [`docs/white-paper/ppt/`](white-paper/ppt/).

## Whitepaper / deck bundle (`DID_WHITEPAPER_MODE`)

Set `DID_WHITEPAPER_MODE=1` (or `Makefile` target `run-did-pipeline-cs-whitepaper`) to land **all** standard outputs **plus**:

- `honest_pretrends_summary.csv` — naive TWFE pretrend magnitudes (\(\max\) pre coeffs, discrete smoothness heuristic).
- `sutva_donut_summary.csv`, `sutva_dose_quartiles.csv`, `sutva_donut.png`, `sutva_dose_response.png` — spatial subsample / neighbour-share contrasts.
- `cohort_dynamics_explainer.{png,csv}` — juxtaposed pooled CS curves vs raw-rent cohort paths.
- `tables/tab_*.tex` — `\input`-ready LaTeX fragments (requires the pipeline to finish the steps above).

Default output directory shifts to **`output/did-cs-whitepaper/`** whenever `DID_WHITEPAPER_MODE` is truthy (unless overridden by `DID_CS_OUTPUT_DIR`).

Build slides after artefacts exist:

```bash
make run-did-pipeline-cs-whitepaper
make whitepaper-deck                # latexmk docs/white-paper/ppt/presentation.tex
```

Deck/story checklist: [`docs/white-paper/STORY_OUTLINE.md`](white-paper/STORY_OUTLINE.md).

## Interpreting two overall ATTs

- **Baseline CS** operates on tract-month **rent levels** (`rental_price` in the merged panel).

- **CS with covariates + tract trends** uses a **residualized** outcome fit on **pre-prohibition months only**. The pooled ATT remains an average causal contrast on that residual scale; do **not** treat its dollar magnitude as interchangeable with observed rent levels without unpacking the residualization step [`CS_WITH_CONTROLS.md`](CS_WITH_CONTROLS.md).
