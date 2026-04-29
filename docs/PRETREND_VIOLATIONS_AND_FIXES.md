# Pre-Trend Violations in CS Event Study: Diagnosis and Recommendations

## Observed Problem

The Callaway-Sant'Anna event study plot shows a **clear pre-treatment trend violation**:

- **Pre-treatment period** (months -12 to -1): Coefficients start at approximately **+$14** at month -12 and decline steadily to **$0** at the reference period (month -1)
- **Expected pattern**: Coefficients should be flat and centered around zero in pre-treatment periods
- **What we see instead**: A systematic downward slope in the blue shaded region

## What This Means

The parallel trends assumption is **violated even after adjusting for**:
- Time-invariant census covariates (median_income, pct_bachelor, etc.)
- Tract-specific linear time trends

**Implication**: The post-treatment decline (ATT = -$85.85) could be:
1. A true causal effect of STR prohibition on rental prices, OR
2. A continuation of pre-existing differential trends that we failed to remove

**We cannot distinguish between these interpretations without fixing the pre-trends.**

## Why Current Controls Are Insufficient

### 1. Linear Trends Are Too Restrictive

From `callaway_santanna_with_controls.py`, the model fits:
```
Y_it = α + γ'X_i + Σ_j δ_j · 1[tract_i = j] · t + ε_it
```

Where `δ_j · t` is a **linear** tract-specific trend estimated from pre-treatment data.

**Problem**: Treated tracts may have **nonlinear** (accelerating or decelerating) growth trajectories. A linear trend cannot capture this.

### 2. Time-Invariant Covariates Miss Growth Rate Heterogeneity

Census covariates capture **levels** (e.g., median income in 2023), not **growth rates** (e.g., how fast income is rising).

Treated tracts may have been gentrifying faster than controls even conditional on their baseline characteristics.

## Recommended Fixes

### Option 1: More Flexible Trend Specifications

**What to do**: Replace linear trends with more flexible functional forms.

**Implementation options**:

1. **Quadratic trends**:
   ```python
   # Add tract × t² terms in addition to tract × t
   panel["time_squared"] = panel["time_index"] ** 2
   trend_dummies_squared = pd.get_dummies(
       panel["tract_geoid"], prefix="tract_sq"
   ) * panel["time_squared"].values.reshape(-1, 1)
   ```

2. **Cohort-specific trends**:
   - Allow different linear slopes for different treatment cohorts
   - Treatment cohorts may have systematically different pre-trends

3. **Non-parametric trends**:
   - Include separate dummies for each pre-treatment period
   - Most flexible but uses many degrees of freedom

**Trade-off**: More flexibility improves fit but reduces power and increases risk of overfitting.

### Option 2: Restrict to Better-Balanced Cohorts

**What to do**: Some treatment cohorts may have better pre-trends than others. Identify and keep only cohorts with flat pre-trends.

**Implementation**:
1. Run CS separately for each cohort
2. Plot pre-treatment coefficients by cohort
3. Drop cohorts that show systematic pre-treatment divergence
4. Re-estimate with remaining cohorts only

**Trade-off**: Loses external validity if you drop many cohorts. Results apply only to the subset with good pre-trends.

### Option 3: Stricter Matching on Pre-Treatment Trends

**What to do**: The existing `trend_matching.py` processor does K-NN matching on pre-treatment price levels. Make matching more aggressive.

**Implementation options**:

1. **Reduce number of matches**:
   ```python
   # In trend_matching.py, reduce n_neighbors
   matcher = NearestNeighbors(n_neighbors=3, metric="euclidean")  # instead of 5
   ```

2. **Match on growth rates, not levels**:
   ```python
   # Compute pre-treatment growth rate for each tract
   pre_growth = (
       panel.groupby("tract_geoid")["rental_price"]
       .apply(lambda x: (x.iloc[-1] - x.iloc[0]) / x.iloc[0])
   )
   # Use pre_growth as matching variable instead of price levels
   ```

3. **Impose caliper restrictions**:
   - Only match if distance is below a threshold
   - Discard treated units with no close matches

