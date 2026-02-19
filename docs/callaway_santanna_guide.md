# Callaway & Sant'Anna (2020) Implementation Guide

## Overview

This project now includes the **Callaway & Sant'Anna (2020)** estimator, a robust alternative to standard Two-Way Fixed Effects (TWFE) for staggered difference-in-differences designs.

## Why Callaway & Sant'Anna?

### The Problem with TWFE in Staggered Settings

When treatment is adopted at different times (staggered adoption), standard TWFE event studies can produce **biased estimates** if treatment effects are heterogeneous. This happens because TWFE implicitly uses **already-treated units as controls** for later-treated units.

**Example of the problem:**

```
Cohort A: Treated in 2020
Cohort B: Treated in 2022

In 2021, TWFE compares:
- Cohort B (not yet treated) vs. Cohort A (already treated for 1 year)

This is problematic because Cohort A is "contaminated" by treatment!
```

### How Callaway & Sant'Anna Fixes This

The CS estimator:

1. **Never uses treated units as controls** - only compares to not-yet-treated or never-treated units
2. **Estimates effects separately by cohort and time** - ATT(g,t) for each cohort g at each time t
3. **Aggregates transparently** - combines estimates with known, non-negative weights

## When to Use Each Estimator

| Scenario | Recommended Estimator | Reasoning |
|----------|----------------------|-----------|
| Treatment all at once (single period) | TWFE | Simplest, equivalent to CS |
| Staggered, homogeneous effects | TWFE or CS | Both valid, CS provides robustness check |
| Staggered, heterogeneous effects | **Callaway-Sant'Anna** | TWFE biased, CS robust |
| Uncertain about heterogeneity | **Run both, compare** | Differences indicate heterogeneity |

**Rule of thumb:** If treatment is staggered, **always run Callaway-Sant'Anna** as a robustness check.

## Running the Analysis

### Basic Usage

```bash
# Run Callaway-Sant'Anna pipeline
make run-did-pipeline-cs

# Or if on Box/cloud drive (to avoid Errno 35):
make run-did-pipeline-cs-local
```

### What Gets Produced

1. **Callaway-Sant'Anna event study plot** - Main results showing dynamic ATTs
2. **TWFE vs. CS comparison** - Side-by-side plots to visualize differences
3. **Difference plot** - Shows CS minus TWFE (bias visualization)
4. **Cohort-specific dynamics** - Separate event studies for each treatment cohort
5. **Comparison table** - CSV with detailed estimates from both methods

## Interpreting Results

### 1. Overall ATT

The **average treatment effect on the treated (ATT)** across all post-treatment periods:

```
Overall ATT: $45.23 (SE: $12.34)
95% CI: [$21.04, $69.42]
P-value: 0.0003
```

**Interpretation:** On average, STR prohibitions increased rental prices by $45.23 per month in treated tracts.

### 2. Event Study Plot

The event study shows how treatment effects evolve relative to treatment timing:

- **Pre-treatment (negative x-axis):** Should be near zero (parallel trends test)
- **Post-treatment (positive x-axis):** Shows dynamic effects over time
  - Immediate effect (rel_time = 0, 1, 2...)
  - Long-run effect (rel_time = 24, 36...)
  - Effect trajectory (growing, fading, or stable)

**Example interpretation:**

```
rel_time = -3, -2, -1: All ≈ 0, CIs include 0 ✓ Parallel trends OK
rel_time = 0: $30 (immediate effect)
rel_time = 12: $50 (effect grows over first year)
rel_time = 24: $55 (stabilizes in long run)
```

### 3. TWFE vs. CS Comparison

Compare the two plots side-by-side:

**Scenario A: Similar estimates**
- CS and TWFE plots look similar
- Difference plot shows small differences (< $10)
- **Interpretation:** Treatment effects are roughly homogeneous; TWFE is approximately unbiased

**Scenario B: Different estimates**
- CS and TWFE plots diverge significantly
- Difference plot shows large differences (> $20)
- **Interpretation:** Treatment effects are heterogeneous; TWFE is biased; trust CS estimates

**Common patterns:**

- **TWFE more negative than CS:** TWFE has negative weight bias (treated used as controls)
- **TWFE more positive than CS:** Later cohorts have larger effects (compositional change)
- **Pre-trends differ:** May indicate violations of parallel trends (investigate!)

### 4. Cohort-Specific Dynamics

Separate event studies for each treatment cohort reveal:

- **Do effects differ by cohort?**
  - Early adopters vs. late adopters
  - Different market conditions at treatment time

- **Do effects vary over time since treatment?**
  - Some cohorts: effects grow over time
  - Other cohorts: effects fade or remain constant

**Example:**

```
2020 cohort: Large immediate effect ($60), then stable
2022 cohort: Small initial effect ($20), grows to $40
```

**Interpretation:** Context matters! 2020 adopters (during pandemic) had different experiences than 2022 adopters.

## Technical Details

### Estimator

For each cohort g (defined by first treatment month) and time period t:

```
ATT(g,t) = E[Y_t - Y_{g-1} | G=g] - E[Y_t - Y_{g-1} | C]
```

Where:
- Y_t: Outcome at time t
- Y_{g-1}: Outcome one period before cohort g's treatment
- G=g: Units first treated in period g
- C: Comparison group (never-treated or not-yet-treated)

