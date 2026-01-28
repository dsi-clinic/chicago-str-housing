# Part 4: Descriptive Analysis

## Introduction

Before running any regression, we need to **understand our data**. Descriptive analysis helps us:
- Verify the data looks sensible
- Check whether parallel trends is plausible
- Identify potential problems before they contaminate our estimates

This lesson covers three key analyses: descriptive statistics, trend visualization, and pre-treatment balance checks.

---

## Treatment Adoption Over Time

First, understand when and how many tracts became treated.

```python
# Count treated tracts by month
adoption = (
    did_panel.groupby("month")["treated"]
    .sum()  # Count of treated tract-months
)

# Or: unique treated tracts over time
treated_by_month = (
    did_panel[did_panel["treated"] == 1]
    .groupby("month")["tract_geoid"]
    .nunique()
)
```

Plot the **adoption curve**—cumulative treated tracts over time:

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 5))
treated_by_month.plot(ax=ax)
ax.set_ylabel("Number of Treated Tracts")
ax.set_xlabel("Month")
ax.set_title("STR Prohibition Adoption Over Time")
```

Key questions:
- When did treatment start? (Should be ~late 2015/early 2016)
- Is adoption gradual or sudden?
- What fraction of tracts are ever treated?

---

## Average Outcomes by Treatment Status

Compare average rental prices for treated vs. control tracts over time.

**Important nuance:** A tract that gets treated in 2018 is "control" in 2017 but "treated" in 2019. We want to compare tracts that *will eventually be treated* vs. tracts that *never get treated*.

```python
# Identify ever-treated vs never-treated tracts
ever_treated = did_panel.groupby("tract_geoid")["treated"].max()
ever_treated_tracts = ever_treated[ever_treated == 1].index

did_panel["ever_treated"] = did_panel["tract_geoid"].isin(ever_treated_tracts).astype(int)

# Average rental price by ever_treated status and month
avg_by_group = (
    did_panel.groupby(["month", "ever_treated"])["rental_price"]
    .mean()
    .unstack()
)
avg_by_group.columns = ["Never Treated", "Eventually Treated"]
```

Plot the trends:

```python
fig, ax = plt.subplots(figsize=(10, 5))
avg_by_group.plot(ax=ax)
ax.set_ylabel("Average Rental Price ($)")
ax.set_xlabel("Month")
ax.set_title("Rental Price Trends: Treated vs. Control Tracts")
ax.legend(title="Group")
```

What to look for:
- **Pre-treatment period:** Are the lines roughly parallel? (Supports parallel trends assumption)
- **Post-treatment period:** Do the lines diverge? (Suggests treatment effect)
- **Level differences:** It's okay if levels differ—DiD accounts for this. What matters is whether *trends* are parallel.

---

## Pre-Treatment Balance

Do treated and control tracts look similar *before* treatment? If they differ dramatically on observables, we should be cautious about the parallel trends assumption.

### Rental Price Comparison

```python
# Define pre-treatment period (before any tract is treated)
first_treatment = did_panel.loc[did_panel["treated"] == 1, "month"].min()
pre_period = did_panel[did_panel["month"] < first_treatment]

# Compare average pre-treatment rental prices
pre_balance = (
    pre_period.groupby("ever_treated")["rental_price"]
    .agg(["mean", "std", "count"])
)
pre_balance.index = ["Never Treated", "Eventually Treated"]
print(pre_balance)
```

### Statistical Test

A t-test can formalize whether the difference is statistically significant:

```python
from scipy import stats

never_treated_prices = pre_period.loc[pre_period["ever_treated"] == 0, "rental_price"]
eventually_treated_prices = pre_period.loc[pre_period["ever_treated"] == 1, "rental_price"]

t_stat, p_value = stats.ttest_ind(never_treated_prices, eventually_treated_prices)
print(f"t-statistic: {t_stat:.2f}, p-value: {p_value:.4f}")
```

If p < 0.05, the groups have statistically different pre-treatment rental prices. This doesn't invalidate DiD (which controls for level differences), but large differences warrant caution.

---

## Visual Parallel Trends Check

The most important diagnostic: do pre-treatment trends look parallel?

```python
fig, ax = plt.subplots(figsize=(10, 5))

# Plot both groups
avg_by_group.plot(ax=ax, alpha=0.7)

# Add vertical line at first treatment
ax.axvline(first_treatment, color='red', linestyle='--', label='First Treatment')

ax.set_ylabel("Average Rental Price ($)")
ax.set_xlabel("Month")
ax.set_title("Parallel Trends Check")
ax.legend()
```

What you want to see:
- **Before the red line:** Lines move together (parallel or nearly parallel)
- **After the red line:** Lines may diverge (this is the treatment effect)

What would be concerning:
- Lines already diverging before treatment
- One group trending up while the other trends down pre-treatment
- Erratic pre-treatment patterns in one group but not the other

---

## Summary Statistics Table

Create a summary table for your report:

```python
summary = did_panel.groupby("ever_treated").agg({
    "tract_geoid": "nunique",
    "rental_price": ["mean", "std", "min", "max"],
    "treated": "sum"  # Total treated tract-months
})

summary.columns = ["N Tracts", "Mean Rent", "Std Dev", "Min Rent", "Max Rent", "Treated Obs"]
summary.index = ["Never Treated", "Eventually Treated"]
print(summary.round(2))
```

---

## Building the Components

### DIDDescriptiveAnalyzer

Should compute and return:
- Count of treated vs. never-treated tracts
- Average rental prices by group and month
- Pre-treatment balance statistics
- Summary statistics table

### DIDTrendsVisualizer

Should create and save:
- Adoption curve plot
- Parallel trends plot (treated vs. control over time)
- Pre-treatment balance comparison

---

## Deliverable

1. **`DIDDescriptiveAnalyzer`** component that outputs summary statistics
2. **`DIDTrendsVisualizer`** component that creates diagnostic plots
3. Brief written summary answering:
   - How many tracts are treated? When does treatment start?
   - Do pre-treatment trends appear parallel?
   - Are there notable differences between treated and control groups?

---

## Next Steps

If the descriptive analysis looks reasonable—roughly parallel pre-trends, no obvious data issues—you're ready for Part 5: estimating the actual DiD model with two-way fixed effects.

If pre-trends look problematic, you may need to reconsider the research design or document the limitation.
