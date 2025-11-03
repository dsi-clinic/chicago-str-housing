# Chicago Housing Clustering Pipeline Methodology

## Overview

This document describes the methodology for preparing census tract-level housing data for clustering analysis. The pipeline integrates multiple data sources, handles missing values through spatial interpolation, and applies data quality filters to create a clean dataset suitable for neighborhood clustering.

## Pipeline Architecture

The clustering pipeline follows a modular design with the following stages:

1. **Data Loading** - Load and validate multiple data sources
2. **Spatial Processing** - Clip to Chicago boundaries and filter non-residential areas  
3. **Data Integration** - Merge data sources at census tract level
4. **Missing Value Imputation** - Spatial KNN interpolation for gaps
5. **Data Quality Processing** - Outlier handling and data cleaning
6. **Export** - Generate analysis-ready dataset

## Data Sources

### Primary Data Sources

| Source | Type | Variables | Coverage |
|--------|------|-----------|----------|
| **US Census ACS** | Demographics | Income, age, education, housing values, tenure | Complete (with interpolation) |
| **Rental Listings** | Market Data | Rental prices by ZIP code, aggregated to tracts | ~95% of tracts |
| **Airbnb** | Short-term Rentals | Listing counts and prices per tract | ~85% of tracts |
| **STR Prohibitions** | Policy Data | Prohibited units by building/tract | ~60% of tracts |

### Census Variables (ACS 5-Year Estimates)

Raw variables loaded from Census API:
- `census_median_income` - Median household income (B19013_001E)
- `census_median_house_value` - Median owner-occupied housing value (B25077_001E)
- `census_median_age` - Median age of residents (B01002_001E)
- `census_population` - Total population (B01003_001E)
- Bachelor's degree count (B15003_022E) - used for calculating education percentage
- Population 25+ years (B15003_001E) - used for calculating education percentage
- Total occupied housing units (B25003_001E) - used for calculating tenure percentage
- Owner-occupied housing units (B25003_002E) - used for calculating tenure percentage

### Derived Variables

- `census_pct_bachelor` - Percentage with bachelor's degree or higher (calculated from ACS education data)
- `census_pct_rented` - Percentage of housing units that are rented (calculated from ACS tenure data)
- `population_density` - People per square kilometer (calculated from population and tract area)
- `rental_price_mean` - Area-weighted average rental price from ZIP to tract aggregation
- `airbnb_price_mean` - Average Airbnb listing price per tract  
- `airbnb_density` - Airbnb listings per square kilometer
- `str_prohibition_building_density` - STR-prohibited buildings per square kilometer
- `str_prohibition_units_density` - STR-prohibited units per square kilometer

## Spatial Processing

### Geographic Scope

1. **Initial Tract Loading**: Load all Cook County census tracts from TIGER/Line files
2. **Chicago Boundary Clipping**: Clip tracts to Chicago city administrative boundaries using `gpd.clip()`
3. **Non-Residential Filtering**: Remove O'Hare census tracts

## Data Integration and Processing

The clustering pipeline merges multiple datasets at the census tract level through the following process:

### Base Geographic Framework

1. **Tract Boundaries**: Start with Cook County census tracts as the base geographic framework
2. **Chicago Clipping**: Clip tracts to Chicago city administrative boundaries using `gpd.clip()`
3. **Non-Residential Filtering**: Remove O'Hare airport tracts (4 tracts filtered out)

### Sequential Data Merging

Datasets are merged in this order using tract identifiers:

#### 1. Rental Data Integration
- Uses pre-computed area-weighted average rental prices aggregated from ZIP codes to tracts
- Renames `area_weighted_avg_rent` to `rental_price_mean` (primary clustering variable)
- Drops less accurate unweighted averages

#### 2. Airbnb Data Integration  
- Merges aggregated Airbnb listing data (points-to-tract processing done upstream)
- Renames variables: `point_count` → `airbnb_count`, `point_density` → `airbnb_density`
- Includes price statistics: `price_numeric_mean` → `airbnb_price_mean`

