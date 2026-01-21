# Part 2: Panel Data & Infrastructure

## Introduction

In Part 1, we learned about Difference-in-Differences (DiD) as an identification strategy. We saw that DiD compares changes over time between treated and control groups to isolate causal effects.

But to actually implement DiD, we need data structured in a specific way. We can't just have a snapshot of rents at one point in time—we need to track the same units across multiple time periods. This type of data structure is called **panel data**.

In this lesson, you'll learn about panel data, practice reshaping data using pandas, build a component to load all monthly rental price data, and convert that data from ZIP code level to census tract level (matching our treatment assignment geography).

---

## What is Panel Data?

Data can be structured in three fundamentally different ways:

### Cross-Sectional Data

Cross-sectional data captures many units at a **single point in time**.

```
person_id | age | income
----------|-----|--------
1         | 25  | 50000
2         | 30  | 60000
3         | 35  | 70000
```

This is like taking a photograph—you see everything at once, but you can't see how things change. If we only had cross-sectional rent data, we could compare treated and untreated areas, but we couldn't distinguish pre-existing differences from treatment effects.

### Time Series Data

Time series data tracks a **single unit** across multiple time periods.

```
year | gdp
-----|-----
2015 | 1000
2016 | 1050
2017 | 1100
```

This is like watching a movie of one character—you see how they change, but you can't compare them to anyone else. If we only had time series data for one neighborhood, we could see rent trends, but we couldn't separate the treatment effect from overall market trends.

### Panel Data (Longitudinal Data)

Panel data tracks **multiple units** across **multiple time periods**.

```
person_id | year | income
----------|------|-------
1         | 2015 | 50000
1         | 2016 | 52000
1         | 2017 | 54000
2         | 2015 | 60000
2         | 2016 | 62000
2         | 2017 | 64000
```

This is like watching a movie with multiple characters—you can see how each one changes, and you can compare their trajectories. Panel data gives us the best of both worlds: cross-sectional variation (comparing across units) AND time variation (comparing within units over time).

---

## Why We Need Panel Data for DiD

Recall the DiD formula:

```
DiD = (Treatment_After - Treatment_Before) - (Control_After - Control_Before)
```

To compute this, we need:
1. Observations of the **same units** at multiple time points
2. Knowledge of **which units** are treated and **when**
3. Outcome measurements **before and after** treatment

Our panel data structure will be: `(tract, month, rental_price, treated)`

Each row represents one tract in one month. For each tract-month, we know the rental price and whether STR restrictions were in effect. This structure enables DiD analysis.

---

## Reshaping Data: Wide to Long Format

Real-world data often comes in **wide format**—one column for each time period. We need to convert it to **long format**—one row for each unit-time combination.

### Wide Format (What We Have)

The Zillow rental data comes like this:

```
zip_code | 2015-01-31 | 2015-02-28 | 2015-03-31 | ...
---------|------------|------------|------------|----
60601    | 1200       | 1210       | 1220       | ...
60602    | 1500       | 1510       | 1520       | ...
```

Each ZIP code gets one row. Each month gets its own column. This is compact for storage but awkward for analysis.

### Long Format (What We Need)

For panel data analysis, we need:

```
zip_code | month      | rental_price
---------|------------|-------------
60601    | 2015-01-31 | 1200
60601    | 2015-02-28 | 1210
60601    | 2015-03-31 | 1220
60602    | 2015-01-31 | 1500
60602    | 2015-02-28 | 1510
60602    | 2015-03-31 | 1520
```

Each observation (ZIP × month) gets its own row. The month value that was a column name is now a data value.

---

## Using `pd.melt()` to Reshape Data

Pandas provides the `melt()` function to convert wide data to long format.

```python
import pandas as pd

# Assume wide_df is our wide-format DataFrame
# Identify date columns (all columns starting with "20")
date_cols = [col for col in wide_df.columns if col.startswith("20")]

# Reshape from wide to long
long_df = wide_df.melt(
    id_vars=["zip_code"],      # Columns to keep as identifiers
    value_vars=date_cols,      # Columns to unpivot (convert to rows)
    var_name="month",          # Name for the new column with old column names
    value_name="rental_price"  # Name for the new column with values
)
```

