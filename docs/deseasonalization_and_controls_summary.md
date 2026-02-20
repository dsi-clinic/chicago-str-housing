# Deseasonalization and Time-Varying Controls Implementation

## Summary

Implemented enhancements to address the **parallel trends violation** observed in the original Callaway-Sant'Anna results, where pre-treatment coefficients showed a clear U-shaped pattern (ranging from -$40 to near zero) instead of being flat around zero.

## What Was the Problem?

The original CS event study showed:
- Pre-treatment coefficients starting at **-$20 to -$25** at month -12
- **Dropping to -$40** around month -10
- **Gradually rising** back toward zero
- This U-shaped pattern = **violated parallel trends assumption**

**Root causes:**
1. **Seasonality**: Rental prices peak in summer/moving season, low in winter
2. **Treatment timing correlation**: Most STR prohibitions occurred in summer 2016 (212 tracts in Jul-Aug alone)
3. **Differential trends**: Treated and control tracts may have different baseline growth rates

## Solutions Implemented

### 1. Deseasonalization (Primary Fix)

**File**: `src/housing/components/processors/deseasonalize_rental.py`

**What it does:**
- Computes average rental price for each calendar month (Jan, Feb, ..., Dec)
- Subtracts month-of-year effects from observed prices
- Re-centers at the overall mean

**Formula:**
```
deseasonalized_price = price - month_of_year_mean + overall_mean
```

**Why this helps:**
If treatment timing correlates with seasons (e.g., prohibitions in summer when rents are naturally high), you'll see artificial pre-trends. Removing seasonal patterns eliminates this confound.

**Output:**
- Logs seasonal pattern (adjustment for each month)
- Reports maximum seasonal adjustment magnitude
- Preserves original prices in `rental_price_original` column

### 2. Tract-Specific Linear Time Trends

**File**: `src/housing/components/analyzers/callaway_santanna_with_controls.py`

**What it does:**
- Adds tract × time interaction terms to allow each tract its own linear trend
- Residualizes the outcome before computing DiD estimates

**Why this helps:**
Allows for mild violations of parallel trends where treated and control groups have different baseline growth rates, as long as the difference is linear (not accelerating/decelerating).

**Method:**
- Creates time index (months since start)
- Generates tract dummies × time_index
- Runs OLS: `rental_price ~ tract_trends + covariates`
- Uses residuals as outcome in CS estimation

### 3. Time-Invariant Covariate Adjustment

**Covariates included:**
- `median_income` - Census tract median household income
- `median_house_value` - Median house value
- `baseline_rent` - Pre-treatment average rent
- `pct_bachelor` - % with bachelor's degree or higher
- `pct_rented` - % of housing units rented
- `median_age` - Median age of residents
- `total_population` - Total tract population

**Why this helps:**
Controls for confounding due to tract characteristics that differ between treated and control groups and might be correlated with price trends.

## New Pipeline

**File**: `src/housing/scripts/did_pipeline_deseasonalized.py`

**Pipeline steps:**
1. Load data (tracts, rental prices, STR prohibitions, census)
2. Process panel (zip to tract conversion, treatment indicators)
3. **Deseasonalize rental prices** ✨ NEW
4. **Add covariates** (census demographics, baseline rent)
5. Run descriptive analysis
6. Run baseline CS (deseasonalized, no trends)
7. **Run enhanced CS (deseasonalized + tract trends + covariates)** ✨ NEW

**To run:**
```bash
make run-did-pipeline-deseasonalized
```

## Expected Results

**Before (original CS):**
- Pre-treatment coefficients: U-shaped pattern, -$40 to -$20
- Clear parallel trends violation
- Questionable causal interpretation

**After (deseasonalized + controls):**
- Pre-treatment coefficients: Should be flatter, closer to zero
- Reduced pre-treatment dynamics
- More credible parallel trends assumption

**Interpretation:**
If pre-treatment estimates are now closer to zero after deseasonalization:
- Original violation was driven by **seasonality** and/or **differential trends**
- Not fundamental non-comparability of treated vs. control groups
- Post-treatment estimates are now more credible causal effects

If pre-treatment estimates are still not flat:
- May need stronger controls (e.g., matching, synthetic control)
- Or parallel trends may not hold even conditionally
- Consider alternative identification strategies

## Files Created/Modified

### New Files:
1. `src/housing/components/processors/deseasonalize_rental.py`
   - Deseasonalization processor

2. `src/housing/components/analyzers/callaway_santanna_with_controls.py`
   - Enhanced CS analyzer with covariate/trend adjustment

3. `src/housing/scripts/did_pipeline_deseasonalized.py`
   - New pipeline integrating all enhancements

### Modified Files:
1. `Makefile`
   - Added `run-did-pipeline-deseasonalized` target

## Additional Considerations

### Double/Debiased ML
You asked about **double-debiased ML**. This is complementary to deseasonalization:

**When DML helps:**
- Many potential confounders (>10 covariates)
- Complex nonlinear relationships
- Want flexible machine learning prediction of treatment and outcomes

**When to use:**
- After deseasonalization (DML doesn't fix seasonality itself)
- If covariates have complex relationships with outcomes
- If propensity score varies nonlinearly with covariates

**Implementation:**
Could use `econml.DML` package with:
- Outcome model: gradient boosting or random forest
- Propensity model: logistic regression or boosting
- Then estimate ATT on residuals

**Not implemented here because:**
- Start with simpler approach (deseasonalization + linear trends)
- If results are still problematic, DML is a good next step
- DML adds complexity; better to rule out simpler fixes first

### Synthetic Control
Another alternative you mentioned:

**When to use synthetic control instead:**
- Single treated unit (or very few) - **not your case** (you have 373 tracts)
- Long pre-treatment period to validate synthetic match
- Treatment at aggregate level (city, state, country)

**Your setting:**
- Multiple treatment cohorts with staggered adoption
- Callaway-Sant'Anna is more appropriate than synthetic control
- Could potentially use synthetic DiD (Arkhangelsky et al. 2021) as robustness check

## Next Steps

1. **Check results** from deseasonalized pipeline
   - Are pre-treatment estimates flatter now?
   - What is the overall ATT after controls?

2. **Compare with original results**
   - How much did deseasonalization change the estimates?
   - Is the seasonal adjustment economically significant?

3. **Assess remaining threats**
   - Are pre-trends now zero or still problematic?
   - If still problematic, consider:
     - Matching + CS
     - Synthetic DiD
     - Double ML
     - Alternative outcome (growth rates instead of levels)

4. **Robustness checks**
   - Try different comparison groups (not-yet-treated vs. never-treated)
   - Vary cohort size threshold
   - Exclude small cohorts
   - Use quarterly instead of monthly data (if noise is an issue)

## References

- **Callaway & Sant'Anna (2021)**. "Difference-in-differences with multiple time periods." *Journal of Econometrics*.
- **Chernozhukov et al. (2018)**. "Double/debiased machine learning for treatment and structural parameters." *The Econometrics Journal*.
- **Arkhangelsky et al. (2021)**. "Synthetic difference-in-differences." *American Economic Review*.
- **Goodman-Bacon (2021)**. "Difference-in-differences with variation in treatment timing." *Journal of Econometrics*.
