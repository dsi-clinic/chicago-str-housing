"""Chicago Housing Clustering Analysis.

This script prepares data for clustering and regionalization analysis following
the methods from Geographic Data Science textbook. It includes:
1. Choropleth maps for each variable
2. Moran's I for spatial autocorrelation
3. Pairwise correlation analysis
4. Data standardization
"""

import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from housing.components.constants import MAX_POPULATION_DENSITY_DISPLAY
from housing.components.utils import (
    calculate_morans_i,
    calculate_value_cap,
    create_choropleth_maps,
    create_correlation_matrix,
    standardize_data,
)

logger = logging.getLogger(__name__)

# Base paths for input and output
PROJECT_ROOT = Path("/project")
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Input and output file paths
CLUSTERING_DATA_INPUT = OUTPUT_DIR / "clustering_data.geojson"
CHOROPLETH_MAPS_OUTPUT = OUTPUT_DIR / "choropleth_maps.png"
MORANS_I_OUTPUT = OUTPUT_DIR / "morans_i_results.csv"
SCATTERPLOT_MATRIX_OUTPUT = OUTPUT_DIR / "scatterplot_matrix.png"
SCALED_DATA_OUTPUT = OUTPUT_DIR / "clustering_data_scaled.csv"


def load_clustering_data(file_path: Path | None = None) -> gpd.GeoDataFrame:
    """Load the clustering data prepared by the pipeline."""
    if file_path is None:
        file_path = CLUSTERING_DATA_INPUT

    logger.info("Loading clustering data from %s", file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Clustering data not found: {file_path}\n"
            "Please run the clustering pipeline first: make run-clustering-pipeline"
        )

    gdf = gpd.read_file(file_path)
    logger.info("Loaded %d census tracts", len(gdf))

    return gdf


def select_cluster_variables(gdf: gpd.GeoDataFrame) -> tuple[list[str], pd.DataFrame]:
    """Select and prepare variables for clustering.

    Returns:
        Tuple of (variable names, dataframe with selected variables)
    """
    # Select variables for clustering - mix of housing market, demographics, and STR activity
    cluster_variables = [
        # Demographics
        "census_median_income",
        "census_median_age",
        "census_pct_bachelor",
        # Housing market
        "census_median_house_value",
        "census_pct_rented",
        "rental_price_mean",
        "airbnb_price_mean",
        # STR activity
        "airbnb_density",
        "str_prohibition_building_density",
        "str_prohibition_units_density",
        # Population
        "population_density",
        # Affordable and foreclosed housing
        "affordable_development_density",
        "affordable_unit_density",
        "foreclosed_density",
    ]

    # Filter to only variables that exist in the data
    available_vars = [var for var in cluster_variables if var in gdf.columns]

    # Create subset with only clustering variables
    # Data processing (missing values, outliers) now handled upstream in clustering pipeline
    cluster_data = gdf[available_vars].copy()

    logger.info(
        "Selected %d clustering variables for %d tracts",
        len(available_vars),
        len(cluster_data),
    )

    return available_vars, cluster_data


def main() -> None:
    """Run the clustering analysis pipeline."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

    # Set random seed for reproducibility
    np.random.seed(123456)

    logger.info("Chicago Housing Clustering Analysis")
    logger.info("=" * 50)

    # Step 1: Load data (already clipped to Chicago in pipeline)
    gdf_full = load_clustering_data()
    logger.info("Loaded clustering data with %d tracts", len(gdf_full))

    # Define variables for clustering
    cluster_variables = [
        "census_median_income",
        "census_median_age",
        "census_pct_bachelor",
        "census_median_house_value",
        "census_pct_rented",
        "rental_price_mean",
        "airbnb_price_mean",
        "airbnb_density",
        "str_prohibition_building_density",
        "str_prohibition_units_density",
        "population_density",
        "affordable_development_density",
        "affordable_unit_density",
        "foreclosed_density",
    ]
    variables = [var for var in cluster_variables if var in gdf_full.columns]

    # Step 2: Create choropleth maps (includes all tracts, applies display capping for visualization)
    logger.info("\nStep 2: Creating choropleth maps")
    # Calculate population density cap for visualization
    max_value_caps = calculate_value_cap(
        gdf_full,
        "population_density",
        percentile=0.95,
        max_value=MAX_POPULATION_DENSITY_DISPLAY,
    )

    create_choropleth_maps(
        gdf_full,
        variables,
        output_path=CHOROPLETH_MAPS_OUTPUT,
        max_value_caps=max_value_caps,
    )

    # Step 3: Select clustering variables and remove tracts with missing data
    logger.info("\nStep 3: Filtering data for statistical analysis")
    variables, cluster_data = select_cluster_variables(gdf_full)

    # Update gdf for analysis
    gdf_analysis = gdf_full.loc[cluster_data.index]

    # Step 4: Calculate Moran's I
    logger.info("\nStep 4: Calculating Moran's I")
    moran_results = calculate_morans_i(gdf_analysis, variables)
    moran_results.to_csv(MORANS_I_OUTPUT)

    # Step 5: Create correlation matrix
    logger.info("\nStep 5: Creating pairwise scatterplot matrix")
    create_correlation_matrix(
        cluster_data,
        output_path=SCATTERPLOT_MATRIX_OUTPUT,
        title="Pairwise Relationships Between Clustering Variables",
    )

    # Step 6: Standardize data
    logger.info("\nStep 6: Standardizing data")
    scaled_data = standardize_data(cluster_data)

    # Save standardized data
    scaled_df = pd.DataFrame(scaled_data, columns=variables, index=cluster_data.index)
    scaled_df.to_csv(SCALED_DATA_OUTPUT)

    logger.info("\n" + "=" * 50)
    logger.info("Clustering data preparation complete!")
    logger.info("Standardized data saved to: %s", SCALED_DATA_OUTPUT)

    return gdf_full, cluster_data, scaled_data, moran_results


if __name__ == "__main__":
    gdf_full, cluster_data, scaled_data, moran_results = main()
