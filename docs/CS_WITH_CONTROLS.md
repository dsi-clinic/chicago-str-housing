# Callaway-Sant'Anna with Controls: What It Does and Why

## The Problem

The basic Callaway-Sant'Anna (CS) estimator computes treatment effects under the **parallel trends assumption**: absent treatment, treated and control tracts would have followed the same rental price trajectory.

But in Chicago, tracts that adopted STR prohibitions differ systematically from those that didn't. Treated tracts tend to be higher-income, higher-rent neighborhoods. If these tracts were already on a different growth trajectory *before* treatment, our ATT estimates are biased.

## What the Controls Do

Our implementation adds two layers of adjustment:

1. **Census tract covariates** (time-invariant characteristics)
2. **Tract-specific linear time trends**

Both are handled through a **residualization step** that runs *before* the standard CS estimation.

## The Estimation: Two Steps

### Step 1: Residualize the outcome

We estimate the following model using **only pre-treatment observations**:

```
Y_it = α + γ'X_i + Σ_j δ_j · 1[tract_i = j] · t + ε_it
```

Where:
- **Y_it** is the rental price for tract *i* at time *t*
- **X_i** are time-invariant census covariates for tract *i* (standardized to mean 0, SD 1)
- **δ_j · t** is a tract-specific linear time trend (each tract gets its own slope over time)
- The model is fit on pre-treatment data only to avoid contaminating trend estimates with treatment effects

The residualized outcome is:

```
Ỹ_it = Y_it - Ŷ_it + Ȳ
```

We subtract the predicted values and add back the grand mean so the residuals remain in dollar units (interpretable as "rent after removing the effect of covariates and individual trends").

### Step 2: Standard CS on residualized data

For each cohort *g* and time *t*, compute:

```
ATT(g,t) = E[Ỹ_t - Ỹ_{g-1} | treated] - E[Ỹ_t - Ỹ_{g-1} | control]
```

This is the same 2×2 DiD as basic CS, but applied to the detrended, covariate-adjusted outcome.

## The Census Covariates

We use seven tract-level characteristics from ACS data:

| Covariate | Why it matters |
|-----------|---------------|
| `median_income` | Higher-income tracts may have different rent trajectories |
| `median_house_value` | Captures housing market conditions that drive rent growth |
| `baseline_rent` | Controls for level differences (expensive vs. cheap tracts grow differently) |
| `pct_bachelor` | Education composition correlates with gentrification and rent trends |
| `pct_rented` | Renter share affects how supply/demand dynamics play out |
| `median_age` | Age composition proxies for neighborhood lifecycle stage |
| `total_population` | Population density relates to housing market tightness |

**How they enter the model:**

- In **outcome regression (OR)**: covariates are used to residualize rental prices before computing DiD
- In **inverse probability weighting (IPW)**: covariates predict treatment probability (propensity score), which reweights comparison tracts to look more like treated tracts
- In **doubly robust (DR)**: combines both — consistent if *either* the outcome model *or* the propensity score model is correctly specified (this is the default)

## The Tract-Specific Time Trends

Each tract gets its own linear slope over time:

```
tract_17031010100 × time_index
tract_17031010200 × time_index
...
```

This absorbs the fact that, for example, Logan Square tracts may have been appreciating at 3% per year while South Side tracts were flat — even before any STR prohibition.

**Key constraint:** Trends are linear. If treated tracts had *nonlinear* pre-treatment trajectories that differed from controls, this adjustment won't fully fix the bias.

## Why This Helps

### Without controls
The basic CS estimator assumes:
> "Absent treatment, treated and control tracts would have had the same rental price changes."

This is violated if treated tracts (wealthier, gentrifying) were already growing faster.

### With controls
The adjusted CS estimator assumes:
> "After removing the effect of observable tract characteristics and individual linear trends, treated and control tracts would have had the same rental price changes."

This is a weaker (more plausible) assumption. We're not claiming the groups are identical — just that *after accounting for their observable differences and individual growth rates*, the remaining variation is comparable.

## How to Interpret the Results

- **Basic CS ATT**: The raw treatment effect, potentially confounded by pre-existing differences
- **CS with controls ATT**: The treatment effect after adjusting for observable confounders

If both estimates are similar, that's reassuring — it suggests the basic parallel trends assumption holds and selection on observables isn't driving the result.

If they differ substantially, the controls are doing real work. The CS-with-controls estimate is more credible because it relaxes the parallel trends assumption.

## Limitations

1. **Only linear trends**: If pre-treatment trajectories were nonlinear (e.g., accelerating), the adjustment is incomplete
2. **Only observable confounders**: Unobserved factors (zoning changes, transit investment) aren't captured
3. **Pre-treatment fit only**: The trend model can't account for structural breaks that happen to coincide with treatment timing
4. **Covariate availability**: If ACS covariates are missing for some tracts, those tracts get less adjustment

## Code Reference

- Analyzer: `src/housing/components/analyzers/callaway_santanna_with_controls.py`
- Covariates loaded by: `src/housing/components/processors/did_covariate_merger.py`
- Census data from: `src/housing/components/loaders/census_data.py`
- Pipeline: `src/housing/scripts/did_pipeline_callaway_santanna.py`
