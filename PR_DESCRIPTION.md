# Add TimeSeriesRentalLoader Component for Panel Data Processing

## Overview

This PR introduces the `TimeSeriesRentalLoader` component, which loads rental price time series data from the ZORI dataset and reshapes it from wide format (one column per month) to long format (panel data). This component is a foundational building block for difference-in-differences (DiD) analysis as outlined in Part 2 of the DiD Student Plan.

**Related to:** [DID_STUDENT_PLAN.md](../../docs/DID_STUDENT_PLAN.md) - Part 2: Panel Data & Infrastructure

## Motivation

The existing `RentalDataLoader` only extracts the most recent month's rental data for cross-sectional analysis. For causal inference methods like DiD, we need panel data with multiple time periods per geographic unit. The `TimeSeriesRentalLoader` fills this gap by:

1. Loading all historical time periods from the ZORI dataset
2. Automatically identifying date columns (YYYY-MM-DD format)
3. Reshaping the data from wide format to long format suitable for panel analysis

## Changes Made

### New Component
- **Added:** `src/housing/components/loaders/timeseries_rental_data.py`
  - Implements `TimeSeriesRentalLoader` class inheriting from `DataLoader`
  - Three-step incremental development:
    - **Step 1:** Load CSV file with error handling
    - **Step 2:** Automatically identify date columns (starting with "20")
    - **Step 3:** Reshape to long format using `pd.melt()`

### Package Integration
- **Updated:** `src/housing/__init__.py`
  - Added import for `TimeSeriesRentalLoader`
  - Added to `__all__` export list

### Testing
- **Added:** Test case in `tests/test_pipeline_system.py`
  - `test_timeseries_rental_loader_success()` - Validates component execution and output structure

## Implementation Details

### Data Transformation

**Input Format (Wide):**
```
zip_code | 2015-01-31 | 2015-02-28 | ... | 2025-12-31
---------|------------|------------|-----|------------
60601    | 2000.00    | 2050.00    | ... | 2500.00
60602    | 1800.00    | 1820.00    | ... | 2200.00
```

**Output Format (Long/Panel):**
```
zip_code | month      | rental_price
---------|------------|-------------
60601    | 2015-01-31 | 2000.00
60601    | 2015-02-28 | 2050.00
60601    | ...        | ...
60602    | 2015-01-31 | 1800.00
60602    | 2015-02-28 | 1820.00
```

### Features

- **Automatic date column detection:** Identifies columns starting with "20" (years 2000+)
- **Data cleaning:** 
  - Renames `RegionName` to `zip_code`
  - Pads zip codes to 5 digits with leading zeros
  - Removes rows with missing rental prices
- **Sorting:** Output sorted by `zip_code` and `month` for easy inspection
- **Logging:** Comprehensive logging of data shape, date ranges, and statistics

## Usage

### Basic Usage

```python
from housing import TimeSeriesRentalLoader

# Use default file path
loader = TimeSeriesRentalLoader()
result = loader.execute({})
panel_data = result["timeseries_rental_data"]

# Or specify custom file path
loader = TimeSeriesRentalLoader(file_path="/path/to/data.csv")
result = loader.execute({})
```

### Expected Output

```python
# DataFrame columns: zip_code, month, rental_price (plus metadata columns)
# Shape: (N × T, columns) where N = number of zip codes, T = number of months
# Example: ~408,455 rows for 7,343 zip codes × ~56 months
```

### Pipeline Integration

```python
from pipeline import Pipeline
from housing import TimeSeriesRentalLoader

pipeline = Pipeline("DiD Analysis Pipeline")
pipeline.register_component(TimeSeriesRentalLoader())
results = pipeline.execute()

# Access panel data
panel_data = pipeline.context["timeseries_rental_data"]
```

## Testing

### Manual Testing

Tested successfully on sample data:
- **Input:** `/Users/clairehuang/Downloads/Zip_zori_uc_sfrcondomfr_sm_month.csv`
- **Output:** 408,455 rows of panel data
- **Date Range:** 2015-01-31 to 2025-12-31
- **Zip Codes:** 7,343 unique zip codes

### Automated Testing

```bash
pytest tests/test_pipeline_system.py::TestPipelineComponents::test_timeseries_rental_loader_success -v
```

## Output Data Structure

The output DataFrame contains:
- **Primary columns:**
  - `zip_code` (str): 5-digit zip code identifier
  - `month` (str): Date in YYYY-MM-DD format
  - `rental_price` (float): Rental price value
- **Metadata columns** (preserved from original data):
  - `RegionID`, `SizeRank`, `RegionType`, `StateName`, `State`, `City`, `Metro`, `CountyName`

## Validation Results

From test run:
- ✅ Successfully loads CSV with 7,343 rows, 141 columns
- ✅ Identifies 132 date columns (2015-01-31 to 2025-12-31)
- ✅ Reshapes to 408,455 panel observations
- ✅ Preserves all zip codes and date range
- ✅ Rental price range: $516 - $95,833 (reasonable values)
- ✅ Data sorted by zip_code and month
- ✅ Missing values removed

## Next Steps

This component enables the following downstream analyses:
1. **Treatment Indicator Creation** (Part 3 of DiD Plan)
2. **Descriptive Analysis** (Part 4 of DiD Plan)
3. **DiD Estimation** (Part 5 of DiD Plan)
4. **Event Study Analysis** (Part 6 of DiD Plan)

## Breaking Changes

None. This is a new component and does not modify existing functionality.

## Checklist

- [x] Component follows existing loader patterns
- [x] Code passes linter checks
- [x] Unit tests added and passing
- [x] Component exported in `__init__.py`
- [x] Documentation strings added
- [x] Logging implemented
- [x] Error handling for missing files
- [x] Manual testing completed
