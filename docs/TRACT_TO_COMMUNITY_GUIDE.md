# Tract to Community Area Aggregation Guide

This guide explains how to use the `TractToCommunityProcessor` to aggregate census tract-level data up to community area level in Chicago.

## Overview

The `TractToCommunityProcessor` performs hierarchical spatial aggregation from census tracts to community areas using area-weighted aggregation and centroid-based spatial joins. This is essential for Chicago housing analysis since:

- **Census tracts** (800+ in Chicago) provide detailed spatial granularity
- **Community areas** (77 in Chicago) are the standard geographic units for city planning and policy
- **Hierarchical aggregation** ensures proper data flow from detailed to summary levels

## Key Features

- **Area-weighted aggregation**: Properly weights tract data by area when aggregating
- **Spatial join mapping**: Maps tracts to community areas using centroid-based joins
- **Flexible column handling**: Supports various aggregation methods for different data types
- **Robust error handling**: Handles missing data and edge cases gracefully

## Usage

### Basic Usage

```python
from housing import TractToCommunityProcessor

# Create processor
processor = TractToCommunityProcessor()

# Register in pipeline
pipeline.register_component(processor)
```

### Pipeline Context Requirements

The processor expects the following data in the pipeline context:

- **Input**: `tract_rental_data` - GeoDataFrame with tract-level rental data
- **Boundaries**: `community_boundaries` - GeoDataFrame with community area boundaries
- **Output**: `community_rental_data` - GeoDataFrame with aggregated community-level data

## Data Flow

### 1. Spatial Join (Tracts → Community Areas)

The processor performs a spatial join to determine which community area each census tract belongs to:

```python
# Use centroid-based join for nested geographies
tract_centroids = tract_data.copy()
tract_centroids["geometry"] = tract_centroids.geometry.centroid

# Spatial join - which community does each tract belong to?
tract_community = gpd.sjoin(
    tract_centroids,
    community_boundaries[["community_name", "geometry"]],
    how="left",
    predicate="within",
)
```

### 2. Area-Weighted Aggregation

For accurate aggregation, the processor calculates area-weighted averages:

```python
# Calculate tract areas in projected CRS
temp_gdf_projected = temp_gdf.to_crs("EPSG:32616")
tract_community_clean["tract_area"] = temp_gdf_projected.geometry.area

# Weight rental prices by tract area
tract_community_clean["weighted_rent"] = (
    tract_community_clean["avg_rental_price"] * tract_community_clean["tract_area"]
)
```

### 3. Community-Level Aggregation

Data is aggregated by community area using pandas groupby operations:

```python
community_agg = tract_community_clean.groupby("community_name").agg({
    "weighted_rent": "sum",
    "tract_area": "sum", 
    "avg_rental_price": ["mean", "min", "max", "count"],
}).reset_index()
```

## Output Schema

The processor outputs a GeoDataFrame with the following columns:

| Column | Description |
|--------|-------------|
| `community_name` | Name of the community area |
| `geometry` | Community area boundary geometry |
| `avg_rental_price` | Mean rental price across tracts |
| `min_rental_price` | Minimum rental price across tracts |
| `max_rental_price` | Maximum rental price across tracts |
| `tract_count` | Number of tracts in the community area |
| `area_weighted_avg_rent` | Area-weighted average rental price |

## Spatial Considerations

### Coordinate Reference Systems

The processor handles CRS transformations automatically:

1. **Input tracts**: Typically in EPSG:4269 (NAD83)
2. **Community boundaries**: Typically in EPSG:4326 (WGS84)
3. **Area calculations**: Converted to EPSG:32616 (UTM Zone 16N) for accurate area calculations

### Centroid-Based Joins

Uses tract centroids for spatial joining rather than full geometries:
- **Faster performance**: Centroid calculations are computationally efficient
- **Robust results**: Avoids edge cases with complex geometries
- **Appropriate for nested geographies**: Tracts are designed to nest within community areas


## Integration with Pipeline

### Pipeline Registration

```python
# In your pipeline script
pipeline.register_component(
    TractToCommunityProcessor()
)
```

### Downstream Components

The output `community_rental_data` can be used by:

- **Correlation analyzers**: For community-level correlation analysis
- **Visualization components**: For community-level maps and charts
- **Summary reporters**: For community-level statistics and summaries

## Example Pipeline Flow

```python
# 1. Load tract-level rental data
pipeline.register_component(RentalDataLoader())
pipeline.register_component(ZipToTractProcessor())

# 2. Aggregate to community level
pipeline.register_component(TractToCommunityProcessor())

# 3. Analyze at community level
pipeline.register_component(RentalCorrelationAnalyzer())
pipeline.register_component(CommunityVisualizer())
```

## Best Practices

1. **Validate input data**: Ensure tract data has required columns and valid geometries
2. **Check CRS consistency**: Verify that all spatial data uses appropriate coordinate systems
3. **Monitor aggregation results**: Review tract counts and area-weighted averages for reasonableness
4. **Handle missing data**: Be aware that some community areas may have no tract data
