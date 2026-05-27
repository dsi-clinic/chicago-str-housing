# DiD robustness sweeps

Committed **summary tables** for issue-driven sensitivity analyses (#81 k-neighbors, #82 threshold percentiles). Raw pipeline artefacts stay under gitignored `output/did-cs-robustness/`.

## Regenerate

```bash
export PYTHONPATH=src
export DATA_DIR="$(pwd)/data"
# optional: export CENSUS_API_KEY=...

# Fast path when a whitepaper panel CSV already exists
.venv/bin/python -u src/housing/scripts/run_robustness_sweeps_fast.py \\
  --panel-csv output/did-cs-whitepaper-threshold/did_panel_data.csv

# percentiles 0.10, 0.15, 0.25, 0.33, 0.50 (default k=3)
.venv/bin/python src/housing/scripts/run_robustness_sweeps.py --percentile-only

# both sweeps (long-running; auto-plots when done)
.venv/bin/python -u src/housing/scripts/run_robustness_sweeps.py --all
.venv/bin/python src/housing/scripts/plot_robustness_sweeps.py
```

## Outputs

| File | Sweep |
|------|-------|
| [`k_neighbors_sweep_summary.csv`](k_neighbors_sweep_summary.csv) | `DID_MATCH_K_NEIGHBORS` ∈ {1,…,5} |
| [`threshold_percentile_sweep_summary.csv`](threshold_percentile_sweep_summary.csv) | `DID_THRESHOLD_PERCENTILE` grid |
| [`figures/`](figures/) | ATT lines (full-panel vs matched vs residualized) + sample diagnostics |
| [`tables/`](tables/) | Wide CSV tables for appendix |
| [`ROBUSTNESS_FINDINGS.md`](ROBUSTNESS_FINDINGS.md) | Auto narrative with numeric ranges |

Columns include full-panel and matched CS ATTs, optional CS-with-controls ATT, matched tract counts, and max control reuse from `matching_diagnostics`.