### Understanding the Parameters

- **`id_vars`**: Columns that identify each unit. These stay as columns and get repeated for each time period. In our case, `zip_code` identifies each geographic unit.

- **`value_vars`**: Columns to "melt" into rows. These are the time-period columns. Each becomes a value in the new `month` column.

- **`var_name`**: What to call the new column that holds the old column names. We call it `month` because the old column names are dates.

- **`value_name`**: What to call the new column that holds the values. We call it `rental_price` because that's what the values represent.

### Before and After

**Before melt (3 ZIPs × 3 months = 3 rows, 4 columns):**
```
zip_code | 2015-01-31 | 2015-02-28 | 2015-03-31
---------|------------|------------|------------
60601    | 1200       | 1210       | 1220
60602    | 1500       | 1510       | 1520
60603    | 1800       | 1820       | 1830
```

**After melt (3 ZIPs × 3 months = 9 rows, 3 columns):**
```
zip_code | month      | rental_price
---------|------------|-------------
60601    | 2015-01-31 | 1200
60602    | 2015-01-31 | 1500
60603    | 2015-01-31 | 1800
60601    | 2015-02-28 | 1210
60602    | 2015-02-28 | 1510
60603    | 2015-02-28 | 1820
60601    | 2015-03-31 | 1220
60602    | 2015-03-31 | 1520
60603    | 2015-03-31 | 1830
```

---

## Working with Panel Data in Pandas

Once data is in long format, pandas provides powerful tools for panel data analysis.

### Setting a Multi-Index

Panel data has two identifying dimensions: entity (who) and time (when). We can set these as a multi-index:

```python
# Set multi-index: (entity, time)
panel_df = long_df.set_index(['zip_code', 'month'])

# Now we can easily select by entity
panel_df.loc['60601']  # All observations for ZIP 60601

# Or select a specific entity-time combination
panel_df.loc[('60601', '2015-01-31')]  # Specific observation
```

### Grouping Operations

Group by entity to see time trends for each unit:

```python
# Average rental price per ZIP code (across all months)
long_df.groupby('zip_code')['rental_price'].mean()
```

Group by time to see cross-sectional patterns:

```python
# Average rental price per month (across all ZIPs)
long_df.groupby('month')['rental_price'].mean()
```

Group by both to verify uniqueness:

```python
# Should have exactly one observation per ZIP-month
long_df.groupby(['zip_code', 'month']).size()
```

---

## Common Issues and Solutions

### 1. Date Columns Not Recognized

If your date columns don't all start with "20", adjust the filter:

```python
# Alternative: select columns that parse as dates
date_cols = []
for col in wide_df.columns:
    try:
        pd.to_datetime(col)
        date_cols.append(col)
    except:
        pass
```

### 2. Missing Values

For panel data analysis, we want to **impute** missing values rather than drop them. Dropping creates gaps in the time series and can bias results.

**Recommended approach — linear interpolation within each ZIP:**

```python
# Sort first to ensure correct order
long_df = long_df.sort_values(["zip_code", "month"])

# Interpolate missing values within each ZIP code
long_df["rental_price"] = (
    long_df.groupby("zip_code")["rental_price"]
    .transform(lambda x: x.interpolate(method="linear"))
)

# For any remaining NaNs at the edges, forward/backward fill
long_df["rental_price"] = (
    long_df.groupby("zip_code")["rental_price"]
    .transform(lambda x: x.ffill().bfill())
)
```

This fills gaps by estimating values between known data points, which is reasonable for rental prices that change gradually over time.

### 3. Date Format Issues

If dates don't parse automatically, specify the format:

```python
long_df["month"] = pd.to_datetime(long_df["month"], format="%Y-%m-%d")
```

### 4. Memory Issues

For very large datasets, process in chunks:

```python
# Only load necessary columns
cols_to_load = ["RegionName"] + date_cols[-36:]  # Last 3 years only
wide_df = pd.read_csv("data/rental_data.csv", usecols=cols_to_load)
```

