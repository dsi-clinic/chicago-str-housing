# Census Tract Analysis Guide

## Overview

This guide explains how to work with **census tracts** for spatial aggregation in Chicago. The typical workflow is:

1. **Point data → Census tracts** (spatial join + aggregation)
2. **Census tracts → Community areas** (area-weighted aggregation)

This two-step process provides both fine-grained analysis and neighborhood-level summaries.

---

## Why Census Tracts?

### The Three Geographic Levels

| Level | Count | Size | Best For |
|-------|-------|------|----------|
| **Points** | Thousands | Individual locations | Raw data (Airbnb, STR prohibitions) |
| **Census Tracts** | ~801 | ~4,000 residents | Fine-grained analysis, density calculations |
| **Community Areas** | 77 | ~35,000 residents | Neighborhood summaries, public communication |

### When to Use Each Level

**Use Census Tracts when:**
- Calculating densities (per km²)
- Joining with census demographic data (ACS)
- Detecting local variations and hotspots

**Use Community Areas when:**
- Summarizing for public communication
- Matching local neighborhood names

---

## The Two-Step Aggregation Pattern

### Pattern Overview

```
Point Data (Airbnb, STR)
    ↓ (spatial join: which tract is each point in?)
Census Tracts (aggregated counts, densities)
    ↓ (area-weighted aggregation)
Community Areas (neighborhood summaries)
```

### Why Two Steps?

1. **Granularity**: Tracts preserve local detail that would be lost going directly to communities
2. **Density calculations**: Tracts have consistent size, good for per-km² metrics
3. **Flexibility**: Can analyze at either tract or community level
4. **Accuracy**: Area-weighted aggregation preserves spatial precision

---

## Step 1: Points to Census Tracts

### Get Census Tract Boundaries

**Use 2023 TIGER/Line Shapefiles (matches 2019-2023 ACS 5-year estimates)**

