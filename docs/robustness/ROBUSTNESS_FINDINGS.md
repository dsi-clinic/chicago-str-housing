# Robustness sweep findings (auto-generated)
Compare **full-panel** and **matched** CS ATTs (rent index, $/month) with **residualized CS w/ controls** (different scale — do not compare levels directly).
## k-neighbors (threshold treatment, default percentile)
- Full-panel ATT range: $20.65 – $20.65 across k=[1, 2, 3, 4, 5]
- Matched ATT range: $3.68 – $7.88; residualized range: $-91.62 – $-57.98
- Matched treated tracts at k=3: 274

## Threshold percentile (k=3 matching)
- Full-panel ATT range across percentiles: $19.83 – $21.16
- Ever-treated tracts: 183 (min pct) to 329 (max pct)

## Figures
- `figures/k_neighbors_att_by_spec.png` — ATT vs k for three estimators
- `figures/threshold_percentile_att_by_spec.png` — ATT vs percentile
- `figures/k_neighbors_sample_diagnostics.png` — sample size & control reuse

See [`PREFERRED_SPEC.md`](../PREFERRED_SPEC.md) for locked defaults.
