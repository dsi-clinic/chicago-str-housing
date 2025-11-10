"""Reusable utilities for clustering analysis on tract data."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from numpy.typing import ArrayLike
from scipy import stats
from scipy.sparse import spmatrix
from scipy.spatial.distance import pdist, squareform
from skbio.stats.distance import DistanceMatrix, permanova
from sklearn import metrics
from sklearn.cluster import AgglomerativeClustering, KMeans
from statsmodels.multivariate.manova import MANOVA
from statsmodels.stats.multitest import multipletests

logger = logging.getLogger(__name__)

MIN_K_VALUES = 2


@dataclass(slots=True)
class KMeansClusteringResult:
    """Container for the outputs of a K-means run."""

    labels: pd.Series
    cluster_centers: pd.DataFrame
    inertia: float
    n_iter: int
    model: Any

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
    return summary[["count", *means.columns]]  # ensure count column is first


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


def run_ward_clustering(
    data: pd.DataFrame,
    *,
    n_clusters: int,
    labels_column: str = "ward",
    connectivity: spmatrix | None = None,
) -> KMeansClusteringResult:
    """Fit Ward's hierarchical agglomerative clustering on scaled data."""
    if data.empty:
        msg = "Ward clustering requires at least one observation."
        raise ValueError(msg)

    logger.debug(
        "Running Ward hierarchical clustering with n_clusters=%d on %d observations",
        n_clusters,
        len(data),
    )

    model = AgglomerativeClustering(
        linkage="ward",
        n_clusters=n_clusters,
        connectivity=connectivity,
    )
    labels = model.fit_predict(data)

    result = KMeansClusteringResult(
        labels=pd.Series(labels, index=data.index, name=labels_column, dtype="int64"),
        cluster_centers=pd.DataFrame(),  # Ward does not provide centroids
        inertia=float("nan"),
        n_iter=0,
        model=model,  # type: ignore[arg-type]
    )

    logger.debug("Ward clustering completed for %d clusters", n_clusters)
    return result


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


def build_tidy_cluster_frame(
    features: pd.DataFrame,
    labels: pd.Series,
    *,
    index_name: str | None = None,
) -> pd.DataFrame:
    """Return long-form dataframe for per-cluster univariate analysis."""
    index_name = index_name or features.index.name or "index"
    cluster_name = labels.name or "cluster"

    tidy = (
        features.assign(**{cluster_name: labels})
        .reset_index()
        .rename(columns={features.index.name or "index": index_name})
        .melt(
            id_vars=[index_name, cluster_name],
            var_name="attribute",
            value_name="value",
        )
    )
    return tidy.dropna(subset=["value"])


def kruskal_wallis_by_attribute(
    tidy_frame: pd.DataFrame,
    cluster_column: str,
    *,
    p_adjust: str | None = "fdr_bh",
) -> pd.DataFrame:
    """Run Kruskal-Wallis test for each attribute across clusters."""
    results: list[dict[str, float | str]] = []
    for attribute, group in tidy_frame.groupby("attribute"):
        samples = [
            grp["value"].to_numpy()
            for _, grp in group.groupby(cluster_column)
            if not grp.empty
        ]
        if len(samples) < MIN_K_VALUES:
            continue

        statistic, pvalue = stats.kruskal(*samples, nan_policy="omit")
        results.append(
            {
                "attribute": attribute,
                "statistic": statistic,
                "pvalue": pvalue,
            }
        )

    if not results:
        return pd.DataFrame(columns=["statistic", "pvalue", "pvalue_adj"])

    result_df = pd.DataFrame(results).set_index("attribute")
    if p_adjust and not result_df.empty:
        result_df["pvalue_adj"] = _adjust_pvalues(
            result_df["pvalue"].to_numpy(), method=p_adjust
        )
    else:
        result_df["pvalue_adj"] = result_df["pvalue"]

    return result_df.sort_values("pvalue")


def pairwise_ks_tests(
    tidy_frame: pd.DataFrame,
    cluster_column: str,
    *,
    p_adjust: str | None = "fdr_bh",
) -> pd.DataFrame:
    """Run pairwise Kolmogorov-Smirnov tests for each attribute."""
    rows: list[dict[str, float | str]] = []
    for attribute, group in tidy_frame.groupby("attribute"):
        grouped = group.groupby(cluster_column)
        clusters = sorted(grouped.groups.keys())
        for idx, a in enumerate(clusters):
            for b in clusters[idx + 1 :]:
                sample_a = grouped.get_group(a)["value"].to_numpy()
                sample_b = grouped.get_group(b)["value"].to_numpy()

                if len(sample_a) == 0 or len(sample_b) == 0:
                    continue

                statistic, pvalue = stats.ks_2samp(
                    sample_a,
                    sample_b,
                    alternative="two-sided",
                    mode="auto",
                )
                rows.append(
                    {
                        "attribute": attribute,
                        "cluster_a": a,
                        "cluster_b": b,
                        "statistic": statistic,
                        "pvalue": pvalue,
                    }
                )

    if not rows:
        return pd.DataFrame(
            columns=[
                "attribute",
                "cluster_a",
                "cluster_b",
                "statistic",
                "pvalue",
                "pvalue_adj",
            ]
        )

    result_df = pd.DataFrame(rows)
    if p_adjust:
        result_df["pvalue_adj"] = _adjust_pvalues(
            result_df["pvalue"].to_numpy(), method=p_adjust
        )
    else:
        result_df["pvalue_adj"] = result_df["pvalue"]

    return result_df.sort_values(["attribute", "pvalue"])


