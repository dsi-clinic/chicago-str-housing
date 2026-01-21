# Part 3: Treatment Indicators

## Introduction

In Part 2, you built a tract-level rental panel: `(tract_geoid, month, rental_price)`. Now we need to add the key ingredient for DiD: **treatment indicators** that tell us which tracts are treated and when.

By the end of this lesson, you'll have a complete DiD-ready dataset with columns: `tract_geoid`, `month`, `rental_price`, `treated`, and `months_since_treatment`.

---

## What is a Treatment Indicator?

A treatment indicator is a binary variable that equals:
- **0** when a unit is untreated (pre-treatment or never-treated)
- **1** when a unit is treated (post-treatment)

For a tract that adopted STR prohibition on 2016-08-01:

```
tract_geoid  | month      | treated
-------------|------------|--------
17031010100  | 2016-06-01 | 0       ← before treatment
17031010100  | 2016-07-01 | 0       ← before treatment
17031010100  | 2016-08-01 | 1       ← treatment begins
17031010100  | 2016-09-01 | 1       ← after treatment
17031010100  | 2016-10-01 | 1       ← after treatment
```

Once a tract becomes treated, it stays treated. The indicator "turns on" and never turns off.

For never-treated tracts, `treated = 0` for all months.

---

## Treatment Dates

We have tract-level prohibition dates in `output/tract_prohibition_dates.csv`:

```
tract_geoid     | first_prohibition_date | building_count
----------------|------------------------|---------------
17031010100     | 2016-08-08            | 2
17031010201     | 2016-08-03            | 10
17031010300     | 2016-08-03            | 5
```

The `first_prohibition_date` is when the first building in that tract adopted STR prohibition. This is our treatment date.

Tracts not in this file were never treated during our sample period.

---

## Creating the Treatment Indicator

The logic is straightforward:

```python
# Merge panel with treatment dates
merged = panel_df.merge(
    treatment_dates[["tract_geoid", "first_prohibition_date"]],
    on="tract_geoid",
    how="left"
)

# Create treated indicator
# treated = 1 if month >= first_prohibition_date, else 0
# For never-treated tracts (NaT date), this evaluates to False → 0
merged["treated"] = (
    merged["month"] >= merged["first_prohibition_date"]
).astype(int)
```

Key points:
- Use `how="left"` to keep all tract-months, even never-treated ones
- Never-treated tracts get `NaT` for `first_prohibition_date`
- Comparing a date to `NaT` returns `False`, so `treated = 0` for never-treated tracts

---

## Relative Time: Months Since Treatment

For event study analysis (Part 6), we need to know how many months before/after treatment each observation is. This is called **relative time** or **event time**.

```
tract_geoid  | month      | treated | months_since_treatment
-------------|------------|---------|------------------------
17031010100  | 2016-06-01 | 0       | -2    ← 2 months before
17031010100  | 2016-07-01 | 0       | -1    ← 1 month before
17031010100  | 2016-08-01 | 1       | 0     ← treatment month
17031010100  | 2016-09-01 | 1       | 1     ← 1 month after
17031010100  | 2016-10-01 | 1       | 2     ← 2 months after
```

Calculate it as the difference in months:

```python
merged["months_since_treatment"] = (
    (merged["month"].dt.year - merged["first_prohibition_date"].dt.year) * 12 +
    (merged["month"].dt.month - merged["first_prohibition_date"].dt.month)
)
```

For never-treated tracts, this will be `NaN` (which is fine—they have no treatment event).

---

## Building the TreatmentIndicatorProcessor

Your component should:
1. Get the tract-level rental panel from context (`context["tract_rental_panel"]`)
2. Get the treatment dates from context (`context["tract_prohibition_dates"]`)
3. Merge, create `treated` and `months_since_treatment`
4. Return `{"did_panel": merged}`

The core logic is already shown above—wrap it in a `DataProcessor` class following the pattern from previous components.

---

## Validation

Check your output carefully:

```python
did_panel = context["did_panel"]

# 1. Check structure
print(did_panel.columns.tolist())
# Expected: ['tract_geoid', 'month', 'rental_price', 'first_prohibition_date', 
#            'treated', 'months_since_treatment']

# 2. Verify treated indicator
# Pick a tract you know is treated and check the switch point
tract = "17031010100"
print(did_panel[did_panel["tract_geoid"] == tract][
    ["month", "treated", "months_since_treatment"]
].head(20))

# 3. Count treated vs control
print(did_panel.groupby("treated")["tract_geoid"].nunique())

# 4. Check never-treated tracts have treated=0 always
never_treated = did_panel[did_panel["first_prohibition_date"].isna()]
assert (never_treated["treated"] == 0).all(), "Never-treated should have treated=0"

# 5. Check treated tracts switch at the right time
treated_tracts = did_panel[did_panel["first_prohibition_date"].notna()]
for tract_id, group in treated_tracts.groupby("tract_geoid"):
    first_treated_month = group.loc[group["treated"] == 1, "month"].min()
    prohibition_date = group["first_prohibition_date"].iloc[0]
    assert first_treated_month.month == prohibition_date.month, f"Mismatch for {tract_id}"
```

---

## Summary

1. **Treatment indicator** (`treated`): Binary variable, 0 before treatment, 1 after.

2. **Relative time** (`months_since_treatment`): How many months before/after the treatment date. Used for event study analysis.

3. The **TreatmentIndicatorProcessor** merges the rental panel with treatment dates and creates both variables.

4. **Validation** is critical: verify that the indicator switches at the correct time for treated tracts and stays 0 for never-treated tracts.

---

## Deliverable

- `TreatmentIndicatorProcessor` component in `src/housing/components/processors/`
- Output file: `output/did_panel_data.csv` with columns:
  - `tract_geoid`
  - `month`
  - `rental_price`
  - `treated`
  - `months_since_treatment`

---

## Next Steps

With the DiD panel complete, Part 4 will explore the data through descriptive analysis: comparing treated vs. control tracts, visualizing pre-treatment trends, and checking whether the parallel trends assumption is plausible.
