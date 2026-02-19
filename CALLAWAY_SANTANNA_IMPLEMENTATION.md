# Callaway & Sant'Anna Implementation Summary

## What Was Implemented

I've implemented a complete **Callaway & Sant'Anna (2020)** estimator for your staggered difference-in-differences analysis, addressing the TWFE limitations identified in your current implementation.

## Files Created

### 1. Core Implementation
- **`src/housing/components/analyzers/callaway_santanna.py`** (314 lines)
  - Complete CS estimator implementation
  - Group-time ATT estimation
  - Event study aggregation
  - Cohort-specific dynamics
  - Flexible comparison groups (never-treated or not-yet-treated)

### 2. Visualization
- **`src/housing/components/visualizers/callaway_santanna.py`** (293 lines)
  - Main CS event study plot
  - TWFE vs. CS side-by-side comparison
  - Difference plot (CS - TWFE) showing bias
  - Cohort-specific dynamic effects plots
  - Comparison table generator

### 3. Pipeline
- **`src/housing/scripts/did_pipeline_callaway_santanna.py`** (215 lines)
  - Complete pipeline running both TWFE and CS
  - Automatic comparison and diagnostics
  - Detailed summary output

### 4. Documentation
- **`docs/callaway_santanna_guide.md`** - Complete implementation guide
- **`docs/did_estimator_comparison.md`** - Quick reference comparing TWFE vs. CS
- **`docs/README.md`** - Updated documentation index

### 5. Updates
- **`Makefile`** - Added new commands:
  - `make run-did-pipeline-cs`
  - `make run-did-pipeline-cs-local`
- **`src/housing/components/analyzers/event_study.py`** - Added warning about TWFE limitations

## How to Use

### Basic Usage

```bash
# Run the Callaway-Sant'Anna pipeline
make run-did-pipeline-cs

# Or if on Box/cloud drive (to avoid file lock issues):
make run-did-pipeline-cs-local
```

### What You Get

The pipeline produces:

1. **Main CS event study plot** (`did_callaway_santanna_event_study.png`)
   - Dynamic treatment effects over time
   - Confidence intervals
   - Overall ATT annotation

2. **TWFE vs. CS comparison** (`did_twfe_vs_cs_comparison.png`)
   - Side-by-side plots
   - Shows whether TWFE is biased

3. **Difference plot** (`did_cs_twfe_difference.png`)
   - Visualizes CS - TWFE difference
   - Quantifies bias in TWFE

4. **Cohort dynamics** (`did_cohort_dynamics.png`)
   - Separate event studies for each treatment cohort
   - Reveals heterogeneity patterns

5. **Comparison table** (`did_twfe_cs_comparison_table.csv`)
   - Detailed estimates from both methods
   - For creating publication tables

## Key Features

### 1. Robust to Heterogeneous Effects
- Avoids negative weighting problem
- Valid even when treatment effects differ by:
  - Cohort (early vs. late adopters)
  - Time since treatment (dynamic effects)
  - Calendar time (market conditions)

### 2. Transparent Aggregation
- Estimates ATT(g,t) for each cohort-time pair
- Aggregates with known, non-negative weights
- No hidden comparisons

### 3. Flexible Comparison Groups
```python
# Never-treated only (preferred)
CallawaySantAnnaAnalyzer(comparison_group="nevertreated")

# Not-yet-treated (if no never-treated units)
CallawaySantAnnaAnalyzer(comparison_group="notyettreated")
```

### 4. Comprehensive Diagnostics
- Pre-treatment parallel trends testing
- Cohort-by-cohort effect heterogeneity
- Automatic comparison with TWFE

## Understanding the Results

### Interpreting Overall ATT

```
Overall ATT: $45.23 (SE: $12.34)
95% CI: [$21.04, $69.42]
P-value: 0.0003
```

**Meaning**: On average, STR prohibitions increased rental prices by $45.23/month in treated tracts.

### Interpreting TWFE vs. CS Comparison

