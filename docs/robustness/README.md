# DiD robustness sweeps

Committed **summary tables** for issue-driven sensitivity analyses (#81 k-neighbors, #82 threshold percentiles). Raw pipeline artefacts stay under gitignored `output/did-cs-robustness/`.

## Regenerate

```bash
export PYTHONPATH=src
export DATA_DIR="$(pwd)/data"
# optional: export CENSUS_API_KEY=...

# k = 1 … 5 (default matching percentile 0.25)
.venv/bin/python src/housing/scripts/run_robustness_sweeps.py --k-only

# percentiles 0.10, 0.15, 0.25, 0.33, 0.50 (default k=3)
.venv/bin/python src/housing/scripts/run_robustness_sweeps.py --percentile-only

# both sweeps (long-running)
.venv/bin/python src/housing/scripts/run_robustness_sweeps.py --all
```

## Outputs

| File | Sweep |
|------|-------|
| [`k_neighbors_sweep_summary.csv`](k_neighbors_sweep_summary.csv) | `DID_MATCH_K_NEIGHBORS` ∈ {1,…,5} |
| [`threshold_percentile_sweep_summary.csv`](threshold_percentile_sweep_summary.csv) | `DID_THRESHOLD_PERCENTILE` grid |

Columns include full-panel and matched CS ATTs, optional CS-with-controls ATT, matched tract counts, and max control reuse from `matching_diagnostics`.
