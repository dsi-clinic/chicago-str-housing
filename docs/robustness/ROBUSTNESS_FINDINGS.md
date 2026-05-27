# Robustness sweep findings

**Method:** `run_robustness_sweeps_fast.py` rematches and re-estimates CS from `output/did-cs-whitepaper-threshold/did_panel_data.csv`.

**Scales:** Full-panel and matched ATTs are **$/month on the rent index**. Residualized CS w/ controls is on a **preconditioned residual scale** — use for sign/stability, not dollar magnitudes.

## k-neighbors (threshold p = 0.25)

| k | Matched controls | Max reuse | Matched CS ATT | Residualized CS ATT |
|---|-----------------:|----------:|---------------:|--------------------:|
| 1 | 84 | 24 | +$2.45 | −$58.27 |
| 2 | 139 | 29 | +$3.46 | −$82.27 |
| **3 (preferred)** | **179** | **30** | **+$4.60** | **−$86.20** |
| 4 | 214 | 41 | +$5.72 | −$87.58 |
| 5 | 247 | 42 | +$6.77 | −$89.73 |

**Full-panel CS** is **flat at ~+$20.65/mo** across k (headline estimand does not depend on matching).

**Matched CS** rises with k (+$2.5 → +$6.8) as more controls enter the pool and reuse increases — direction stays **positive**, magnitude is **moderately sensitive** to k.

**Residualized CS** stays **negative** on its scale for all k.

## Threshold percentile (k = 3)

| Percentile | Ever-treated | Matched CS ATT | Residualized CS ATT |
|------------|-------------:|---------------:|--------------------:|
| 0.10 | 329 | +$9.37 | −$70.45 |
| 0.15 | 311 | +$8.02 | −$75.16 |
| **0.25** | **274** | **+$4.60** | **−$86.20** |
| 0.33 | 245 | +$4.00 | −$73.89 |
| 0.50 | 183 | +$3.65 | −$87.82 |

**Full-panel CS** ~+$20–21/mo across percentiles (stable headline).

**Matched CS** is **positive** everywhere but **larger** when more tracts qualify as treated (lower percentile).

## Figures and tables

- `figures/k_neighbors_att_by_spec.png` — three estimators vs k
- `figures/threshold_percentile_att_by_spec.png` — three estimators vs percentile
- `figures/k_neighbors_sample_diagnostics.png` — matched N and control reuse
- `tables/tab_k_neighbors_sweep.csv`, `tables/tab_threshold_percentile_sweep.csv`

## Paper takeaway

1. **Preferred full-panel** result is **robust** to k and threshold in this grid.
2. **Matched** positive ATTs are **sensitive** to treatment definition (percentile) and **moderately** to k.
3. **Residualized** specs show **negative** preconditioned ATTs — report as parallel-trends/sensitivity, not as rent dollars.
