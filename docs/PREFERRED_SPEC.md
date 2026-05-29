# Preferred DiD specification (locked defaults)

Single reference for the **headline** staggered-DiD design. Robustness sweeps and treatment-definition sensitivity are documented separately; this doc states what the paper/deck treat as **preferred**.

## Headline estimand

| Layer | Spec | Notes |
|-------|------|-------|
| **Primary** | Full-panel **Callaway–Sant'Anna** (`nevertreated`, `min_cohort_size=5`) | Run **before** trend matching; keys `cs_overall_att_full_panel` |
| **Matched robustness** | Same CS on **trend-matched** panel | k-NN on standardized slope, avg pre-rent, and lagged levels at t−1/−6/−12 (global calendar anchor) |
| **TWFE contrast** | Matched-sample event study | Report early as **naive** benchmark only |
| **Residualized** | CS w/ ACS + tract linear trends | Robustness; **do not** compare ATT levels to raw rent CS |

## Treatment definition (default)

| Setting | Value |
|---------|-------|
| Mode | `DID_TREATMENT_MODE=threshold` (also run `binary` for sensitivity) |
| Threshold rule | Year-specific percentile of restricted-unit share vs ACS occupied units |
| Default percentile | `0.25` (`DID_TREATMENT_THRESHOLD_PERCENTILE` / `DID_THRESHOLD_PERCENTILE` env) |

## Matching (default)

| Setting | Value |
|---------|-------|
| `k_neighbors` | `3` (`DID_TREND_MATCH_K_NEIGHBORS`; override `DID_MATCH_K_NEIGHBORS`) |
| `min_pre_periods` | `6` |
| Features | `pre_trend_slope`, `avg_pre_rent`, `rent_lag_1`, `rent_lag_6`, `rent_lag_12` (standardized) |
| Caliper | `None` (optional `DID_MATCH_CALIPER` in standardized feature space) |

## Callaway–Sant'Anna (matched branch)

| Setting | Value |
|---------|-------|
| `comparison_group` | `nevertreated` |
| `anticipation` | `0` |
| `min_cohort_size` | `5` |
| Bootstrap | Optional; `CS_BOOTSTRAP_REPS` / `--cs-bootstrap-reps` (Tim's paper uses B=1000) |

## TWFE window

| Setting | Value |
|---------|-------|
| Pre periods | `12` |
| Post periods | `36` |

## Output layout

| Run | Directory |
|-----|-----------|
| Standard CS | `output/did-cs/` (or `DID_CS_OUTPUT_DIR`) |
| Whitepaper extras | `output/did-cs-whitepaper/` (`DID_WHITEPAPER_MODE=1`) |
| Threshold vs binary | `{base}-threshold`, `{base}-binary` when `DID_TREATMENT_MODE=both` |
| k / percentile sweeps | `output/did-cs-robustness/…` → summaries in `docs/robustness/` |

## Environment variables (copy-paste)

```bash
export DATA_DIR="$(pwd)/data"
export PYTHONPATH=src
export CENSUS_API_KEY="..."   # see .env.example
export DID_TREATMENT_MODE=threshold
export DID_CS_OUTPUT_DIR="$(pwd)/output/did-cs-whitepaper-threshold"
# optional whitepaper diagnostics + LaTeX tables:
export DID_WHITEPAPER_MODE=1
# optional tract-cluster bootstrap on matched CS:
export CS_BOOTSTRAP_REPS=399
export CS_BOOTSTRAP_SEED=42
```

## Companion dashboard

The interactive Next.js audit UI lives on branch **[`AFC/dashboard`](https://github.com/dsi-clinic/chicago-str-housing/tree/AFC/dashboard)** — **not** on `main`. Sync from `main` for pipeline output paths only.

## Related docs

- [`docs/DID_CS_RUNBOOK.md`](DID_CS_RUNBOOK.md) — how to run pipelines
- [`docs/CS_WITH_CONTROLS.md`](CS_WITH_CONTROLS.md) — residualized CS semantics
- [`docs/robustness/README.md`](robustness/README.md) — k and percentile sweeps
- [`docs/white-paper/PAPER_ALIGNMENT.md`](white-paper/PAPER_ALIGNMENT.md) — vs Tim's Jekyll paper
