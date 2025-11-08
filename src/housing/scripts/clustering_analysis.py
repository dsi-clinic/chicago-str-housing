"""Chicago Housing Clustering Analysis.

This script performs analysis on pre-processed clustering data. It includes:
1. Choropleth maps for each variable
2. Moran's I for spatial autocorrelation
3. Pairwise correlation analysis
"""

import logging
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from housing.components.analyzers.kmeans_clusterer import (
    KMeansClusteringResult,
    attach_cluster_labels,
    create_attribute_distribution_facets,
    create_cluster_map,
    create_cluster_profiles_table,
    create_cluster_sizes_plot,
    prepare_cluster_analysis_data,
    run_kmeans_workflow,
    save_kmeans_outputs,
)
from housing.components.constants import MAX_POPULATION_DENSITY_DISPLAY
from housing.components.utils import (
    calculate_morans_i,
    calculate_value_cap,
    create_choropleth_maps,
    create_correlation_matrix,
)

logger = logging.getLogger(__name__)

warnings.filterwarnings(
    "ignore",
    message="Numba not installed. Using slow pure python version.",
    category=UserWarning,
    module="geopandas.plotting",
)

# Base paths for input and output
PROJECT_ROOT = Path("/project")
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Input and output file paths
CLUSTERING_DATA_INPUT = OUTPUT_DIR / "clustering_data.geojson"
CLUSTERING_DATA_SCALED_INPUT = OUTPUT_DIR / "clustering_data_scaled.csv"
CHOROPLETH_MAPS_OUTPUT = OUTPUT_DIR / "choropleth_maps.png"
MORANS_I_OUTPUT = OUTPUT_DIR / "morans_i_results.csv"
SCATTERPLOT_MATRIX_OUTPUT = OUTPUT_DIR / "scatterplot_matrix.png"
KMEANS_LABELS_OUTPUT = OUTPUT_DIR / "kmeans_cluster_labels.csv"
KMEANS_CENTERS_OUTPUT = OUTPUT_DIR / "kmeans_cluster_centers.csv"
KMEANS_PROFILES_OUTPUT = OUTPUT_DIR / "kmeans_cluster_profiles.csv"
KMEANS_COUNTS_OUTPUT = OUTPUT_DIR / "kmeans_cluster_sizes.csv"
KMEANS_MAP_OUTPUT = OUTPUT_DIR / "kmeans_cluster_map.png"
KMEANS_ATTRIBUTE_DISTRIBUTIONS_OUTPUT = (
    OUTPUT_DIR / "kmeans_attribute_distributions.png"
)
KMEANS_PROFILES_TABLE_OUTPUT = OUTPUT_DIR / "kmeans_cluster_profiles.txt"
KMEANS_COUNTS_FIGURE_OUTPUT = OUTPUT_DIR / "kmeans_cluster_sizes.png"


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


def load_cluster_variables(scaled_data_path: Path) -> list[str]:
    """Load cluster variable names from standardized data CSV.

    Args:
        scaled_data_path: Path to the standardized data CSV file

    Returns:
        List of cluster variable names
    """
    if not scaled_data_path.exists():
        raise FileNotFoundError(
            f"Standardized data not found: {scaled_data_path}\n"
            "Please run the clustering pipeline first: make run-clustering-pipeline"
        )

    # Read just the header to get variable names
    scaled_df = pd.read_csv(scaled_data_path, nrows=0, index_col=0)
    variables = list(scaled_df.columns)  # Get variable names from columns
    logger.info("Loaded %d cluster variables from standardized data", len(variables))
    return variables


def main() -> (
    tuple[
        gpd.GeoDataFrame,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        KMeansClusteringResult,
    ]
):
    """Run the clustering analysis pipeline."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

    # Set random seed for reproducibility
    np.random.seed(123456)

    logger.info("Chicago Housing Clustering Analysis")
    logger.info("=" * 50)

    # Step 1: Load data (already processed by pipeline)
    gdf_full = load_clustering_data()
    logger.info("Loaded clustering data with %d tracts", len(gdf_full))

    # Load cluster variables (already selected and standardized by pipeline)
    variables = load_cluster_variables(CLUSTERING_DATA_SCALED_INPUT)

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
        scheme="FisherJenks",
    )

    # Step 3: Filter data for statistical analysis (only tracts that were used in clustering)
    logger.info("\nStep 3: Filtering data for statistical analysis")
    cluster_data, gdf_analysis, scaled_df = prepare_cluster_analysis_data(
        gdf_full, variables, CLUSTERING_DATA_SCALED_INPUT
    )

    # Step 4: Run K-means clustering
    logger.info("\nStep 4: Running K-means clustering")
    kmeans_result, cluster_profiles, cluster_sizes = run_kmeans_workflow(
        cluster_data,
        scaled_df,
        n_clusters=5,
        random_state=123456,
        labels_column="kmeans_5",
    )

    # Attach cluster labels to GeoDataFrames for mapping and further analysis
    gdf_full, gdf_analysis = attach_cluster_labels(gdf_full, scaled_df, kmeans_result)

    save_kmeans_outputs(
        kmeans_result,
        cluster_profiles,
        cluster_sizes,
        labels_path=KMEANS_LABELS_OUTPUT,
        centers_path=KMEANS_CENTERS_OUTPUT,
        profiles_path=KMEANS_PROFILES_OUTPUT,
        sizes_path=KMEANS_COUNTS_OUTPUT,
    )

    logger.info("First five cluster labels: %s", kmeans_result.labels.head().tolist())

    # Step 4a: Visualise spatial distribution of clusters
    logger.info("Creating K-means cluster map")
    create_cluster_map(
        gdf_full,
        kmeans_result.labels.name,
        KMEANS_MAP_OUTPUT,
    )

    logger.info("Writing cluster profile summary table")
    create_cluster_profiles_table(
        cluster_profiles,
        KMEANS_PROFILES_TABLE_OUTPUT,
    )
    logger.info("Rendering cluster size bar chart")
    create_cluster_sizes_plot(
        cluster_sizes,
        KMEANS_COUNTS_FIGURE_OUTPUT,
    )

    # Step 4b: Plot attribute distributions by cluster
    logger.info("Creating attribute distribution plots by cluster")
    create_attribute_distribution_facets(
        cluster_data,
        kmeans_result.labels,
        KMEANS_ATTRIBUTE_DISTRIBUTIONS_OUTPUT,
    )

    # Step 5: Calculate Moran's I
    logger.info("\nStep 5: Calculating Moran's I")
    moran_results = calculate_morans_i(gdf_analysis, variables)
    moran_results.to_csv(MORANS_I_OUTPUT)

    # Step 6: Create correlation matrix
    logger.info("\nStep 6: Creating pairwise scatterplot matrix")
    create_correlation_matrix(
        cluster_data,
        output_path=SCATTERPLOT_MATRIX_OUTPUT,
        title="Pairwise Relationships Between Clustering Variables",
    )

    logger.info("\n" + "=" * 50)
    logger.info("Clustering analysis complete!")

    return gdf_full, cluster_data, scaled_df, moran_results, kmeans_result


if __name__ == "__main__":
    (
        gdf_full,
        cluster_data,
        scaled_data,
        moran_results,
        kmeans_result,
    ) = main()