**Scenario A: Similar estimates**
```
CS:   $42.50
TWFE: $43.10
Diff: $0.60
```
✓ Treatment effects are homogeneous; TWFE is approximately unbiased.

**Scenario B: Different estimates**
```
CS:   $45.80
TWFE: $15.30
Diff: $30.50 ⚠️
```
✗ Treatment effects are heterogeneous; TWFE is biased; trust CS.

### Interpreting Cohort Dynamics

If different cohorts show different patterns:
- Early adopters (2020): Large immediate effect, then stable
- Late adopters (2022): Small initial effect, grows over time

**Implication**: Context matters! Treatment effects depend on when units were treated.

## Methodology Overview

### The CS Estimator

For each cohort g and time t:

```
ATT(g,t) = [Average change in treated cohort g from pre to t]
         - [Average change in comparison group from pre to t]
```

Where:
- Cohort g = units first treated at time g
- Comparison = never-treated or not-yet-treated units
- Pre = one period before cohort g's treatment

### Aggregation to Event Study

For each relative time e (e.g., e = 0, 1, 2, ...):

```
ATT(e) = Weighted average of ATT(g, g+e) across all cohorts
```

Weights are proportional to cohort sizes.

## Comparison with TWFE

| Aspect | TWFE | Callaway-Sant'Anna |
|--------|------|-------------------|
| **Staggered treatment** | Can be biased | Robust |
| **Heterogeneous effects** | ❌ Assumes homogeneous | ✅ Allows heterogeneity |
| **Negative weights** | ⚠️ Possible | ✅ Never |
| **Comparison group** | All untreated (including already-treated) | Never/not-yet-treated only |
| **Speed** | Fast | Slower |
| **When to use** | Single treatment time OR robustness check | Staggered treatment |

## When to Use Which

### Use Callaway-Sant'Anna (Primary) When:
- ✅ Treatment is staggered (different timing for different units)
- ✅ Effects may differ by cohort or over time
- ✅ You want robust, conservative estimates

### Use TWFE (Secondary) When:
- ✅ All units treated at same time (no staggering)
- ✅ As robustness check alongside CS
- ✅ For comparison to previous literature

### Always Do:
- ✅ Run BOTH if treatment is staggered
- ✅ Compare results
- ✅ Report CS as primary, TWFE as robustness

## Example Workflow

```bash
# Step 1: Run basic DiD (TWFE)
make run-did-pipeline

# Step 2: Run Callaway-Sant'Anna
make run-did-pipeline-cs

# Step 3: Compare results
# Open: output/did_twfe_vs_cs_comparison.png
# Question: Are estimates similar or different?

# Step 4: Investigate heterogeneity
# Open: output/did_cohort_dynamics.png
# Question: Do cohorts have different effects?

# Step 5: Report
# - Primary: Callaway-Sant'Anna estimates
# - Robustness: TWFE comparison
# - Discussion: Any differences and what they mean
```

## Customization Options

### Minimum Cohort Size

```python
CallawaySantAnnaAnalyzer(
    min_cohort_size=10  # Require at least 10 tracts per cohort
)
```

### Anticipation Effects

If you suspect units anticipate treatment:

```python
CallawaySantAnnaAnalyzer(
    anticipation=2  # Allow effects 2 periods before treatment
)
```

### Comparison Group

```python
# Preferred: Never-treated only
CallawaySantAnnaAnalyzer(comparison_group="nevertreated")

# Alternative: Not-yet-treated (if no never-treated)
CallawaySantAnnaAnalyzer(comparison_group="notyettreated")
```

## Limitations and Assumptions

### Still Required:
1. **Parallel trends** - Treated and control would have followed parallel trends absent treatment
2. **No spillovers** - Treatment in one unit doesn't affect others
3. **SUTVA** - Stable unit treatment value assumption

### New Assumptions:
4. **No anticipation** - Units don't change behavior before treatment (if using not-yet-treated)

### What CS Fixes:
- ✅ Heterogeneous treatment effects
- ✅ Negative weighting problem
- ✅ Forbidden comparisons (treated vs. treated)

