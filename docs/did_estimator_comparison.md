# DiD Estimator Quick Reference

## Which Estimator Should I Use?

```
┌─────────────────────────────────────────────────────────────────┐
│                      DECISION TREE                              │
└─────────────────────────────────────────────────────────────────┘

Is treatment staggered? (Different units treated at different times)
│
├─ NO → Use standard TWFE
│       (EventStudyAnalyzer)
│
└─ YES → Are treatment effects likely heterogeneous?
         │
         ├─ UNSURE → Use BOTH, compare results
         │           • If similar: Treatment effects homogeneous ✓
         │           • If different: Use Callaway-Sant'Anna ✓
         │
         ├─ NO (homogeneous) → Either is fine, but CS provides
         │                      robustness check
         │
         └─ YES (heterogeneous) → Use Callaway-Sant'Anna
                                   (CallawaySantAnnaAnalyzer)
```

## Estimator Comparison Table

| Feature | TWFE (Standard) | Callaway-Sant'Anna |
|---------|-----------------|-------------------|
| **Implementation** | `EventStudyAnalyzer` | `CallawaySantAnnaAnalyzer` |
| **Pipeline Command** | `make run-did-pipeline` | `make run-did-pipeline-cs` |
| **Treatment Timing** | Any (single or staggered) | Staggered only |
| **Heterogeneous Effects** | ❌ Biased if heterogeneous | ✅ Robust |
| **Negative Weights** | ⚠️ Possible | ✅ Never |
| **Comparison Group** | All non-treated (including already-treated) | Never-treated or not-yet-treated only |
| **Computation Speed** | Fast | Slower (more estimates) |
| **Interpretation** | Single event study | Event study + cohort-specific dynamics |
| **When to Use** | Single treatment time OR robustness check | Staggered treatment (primary analysis) |

## What Are "Heterogeneous Treatment Effects"?

Treatment effects are **heterogeneous** when they differ by:

1. **Treatment cohort** - Early vs. late adopters have different effects
   - Example: 2020 STR bans (during pandemic) vs. 2022 bans (post-pandemic)

2. **Time since treatment** - Effects change over time
   - Example: Immediate effect = $30, but grows to $50 after 12 months

3. **Unit characteristics** - Effects differ by tract type
   - Example: High-tourism areas vs. residential areas

**Signs of heterogeneity:**
- Cohort-specific plots show different patterns
- Effects grow or fade over time (not constant)
- TWFE and CS estimates differ substantially

## Output Comparison

### TWFE Output
```
/project/output/
├── did_event_study.png          # Single event study plot
└── did_descriptive_stats.csv    # Basic summary
```

### Callaway-Sant'Anna Output
```
/project/output/
├── did_callaway_santanna_event_study.png  # Main CS results
├── did_twfe_vs_cs_comparison.png          # Side-by-side comparison
├── did_cs_twfe_difference.png             # Bias visualization
├── did_cohort_dynamics.png                # Cohort-specific effects
└── did_twfe_cs_comparison_table.csv       # Detailed comparison
```

## Example Results

### Scenario 1: Homogeneous Effects (TWFE OK)

```
TWFE estimate (post-treatment avg): $42.50 (SE: $8.20)
CS estimate (overall ATT):          $43.10 (SE: $9.50)
Difference:                         $0.60

✓ Estimates are similar → Use either (prefer CS for robustness)
```

### Scenario 2: Heterogeneous Effects (Use CS!)

```
TWFE estimate (post-treatment avg): $15.30 (SE: $6.10)
CS estimate (overall ATT):          $45.80 (SE: $10.20)
Difference:                         $30.50 ⚠️

✗ Large difference → TWFE biased, trust CS estimate
```

## How to Interpret Differences

| Magnitude | Interpretation | Action |
|-----------|----------------|--------|
| \|Difference\| < $10 | Small, likely sampling variation | Use either estimator |
| $10 < \|Difference\| < $20 | Moderate heterogeneity | Prefer CS, investigate cohorts |
| \|Difference\| > $20 | Large heterogeneity | Use CS only, TWFE biased |

**Direction matters:**

- **CS > TWFE**: Later cohorts have larger effects (compositional heterogeneity)
- **CS < TWFE**: TWFE has negative weight bias (already-treated as controls)
- **CS ≈ TWFE**: Effects are roughly homogeneous (both valid)

## Recommended Workflow