1. Visit: [2023 TIGER/Line® Shapefiles: Census Tracts](https://www.census.gov/cgi-bin/geo/shapefiles/index.php?year=2023&layergroup=Census+Tracts)
2. Select **Illinois** from the state dropdown
3. Click **Download** to get `tl_2023_17_tract.zip`
4. Extract the zip to a subdirectory in your data folder:
   
   **Option A - Command line:**
   ```bash
   # Extract to a subdirectory (keeps data/ clean)
   unzip tl_2023_17_tract.zip -d /project/data/tl_2023_17_tract/
   ```
   
   **Option B - GUI (easier):**
   - Move `tl_2023_17_tract.zip` to `/project/data/`
   - Double-click the zip file (automatically creates `tl_2023_17_tract/` folder)
   
   **Result:** Files will be in `/project/data/tl_2023_17_tract/`:
   - `tl_2023_17_tract.shp` (main file)
   - `tl_2023_17_tract.shx` (shape index)
   - `tl_2023_17_tract.dbf` (attributes)
   - `tl_2023_17_tract.prj` (projection)
   - `tl_2023_17_tract.cpg` (character encoding)

**Why 2023 TIGER/Line?**
- Matches the 2019-2023 ACS 5-year estimates (most recent)
- Includes all Illinois tracts (filter to Cook County for Chicago)
- Standard format for joining with census demographic data

### Spatial Join: Points to Tracts

**Example: Airbnb listings**

```python
import pandas as pd
import geopandas as gpd

# Load point data
airbnb = pd.read_csv('/project/data/listings.csv')
airbnb_gdf = gpd.GeoDataFrame(
    airbnb,
    geometry=gpd.points_from_xy(airbnb.longitude, airbnb.latitude),
    crs="EPSG:4326"
)

# Load tract boundaries from TIGER/Line shapefile
tracts_gdf = gpd.read_file('/project/data/tl_2023_17_tract/tl_2023_17_tract.shp')

# Filter to Cook County (Chicago) only
tracts_gdf = tracts_gdf[tracts_gdf['COUNTYFP'] == '031'].copy()

# Create standardized tract ID (GEOID is the 11-digit tract identifier)
tracts_gdf['tract_geoid'] = tracts_gdf['GEOID']

# Spatial join: which tract is each point in?
airbnb_with_tracts = gpd.sjoin(
    airbnb_gdf,
    tracts_gdf[['tract_geoid', 'geometry']],
    how='left',
    predicate='within'
)
```

### Aggregate to Tract Level

**Count and density:**

```python
# Calculate tract areas (needed for density)
tracts_gdf = tracts_gdf.to_crs("EPSG:3857")  # Project to meters
tracts_gdf['area_km2'] = tracts_gdf.geometry.area / 1_000_000
tracts_gdf = tracts_gdf.to_crs("EPSG:4326")  # Back to lat/lon

# Aggregate points by tract
tract_agg = airbnb_with_tracts.groupby('tract_geoid').agg({
    'id': 'count',  # Number of listings
    'price': 'mean'  # Average price
}).rename(columns={'id': 'airbnb_count', 'price': 'avg_price'}).reset_index()

# Calculate density
tract_agg = tract_agg.merge(
    tracts_gdf[['tract_geoid', 'area_km2']],
    on='tract_geoid'
)
tract_agg['airbnb_density'] = tract_agg['airbnb_count'] / tract_agg['area_km2']
```

---

## Step 2: Tracts to Community Areas

### Get Community Area Boundaries

```python
# Load from Chicago Data Portal JSON endpoint
community_gdf = gpd.read_file('https://data.cityofchicago.org/resource/igwz-8jzy.json')

# Standardize community area identifier
community_gdf['community_area'] = community_gdf['area_numbe']
```

**Note:** The pipeline loaders automatically cache API responses in `/project/data/.cache/` to avoid repeated API calls. The cache is used on subsequent runs, making the pipeline much faster.

### Area-Weighted Aggregation

**Why area-weighted?** Tracts often cross community boundaries. A tract that's 30% in one community and 70% in another should contribute proportionally.

```python
# 1. Find intersections between tracts and communities
tracts_proj = tracts_gdf.to_crs("EPSG:3857")
community_proj = community_gdf.to_crs("EPSG:3857")

intersections = gpd.overlay(
    tracts_proj,
    community_proj[['community_area', 'geometry']],
    how='intersection'
)

# 2. Calculate intersection areas
intersections['intersection_area'] = intersections.geometry.area

# 3. Merge with tract data
intersections = intersections.merge(
    tract_agg,
    on='tract_geoid',
    how='left'
)

# 4. Calculate weighted values
intersections['weighted_count'] = (
    intersections['airbnb_count'] * 
    intersections['intersection_area'] / 
    intersections['area_km2']
)

# 5. Aggregate to community level
community_agg = intersections.groupby('community_area').agg({
    'weighted_count': 'sum',
    'intersection_area': 'sum'
}).reset_index()

community_agg['airbnb_density'] = (
    community_agg['weighted_count'] / 
    (community_agg['intersection_area'] / 1_000_000)  # Convert to km²
)
```

---

## Using Pipeline Components

The pipeline handles this automatically!

### Example: Airbnb Analysis

```python
from pipeline import Pipeline
from pipeline.config import PipelineConfig
from housing.components import (
    AirbnbDataLoader,
    TractBoundariesLoader,
    CommunityBoundariesLoader,
    AirbnbToTractProcessor,
    TractToCommunityProcessor
)

config = PipelineConfig()
pipeline = Pipeline("Airbnb Analysis", config=config)
pipeline.load_config()

# Load data
pipeline.register_component(AirbnbDataLoader())
pipeline.register_component(TractBoundariesLoader())
pipeline.register_component(CommunityBoundariesLoader())

# Two-step aggregation
pipeline.register_component(AirbnbToTractProcessor())
pipeline.register_component(TractToCommunityProcessor())

# Execute
results = pipeline.execute()

# Access results
tract_data = pipeline.context["airbnb_tract_data"]
community_data = pipeline.context["community_airbnb_data"]
```

### Available Processors

| Processor | Input | Output |
|-----------|-------|--------|
| `AirbnbToTractProcessor` | Airbnb points → | Tract aggregation with density |
| `ZipToTractProcessor` | ZIP polygons → | Tract aggregation (rental prices) |
| `TractToCommunityProcessor` | Tract data → | Community aggregation |

---

## Common Calculations

### 1. Density (per km²)

```python
# Always calculate density at tract level
tract_agg['density'] = tract_agg['count'] / tract_agg['area_km2']

# Why: Tracts have consistent size, makes density comparable
```

### 2. Count Aggregation

```python
# For counts: simple sum (but weighted when aggregating tracts→communities)
tract_total_count = tract_agg['count'].sum()

# For weighted community aggregation, see area-weighted section above
```

### 3. Average Values

```python
# For tract-level averages
tract_agg['avg_value'] = tract_agg['total_value'] / tract_agg['count']

# For community-level weighted averages
community_agg['weighted_avg'] = (
    community_agg['weighted_total'] / community_agg['weighted_count']
)
```

---

## Practical Example: Building Your Own Aggregation

### Scenario: You have building inspection data

```python
# 1. Load your point data
inspections = pd.read_csv('building_inspections.csv')
# Should have: latitude, longitude, violation_count, etc.

# 2. Create GeoDataFrame
inspections_gdf = gpd.GeoDataFrame(
    inspections,
    geometry=gpd.points_from_xy(inspections.longitude, inspections.latitude),
    crs="EPSG:4326"
)

# 3. Spatial join to tracts
tracts_gdf = gpd.read_file('/project/data/tl_2023_17_tract/tl_2023_17_tract.shp')
tracts_gdf = tracts_gdf[tracts_gdf['COUNTYFP'] == '031'].copy()  # Cook County
tracts_gdf['tract_geoid'] = tracts_gdf['GEOID']

inspections_with_tract = gpd.sjoin(
    inspections_gdf,
    tracts_gdf[['tract_geoid', 'geometry']],
    how='left',
    predicate='within'
)

# 4. Aggregate by tract
tract_inspections = inspections_with_tract.groupby('tract_geoid').agg({
    'building_id': 'count',
    'violation_count': 'sum'
}).rename(columns={'building_id': 'inspection_count'}).reset_index()

# 5. Add density
tracts_gdf_proj = tracts_gdf.to_crs("EPSG:3857")
tracts_gdf_proj['area_km2'] = tracts_gdf_proj.geometry.area / 1_000_000
tracts_gdf_proj = tracts_gdf_proj.to_crs("EPSG:4326")

tract_inspections = tract_inspections.merge(
    tracts_gdf_proj[['tract_geoid', 'area_km2']],
    on='tract_geoid'
)
tract_inspections['inspection_density'] = (
    tract_inspections['inspection_count'] / tract_inspections['area_km2']
)

# 6. Join geometries for mapping
tract_inspections_gdf = tracts_gdf.merge(
    tract_inspections,
    on='tract_geoid',
    how='left'
)

# 7. Map it
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(12, 10))
tract_inspections_gdf.plot(
    column='inspection_density',
    cmap='YlOrRd',
    legend=True,
    ax=ax
)
plt.title('Building Inspections per km² by Census Tract')
plt.savefig('inspection_density_map.png')
```

---

## Common Issues

### Issue 1: Points Missing Tract Assignment

**Symptom**: Many rows have `NaN` for `tract_geoid` after spatial join

**Causes**:
- Points outside Chicago/Cook County boundaries
- CRS mismatch
- Geometry errors
- Shapefile not filtered to Cook County

**Solutions**:
```python
# Check how many points have no tract
missing = inspections_with_tract['tract_geoid'].isna().sum()
print(f"{missing} points have no tract assignment")

# Verify tract file loaded correctly
print(f"Total tracts loaded: {len(tracts_gdf)}")
print(f"Tracts in Cook County: {len(tracts_gdf[tracts_gdf['COUNTYFP'] == '031'])}")

# Check CRS match
print(f"Points CRS: {inspections_gdf.crs}")
print(f"Tracts CRS: {tracts_gdf.crs}")

# Check bounds overlap
print(f"Points bounds: {inspections_gdf.total_bounds}")
print(f"Tracts bounds: {tracts_gdf.total_bounds}")

# Fix: Reproject to same CRS
inspections_gdf = inspections_gdf.to_crs(tracts_gdf.crs)
```

### Issue 2: Density Calculation Errors

**Symptom**: Extremely high or low density values

**Cause**: Area not in km² or wrong units

**Solution**:
```python
# Always project to meters before calculating area
gdf_proj = gdf.to_crs("EPSG:3857")  # Web Mercator (meters)
gdf_proj['area_m2'] = gdf_proj.geometry.area
gdf_proj['area_km2'] = gdf_proj['area_m2'] / 1_000_000

# Then convert back to geographic CRS for mapping
gdf = gdf_proj.to_crs("EPSG:4326")
```

### Issue 3: Slow Spatial Operations

**Symptom**: Spatial join or overlay takes forever

**Solutions**:
```python
# 1. Use spatial index (happens automatically with GeoPandas)
# 2. Filter to relevant area first
chicago_bounds = tracts_gdf.total_bounds
points_chicago = points_gdf.cx[
    chicago_bounds[0]:chicago_bounds[2],
    chicago_bounds[1]:chicago_bounds[3]
]

# 3. Simplify geometries (for tracts/communities, not points)
tracts_gdf['geometry'] = tracts_gdf.geometry.simplify(0.001)
```

---

## Next Steps

### 1. Add Census Demographics

```python
# Get ACS data from census.gov API or data.census.gov
acs_data = pd.read_csv('acs_tract_demographics.csv')

# Join with your tract data
enriched = tract_inspections.merge(
    acs_data,
    left_on='tract_geoid',
    right_on='GEOID',
    how='left'
)

# Analyze correlations
enriched['median_income'].corr(enriched['violation_count'])
```

### 2. Temporal Analysis

```python
# If your data has dates
inspections_2023 = inspections[inspections['year'] == 2023]
inspections_2024 = inspections[inspections['year'] == 2024]

# Aggregate each year separately
# Compare densities over time
```

### 3. Create a Pipeline Component

```python
# Turn your workflow into a reusable component
# See docs/STUDENT_GUIDE.md for template

class InspectionToTractProcessor(DataProcessor):
    def __init__(self):
        super().__init__(
            "inspection_tract_processor",
            "Aggregate inspections to census tracts"
        )
    
    def execute(self, context):
        # Your aggregation logic here
        # Return tract-level data
        return {"tract_inspections": tract_inspections}
```

---

## Key Takeaways

✅ **Two-step aggregation**: Points → Tracts → Communities  
✅ **Calculate density** at tract level (per km²)  
✅ **Use area-weighted aggregation** for tract → community  
✅ **Always check CRS** before spatial operations  
✅ **Pipeline components** handle this automatically

For more details on pipeline architecture, see [PIPELINE_GUIDE.md](PIPELINE_GUIDE.md).
