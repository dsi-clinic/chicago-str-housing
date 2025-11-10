"""Chicago Housing Clustering Analysis.

This script performs analysis on pre-processed clustering data. It includes:
1. Choropleth maps for each variable
2. Moran's I for spatial autocorrelation
3. Pairwise correlation analysis
"""

import argparse
import logging
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from libpysal.weights import KNN, Queen

from housing.components.cluster import (
    KMeansClusteringResult,
    attach_cluster_labels,
    build_tidy_cluster_frame,
    compute_coherence_scores,
    compute_similarity_matrix,
    create_attribute_distribution_facets,
    create_cluster_comparison_map,
    create_cluster_map,
    create_cluster_sizes_plot,
    create_kmeans_elbow_plot,
    dataframe_to_table_png,
    kruskal_wallis_by_attribute,
    pairwise_ks_tests,
    prepare_cluster_analysis_data,
    render_cluster_summary_table,
    run_kmeans_workflow,
    run_manova_test,
    run_permanova_test,
    run_ward_clustering,
    summarise_clusters,
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
CLUSTER_OUTPUT_DIR = OUTPUT_DIR / "clustering"
CHOROPLETH_MAPS_OUTPUT = CLUSTER_OUTPUT_DIR / "choropleth_maps.png"
MORANS_I_OUTPUT = CLUSTER_OUTPUT_DIR / "morans_i_results.csv"
SCATTERPLOT_MATRIX_OUTPUT = CLUSTER_OUTPUT_DIR / "scatterplot_matrix.png"
KMEANS_MAP_OUTPUT = CLUSTER_OUTPUT_DIR / "kmeans_cluster_map.png"
KMEANS_ATTRIBUTE_DISTRIBUTIONS_OUTPUT = (
    CLUSTER_OUTPUT_DIR / "kmeans_attribute_distributions.png"
)
KMEANS_PROFILES_TABLE_OUTPUT = CLUSTER_OUTPUT_DIR / "kmeans_cluster_profiles.png"
KMEANS_COUNTS_FIGURE_OUTPUT = CLUSTER_OUTPUT_DIR / "kmeans_cluster_sizes.png"
KMEANS_ELBOW_OUTPUT = CLUSTER_OUTPUT_DIR / "kmeans_elbow_plot.png"
KMEANS_ELBOW_SCORES_OUTPUT = CLUSTER_OUTPUT_DIR / "kmeans_elbow_scores.csv"
KMEANS_KRUSKAL_OUTPUT = CLUSTER_OUTPUT_DIR / "kmeans_cluster_kruskal.png"
KMEANS_PAIRWISE_KS_OUTPUT = CLUSTER_OUTPUT_DIR / "kmeans_cluster_pairwise_ks.png"
KMEANS_PERMANOVA_OUTPUT = CLUSTER_OUTPUT_DIR / "kmeans_cluster_permanova.png"
KMEANS_MANOVA_OUTPUT = CLUSTER_OUTPUT_DIR / "kmeans_cluster_manova.png"
WARD_MAP_OUTPUT = CLUSTER_OUTPUT_DIR / "ward_cluster_map.png"
WARD_ATTRIBUTE_DISTRIBUTIONS_OUTPUT = (
    CLUSTER_OUTPUT_DIR / "ward_attribute_distributions.png"
)
WARD_PROFILES_TABLE_OUTPUT = CLUSTER_OUTPUT_DIR / "ward_cluster_profiles.png"
WARD_COUNTS_FIGURE_OUTPUT = CLUSTER_OUTPUT_DIR / "ward_cluster_sizes.png"
WARD_QUEEN_MAP_OUTPUT = CLUSTER_OUTPUT_DIR / "ward_queen_cluster_map.png"
WARD_QUEEN_ATTRIBUTE_DISTRIBUTIONS_OUTPUT = (
    CLUSTER_OUTPUT_DIR / "ward_queen_attribute_distributions.png"
)
WARD_QUEEN_PROFILES_TABLE_OUTPUT = (
    CLUSTER_OUTPUT_DIR / "ward_queen_cluster_profiles.png"
)
WARD_QUEEN_COUNTS_FIGURE_OUTPUT = CLUSTER_OUTPUT_DIR / "ward_queen_cluster_sizes.png"
WARD_KNN_MAP_OUTPUT = CLUSTER_OUTPUT_DIR / "ward_knn_cluster_map.png"
WARD_KNN_ATTRIBUTE_DISTRIBUTIONS_OUTPUT = (
    CLUSTER_OUTPUT_DIR / "ward_knn_attribute_distributions.png"
)
WARD_KNN_PROFILES_TABLE_OUTPUT = CLUSTER_OUTPUT_DIR / "ward_knn_cluster_profiles.png"
WARD_KNN_COUNTS_FIGURE_OUTPUT = CLUSTER_OUTPUT_DIR / "ward_knn_cluster_sizes.png"
CLUSTER_COMPARISON_MAP_OUTPUT = CLUSTER_OUTPUT_DIR / "kmeans_ward_comparison_map.png"
CLUSTER_COHERENCE_OUTPUT = CLUSTER_OUTPUT_DIR / "cluster_coherence_scores.csv"
CLUSTER_SIMILARITY_OUTPUT = CLUSTER_OUTPUT_DIR / "cluster_similarity_matrix.csv"

ADDITIONAL_CLUSTER_COLUMNS = ["ward5", "ward5wq", "ward5wknn"]


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


def main(
    render_scatter_matrix: bool = False,
) -> tuple[
    gpd.GeoDataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    KMeansClusteringResult,
]:
    """Run the clustering analysis pipeline."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

    CLUSTER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

    # Step 4: Calculate Moran's I (and optionally render the scatterplot matrix)
    logger.info("\nStep 4: Calculating Moran's I for clustering variables")
    moran_results = calculate_morans_i(gdf_analysis, variables)
    moran_results.to_csv(MORANS_I_OUTPUT)

    if render_scatter_matrix:
        logger.info("Step 4a (optional): Creating pairwise scatterplot matrix")
        create_correlation_matrix(
            cluster_data,
            output_path=SCATTERPLOT_MATRIX_OUTPUT,
            title="Pairwise Relationships Between Clustering Variables",
        )

    # Step 5: Run K-means clustering
    kmeans_result, cluster_profiles, cluster_sizes = run_kmeans_workflow(
        cluster_data,
        scaled_df,
        n_clusters=6,
        random_state=123456,
        labels_column="kmeans_6",
    )

    # Attach cluster labels to GeoDataFrames for mapping and further analysis
    gdf_full, gdf_analysis = attach_cluster_labels(gdf_full, scaled_df, kmeans_result)

    # Step 5a: Visualise spatial distribution of clusters
    logger.info("Step 5a: Creating K-means cluster map")
    create_cluster_map(
        gdf_full,
        kmeans_result.labels.name,
        KMEANS_MAP_OUTPUT,
        title="K-means (k=6)",
    )

    logger.info("Writing cluster profile summary table")
    render_cluster_summary_table(
        cluster_profiles,
        cluster_sizes,
        KMEANS_PROFILES_TABLE_OUTPUT,
        title="K-means Cluster Profiles & Counts",
    )
    logger.info("Step 5a: Rendering cluster size bar chart")
    create_cluster_sizes_plot(
        cluster_sizes,
        KMEANS_COUNTS_FIGURE_OUTPUT,
        title="K-means (k=6) Cluster Sizes",
    )
    logger.info("Step 5a: Generating K-means elbow plot")
    elbow_scores = create_kmeans_elbow_plot(
        scaled_df,
        k_range=range(2, 11),
        random_state=123456,
        output_path=KMEANS_ELBOW_OUTPUT,
    )
    elbow_scores.to_csv(KMEANS_ELBOW_SCORES_OUTPUT)

    # Step 5b: Plot attribute distributions by cluster
    logger.info("Step 5b: Creating attribute distribution plots by cluster")
    create_attribute_distribution_facets(
        cluster_data,
        kmeans_result.labels,
        KMEANS_ATTRIBUTE_DISTRIBUTIONS_OUTPUT,
    )
    logger.info(
        "Step 5b: Running statistical tests for K-means attribute distributions"
    )
    tidy_kmeans = build_tidy_cluster_frame(
        cluster_data,
        kmeans_result.labels,
        index_name=cluster_data.index.name or "tract_id",
    )
    cluster_column = kmeans_result.labels.name or "cluster"

    kruskal_df = kruskal_wallis_by_attribute(
        tidy_kmeans,
        cluster_column,
    ).drop(columns=["pvalue_adj"], errors="ignore")
    if not kruskal_df.empty:
        dataframe_to_table_png(
            kruskal_df,
            KMEANS_KRUSKAL_OUTPUT,
            title="K-means Kruskal-Wallis Results",
            figsize=(12, 4),
        )
    else:
        logger.warning("Kruskal-Wallis results empty; skipping output.")

    pairwise_df = pairwise_ks_tests(
        tidy_kmeans,
        cluster_column,
    )
    if not pairwise_df.empty:
        dataframe_to_table_png(
            pairwise_df,
            KMEANS_PAIRWISE_KS_OUTPUT,
            title="K-means Pairwise KS Tests",
            figsize=(14, 6),
        )
    else:
        logger.warning("Pairwise KS results empty; skipping output.")

    permanova_series = run_permanova_test(
        scaled_df,
        kmeans_result.labels,
    )
    if permanova_series is not None:
        dataframe_to_table_png(
            permanova_series.to_frame().T,
            KMEANS_PERMANOVA_OUTPUT,
            title="K-means PERMANOVA",
            figsize=(8, 2.5),
        )
    else:
        logger.warning("PERMANOVA test skipped or unavailable.")

    manova_series = run_manova_test(
        cluster_data,
        kmeans_result.labels,
    )
    if manova_series is not None:
        dataframe_to_table_png(
            manova_series.to_frame().T,
            KMEANS_MANOVA_OUTPUT,
            title="K-means MANOVA",
            figsize=(8, 2.5),
        )
    else:
        logger.warning("MANOVA test skipped or unavailable.")

    # Step 6: Run Ward hierarchical clustering
    logger.info("\nStep 6: Running Ward hierarchical clustering")
    ward_result = run_ward_clustering(
        scaled_df,
        n_clusters=6,
        labels_column="ward6",
    )
    ward_profiles = summarise_clusters(cluster_data, ward_result)
    ward_sizes = ward_result.labels.value_counts().sort_index().rename("count")

    gdf_full.loc[ward_result.labels.index, ward_result.labels.name] = ward_result.labels
    gdf_analysis = gdf_full.loc[scaled_df.index]

    render_cluster_summary_table(
        ward_profiles,
        ward_sizes,
        WARD_PROFILES_TABLE_OUTPUT,
        title="Ward Cluster Profiles & Counts",
    )
    create_cluster_sizes_plot(
        ward_sizes,
        WARD_COUNTS_FIGURE_OUTPUT,
        title="Ward (k=6) Cluster Sizes",
    )
    create_cluster_map(
        gdf_full,
        ward_result.labels.name,
        WARD_MAP_OUTPUT,
        title="Ward (k=6)",
    )
    create_attribute_distribution_facets(
        cluster_data,
        ward_result.labels,
        WARD_ATTRIBUTE_DISTRIBUTIONS_OUTPUT,
    )
    create_cluster_comparison_map(
        gdf_full,
        kmeans_result.labels.name,
        ward_result.labels.name,
        CLUSTER_COMPARISON_MAP_OUTPUT,
        titles=("K-means (k=6)", "Ward (k=6)"),
    )

    logger.info("Building spatial connectivity matrices for regionalization")
    gdf_connectivity = gdf_full.loc[scaled_df.index]
    queen_weights = Queen.from_dataframe(gdf_connectivity, ids=gdf_connectivity.index)
    queen_connectivity = queen_weights.sparse

    knn_weights = KNN.from_dataframe(
        gdf_connectivity,
        k=4,
        ids=gdf_connectivity.index,
        silence_warnings=True,
    )
    knn_weights.symmetrize()
    knn_connectivity = knn_weights.sparse

    logger.info("Running Ward clustering with Queen contiguity constraint")
    ward_queen_result = run_ward_clustering(
        scaled_df,
        n_clusters=6,
        labels_column="ward6wq",
        connectivity=queen_connectivity,
    )
    ward_queen_profiles = summarise_clusters(cluster_data, ward_queen_result)
    ward_queen_sizes = (
        ward_queen_result.labels.value_counts().sort_index().rename("count")
    )
    gdf_full.loc[ward_queen_result.labels.index, ward_queen_result.labels.name] = (
        ward_queen_result.labels
    )
    gdf_analysis = gdf_full.loc[scaled_df.index]

    render_cluster_summary_table(
        ward_queen_profiles,
        ward_queen_sizes,
        WARD_QUEEN_PROFILES_TABLE_OUTPUT,
        title="Ward + Queen Profiles & Counts",
    )
    create_cluster_sizes_plot(
        ward_queen_sizes,
        WARD_QUEEN_COUNTS_FIGURE_OUTPUT,
        title="Ward + Queen (k=6) Cluster Sizes",
    )
    create_cluster_map(
        gdf_full,
        ward_queen_result.labels.name,
        WARD_QUEEN_MAP_OUTPUT,
        cmap="Set2",
        title="Ward + Queen (k=6)",
    )
    create_attribute_distribution_facets(
        cluster_data,
        ward_queen_result.labels,
        WARD_QUEEN_ATTRIBUTE_DISTRIBUTIONS_OUTPUT,
        palette="Set2",
    )

    logger.info("Running Ward clustering with 4-nearest-neighbor constraint")
    ward_knn_result = run_ward_clustering(
        scaled_df,
        n_clusters=6,
        labels_column="ward6wknn",
        connectivity=knn_connectivity,
    )
    ward_knn_profiles = summarise_clusters(cluster_data, ward_knn_result)
    ward_knn_sizes = ward_knn_result.labels.value_counts().sort_index().rename("count")
    gdf_full.loc[ward_knn_result.labels.index, ward_knn_result.labels.name] = (
        ward_knn_result.labels
    )
    gdf_analysis = gdf_full.loc[scaled_df.index]

    render_cluster_summary_table(
        ward_knn_profiles,
        ward_knn_sizes,
        WARD_KNN_PROFILES_TABLE_OUTPUT,
        title="Ward + 4-NN Profiles & Counts",
    )
    create_cluster_sizes_plot(
        ward_knn_sizes,
        WARD_KNN_COUNTS_FIGURE_OUTPUT,
        title="Ward + 4-NN (k=6) Cluster Sizes",
    )
    create_cluster_map(
        gdf_full,
        ward_knn_result.labels.name,
        WARD_KNN_MAP_OUTPUT,
        cmap="Set3",
        title="Ward + 4-NN (k=6)",
    )
    create_attribute_distribution_facets(
        cluster_data,
        ward_knn_result.labels,
        WARD_KNN_ATTRIBUTE_DISTRIBUTIONS_OUTPUT,
        palette="Set3",
    )

    # Step 7: Evaluate feature coherence and clustering similarity
    logger.info("\nStep 7: Evaluating cluster feature coherence")
    label_sets: dict[str, pd.Series] = {
        kmeans_result.labels.name: kmeans_result.labels,
        ward_result.labels.name: ward_result.labels,
        ward_queen_result.labels.name: ward_queen_result.labels,
        ward_knn_result.labels.name: ward_knn_result.labels,
    }
    for column in ADDITIONAL_CLUSTER_COLUMNS:
        if column in gdf_full.columns and column not in label_sets:
            label_sets[column] = (
                gdf_full.loc[kmeans_result.labels.index, column]
                .astype("int64")
                .rename(column)
            )

    coherence_scores = compute_coherence_scores(scaled_df, label_sets)
    if not coherence_scores.empty:
        coherence_scores.to_csv(CLUSTER_COHERENCE_OUTPUT)
        logger.info(
            "Top coherence scores:\n%s",
            coherence_scores.head().to_string(),
        )
    else:
        logger.warning("No coherence scores computed (no label sets available).")

    logger.info("Evaluating clustering similarity via adjusted mutual information")
    similarity_matrix = compute_similarity_matrix(label_sets)
    if not similarity_matrix.empty:
        similarity_matrix.to_csv(CLUSTER_SIMILARITY_OUTPUT)
    else:
        logger.warning("No similarity scores computed (insufficient label sets).")

    logger.info("\n" + "=" * 50)
    logger.info("Clustering analysis complete!")

    return gdf_full, cluster_data, scaled_df, moran_results, kmeans_result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run clustering analysis pipeline.")
    parser.add_argument(
        "--scatter-matrix",
        action="store_true",
        help="Generate the optional pairwise scatterplot matrix (Step 4).",
    )
    args = parser.parse_args()

    (
        gdf_full,
        cluster_data,
        scaled_data,
        moran_results,
        kmeans_result,
    ) = main(render_scatter_matrix=args.scatter_matrix)