```bash
# Step 1: Run TWFE (baseline)
make run-did-pipeline

# Step 2: Run Callaway-Sant'Anna (robust)
make run-did-pipeline-cs

# Step 3: Compare
# Open: /project/output/did_twfe_vs_cs_comparison.png
# Check: Are estimates similar or different?

# Step 4: Investigate heterogeneity
# Open: /project/output/did_cohort_dynamics.png
# Ask: Do cohorts have different treatment effects?

# Step 5: Report
# - Main results: Callaway-Sant'Anna
# - Robustness: Show TWFE comparison
# - Discussion: Explain any differences
```

## Code Examples

### Running TWFE

```python
from housing.components.analyzers.event_study import EventStudyAnalyzer

# Standard TWFE event study
analyzer = EventStudyAnalyzer()
results = analyzer.execute(context)

event_study_results = results["event_study_results"]
# DataFrame with columns: rel_time, coef, se, ci_low, ci_high
```

### Running Callaway-Sant'Anna

```python
from housing.components.analyzers.callaway_santanna import CallawaySantAnnaAnalyzer

# Callaway-Sant'Anna with never-treated comparison
analyzer = CallawaySantAnnaAnalyzer(
    comparison_group="nevertreated",  # or "notyettreated"
    anticipation=0,                    # number of periods with anticipation
    min_cohort_size=5                 # minimum units per cohort
)
results = analyzer.execute(context)

cs_event_study = results["cs_event_study"]      # Aggregated event study
cs_overall_att = results["cs_overall_att"]      # Overall ATT
cs_cohort_dynamics = results["cs_cohort_dynamics"]  # By cohort
```

## Common Questions

### Q: Do I always need to run both?

**A:** For staggered DiD, **yes**. Even if you only report CS, showing the TWFE comparison demonstrates robustness and helps readers understand whether heterogeneity is present.

### Q: What if CS and TWFE give opposite signs?

**A:** This is a serious red flag! Possible causes:
1. Severe negative weight bias in TWFE
2. Violation of parallel trends
3. Data issues

Investigate carefully and trust CS if parallel trends hold.

### Q: CS has wider confidence intervals than TWFE. Is that bad?

**A:** No! CS is being more honest about uncertainty. TWFE may appear more precise but is biased. Prefer unbiased estimates with larger SEs over biased estimates with small SEs.

### Q: What if I have no never-treated units?

**A:** Use `comparison_group="notyettreated"`. This is still valid under "no anticipation" (units don't change behavior before treatment).

### Q: Can I use CS with single treatment timing?

**A:** Yes, but unnecessary. CS and TWFE are equivalent when all units are treated simultaneously. Use TWFE (simpler).

## References

### Key Papers (Must Read)

1. **Callaway & Sant'Anna (2021)** - "Difference-in-differences with multiple time periods"
   - Journal of Econometrics 225.2: 200-230
   - Original CS paper with methodology

2. **Goodman-Bacon (2021)** - "Difference-in-differences with variation in treatment timing"
   - Journal of Econometrics 225.2: 254-277
   - Explains TWFE decomposition and negative weights

3. **Sun & Abraham (2020)** - "Estimating dynamic treatment effects in event studies"
   - Journal of Econometrics 225.2: 175-199
   - Alternative interaction-weighted estimator

### Additional Resources

4. **Roth et al. (2023)** - "What's trending in difference-in-differences?"
   - Comprehensive review of modern DiD methods

5. **Baker et al. (2022)** - "How much should we trust staggered DiD estimates?"
   - Journal of Financial Economics 144.2: 370-395
   - Empirical assessment of bias

## Summary: When in Doubt...

**Default recommendation for staggered DiD:**

```
✅ PRIMARY ANALYSIS:  Callaway-Sant'Anna
✅ ROBUSTNESS CHECK:  TWFE (for comparison)
✅ ALWAYS:            Run both, show comparison
```

**Report template:**

> "We estimate treatment effects using the Callaway & Sant'Anna (2020)
> estimator, which is robust to heterogeneous treatment effects in staggered
> adoption designs. As a robustness check, we also report standard TWFE
> estimates. The estimates [are similar/differ by $X], [suggesting homogeneous/
> indicating heterogeneous] treatment effects. Based on this, we rely on the
> CS estimates as our primary specification."

---

For detailed implementation guide, see: `docs/callaway_santanna_guide.md`