def _adjust_pvalues(values: ArrayLike, *, method: str = "fdr_bh") -> pd.Series:
    """Adjust p-values using statsmodels."""
    _, pvals_adj, _, _ = multipletests(values, method=method)
    return pd.Series(pvals_adj)


def run_permanova_test(
    data: pd.DataFrame,
    labels: pd.Series,
    *,
    permutations: int = 999,
) -> pd.Series | None:
    """Perform PERMANOVA to assess multivariate separation among clusters."""
    aligned_labels = labels.loc[data.index].copy()
    aligned_labels.index = aligned_labels.index.astype(str)
    distances = squareform(pdist(data.to_numpy(), metric="euclidean"))
    dm = DistanceMatrix(distances, ids=aligned_labels.index.tolist())

    result = permanova(
        dm, grouping=aligned_labels.astype(str), permutations=permutations
    )
    result_series = pd.Series(result)

    statistic = result_series.get("test statistic")
    if statistic is None:
        statistic = result_series.get("statistic")

    p_value = result_series.get("p-value")
    if p_value is None:
        p_value = result_series.get("p_value")

    permutations_used = result_series.get("permutations", permutations)
    sample_size = result_series.get("sample size", len(aligned_labels))
    num_groups = result_series.get("number of groups", aligned_labels.nunique())

    if statistic is None or p_value is None:
        logger.warning(
            "PERMANOVA result missing statistic or p-value. Raw output: %s",
            result_series.to_dict(),
        )
        return None

    return pd.Series(
        {
            "pseudo_f": statistic,
            "p_value": p_value,
            "permutations": permutations_used,
            "sample_size": sample_size,
            "number_of_groups": num_groups,
        }
    )


def run_manova_test(
    data: pd.DataFrame,
    labels: pd.Series,
) -> pd.Series | None:
    """Perform MANOVA (Wilks' lambda) to assess multivariate centroid differences."""
    manova_frame = data.copy()
    manova_frame = manova_frame.assign(cluster=labels.loc[data.index])
    manova_frame["cluster"] = manova_frame["cluster"].astype("category")

    response_terms = " + ".join([f"Q('{col}')" for col in data.columns])
    formula = f"{response_terms} ~ C(cluster)"

    manova = MANOVA.from_formula(formula, data=manova_frame)
    res = manova.mv_test()

    term_key = next(iter(res.results))
    stats_table = res.results[term_key]["stat"]

    wilks = stats_table.loc["Wilks' lambda"]
    summary = pd.Series(
        {
            "wilks_lambda": wilks["Value"],
            "F_value": wilks["F Value"],
            "num_df": wilks["Num DF"],
            "den_df": wilks["Den DF"],
            "p_value": wilks["Pr > F"],
        }
    )

    return summary


def compute_coherence_scores(
    data: pd.DataFrame,
    label_sets: dict[str, pd.Series],
) -> pd.DataFrame:
    """Calculate Calinski-Harabasz scores for multiple clustering solutions."""
    rows: list[dict[str, float | str]] = []
    for name, labels in label_sets.items():
        if labels.isna().any():
            logger.warning("Skipping %s due to missing labels", name)
            continue
        score = metrics.calinski_harabasz_score(data, labels)
        rows.append({"cluster_type": name, "calinski_harabasz": score})

    if not rows:
        return pd.DataFrame(columns=["calinski_harabasz"], dtype="float64")

    scores = (
        pd.DataFrame(rows)
        .set_index("cluster_type")
        .sort_values("calinski_harabasz", ascending=False)
    )
    return scores


def compute_similarity_matrix(
    label_sets: dict[str, pd.Series],
) -> pd.DataFrame:
    """Compute adjusted mutual information scores between clustering solutions."""
    if not label_sets:
        return pd.DataFrame()

    names = sorted(label_sets.keys())
    matrix = pd.DataFrame(index=names, columns=names, dtype="float64")

    for source, target in product(names, repeat=2):
        matrix.loc[source, target] = metrics.adjusted_mutual_info_score(
            label_sets[source], label_sets[target]
        )

    return matrix
