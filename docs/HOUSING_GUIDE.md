# Housing Analysis Components Guide

This guide covers the housing-specific components (`src/housing/`) used in the Chicago housing clustering pipeline and analysis.

## Overview

The housing components are organized into four categories:
- **Loaders**: Load housing data from files and APIs
- **Processors**: Aggregate and transform spatial data
- **Cluster Analysis**: Clustering algorithms and evaluation
- **Utilities**: Shared functions for spatial analysis and visualization

## Pipeline Components

The clustering pipeline (`clustering_pipeline.py`) prepares census tract-level data for clustering analysis.

### Data Loaders

**Available Loaders:**
- `RentalDataLoader` - ZORI rental price data by ZIP code
- `AirbnbDataLoader` - Airbnb listings with prices and locations
- `STRProhibitionDataLoader` - Short-term rental prohibited buildings
- `CensusDataLoader` - ACS demographic data (requires Census API key)
- `AffordableDataLoader` - Affordable housing developments
- `ForeclosedDataLoader` - Foreclosed rental properties
- `TractBoundariesLoader` - Census tract boundaries (TIGER/Line)
- `ZipBoundariesLoader` - ZIP code boundaries (Chicago Data Portal)
- `CommunityBoundariesLoader` - Community area boundaries
- `CityBoundariesLoader` - Chicago city boundaries

### Spatial Processors

**Key Processors:**
- `ZipToTractProcessor` - Area-weighted aggregation from ZIP codes to census tracts
- `PointsToTractProcessor` - Spatial join and aggregation of point data to tracts
- `TractDataMerger` - Merges multiple data sources at tract level, handles missing values, winsorizes outliers
- `SpatialInterpolator` - KNN interpolation for missing values (used internally by TractDataMerger)
- `TractToCommunityProcessor` - Aggregate tract data to community areas

The clustering pipeline uses these processors to:
1. Aggregate ZIP-level rental data to census tracts
2. Aggregate point data (Airbnb, STR prohibitions) to tracts
3. Merge all data sources and prepare for clustering

## Clustering Analysis Components

The clustering analysis (`clustering_analysis.py`) performs clustering and evaluation on prepared data.

### Cluster Analysis Functions

**Key Functions:**
- `run_kmeans_workflow()` - Complete K-means workflow with elbow plot, profiles, sizes
- `run_ward_clustering()` - Ward hierarchical clustering (with optional spatial constraints)
- `create_cluster_map()` - Choropleth maps of cluster assignments
- `create_attribute_distribution_facets()` - KDE plots by cluster
- `compute_coherence_scores()` - Calinski-Harabasz scores for cluster quality
- `compute_similarity_matrix()` - Adjusted Mutual Information between solutions
- `kruskal_wallis_by_attribute()` - Statistical tests for cluster differences
- `run_permanova_test()` - Multivariate permutation tests
- `run_manova_test()` - Multivariate analysis of variance

### Spatial Analysis Utilities

**Utility Functions:**
- `calculate_morans_i()` - Calculate spatial autocorrelation for variables
- `create_choropleth_maps()` - Create choropleth maps for multiple variables
- `create_correlation_matrix()` - Create pairwise correlation/scatterplot matrix

## Component Details

### PointsToTractProcessor

Aggregates point data (Airbnb listings, STR prohibitions) to census tracts.

**Parameters:**
- `input_key` - Context key for input points
- `output_key` - Context key for output
- `id_column` - Column to count (or None for row count)
- `aggregate_columns` - Dictionary of columns to aggregate (e.g., `{"price": ["mean", "median"]}`)
- `calculate_density` - Whether to calculate points per km²
- `data_source_name` - Prefix for column names

**Output columns:**
- `{data_source_name}_count` - Number of points per tract
- `{data_source_name}_density` - Points per square kilometer
- Aggregated columns (e.g., `price_numeric_mean`, `price_numeric_median`)

### ZipToTractProcessor

Aggregates ZIP code-level data to census tracts using area-weighted averaging.

**Requirements:**
- `rental_data` in context (ZIP-level rental prices)
- `zip_boundaries` in context
- `tract_boundaries` in context

**Output:**
- `tract_rental_data` with area-weighted average rental prices

### TractDataMerger

Merges multiple data sources at the tract level and prepares data for clustering.

**What it does:**
1. Filters tracts to Chicago boundaries (centroid-based)
2. Removes non-residential tracts (O'Hare airport)
3. Merges rental, Airbnb, STR prohibition, census, affordable, and foreclosed data
4. Calculates density metrics (population, STR units, etc.)
5. Interpolates missing values using spatial KNN
6. Winsorizes extreme density outliers
7. Standardizes variables for clustering

**Output:**
- `clustering_data` - GeoDataFrame with all variables
- `clustering_data_scaled` - Standardized DataFrame for clustering
- `cluster_variables` - List of variable names used for clustering

## Running the Pipelines

### Clustering Data Preparation

```bash
make run-clustering-pipeline
```

**Outputs:**
- `output/clustering_data.geojson` - Complete tract-level dataset
- `output/clustering_data_scaled.csv` - Standardized variables for clustering

### Clustering Analysis

```bash
# Run clustering analysis
make run-clustering-analysis

# Include optional scatterplot matrix
make run-clustering-analysis ARGS="--scatter-matrix"
```

**Outputs:**
- Cluster maps, profiles, distributions, statistical tests
- Evaluation metrics (coherence scores, similarity matrix)
- See `docs/CLUSTERING_ANALYSIS.md` for complete output list

## Data Requirements

### Required Data Files

- **Census Tracts**: `data/tl_2023_17_tract/tl_2023_17_tract.shp` (TIGER/Line)
- **Rental Data**: `data/Zip_zori_uc_sfrcondomfr_sm_month.csv` (ZORI)
- **Airbnb Data**: `data/listings.csv`
- **STR Prohibition**: Fetched from Chicago Data Portal API
- **Census Data**: Requires Census API key in environment

### Environment Variables

```bash
CENSUS_API_KEY=your_api_key_here
```

## See Also

- `docs/CLUSTERING_PIPELINE.md` - Detailed methodology for data preparation
- `docs/CLUSTERING_ANALYSIS.md` - Clustering analysis workflow and outputs
- `docs/PIPELINE_GUIDE.md` - General pipeline framework guide
