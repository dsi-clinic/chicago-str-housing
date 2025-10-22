# Analysis Methodology

## Statistical Methods

### Winsorization for Outlier Management

**Density Metrics**: To prevent extreme outliers from skewing analysis and clustering, all density metrics (STR Units Density, Airbnb Density, etc.) are winsorized at the 99th percentile using the `DensityOutlierRemovalProcessor`. This means:

- Values above the 99th percentile are capped at that threshold
- All tracts are preserved (no data loss)
- Extreme outliers are capped rather than removed to maintain spatial coverage
- This approach maintains statistical validity while reducing the influence of extreme outliers

**Implementation**: The `DensityOutlierRemovalProcessor` supports multiple methods:
- `winsorize`: Caps extreme values at specified percentile (default: 99th)
- `percentile`: Removes tracts above specified percentile
- `iqr`: Removes tracts beyond IQR-based thresholds
- `zscore`: Removes tracts beyond z-score thresholds

**Rationale**: Very small census tracts with large prohibited buildings or high concentrations of listings can create extreme density values that disproportionately influence correlation analysis, clustering algorithms, and make visualizations less interpretable. Winsorization preserves all data while reducing skew.

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
