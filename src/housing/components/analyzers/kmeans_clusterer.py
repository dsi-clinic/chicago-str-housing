"""Reusable utilities for running K-means clustering on tract data.

The functions in this module separate clustering logic from analysis scripts so
that multiple pipelines can share the same implementation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class KMeansClusteringResult:
    """Container for the outputs of a K-means run."""

    labels: pd.Series
    cluster_centers: pd.DataFrame
    inertia: float
    n_iter: int
    model: KMeans

    def save_labels(self, output_path: Path) -> None:
        """Persist cluster labels to disk."""
        logger.info("Saving K-means labels to %s", output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.labels.to_frame(name=self.labels.name).to_csv(output_path)

    def save_cluster_centers(self, output_path: Path) -> None:
        """Persist cluster centroids to disk."""
        logger.info("Saving K-means cluster centers to %s", output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.cluster_centers.to_csv(output_path, index=True)


def summarise_clusters(
    features: pd.DataFrame, result: KMeansClusteringResult
) -> pd.DataFrame:
    """Compute simple profiles (count and mean) for each cluster."""
    labelled = features.copy()
    label_col = result.labels.name
    labelled[label_col] = result.labels

    grouped = labelled.groupby(label_col, sort=True, observed=True)
    means = grouped.mean(numeric_only=True)
    counts = grouped.size().rename("count")

    summary = means.assign(count=counts)
    return summary[
        ["count", *means.columns]
    ]  # ensure count column is first


def fit_kmeans(
    data: pd.DataFrame,
    *,
    n_clusters: int,
    random_state: int | None,
    labels_column: str,
    max_iter: int = 300,
    n_init: int = 10,
) -> KMeansClusteringResult:
    """Run the K-means algorithm on a scaled feature matrix."""
    if data.empty:
        msg = "K-means fitting requires at least one observation."
        raise ValueError(msg)

    if data.isna().any().any():
        msg = "K-means input data must not contain missing values."
        raise ValueError(msg)

    logger.debug(
        "Running K-means with n_clusters=%d on %d observations and %d variables",
        n_clusters,
        len(data),
        data.shape[1],
    )

    model = KMeans(
        n_clusters=n_clusters,
        random_state=random_state,
        max_iter=max_iter,
        n_init=n_init,
    )
    model.fit(data)

    labels = pd.Series(
        model.labels_,
        index=data.index,
        name=labels_column,
        dtype="int64",
    )
    cluster_centers = pd.DataFrame(
        model.cluster_centers_,
        columns=data.columns,
    )
    cluster_centers.index.name = labels_column

    logger.debug(
        "K-means converged in %d iterations with inertia %.2f",
        model.n_iter_,
        model.inertia_,
    )

    return KMeansClusteringResult(
        labels=labels,
        cluster_centers=cluster_centers,
        inertia=float(model.inertia_),
        n_iter=int(model.n_iter_),
        model=model,
    )


def prepare_cluster_analysis_data(
    gdf_full: gpd.GeoDataFrame,
    variables: list[str],
    scaled_data_path: Path,
) -> tuple[pd.DataFrame, gpd.GeoDataFrame, pd.DataFrame]:
    """Prepare aligned datasets for clustering analysis steps.

    Args:
        gdf_full: GeoDataFrame containing all census tracts.
        variables: Ordered list of clustering variables to extract.
        scaled_data_path: Path to the standardized CSV produced by the pipeline.

    Returns:
        Tuple of (cluster_data, gdf_analysis, scaled_df) where:
            - cluster_data is the unscaled data aligned to the scaled index
            - gdf_analysis is the GeoDataFrame subset used for spatial stats
            - scaled_df is the standardized feature matrix loaded from disk
    """
    if not scaled_data_path.exists():
        msg = (
            f"Standardized data not found: {scaled_data_path}\n"
            "Please run the clustering pipeline first: make run-clustering-pipeline"
        )
        raise FileNotFoundError(msg)

    logger.debug("Loading standardized clustering data from %s", scaled_data_path)
    scaled_df = pd.read_csv(scaled_data_path, index_col=0)

    logger.debug("Scaled dataset shape: %s", scaled_df.shape)

    # Ensure the requested variables are present in the GeoDataFrame
    missing_vars = [var for var in variables if var not in gdf_full.columns]
    if missing_vars:
        msg = f"Variables missing from GeoDataFrame: {missing_vars}"
        raise KeyError(msg)

    # Align the GeoDataFrame and raw variables with the standardized index
    cluster_data = gdf_full.loc[scaled_df.index, variables].copy()
    gdf_analysis = gdf_full.loc[scaled_df.index].copy()

    logger.debug(
        "Prepared clustering analysis datasets with %d tracts and %d variables",
        len(cluster_data),
        len(variables),
    )

    return cluster_data, gdf_analysis, scaled_df


def run_kmeans_workflow(
    cluster_data: pd.DataFrame,
    scaled_df: pd.DataFrame,
    *,
    n_clusters: int,
    random_state: int | None,
    labels_column: str,
) -> tuple[
    KMeansClusteringResult,
    pd.DataFrame,
    pd.Series,
]:
    """Execute the K-means fitting and summarisation workflow."""
    result = fit_kmeans(
        scaled_df,
        n_clusters=n_clusters,
        random_state=random_state,
        labels_column=labels_column,
    )
    profiles = summarise_clusters(cluster_data, result)
    sizes = result.labels.value_counts().sort_index().rename("count")

    logger.debug(
        "Created %d clusters with label column '%s'",
        n_clusters,
        labels_column,
    )
    logger.debug("Cluster sizes:\n%s", sizes.to_string())

    return result, profiles, sizes


def save_kmeans_outputs(
    result: KMeansClusteringResult,
    profiles: pd.DataFrame,
    sizes: pd.Series,
    *,
    labels_path: Path,
    centers_path: Path,
    profiles_path: Path,
    sizes_path: Path,
) -> None:
    """Persist standard K-means outputs to disk."""
    result.save_labels(labels_path)
    result.save_cluster_centers(centers_path)
    profiles.to_csv(profiles_path)
    sizes.to_frame().to_csv(sizes_path)


def attach_cluster_labels(
    gdf_full: gpd.GeoDataFrame,
    scaled_df: pd.DataFrame,
    result: KMeansClusteringResult,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Apply cluster labels to GeoDataFrames and return aligned copies."""
    labelled_full = gdf_full.copy()
    labelled_full[result.labels.name] = result.labels.reindex(labelled_full.index)
    labelled_analysis = labelled_full.loc[scaled_df.index].copy()
    return labelled_full, labelled_analysis


