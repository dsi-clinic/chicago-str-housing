# Part 5: Fixed Effects & DiD Estimation

## Introduction

With our DiD panel data ready and descriptive analysis complete, we can now estimate the treatment effect. This lesson covers the intuition behind fixed effects and how to estimate a two-way fixed effects (TWFE) DiD model.

---

## What Are Fixed Effects?

Fixed effects **control for unobserved characteristics** that don't change over time (entity FE) or that affect all units equally (time FE).

### Entity Fixed Effects (Tract FE)

Tract fixed effects control for anything about a tract that stays constant over time:
- Location (lakefront, downtown, etc.)
- Historical neighborhood character
- Underlying land value
- Distance to transit

**How it works:** Instead of comparing Tract A to Tract B (which differ in many ways), we compare Tract A *to itself* over time. Each tract gets its own intercept.

**What it removes:** All time-invariant differences between tracts. If treated tracts are systematically "nicer" than control tracts, tract FE handles this.

### Time Fixed Effects (Month FE)

Time fixed effects control for anything that affects all tracts equally in a given month:
- City-wide economic conditions
- Seasonal rental market patterns
- Interest rate changes
- COVID-19 effects (in 2020)

**How it works:** Each month gets its own intercept. If all rents went up in March 2020, month FE absorbs that.

**What it removes:** Common shocks and trends affecting the entire market.

### Two-Way Fixed Effects (TWFE)

Using *both* tract and time fixed effects:

```
rental_price = β₀ + β₁(treated) + αᵢ + γₜ + ε
```

Where:
- `αᵢ` = tract fixed effect (one for each tract)
- `γₜ` = time fixed effect (one for each month)
- `β₁` = **the treatment effect** (what we want)

After controlling for tract and time effects, `β₁` captures the change in rent attributable to STR prohibition, identified from the timing of treatment.

---

## Intuition: What TWFE Does

TWFE is equivalent to:
1. De-meaning by tract (subtract each tract's average)
2. De-meaning by time (subtract each month's average)
3. Running OLS on the residuals

What remains is **within-tract, within-time variation**. The only source of such variation is *when* a tract becomes treated relative to other tracts.

This is exactly the DiD logic: compare how treated tracts change relative to control tracts, after removing permanent tract differences and common time trends.

---

## Estimation with linearmodels

The `linearmodels` package provides `PanelOLS` for fixed effects estimation.

### Setup

```python
from linearmodels import PanelOLS
import pandas as pd

# Set multi-index: (entity, time)
panel = did_panel.set_index(["tract_geoid", "month"])

# Ensure proper types
panel["treated"] = panel["treated"].astype(float)
panel["rental_price"] = panel["rental_price"].astype(float)
```

### Estimate the Model

```python
model = PanelOLS.from_formula(
    "rental_price ~ 1 + treated",
    data=panel,
    entity_effects=True,   # Tract FE
    time_effects=True      # Month FE
)

results = model.fit(cov_type="clustered", cluster_entity=True)
print(results.summary)
```

**Key arguments:**
- `entity_effects=True`: Include tract fixed effects
- `time_effects=True`: Include time fixed effects
- `cov_type="clustered", cluster_entity=True`: Cluster standard errors by tract (accounts for serial correlation within tracts)

---

## Interpreting Results

The output will look something like:

```
                          PanelOLS Estimation Summary
================================================================================
Dep. Variable:           rental_price   R-squared:                        0.0234
Estimator:                   PanelOLS   R-squared (Between):              0.0012
No. Observations:              125000   R-squared (Within):               0.0234
Date:                Wed, Jan 21 2026   R-squared (Overall):              0.0156
Time:                        14:32:15   Log-likelihood                -9.234e+05
Cov. Estimator:             Clustered
                                        F-statistic:                      18.234
Entities:                         500   P-value                           0.0000
Avg Obs:                       250.00   Distribution:                   F(1,499)
Min Obs:                       120.00
Max Obs:                       250.00   F-statistic (robust):             12.456
                                        P-value                           0.0004

                             Parameter Estimates
================================================================================
            Parameter  Std. Err.     T-stat    P-value    Lower CI    Upper CI
--------------------------------------------------------------------------------
const         1245.32      8.234    151.234     0.0000     1229.12     1261.52
treated        -32.45     12.567     -2.582     0.0101      -57.12       -7.78
================================================================================
```

### Key Numbers

1. **Coefficient on `treated`:** -32.45
   - Interpretation: STR prohibition reduces monthly rent by $32.45 on average
   - Sign: Negative means rent *decreases* when treatment turns on

2. **Standard Error:** 12.567
   - Measures uncertainty in the estimate
   - Clustered by tract to account for within-tract correlation

3. **T-statistic:** -2.582
   - Coefficient divided by standard error
   - Larger absolute values = more statistically significant

4. **P-value:** 0.0101
   - Probability of seeing this result if true effect were zero
   - p < 0.05 conventionally means "statistically significant"

5. **95% Confidence Interval:** [-57.12, -7.78]
   - We're 95% confident the true effect is in this range
   - Doesn't include zero, consistent with p < 0.05

### Writing the Interpretation

> "We estimate that STR prohibition reduces monthly rental prices by $32.45 (SE = $12.57, p = 0.01). This effect is statistically significant at the 5% level. The 95% confidence interval of [-$57.12, -$7.78] suggests the true effect is likely a modest reduction in rents."

---

## Building the DIDAnalyzer Component

Your component should:
1. Get the DiD panel from context
2. Set up the panel index
3. Estimate the TWFE model
4. Extract and return key results (coefficient, SE, p-value, CI)
5. Log a summary of findings

Return a dictionary with the results object and extracted statistics for easy access.

---

## Deliverable

1. **`DIDAnalyzer`** component in `src/housing/components/analyzers/`
2. Results output with:
   - Treatment effect estimate
   - Standard error (clustered)
   - P-value
   - 95% confidence interval
3. One-paragraph interpretation of the main finding

---

## Next Steps

Part 6 covers **event study analysis**—estimating separate effects for each period before and after treatment. This lets us:
- Formally test parallel trends (pre-treatment effects should be ~0)
- See how the effect evolves over time (immediate vs. gradual)
