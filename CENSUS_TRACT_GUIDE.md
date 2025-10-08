# Census Tract Analysis Guide

## Overview

This guide explains how to aggregate data from **zip codes to census tracts** for more granular neighborhood analysis in Chicago.

## Why Use Census Tracts Instead of Community Areas?

### Census Tracts
- **More granular**: ~800 tracts in Chicago vs 77 community areas
- **Standardized**: Consistent boundaries across the entire US
- **Smaller size**: Average ~4,000 residents per tract
- **Better for equity analysis**: Can identify block-level disparities
- **Census data aligned**: Easy to join with ACS demographic data

### Community Areas  
- **Larger**: 77 areas covering entire city
- **Locally meaningful**: Based on historical Chicago neighborhoods
- **Easier visualization**: Less cluttered maps
- **Stable boundaries**: Defined in 1920s, rarely change

### When to Use Each

| Use Census Tracts When... | Use Community Areas When... |
|---------------------------|----------------------------|
| You need fine-grained analysis | You want neighborhood-level overview |
| Joining with census demographic data | Working with Chicago-specific datasets |
| Detecting local variations | Communicating to general public |
| Performing equity analysis | Historical trend analysis |

---

## Getting Census Tract Boundary Data

### Option 1: Chicago Data Portal (Recommended for Chicago)

**Best for**: Quick start with Chicago data

