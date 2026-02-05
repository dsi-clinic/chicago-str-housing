# Part 6: Event Study Analysis

## Introduction

The basic DiD model gives us one number: the average treatment effect. But this hides important details:
- **When** does the effect appear? Immediately or with a lag?
- **How** does the effect evolve? Growing, shrinking, or stable?
- **Are pre-trends really parallel?** A formal test, not just visual inspection.

Event study analysis answers these questions by estimating separate effects for each period relative to treatment.

---

## The Event Study Model

Instead of a single `treated` dummy, we create dummies for each relative time period:

```
rental_price = Σₖ βₖ(relative_time = k) + αᵢ + γₜ + ε
```

Where k = -12, -11, ..., -1, 0, 1, 2, ..., 12 (months relative to treatment).

**Key:** We omit one period as the reference (typically k = -1, the month before treatment). All coefficients are interpreted relative to that period.

---

## Creating Relative Time Dummies

You already have `months_since_treatment` from Part 3. Now create dummies:

```python
# Define the event window (e.g., 12 months before/after)
event_window = range(-12, 13)  # -12 to +12

# Create dummies for each relative time period
for k in event_window:
    if k == -1:  # Skip reference period
        continue
    did_panel[f"rel_time_{k}"] = (
        did_panel["months_since_treatment"] == k
    ).astype(int)

# Get list of dummy column names
rel_time_cols = [f"rel_time_{k}" for k in event_window if k != -1]
```

For never-treated tracts, all dummies will be 0 (they have no event).

---

## Estimation

```python
from linearmodels import PanelOLS

# Set up panel
panel = did_panel.set_index(["tract_geoid", "month"])

# Build formula with all relative time dummies
formula = "rental_price ~ 1 + " + " + ".join(rel_time_cols)

model = PanelOLS.from_formula(
    formula,
    data=panel,
    entity_effects=True,
    time_effects=True
)

results = model.fit(cov_type="clustered", cluster_entity=True)
```

---

## Extracting Coefficients

```python
import pandas as pd

# Extract coefficients and confidence intervals
coef_df = pd.DataFrame({
    "relative_time": [int(col.split("_")[-1]) for col in rel_time_cols],
    "coefficient": [results.params[col] for col in rel_time_cols],
    "std_error": [results.std_errors[col] for col in rel_time_cols],
})

# Add reference period (coefficient = 0 by construction)
ref_row = pd.DataFrame({"relative_time": [-1], "coefficient": [0], "std_error": [0]})
coef_df = pd.concat([coef_df, ref_row]).sort_values("relative_time")

# Calculate 95% CI
coef_df["ci_lower"] = coef_df["coefficient"] - 1.96 * coef_df["std_error"]
coef_df["ci_upper"] = coef_df["coefficient"] + 1.96 * coef_df["std_error"]
```

---

## The Event Study Plot

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 6))

# Plot coefficients
ax.plot(coef_df["relative_time"], coef_df["coefficient"], "o-", color="navy")

# Plot confidence intervals
ax.fill_between(
    coef_df["relative_time"],
    coef_df["ci_lower"],
    coef_df["ci_upper"],
    alpha=0.2,
    color="navy"
)

# Reference lines
ax.axhline(0, color="black", linestyle="-", linewidth=0.5)
ax.axvline(-0.5, color="red", linestyle="--", label="Treatment")

ax.set_xlabel("Months Since Treatment")
ax.set_ylabel("Effect on Rental Price ($)")
ax.set_title("Event Study: Effect of STR Prohibition on Rents")
ax.legend()
```

---

## Interpreting the Plot

**Pre-treatment coefficients (k < 0):**
- Should be close to zero and statistically insignificant
- If they're bouncing around zero with CIs crossing zero → parallel trends supported
- If they show a clear trend (rising or falling) → parallel trends violated

**Post-treatment coefficients (k ≥ 0):**
- Show the treatment effect at each horizon
- Immediate effect: coefficient at k = 0
- Persistent effect: coefficients stay at similar level
- Growing effect: coefficients increase over time
- Fading effect: coefficients shrink toward zero

---

## Testing Parallel Trends

Formal test: Are all pre-treatment coefficients jointly zero?

```python
from scipy import stats

# Get pre-treatment coefficients
pre_coefs = [results.params[f"rel_time_{k}"] for k in range(-12, -1)]
pre_ses = [results.std_errors[f"rel_time_{k}"] for k in range(-12, -1)]

# Simple check: How many are individually significant?
pre_pvals = [2 * (1 - stats.norm.cdf(abs(c/s))) for c, s in zip(pre_coefs, pre_ses)]
n_significant = sum(p < 0.05 for p in pre_pvals)
print(f"Pre-treatment coefficients significant at 5%: {n_significant} / {len(pre_coefs)}")
```

If most pre-treatment coefficients are insignificant and scattered around zero, parallel trends is plausible.

---

## Deliverable

1. **`EventStudyAnalyzer`** component that estimates the event study model
2. **`EventStudyVisualizer`** component that creates the plot
3. Event study plot saved to `output/event_study_plot.png`
4. Brief interpretation answering:
   - Do pre-treatment coefficients support parallel trends?
   - Is the effect immediate or delayed?
   - Does the effect persist, grow, or fade?

---

## Next Steps

Part 7 introduces **trend matching**—restricting the analysis to treated tracts and controls with similar pre-treatment rent trends. This lets us:
- Improve comparability when pre-trends differ between groups
- Re-run DiD on a matched sample
- Compare matched vs. full-panel results to assess robustness