### Aggregation to Event Study

For each relative time e (e.g., e = 0 is treatment period):

```
ATT(e) = Σ_g w_g × ATT(g, g+e)
```

Where w_g is the proportion of treated units in cohort g.

### Standard Errors

- Computed separately for each ATT(g,t)
- Aggregated using delta method (assumes independence across cohorts)
- Conservative approach (may overstate precision if cohorts are correlated)

### Comparison Group Options

**1. Never-treated (preferred)**
- Units that never receive treatment
- Cleanest comparison (no contamination)
- Requires some units stay untreated

**2. Not-yet-treated**
- Units not yet treated at time t
- Allows more comparisons (larger sample)
- Assumes "no anticipation" - units don't change behavior before treatment

**Current implementation uses:** Never-treated (safer assumption)

## Troubleshooting

### Issue: No never-treated units

**Error:** `No comparison units for cohort X at time Y`

**Solution:** Switch to not-yet-treated comparison group:

```python
CallawaySantAnnaAnalyzer(
    comparison_group="notyettreated",  # Changed from "nevertreated"
    ...
)
```

### Issue: Small cohorts

**Warning:** `Cohort X has only 3 units`

**Solution:** Increase minimum cohort size or combine cohorts:

```python
CallawaySantAnnaAnalyzer(
    min_cohort_size=10,  # Require at least 10 tracts per cohort
    ...
)
```

### Issue: Large standard errors

**Observation:** CIs are very wide in CS but not TWFE

**Explanation:** CS is more honest about uncertainty when:
- Few units in cohorts
- High variability within cohorts
- Limited comparison units

**Not necessarily a problem** - just more conservative inference.

## Limitations

1. **Parallel trends assumption still required**
   - CS doesn't eliminate this assumption
   - Check pre-trends in CS plot (should be ≈ 0)

2. **Heterogeneity across units within cohort**
   - CS allows heterogeneity *across cohorts and time*
   - Still averages over units *within* each cohort

3. **Anticipation effects**
   - If units anticipate treatment and adjust early, estimates may be biased
   - Use `anticipation` parameter if you suspect this

4. **Sample size requirements**
   - Need sufficient units in each cohort
   - Need comparison units (never-treated or not-yet-treated)

## Further Reading

### Key Papers

1. **Callaway, Brantly, and Pedro HC Sant'Anna.** "Difference-in-differences with multiple time periods." *Journal of Econometrics* 225.2 (2021): 200-230.
   - Original CS paper with full methodology

2. **Goodman-Bacon, Andrew.** "Difference-in-differences with variation in treatment timing." *Journal of Econometrics* 225.2 (2021): 254-277.
   - Explains TWFE decomposition and negative weight problem

3. **Sun, Liyang, and Sarah Abraham.** "Estimating dynamic treatment effects in event studies with heterogeneous treatment effects." *Journal of Econometrics* 225.2 (2021): 175-199.
   - Alternative interaction-weighted estimator

4. **Roth, Jonathan, et al.** "What's trending in difference-in-differences? A synthesis of the recent econometrics literature." *arXiv* preprint (2023).
   - Comprehensive review of modern DiD methods

### R Implementation

If you're familiar with R, check out:
- `did` package by Callaway & Sant'Anna: https://github.com/bcallaway11/did
- `DIDmultiplegt` package (Stata/R): Another robust estimator

### Python Resources

- Our implementation is based on the methodology in CS (2021)
- For production use, consider the R `did` package (more mature)
- Alternatively, use `pyfixest` which has CS-style estimators

## Example Workflow

Here's a complete analysis workflow:

```bash
# 1. Run descriptive analysis first
make run-did-pipeline

# 2. Add Callaway-Sant'Anna for robustness
make run-did-pipeline-cs

# 3. Compare results:
# - Check /project/output/did_twfe_vs_cs_comparison.png
# - If estimates differ substantially, trust CS
# - If similar, both methods agree (good sign!)

# 4. Investigate heterogeneity:
# - Check /project/output/did_cohort_dynamics.png
# - Do early vs. late cohorts differ?
# - Do effects grow/fade over time?

# 5. Report both in paper:
# - Main results: Callaway-Sant'Anna (robust)
# - Robustness: TWFE (for comparison)
# - Discuss any differences
```

## Checklist for Reporting Results

When writing up your analysis, include:

- [ ] CS overall ATT with confidence interval
- [ ] CS event study plot with pre-trends visible
- [ ] Comparison with TWFE (show both, discuss differences)
- [ ] Cohort summary (how many cohorts, sizes, timing)
- [ ] Parallel trends assessment (are pre-treatment ATTs ≈ 0?)
- [ ] Heterogeneity discussion (do cohorts differ?)
- [ ] Robustness checks (try different comparison groups)

## Questions?

If you encounter issues or have questions about the implementation:

1. Check the code documentation in `callaway_santanna.py`
2. Review the original CS (2021) paper
3. Open an issue on the project repository
4. Consult with your project mentor

## Summary

**Key takeaway:** When analyzing staggered DiD, **always use Callaway & Sant'Anna** as your primary estimator or at minimum as a robustness check. If CS and TWFE differ substantially, trust CS - the differences reveal important treatment effect heterogeneity that TWFE fails to handle correctly.
