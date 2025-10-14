# Points to Tract Aggregation Guide

> Use `PointsToTractProcessor` to aggregate point data to census tracts with automatic spatial joins and density calculations.

## Overview

Aggregates point data (individual locations) to census tract polygons.

**What it does:**
- Matches each point to its census tract
- Aggregates by tract (count, mean, sum, custom)
- Calculates density (points per km²)
- Returns GeoDataFrame with tract geometries + data

## Basic Usage

```python
from housing import PointsToTractProcessor, TractBoundariesLoader

pipeline.register_component(YourPointDataLoader())  # Load points
pipeline.register_component(TractBoundariesLoader())  # Load tracts

processor = PointsToTractProcessor(
    input_key="your_point_data",
    output_key="your_tract_data",
    id_column="point_id",
    aggregate_columns={
        "value": "mean",
        "category": lambda x: x.mode()[0] if len(x) > 0 else None,
    },
    calculate_density=True
)

pipeline.register_component(processor)
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_key` | str | `"point_data"` | Context key for input points |
| `output_key` | str | `"tract_aggregated_data"` | Context key for output |
| `id_column` | str\|None | `None` | Column to count (None = count rows) |
| `aggregate_columns` | dict | `{}` | `{column: agg}` e.g., `{"price": "mean"}` |
| `calculate_density` | bool | `True` | Calculate points per km² |

## Input Requirements

**Point Data:** GeoDataFrame with Point geometries and CRS defined

```python
import geopandas as gpd
df = pd.read_csv('points.csv')
point_gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df.longitude, df.latitude),
    crs="EPSG:4326"
)
```

**Tract Boundaries:** Use `TractBoundariesLoader()`

## Output

| Column | Description |
|--------|-------------|
| `tract_geoid` | Census tract ID |
| `geometry` | Tract polygon |
| `point_count` | Number of points |
| `point_density` | Points per km² |
| `area_km2` | Tract area |
| *custom* | Aggregated values |

## Aggregation Examples

### Count Only
```python
PointsToTractProcessor(input_key="violations", output_key="violation_tracts")
```

### Multiple Aggregations
```python
aggregate_columns={
    "severity": ["mean", "max"],
    "arrests": "sum",
    "officer_id": "nunique",
}
```

### Custom Functions
```python
aggregate_columns={
    "violations": lambda x: (x > 0).sum(),  # Count with violations
    "fine_amount": "sum",
}
```

## Multi-Level Workflow

```python
from housing import TractToCommunityProcessor

# Points → Tracts
pipeline.register_component(PointsToTractProcessor(
    input_key="point_data",
    output_key="tract_data"
))

# Tracts → Communities
pipeline.register_component(CommunityBoundariesLoader())
pipeline.register_component(TractToCommunityProcessor())
```

## Tips

- **Always use density** for comparisons (normalizes by area)
- **Check logs** for match rate: `Matched 4521/4580 (98.7%)`
- **Zero-point tracts** have `point_count=0` (not dropped)
- **CRS is automatic** - handles projection for area calc

## Troubleshooting

**Low match rate?** Points outside Chicago or CRS mismatch  
**Need details?** See `CENSUS_TRACT_GUIDE.md`