1. **Visit**: [Chicago Data Portal - Census Tracts 2010](https://data.cityofchicago.org/Facilities-Geographic-Boundaries/Boundaries-Census-Tracts-2010/5jrd-6zik)

2. **Export to CSV**:
   - Click "Export" button
   - Select "CSV" format
   - Download the file

3. **Save the file**:
   ```bash
   # Save to your data directory
   mv ~/Downloads/Boundaries_-_Census_Tracts_-_2010.csv /project/data/Boundaries_Census_Tracts.csv
   ```

4. **Check the data structure**:
   - Should have columns: `GEOID10`, `the_geom`, `TRACTCE10`, etc.
   - `the_geom` contains WKT polygon strings
   - `GEOID10` is the 11-digit tract identifier (State+County+Tract)

### Option 2: US Census Bureau TIGER/Line Files

**Best for**: Any location in the US, most current boundaries

1. **Visit**: [Census TIGER/Line Shapefiles](https://www.census.gov/cgi-bin/geo/shapefiles/index.php)

2. **Select parameters**:
   - Year: 2020 (most recent) or 2010 (matches community areas)
   - Layer type: "Census Tracts"
   - State: "Illinois"

3. **Download and convert**:
   ```python
   import geopandas as gpd
   
   # Read shapefile
   tracts = gpd.read_file("tl_2020_17_tract.shp")
   
   # Filter to Cook County (Chicago)
   chicago_tracts = tracts[tracts['COUNTYFP'] == '031']
   
   # Export to CSV with WKT geometry
   chicago_tracts['the_geom'] = chicago_tracts.geometry.to_wkt()
   chicago_tracts.to_csv('/project/data/Boundaries_Census_Tracts.csv', index=False)
   ```

### Option 3: HUD USPS Crosswalk (No Geometries)

**Best for**: Just the zip-to-tract mapping without spatial analysis

1. **Visit**: [HUD USPS ZIP-Tract Crosswalk](https://www.huduser.gov/portal/datasets/usps_crosswalk.html)

2. **Download**: Choose the most recent quarter

3. **File format**:
   ```
   ZIP,TRACT,RES_RATIO,BUS_RATIO,OTH_RATIO,TOT_RATIO
   60601,17031081403,0.0,1.0,0.0,1.0
   60602,17031081600,0.12,0.88,0.0,1.0
   ```

4. **Note**: This gives you the crosswalk directly but no geometries for mapping

---

## Understanding the Zip-to-Tract Relationship

### Key Concept: Many-to-Many Mapping

**Unlike zip codes and community areas, zip-to-tract mapping is many-to-many:**

```
ZIP 60614 ──┬──> Tract 17031060100 (40% overlap)
            ├──> Tract 17031060200 (35% overlap)  
            └──> Tract 17031060300 (25% overlap)

Tract 17031060200 <──┬── ZIP 60614 (60% overlap)
                     └── ZIP 60657 (40% overlap)
```

### Why This Matters

1. **Area weighting is critical**: 
   - Can't just assign a zip's value to all intersecting tracts
   - Must weight by intersection area

2. **Data aggregation requires care**:
   - Simple averages will be wrong
   - Need area-weighted averages

3. **The crosswalk is valuable**:
   - Save it for reuse with other datasets
   - Documents the mapping for reproducibility

---

## Using the Pipeline Components

### Basic Usage

```python
from pipeline import (
    Pipeline,
    RentalDataLoader,
    ZipBoundariesLoader,
    TractBoundariesLoader,
    ZipToTractProcessor,
    TractAnalyzer,
)
from pipeline.config import PipelineConfig

# Create pipeline
config = PipelineConfig()
pipeline = Pipeline("Tract Analysis", config=config)
pipeline.load_config()

# Load data
pipeline.register_component(RentalDataLoader())
pipeline.register_component(ZipBoundariesLoader())
pipeline.register_component(TractBoundariesLoader())

# Spatial join and analysis
pipeline.register_component(ZipToTractProcessor())
pipeline.register_component(TractAnalyzer())

# Execute
results = pipeline.execute()

# Access results
tract_data = pipeline.context["tract_rental_data"]
crosswalk = pipeline.context["zip_to_tract_crosswalk"]
```

### Component Details

#### `TractBoundariesLoader`

Loads census tract boundary data from CSV with WKT geometries.

**Input**: CSV file with columns:
- `the_geom` or `geometry`: WKT polygon string
- `GEOID10`, `TRACTCE10`, or similar: Tract identifier

**Output**: `tract_boundaries` GeoDataFrame

**Configuration**:
```python
# Default path
loader = TractBoundariesLoader()

# Custom path
loader = TractBoundariesLoader("/path/to/tracts.csv")
```

#### `ZipToTractProcessor`

Performs spatial join from zip codes to census tracts with area-weighted aggregation.

**Requirements**: 
- `rental_data` (from RentalDataLoader)
- `zip_boundaries` (from ZipBoundariesLoader)
- `tract_boundaries` (from TractBoundariesLoader)

**Outputs**:
- `tract_rental_data`: GeoDataFrame with tract-level aggregated rental data
- `zip_to_tract_crosswalk`: DataFrame mapping zips to tracts with intersection areas

**Key features**:
- Calculates actual intersection areas (not just overlap flags)
- Area-weighted aggregation for accurate prices
- Handles many-to-many relationships properly

#### `TractAnalyzer`

Performs statistical analysis on tract-level data.

**Requirements**: `tract_rental_data`

**Outputs**:
- `tract_correlation_matrix`: Correlation analysis
- `tract_analysis_data`: Clean analysis dataset
- `tract_summary_stats`: Summary statistics

---

## The Zip-to-Tract Crosswalk

### What It Contains

```python
crosswalk.head()
```

| zip_code | tract_geoid | intersection_area |
|----------|-------------|-------------------|
| 60614 | 17031060100 | 0.0023 |
| 60614 | 17031060200 | 0.0018 |
| 60614 | 17031060300 | 0.0012 |

### How to Use It

**1. Map any zip code data to tracts**:
```python
# You have some data by zip code
zip_data = pd.DataFrame({
    'zip_code': ['60614', '60657', '60640'],
    'some_value': [100, 200, 150]
})

# Join with crosswalk
merged = zip_data.merge(crosswalk, on='zip_code')

# Calculate area-weighted values for each tract
merged['weighted_value'] = merged['some_value'] * merged['intersection_area']

tract_values = merged.groupby('tract_geoid').agg({
    'weighted_value': 'sum',
    'intersection_area': 'sum'
}).reset_index()

tract_values['tract_value'] = (
    tract_values['weighted_value'] / tract_values['intersection_area']
)
```

**2. Understand zip coverage**:
```python
# How many tracts does each zip overlap?
zip_coverage = crosswalk.groupby('zip_code').size()
print(zip_coverage.describe())

# Which zip has the most tract overlaps?
max_zip = zip_coverage.idxmax()
print(f"Zip {max_zip} overlaps {zip_coverage.max()} tracts")
```

**3. Save for reuse**:
```python
# Save crosswalk
crosswalk.to_csv('/project/data/zip_to_tract_crosswalk.csv', index=False)

# Load later
crosswalk = pd.read_csv('/project/data/zip_to_tract_crosswalk.csv')
```

---

## Example: Complete Workflow

### Step 1: Prepare Data

```bash
# Download tract boundaries
# Save to /project/data/Boundaries_Census_Tracts.csv

# Verify existing data
ls /project/data/
# Should have:
# - Boundaries_Census_Tracts.csv
# - Boundaries_ZIP_Codes.csv  
# - Zip_zori_uc_sfrcondomfr_sm_month.csv
```

### Step 2: Run Pipeline

```python
from pipeline import Pipeline, RentalDataLoader, ZipBoundariesLoader
from pipeline import TractBoundariesLoader, ZipToTractProcessor, TractAnalyzer
from pipeline.config import PipelineConfig

config = PipelineConfig()
pipeline = Pipeline("Tract Analysis", config=config)
pipeline.load_config()

pipeline.register_component(RentalDataLoader())
pipeline.register_component(ZipBoundariesLoader())
pipeline.register_component(TractBoundariesLoader())
pipeline.register_component(ZipToTractProcessor())
pipeline.register_component(TractAnalyzer())

results = pipeline.execute()
```

### Step 3: Explore Results

```python
# Get tract data
tract_data = pipeline.context["tract_rental_data"]
print(f"Total tracts: {len(tract_data)}")
print(f"Tracts with data: {tract_data['avg_rental_price'].notna().sum()}")

# Get crosswalk
crosswalk = pipeline.context["zip_to_tract_crosswalk"]
print(f"Total zip-tract mappings: {len(crosswalk)}")

# Get statistics
stats = pipeline.context["tract_summary_stats"]
print(f"Average rent: ${stats['avg_rental_price']:,.2f}")
print(f"Std deviation: ${stats['rental_price_std']:,.2f}")
```

### Step 4: Export Results

```python
# Export tract data
tract_export = tract_data.drop(columns=['geometry', 'the_geom'], errors='ignore')
tract_export.to_csv('/project/data/tract_rental_prices.csv', index=False)

# Export crosswalk
crosswalk.to_csv('/project/data/zip_to_tract_crosswalk.csv', index=False)

# Export as GeoJSON for mapping
tract_data.to_file('/project/data/tract_rental_prices.geojson', driver='GeoJSON')
```

---

## Common Issues and Solutions

### Issue 1: Tract File Not Found

**Error**: `FileNotFoundError: Census tract boundaries file not found`

**Solution**: 
```python
# Check if file exists
import os
os.path.exists('/project/data/Boundaries_Census_Tracts.csv')

# If False, download from Chicago Data Portal
# See "Getting Census Tract Boundary Data" above
```

### Issue 2: Wrong Column Names

**Error**: `ValueError: No geometry column found in census tract data`

**Solution**: The loader tries common column names. If your file has different columns:

```python
import pandas as pd

# Check what columns you have
df = pd.read_csv('/project/data/Boundaries_Census_Tracts.csv')
print(df.columns)

# If geometry column is named differently, rename it:
df = df.rename(columns={'YOUR_GEOM_COL': 'the_geom'})
df.to_csv('/project/data/Boundaries_Census_Tracts.csv', index=False)
```

### Issue 3: No Intersections Found

**Error**: Pipeline runs but `tract_rental_data` is empty

**Cause**: CRS mismatch or no geographic overlap

**Solution**:
```python
# Check CRS of each dataset
zip_bounds = pipeline.context["zip_boundaries"]
tract_bounds = pipeline.context["tract_boundaries"]

print(f"Zip CRS: {zip_bounds.crs}")
print(f"Tract CRS: {tract_bounds.crs}")

# Check geographic bounds
print(f"Zip bounds: {zip_bounds.total_bounds}")
print(f"Tract bounds: {tract_bounds.total_bounds}")

# If CRS different, they should be reprojected (processor does this)
# If bounds don't overlap, you have wrong geography
```

### Issue 4: Memory Issues with Large Areas

**Error**: Process killed or very slow

**Cause**: Calculating intersections for many geometries is memory-intensive

**Solution**: Process in batches
```python
# Modify ZipToTractProcessor to work in chunks
# Or filter to specific area first:

tract_bounds_filtered = tract_bounds[
    tract_bounds['COUNTYFP'] == '031'  # Cook County only
]
```

---

## Next Steps

### 1. Join Census Demographic Data

```python
# Get ACS data for tracts
# Example: income, population, race/ethnicity

acs_data = pd.read_csv('acs_tract_data.csv')
# Should have 'tract_geoid' column

# Join with rental data
enriched = tract_data.merge(
    acs_data, 
    left_on='tract_geoid', 
    right_on='tract_geoid',
    how='left'
)
```

### 2. Visualize on a Map

```python
import matplotlib.pyplot as plt

# Choropleth map
fig, ax = plt.subplots(figsize=(12, 10))

tract_data.plot(
    column='avg_rental_price',
    cmap='YlOrRd',
    legend=True,
    ax=ax
)

plt.title('Average Rental Price by Census Tract')
plt.savefig('tract_rental_map.png')
```

### 3. Cluster Analysis

```python
from sklearn.cluster import KMeans

# Prepare features
features = tract_data[['avg_rental_price', 'zip_count', 'area_km2']].dropna()

# Cluster
kmeans = KMeans(n_clusters=5, random_state=42)
tract_data['cluster'] = kmeans.fit_predict(features)

# Map clusters
tract_data.plot(column='cluster', categorical=True, legend=True)
```

### 4. Compare with Community Areas

```python
# Run both pipelines
# Compare granularity and insights

print(f"Community areas: {len(community_data)}")
print(f"Census tracts: {len(tract_data)}")
print(f"Granularity ratio: {len(tract_data) / len(community_data):.1f}x")
```

---