#### 3. STR Prohibition Data Integration
- Merges aggregated STR prohibition data (points-to-tract processing done upstream)  
- Renames variables: `point_count` → `str_prohibition_count`
- Calculates building density: `str_prohibition_building_density = str_prohibition_count / area_sq_km`
- Includes unit counts: `number_of_units_sum` → `str_prohibition_units_total`

#### 4. Census Data Integration
- Merges tract-level ACS demographic data directly (no spatial processing needed)
- Renames all variables with `census_` prefix for clarity
- Includes calculated percentages (`pct_bachelor`, `pct_rented`) from raw ACS variables

### Density Calculations

Density metrics are calculated with geographic accuracy after data merging:

1. **CRS Transformation**: Reproject geometries from WGS84 (EPSG:4326) to Albers Equal Area Conic (EPSG:5070)
2. **Area Calculation**: Calculate tract areas in square meters, convert to square kilometers
3. **Density Computations**: 
   - `population_density = census_population / area_sq_km`
   - `str_prohibition_building_density = str_prohibition_count / area_sq_km`
   - `str_prohibition_units_density = str_prohibition_units_total / area_sq_km`
4. **Small Area Filtering**: Set density to NaN for tracts < 0.01 km² (likely data errors)

### Data Quality Processing

1. **Missing Value Handling**: Set count/density columns to 0 where no data exists (e.g., no Airbnb listings = 0 density)
2. **Outlier Capping**: Winsorize extreme population density values using 99th percentile or 50,000 people/km² cap
3. **Column Cleanup**: Remove redundant columns and standardize naming conventions

## Missing Value Imputation

### Spatial KNN Interpolation

The pipeline uses K-Nearest Neighbors (K=5) spatial interpolation to fill missing values in clustering variables:

#### Algorithm

1. **Feature Preparation**: 
   - Extract tract centroids (reprojected to EPSG:5070 for accurate distances)
   - Combine spatial coordinates with other available variables as features
   - Standardize features using `StandardScaler`

2. **Neighbor Selection**:
   - Find K=5 nearest neighbors with valid data using Euclidean distance
   - Use inverse distance weighting to avoid division by zero: `weights = 1.0 / (distances + 1e-10)`

3. **Interpolation**:
   - Calculate weighted average: `interpolated_value = Σ(neighbor_values × weights)`
   - Only use variables with >50% data coverage as additional features

#### Variables Interpolated

- All census demographic variables (income, age, education, housing values, tenure)
- `rental_price_mean` (market data gaps) 
- `airbnb_price_mean` (short-term rental pricing gaps)
- `population_density` (calculated density gaps)

#### Variables Filled with Zero (Not Interpolated)

- `airbnb_density` - Missing = no Airbnb listings in tract
- `str_prohibition_building_density` - Missing = no STR prohibition buildings in tract  
- `str_prohibition_units_density` - Missing = no STR prohibition units in tract

### Benefits of Spatial Interpolation

- **Preserves spatial patterns**: Uses geographic proximity for realistic estimates
- **Maintains data relationships**: Incorporates similar variables as features
- **Reduces data loss**: Enables inclusion of tracts with partial missing data
- **Geographic realism**: Interpolated values reflect neighborhood characteristics

## Data Quality and Outlier Handling

### Density Variable Winsorization

Extreme density values are capped to prevent distortion of clustering results:

#### Population Density
1. **Distribution Analysis**: Log percentiles (50th, 90th, 95th, 99th, 99.9th) and maximum values
2. **Conservative Capping**: Use 99th percentile OR 50,000 people/km² (very dense urban), whichever is lower
3. **Extreme Value Logging**: Document values being capped for transparency

**Rationale**: Census data occasionally contains calculation errors (e.g., tiny tract areas leading to impossible densities). Winsorization preserves rank order while preventing outlier distortion.