4. **Use synthetic control instead of K-NN**:
   - Construct a weighted average of control tracts that best reproduces each treated tract's pre-treatment trajectory

**Trade-off**: Stricter matching reduces bias but may drop many treated units (smaller effective sample).

### Option 4: Stacked Difference-in-Differences

**What to do**: Instead of pooling all cohorts in a single CS estimator, run separate 2×2 DiDs for each cohort with its own clean comparison group, then stack the results.

**Implementation**:
1. For each treatment cohort *g*:
   - Restrict sample to cohort *g* + never-treated units
   - Run simple 2×2 DiD: ATT(g) = E[Y_{post} - Y_{pre} | treated] - E[Y_{post} - Y_{pre} | control]
   - Test pre-trends separately for this cohort
2. Stack all cohort-specific ATTs with appropriate weights
3. Report both cohort-specific and pooled estimates

**Advantage**: Easier to diagnose which cohorts have good vs. bad pre-trends.

**Trade-off**: Loses efficiency if all cohorts truly have common trends. More complex to implement.

### Option 5: Synthetic Difference-in-Differences (Arkhangelsky et al. 2021)

**What to do**: Use the newer SDID estimator that reweights both units and time periods to achieve pre-treatment balance.

**Implementation**:
- Use the `synthdid` R package or Python port
- Automatically chooses weights to minimize pre-treatment RMSE
- More robust to violations than standard DiD or CS

**Trade-off**: Requires new estimator. Less interpretable weights than CS.

## Diagnostic Steps Before Attempting Fixes

### 1. Run Pre-Trend Test

From `pretrend_diagnostic.py`:
```python
# Check if pre-treatment coefficients are jointly zero
# Should output: number of significant pre-periods, F-test p-value
```

Expected result: Will likely show significant joint test, confirming violation.

### 2. Examine Pre-Trends by Cohort

Plot event study separately for each treatment cohort:
```python
for cohort in treated_cohorts:
    # Run CS for this cohort only
    # Plot pre-treatment coefficients
    # Flag cohorts with large/significant pre-trends
```

### 3. Compare Treatment vs. Control Trends Visually

From `did_trends.py` visualizer:
- Plot raw rental price trajectories for treated vs. control tracts
- Add vertical line at first treatment date
- Check if trends diverge before treatment

### 4. Test Sensitivity to Matching

Re-run pipeline with different matching specifications:
- No matching (current baseline)
- K-NN with k=3, k=5, k=10
- Caliper matching with distance threshold
- Synthetic control

Compare ATT estimates across specifications. If results are stable, more confidence. If they vary widely, matching choice matters (suggests confounding).

## Implementation Priority

**High priority** (do first):
1. Run diagnostic tests (pre-trend test, cohort-specific plots)
2. Try quadratic trends (easiest code change)
3. Compare matched vs. unmatched samples

**Medium priority** (if high-priority fixes insufficient):
1. Cohort restriction based on pre-trend diagnostics
2. Stricter matching with calipers

**Low priority** (substantial refactor, use if other fixes fail):
1. Stacked DiD
2. Synthetic DiD

## Expected Outcomes

After implementing fixes:
- **Pre-treatment coefficients**: Should be flat and statistically indistinguishable from zero
- **ATT estimate**: May change substantially (could be smaller, larger, or even flip sign)
- **Interpretation**: Only the estimate from a model with flat pre-trends is credible

## References

- Callaway, B., & Sant'Anna, P. H. (2021). Difference-in-differences with multiple time periods. *Journal of Econometrics*, 225(2), 200-230.
- Roth, J. (2022). Pretest with caution: Event-study estimates after testing for parallel trends. *American Economic Review: Insights*, 4(3), 305-322.
- Arkhangelsky, D., Athey, S., Hirshberg, D. A., Imbens, G. W., & Wager, S. (2021). Synthetic difference-in-differences. *American Economic Review*, 111(12), 4088-4118.

## Next Steps

1. Document this issue in PR comments or team discussion
2. Decide which fix(es) to implement based on project timeline and goals
3. Implement chosen fix(es) and verify pre-trends are resolved
4. Re-estimate ATT and update interpretation
5. Consider robustness checks across multiple specifications