### What CS Doesn't Fix:
- ❌ Violation of parallel trends
- ❌ Spillovers or interference
- ❌ Fundamental identification problems

## Testing the Implementation

To verify the implementation works:

```bash
# Run the pipeline
make run-did-pipeline-cs

# Check output directory
ls output/did_callaway_santanna*
ls output/did_twfe_vs_cs*
ls output/did_cohort_dynamics*

# Expected files:
# - did_callaway_santanna_event_study.png ✓
# - did_twfe_vs_cs_comparison.png ✓
# - did_cs_twfe_difference.png ✓
# - did_cohort_dynamics.png ✓
# - did_twfe_cs_comparison_table.csv ✓
```

## Troubleshooting

### Error: "No comparison units"
**Cause**: No never-treated units in your data
**Fix**: Switch to not-yet-treated:
```python
CallawaySantAnnaAnalyzer(comparison_group="notyettreated")
```

### Warning: "Small cohort"
**Cause**: Few units in some cohorts
**Fix**: Increase min_cohort_size or accept the limitation

### Issue: Wide confidence intervals
**Not an error**: CS is conservative about uncertainty
**Explanation**: More honest inference, especially with small samples

### Issue: CS very different from TWFE
**Not an error**: Indicates heterogeneous effects
**Explanation**: TWFE is biased, CS is not. Trust CS.

## Further Reading

### Essential Papers

1. **Callaway & Sant'Anna (2021)** - "Difference-in-differences with multiple time periods"
   - *Journal of Econometrics* 225.2: 200-230
   - The original CS paper with full methodology

2. **Goodman-Bacon (2021)** - "Difference-in-differences with variation in treatment timing"
   - *Journal of Econometrics* 225.2: 254-277
   - Explains TWFE decomposition and negative weights

3. **Roth et al. (2023)** - "What's trending in difference-in-differences?"
   - *arXiv* preprint
   - Comprehensive review of modern DiD methods

### Guides in This Repo

- **`docs/callaway_santanna_guide.md`** - Detailed implementation guide
- **`docs/did_estimator_comparison.md`** - Quick reference sheet
- **`docs/README.md`** - Documentation index

## Next Steps

### For Your Analysis

1. **Run the pipeline**: `make run-did-pipeline-cs`
2. **Examine results**: Check all output plots
3. **Compare with TWFE**: Are estimates similar or different?
4. **Investigate heterogeneity**: Review cohort dynamics
5. **Write up results**: Report CS as primary specification

### For Students

1. **Add to curriculum**: Consider adding CS to Part 7 or 8 of DID_STUDENT_PLAN.md
2. **Create lesson**: Explain negative weights problem and why CS matters
3. **Exercise**: Have students run both, compare, interpret differences

### For Paper/Report

**Template language:**

> "We estimate treatment effects using the Callaway & Sant'Anna (2020) estimator, which is robust to treatment effect heterogeneity in staggered adoption designs. This approach avoids the negative weighting problem inherent in two-way fixed effects (TWFE) regressions when treatment timing varies. As a robustness check, we also report TWFE estimates. The two approaches yield [similar/different] results, [suggesting/indicating] [homogeneous/heterogeneous] treatment effects across cohorts and time. We rely on the CS estimates as our primary specification."

## Summary

You now have a **complete, production-ready** implementation of Callaway & Sant'Anna (2020) that:

✅ Handles staggered treatment timing correctly
✅ Is robust to heterogeneous treatment effects
✅ Provides transparent, interpretable results
✅ Includes comprehensive visualizations and diagnostics
✅ Compares automatically with TWFE to detect bias
✅ Is fully documented and ready to use

This addresses the main limitation identified in your original TWFE event study and puts your analysis on solid methodological footing for modern DiD best practices.

## Questions?

If you need help or have questions:
1. Check `docs/callaway_santanna_guide.md` for detailed explanations
2. Review `docs/did_estimator_comparison.md` for quick reference
3. Consult the original CS (2021) paper for theoretical details

---

**Ready to run:** `make run-did-pipeline-cs`

Happy analyzing! 🎉