---

## Building the TimeSeriesRentalLoader Component

Now you'll build a component that implements this data loading process following our pipeline framework.

### Component Structure

The component should inherit from `DataLoader` and implement the standard interface:

```python
from typing import Any
import pandas as pd
from pipeline.base import DataLoader

class TimeSeriesRentalLoader(DataLoader):
    def __init__(self, file_path: str | None = None):
        super().__init__(
            "rental_panel_data",  # Key in context dictionary
            file_path or "/project/data/Zip_zori_uc_sfrcondomfr_sm_month.csv",
            "Load all monthly rental price data"
        )
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        # Your implementation here:
        # 1. Load the CSV
        # 2. Identify date columns
        # 3. Reshape to long format
        # 4. Clean and validate
        # 5. Return updated context with panel data
        pass
```

### What Your Component Should Do

1. **Load** the CSV file from `self.file_path`
2. **Identify** all date columns (columns starting with "20")
3. **Reshape** from wide to long format using `melt()`
4. **Convert** the month column to datetime
5. **Sort** by zip_code and month
6. **Impute** missing rental prices using interpolation
7. **Log** useful information (number of ZIPs, date range, observation count)
8. **Return** the context dictionary with the panel data added

### Testing Your Component

After implementing, test it:

```python
from housing.components.loaders.time_series_rental_data import TimeSeriesRentalLoader

loader = TimeSeriesRentalLoader()
context = loader.execute({})

panel_data = context["rental_panel_data"]
print(panel_data.head())
print(panel_data.info())
```

---

## Validation Checklist: TimeSeriesRentalLoader

Before considering your loader component complete, verify:

- [ ] Data loads successfully from the CSV file
- [ ] All date columns are identified (check the count matches expected)
- [ ] Reshape produces correct structure: columns are `zip_code`, `month`, `rental_price`
- [ ] Month column is datetime type, not string
- [ ] Missing values are imputed (no NaNs in rental_price after processing)
- [ ] Data is sorted by zip_code and month
- [ ] Logging provides useful information about the data
- [ ] Output can be saved to CSV for inspection

---

## Converting ZIP Codes to Census Tracts

We now have rental data at the ZIP code level, but our DiD analysis needs data at the **census tract** level. Why? Because STR prohibitions are tracked and enforced at the tract level—that's the geography where treatment is assigned.

### Why Geography Matters

ZIP codes and census tracts are different geographic units:
- **ZIP codes**: Created by USPS for mail delivery. Larger, irregular shapes.
- **Census tracts**: Created by Census Bureau for statistics. Smaller, designed to have ~4,000 people each.

A single ZIP code might overlap with multiple census tracts, and vice versa. To convert from one to the other, we need **spatial interpolation**.

### Area-Weighted Interpolation

The basic idea: if a ZIP code overlaps with multiple tracts, allocate its rental price to each tract proportionally based on the overlap area.

**Example:**
- ZIP 60601 has a rental price of $1,500
- It overlaps with Tract A (60% of area) and Tract B (40% of area)
- Tract A gets allocated: $1,500 × 0.60 = $900 contribution
- Tract B gets allocated: $1,500 × 0.40 = $600 contribution

When multiple ZIPs overlap with a tract, we sum their weighted contributions and normalize by total overlap area to get the tract's estimated rental price.

### The ZIP→Tract Crosswalk

Rather than computing spatial overlaps for every month (expensive!), we compute a **crosswalk** once: a mapping table showing how each ZIP relates to each tract with area weights.

```
zip_code | tract_geoid | weight
---------|-------------|-------
60601    | 17031010100 | 0.60
60601    | 17031010200 | 0.40
60602    | 17031010200 | 0.35
60602    | 17031010300 | 0.65
```

Then for each month, we apply this crosswalk to convert ZIP-level prices to tract-level prices.

### Building the TimeSeriesZipToTractProcessor

This component converts the ZIP-level panel to a tract-level panel.

**Component Structure:**