#### STR Prohibition Units Density
1. **Distribution Analysis**: Log percentiles (50th, 90th, 95th, 99th, 99.9th) and maximum values
2. **Conservative Capping**: Use 99th percentile as upper bound
3. **Extreme Value Logging**: Document values being capped for transparency

**Rationale**: STR prohibition data can have extreme outliers from small tract areas or data entry errors. The 99th percentile provides robust outlier control while preserving policy intervention patterns.

### Outlier Removal Policy

**No outlier removal** is applied to clustering variables to preserve the full range of neighborhood characteristics:

- **Census variables**: Keep all income, age, education, and housing value ranges
- **Market variables**: Preserve full rental price and Airbnb density distributions  
- **Policy variables**: Maintain complete STR prohibition patterns

**Rationale**: Chicago neighborhoods exhibit genuine extreme values (very high-income areas, very dense urban cores, etc.). Removing these would eliminate important clustering patterns.

## Final Dataset Preparation

### Missing Data Handling After Interpolation

After spatial interpolation, any remaining tracts with missing clustering variables are removed:

1. **Complete Case Analysis**: Require all 11 clustering variables to be non-missing
2. **Documentation**: Log which variables had missing data and how many tracts are affected  
3. **Final Count**: 862 tracts with complete data (full Chicago coverage minus filtered O'Hare tracts)

### Clustering Variables

The final dataset includes 11 standardized variables for clustering:

#### Demographics (3 variables)
- `census_median_income` - Economic status
- `census_median_age` - Life cycle stage  
- `census_pct_bachelor` - Educational attainment

#### Housing Market (4 variables)
- `census_median_house_value` - Housing cost (ownership)
- `census_pct_rented` - Tenure patterns
- `rental_price_mean` - Housing cost (rental market)
- `airbnb_price_mean` - Short-term rental pricing

#### STR Activity (3 variables)  
- `airbnb_density` - Short-term rental supply
- `str_prohibition_building_density` - Policy intervention intensity (buildings)
- `str_prohibition_units_density` - Policy intervention intensity (units)

#### Population (1 variable)
- `population_density` - Urban density patterns

### Data Export Format

The final dataset is exported as:
- **GeoJSON**: `clustering_data.geojson` (preserves spatial geometry)  
- **CSV**: `clustering_data_scaled.csv` (analysis-ready with standardized variables)

Missing values in exports are coded as `-9999` for GeoJSON compatibility, then converted back to NaN for analysis.

## Quality Assurance

### Data Validation Checks

1. **Spatial Validity**: All geometries are valid and within Chicago boundaries
2. **Value Ranges**: All variables have realistic ranges (e.g., median income > $0, percentages 0-100%)
3. **Completeness**: Final dataset has complete data for all clustering variables
4. **Consistency**: Cross-variable relationships are reasonable (e.g., high house values with high incomes)

### Pipeline Logging

Comprehensive logging documents:
- Input data counts and coverage by source
- Interpolation statistics (variables, tract counts, success rates)
- Filtering results (non-residential tracts removed)
- Data quality adjustments (winsorization, missing data handling)
- Final dataset characteristics

## Usage Notes

### Preprocessing for Clustering Algorithms

The pipeline output is ready for clustering with minimal additional preprocessing:

1. **Standardization**: Apply `StandardScaler` or `RobustScaler` to handle different variable scales
2. **Algorithm Selection**: Suitable for K-means, hierarchical clustering, DBSCAN, etc.
3. **Spatial Constraints**: Can be used with spatially-constrained clustering if desired

### Interpretation Guidelines

- **Census variables**: Reflect 5-year ACS estimates (community characteristics)
- **Market variables**: Reflect recent rental market conditions (economic accessibility)  
- **STR variables**: Reflect policy interventions and tourism activity
- **Density**: Reflects urban development patterns and land use intensity

This methodology produces a robust, spatially-complete dataset that captures multiple dimensions of Chicago neighborhood characteristics suitable for housing policy analysis and urban planning applications.