def create_cluster_map(
    gdf: gpd.GeoDataFrame,
    cluster_column: str,
    output_path: Path,
    *,
    figsize: tuple[float, float] = (9, 9),
    cmap: str = "tab20",
) -> None:
    """Generate and save a categorical choropleth of cluster assignments."""
    fig, ax = plt.subplots(1, figsize=figsize)
    gdf.plot(
        column=cluster_column,
        categorical=True,
        legend=True,
        linewidth=0,
        ax=ax,
        cmap=cmap,
    )
    ax.set_axis_off()
    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def create_attribute_distribution_facets(
    cluster_data: pd.DataFrame,
    labels: pd.Series,
    output_path: Path,
    *,
    palette: str = "tab20",
    col_wrap: int = 3,
    height: float = 4,
    font_scale: float = 1.1,
) -> None:
    """Create KDE distribution plots for each attribute colored by cluster."""
    tidy_df = cluster_data.copy()
    label_name = labels.name or "cluster"
    tidy_df[label_name] = labels
    tidy_df = tidy_df.reset_index(drop=True)
    tidy_df = tidy_df.melt(
        id_vars=label_name, var_name="Attribute", value_name="Values"
    )

    sns.set_theme(style="whitegrid", font_scale=font_scale)
    facets = sns.FacetGrid(
        data=tidy_df,
        col="Attribute",
        hue=label_name,
        sharex=False,
        sharey=False,
        aspect=1.5,
        col_wrap=col_wrap,
        height=height,
        palette=palette,
    )
    facets.map(
        sns.kdeplot,
        "Values",
        fill=True,
        common_norm=False,
        warn_singular=False,
    )
    facets.add_legend(title="Cluster")
    facets.set_titles(col_template="{col_name}")

    facets.figure.tight_layout()
    facets.figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(facets.figure)


def create_cluster_profiles_table(
    profiles: pd.DataFrame,
    output_path: Path,
    *,
    float_format: str = "{:.2f}",
) -> None:
    """Write cluster profiles to a text file in a readable table layout."""
    if profiles.empty:
        logger.warning("No profiles provided for tabulation; skipping output.")
        return

    profiles_to_print = profiles.copy()
    numeric_cols = profiles_to_print.select_dtypes(include="number").columns
    profiles_to_print = profiles_to_print.astype(
        dict.fromkeys(numeric_cols, str)
    )
    for col in numeric_cols:
        profiles_to_print[col] = profiles_to_print[col].map(
            lambda x: float_format.format(float(x))
        )

    table_lines = profiles_to_print.to_string().splitlines()
    formatted = "\n".join(table_lines)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(formatted, encoding="utf-8")


def create_cluster_sizes_plot(
    sizes: pd.Series,
    output_path: Path,
    *,
    figsize: tuple[float, float] = (8, 5),
) -> None:
    """Create a bar chart showing the size of each cluster."""
    if sizes.empty:
        logger.warning("No size data provided for plotting; skipping bar chart.")
        return

    data = sizes.reset_index()
    data.columns = ["cluster", "count"]
    data["cluster_label"] = data["cluster"].apply(lambda c: f"Cluster {c}")

    sns.set_theme(style="whitegrid", font_scale=1.0)
    plt.figure(figsize=figsize)
    ax = sns.barplot(
        data=data,
        x="cluster_label",
        y="count",
        hue="cluster_label",
        palette="tab20",
        legend=False,
    )
    ax.set_xlabel("Cluster")
    ax.set_ylabel("Number of Tracts")

    # Annotate bars with counts
    for idx, count in enumerate(data["count"].values):
        ax.text(
            idx,
            count,
            f"{int(count)}",
            ha="center",
            va="bottom",
            fontweight="bold",
        )

    plt.title("K-means Cluster Sizes")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
