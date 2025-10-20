# Spatial Aggregation Guide

This guide covers spatial data aggregation in the housing analysis pipeline, including point-to-tract and tract-to-community aggregation.

## Overview

The pipeline uses two main aggregation processors:

- **`PointsToTractProcessor`** - Aggregates point data to census tracts
- **`TractToCommunityProcessor`** - Aggregates tract data to community areas

## Points to Tract Aggregation

### Basic Usage

```python
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.processors.points_to_tract import PointsToTractProcessor

# Load tract boundaries
pipeline.register_component(TractBoundariesLoader())

# Aggregate points to tracts
processor = PointsToTractProcessor(
    input_key="airbnb_data",
    output_key="airbnb_tract_data", 
    id_column="id",
    aggregate_columns={"price": ["mean", "median"]}
)
pipeline.register_component(processor)
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `input_key` | `"point_data"` | Context key for input points |
| `output_key` | `"tract_aggregated_data"` | Context key for output |
| `id_column` | `None` | Column to count (None = count rows) |
| `aggregate_columns` | `{}` | Dict of {column: aggregation} for additional stats |
| `calculate_density` | `True` | Whether to calculate points per km² |

### What It Does

1. **Spatial Join**: Matches each point to its census tract
2. **Aggregation**: Counts points and calculates mean prices per tract
3. **Density Calculation**: Computes points per km²
4. **Geometry Join**: Adds tract geometries to results

## Tract to Community Aggregation

### Basic Usage

```python
from housing.components.processors.tract_to_community import TractToCommunityProcessor

# Aggregate tracts to community areas
pipeline.register_component(TractToCommunityProcessor())
```

### What It Does

1. **Spatial Mapping**: Maps tracts to community areas using centroids
2. **Area-Weighted Aggregation**: Properly weights data by area
3. **Hierarchical Flow**: Enables point → tract → community analysis

### Custom Configuration

The processor uses smart defaults but can be configured for custom data:

```python
# Custom configuration example
processor = TractToCommunityProcessor(
    input_key="airbnb_tract_data",     # Instead of default "tract_data"
    output_key="airbnb_community_data", # Instead of default "community_data"
    id_column="tract_geoid",           # Column for counting tracts
    aggregate_columns={                # Custom aggregations
        "price_mean": "mean",
        "price_median": "median"
    },
    area_weighted_columns=["price_mean"]  # Columns to area-weight
)
```

## Two-Step Aggregation Pattern

For point data analysis, use both processors:

```python
# Step 1: Points → Tracts
pipeline.register_component(PointsToTractProcessor("airbnb_data", "airbnb_tract_data"))

# Step 2: Tracts → Communities  
pipeline.register_component(TractToCommunityProcessor())
```

## Data Requirements

### Input Data
- **Points**: GeoDataFrame with Point geometries and CRS
- **Tracts**: GeoDataFrame with Polygon geometries  
- **Communities**: GeoDataFrame with community area boundaries

### Output Data
- **Tract Level**: Aggregated point data with tract geometries
- **Community Level**: Aggregated tract data with community geometries

## Common Use Cases

### Airbnb Analysis
```python
pipeline.register_component(AirbnbDataLoader())
pipeline.register_component(TractBoundariesLoader())
# Option 1: Use base processor with manual aggregation
pipeline.register_component(PointsToTractProcessor(
    "airbnb_data", 
    "airbnb_tract_data",
    id_column="id",
    aggregate_columns={"price": ["mean", "median", "min", "max"]}
))
# Option 2: Use convenience class (if available)
# pipeline.register_component(AirbnbToTractProcessor())
pipeline.register_component(TractToCommunityProcessor())
```

### STR Prohibition Analysis
```python
pipeline.register_component(STRProhibitionDataLoader())
pipeline.register_component(TractBoundariesLoader())
pipeline.register_component(PointsToTractProcessor("str_prohibition_data", "str_tract_data"))
# STR units density (units per km²) is computed in the analyzer
pipeline.register_component(TractToCommunityProcessor())
```