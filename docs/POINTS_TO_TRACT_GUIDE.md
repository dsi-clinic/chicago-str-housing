# Points to Tract Aggregation Guide

## Overview

The `PointsToTractProcessor` component provides a reusable way to aggregate point datato census tract level.

## Components

### 1. `PointsToTractProcessor` (General Purpose)

A flexible processor for any point data aggregation.

**What it does:**
1. Spatial join: matches each point to its census tract
2. Aggregates points by tract (count, averages, etc.)
3. Calculates point density per km²
4. Returns tract-level GeoDataFrame

---

## Basic Usage

### Example 1: Airbnb Listings

```python
from housing import AirbnbDataLoader, TractBoundariesLoader, AirbnbToTractProcessor
from pipeline import Pipeline
from pipeline.config import PipelineConfig

# Create pipeline
config = PipelineConfig()
pipeline = Pipeline("Airbnb Tract Analysis", config=config)
pipeline.load_config()

# Load data
pipeline.register_component(AirbnbDataLoader())  # Loads as 'airbnb_data'
pipeline.register_component(TractBoundariesLoader())  # Loads as 'tract_boundaries'

# Aggregate to tracts
pipeline.register_component(AirbnbToTractProcessor())

# Run
results = pipeline.execute()

# Access results
airbnb_tracts = pipeline.context['airbnb_tract_data']
print(airbnb_tracts.columns)
# Output: ['tract_geoid', 'geometry', 'point_count', 'price_mean', 'price_median', 
#          'price_min', 'price_max', 'area_km2', 'point_density']
```

### Example 2: Custom Point Data

```python
from housing import PointsToTractProcessor

# For custom point data (e.g., crime incidents)
crime_processor = PointsToTractProcessor(
    input_key="crime_data",           # Context key for input points
    output_key="crime_tract_data",    # Context key for output
    id_column="incident_id",          # Column to count
    aggregate_columns={
        "severity": "max",            # Maximum severity per tract
        "arrests": "sum",             # Total arrests per tract
    },
    calculate_density=True            # Calculate crimes per km²
)

pipeline.register_component(crime_processor)
```

### Example 3: STR Prohibitions

```python
from housing import PointsToTractProcessor

# Aggregate STR prohibition zones
str_processor = PointsToTractProcessor(
    input_key="str_prohibitions",
    output_key="str_tract_data",
    id_column="zone_id",
    aggregate_columns={
        "prohibition_type": lambda x: x.mode()[0] if len(x) > 0 else None,  # Most common type
        "effective_date": "min",      # Earliest prohibition date
    },
    calculate_density=True
)
```

---

## Input Requirements

### Point Data (GeoDataFrame)

Your point data must be a GeoPandas GeoDataFrame with:
- **geometry column**: Point geometries
- **CRS defined**: e.g., `EPSG:4326` (lat/lon)
- Any additional columns you want to aggregate

Example:
```python
import geopandas as gpd
import pandas as pd

# From CSV with lat/lon
df = pd.read_csv('my_points.csv')
point_gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df.longitude, df.latitude),
    crs="EPSG:4326"
)
```

### Tract Boundaries (from context)

The processor expects `tract_boundaries` in the pipeline context. Use `TractBoundariesLoader` to load:

```python
from housing import TractBoundariesLoader
pipeline.register_component(TractBoundariesLoader())
```

---

## Output Structure

The processor returns a GeoDataFrame with:

| Column | Description |
|--------|-------------|
| `tract_geoid` | Census tract identifier |
| `geometry` | Tract polygon geometry |
| `point_count` | Number of points in tract |
| `area_km2` | Tract area in km² |
| `point_density` | Points per km² |
| *custom columns* | Aggregated values from your configuration |

### Summary Statistics

Also returns a summary dict:
```python
summary = pipeline.context['airbnb_tract_data_summary']
# {
#     'total_tracts': 801,
#     'tracts_with_points': 245,
#     'total_points': 4521,
#     'avg_points_per_tract': 5.6,
#     'max_points_per_tract': 87
# }
```

---

## Aggregation Options

### Count Only

```python
processor = PointsToTractProcessor(
    input_key="points",
    output_key="tract_counts"
    # No id_column or aggregate_columns needed
)
```

