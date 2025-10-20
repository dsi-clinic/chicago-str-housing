# Analysis Methodology

## Statistical Methods

### Winsorization for Outlier Management

**STR Units Density**: To prevent extreme outliers from skewing analysis and visualizations, STR Units Density is winsorized at the 99th percentile. This means:

- Values above the 99th percentile are capped at that threshold
- The original uncapped values are preserved in `str_prohibition_density_raw` for auditing
- All correlations and visualizations use the winsorized values
- This approach maintains statistical validity while reducing the influence of extreme outliers

**Rationale**: Very small census tracts with large prohibited buildings can create extreme density values that disproportionately influence correlation analysis and make visualizations less interpretable.

### Density Calculations

**STR Units Density**: Calculated as total prohibited units per tract divided by tract area (km²)
**Airbnb Units Density**: Calculated as total Airbnb listings per tract divided by tract area (km²)

Both metrics provide normalized measures that enable meaningful comparison across tracts of different sizes.

## Spatial Analysis

### Geographic Hierarchy

The analysis uses a three-level geographic hierarchy:

1. **Census Tracts** (~1,300 in Cook County) - Primary analysis unit
2. **Community Areas** (77 neighborhoods) - Aggregation target
3. **ZIP Codes** (59 postal zones) - Data source bridge

### Spatial Aggregation Methods

- **Points to Tracts**: Spatial joins using `geopandas.sjoin()` with `within` predicate
- **Tracts to Communities**: Area-weighted aggregation preserving statistical properties