```python
from typing import Any
import pandas as pd
from pipeline.base import DataProcessor

class TimeSeriesZipToTractProcessor(DataProcessor):
    def __init__(self):
        super().__init__(
            "zip_to_tract_panel",
            "Convert ZIP-level rental panel to tract-level panel"
        )
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        # Get inputs from context
        zip_panel = context["rental_panel_data"]  # From TimeSeriesRentalLoader
        crosswalk = context["zip_to_tract_crosswalk"]  # From ZipToTractProcessor
        
        # Your implementation here:
        # 1. Merge panel data with crosswalk
        # 2. Calculate weighted rental prices
        # 3. Aggregate to tract level for each month
        # 4. Return tract-level panel
        pass
```

**Implementation Approach:**

```python
# Step 1: Merge panel data with crosswalk
# Each ZIP-month observation gets expanded to multiple rows
# (one for each tract it overlaps with)
merged = zip_panel.merge(crosswalk, on="zip_code", how="inner")

# Step 2: Calculate weighted rental prices
merged["weighted_rent"] = merged["rental_price"] * merged["weight"]

# Step 3: Aggregate to tract level for each month
tract_panel = (
    merged.groupby(["tract_geoid", "month"])
    .agg({
        "weighted_rent": "sum",
        "weight": "sum"  # Total weight for normalization
    })
    .reset_index()
)

# Step 4: Normalize to get tract-level rental price
tract_panel["rental_price"] = (
    tract_panel["weighted_rent"] / tract_panel["weight"]
)

# Clean up
tract_panel = tract_panel[["tract_geoid", "month", "rental_price"]]
tract_panel = tract_panel.sort_values(["tract_geoid", "month"])
```

### Getting the Crosswalk

The crosswalk comes from spatial analysis of ZIP and tract boundaries. The existing `ZipToTractProcessor` component already computes this—you'll use its output.

When building your pipeline, order matters:

```python
pipeline = Pipeline([
    # Load boundaries
    ZipBoundaryLoader(),
    TractBoundaryLoader(),
    
    # Create crosswalk (only needs to run once)
    ZipToTractProcessor(),
    
    # Load time series rental data
    TimeSeriesRentalLoader(),
    
    # Convert to tract level using the crosswalk
    TimeSeriesZipToTractProcessor(),
])
```

### Validation Checklist: TimeSeriesZipToTractProcessor

- [ ] Crosswalk is correctly loaded from context
- [ ] Merge preserves all ZIP-month observations that have matching tracts
- [ ] Weighted calculations are correct (weighted_rent = price × weight)
- [ ] Aggregation produces one row per tract-month
- [ ] Normalization accounts for partial coverage (divide by sum of weights)
- [ ] Output has columns: `tract_geoid`, `month`, `rental_price`
- [ ] No unexpected missing values in output
- [ ] Number of unique tracts matches expected (check against tract boundaries)

---

## Summary

1. **Panel data** tracks multiple units across multiple time periods, providing both cross-sectional and time-series variation.

2. **Wide format** has one column per time period; **long format** has one row per unit-time combination. DiD analysis requires long format.

3. **`pd.melt()`** converts wide data to long format. The key parameters are `id_vars` (identifiers to keep), `value_vars` (columns to unpivot), `var_name` (name for old column names), and `value_name` (name for values).

4. **Multi-index** DataFrames and **groupby** operations make panel data analysis easier in pandas.

5. **Geographic conversion** from ZIP codes to census tracts uses area-weighted interpolation: a crosswalk maps ZIPs to tracts with overlap weights, then we aggregate weighted prices to the tract level.

6. The **TimeSeriesRentalLoader** loads rental data in panel format, and the **TimeSeriesZipToTractProcessor** converts it to the tract level needed for DiD analysis.

---

## Next Steps

After completing this lesson, you should have:
- A working panel dataset at the census tract level: `(tract_geoid, month, rental_price)`
- Understanding of panel data structure and manipulation
- Understanding of geographic interpolation between ZIP codes and tracts

In Part 3, we'll create the treatment indicators—determining which tracts are treated and when—to complete the data preparation for DiD estimation.