### Multiple Aggregations

```python
processor = PointsToTractProcessor(
    input_key="listings",
    output_key="listing_tracts",
    id_column="listing_id",
    aggregate_columns={
        "price": ["mean", "median", "std"],
        "bedrooms": "max",
        "host_id": "nunique",  # Count unique hosts
    }
)
```

### Custom Functions

```python
processor = PointsToTractProcessor(
    input_key="violations",
    output_key="violation_tracts",
    aggregate_columns={
        "severity": lambda x: (x >= 3).sum(),  # Count severe violations
        "fine_amount": "sum",
    }
)
```

---

## Pipeline Integration

### Complete Example: Airbnb Density Analysis

```python
from housing import (
    AirbnbDataLoader,
    TractBoundariesLoader,
    AirbnbToTractProcessor,
)
from pipeline import Pipeline

pipeline = Pipeline("Airbnb Density Analysis")
pipeline.load_config()

# Step 1: Load data
pipeline.register_component(AirbnbDataLoader())
pipeline.register_component(TractBoundariesLoader())

# Step 2: Aggregate to tracts
pipeline.register_component(AirbnbToTractProcessor(
    input_key="airbnb_data",
    output_key="airbnb_tracts",
    id_column="id",
    price_column="price"
))

# Step 3: Run
results = pipeline.execute()

# Step 4: Analyze
tracts = pipeline.context['airbnb_tracts']
high_density = tracts[tracts['point_density'] > tracts['point_density'].quantile(0.75)]
print(f"High density tracts: {len(high_density)}")
print(f"Average price in high density: ${high_density['price_mean'].mean():.2f}")
```

---

## Comparison with Other Processors

| Processor | Input → Output | Use Case |
|-----------|---------------|----------|
| `PointsToTractProcessor` | **Points → Tracts** | Airbnb, STR, crime, violations |
| `ZipToTractProcessor` | ZIP polygons → Tracts | Rental price data from ZIP codes |
| `TractToCommunityProcessor` | Tracts → Communities | Aggregate tracts to neighborhoods |

### Typical Workflow

```
Point Data (Airbnb)
    ↓ PointsToTractProcessor
Census Tracts (density, averages)
    ↓ TractToCommunityProcessor
Community Areas (neighborhood summaries)
```

---

## Tips & Best Practices

### 1. **Always Calculate Density for Points**
```python
calculate_density=True  # This normalizes by area
```

### 2. **Use Appropriate Aggregations**
- **Counts**: Sum or count
- **Prices/Values**: Mean, median (weighted if possible)
- **Categories**: Mode (most common)
- **Dates**: Min (earliest), max (latest)

### 3. **Check Match Rate**
The processor logs how many points matched to tracts:
```
INFO: Matched 4521/4580 points to census tracts (98.7%)
```

Unmatched points are usually outside Chicago boundaries.

### 4. **Tracts with Zero Points**
By default, tracts with no points have `point_count = 0`. Use this for:
```python
# Find tracts with no Airbnb
no_airbnb = tracts[tracts['point_count'] == 0]
```

---

## Troubleshooting

### Issue: Low match rate (<90%)

**Possible causes:**
- Point data CRS doesn't match tract CRS
- Points outside Chicago/Cook County
- Invalid geometries

**Solution:**
```python
# Check CRS
print(point_data.crs)  # Should be EPSG:4326 or similar
point_data = point_data.to_crs("EPSG:4326")
```

### Issue: Density values seem wrong

**Cause:** Not using projected CRS for area calculation

**Solution:** The processor handles this automatically! It:
1. Projects to EPSG:32616 (UTM Zone 16N for Chicago)
2. Calculates area in meters
3. Converts to km²
4. Reprojects back to original CRS

No action needed!

---

## Next Steps

After aggregating points to tracts, you can:

1. **Visualize density maps**
2. **Aggregate to community areas** using `TractToCommunityProcessor`
3. **Join with census demographic data** using tract GEOID
4. **Analyze spatial patterns** (hotspots, clusters)

See `CENSUS_TRACT_GUIDE.md` for more analysis patterns.

