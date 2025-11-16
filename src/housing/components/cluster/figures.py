"""Figure generation helpers for clustering analysis outputs."""

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.colors import ListedColormap, to_rgb
from sklearn.cluster import KMeans

logger = logging.getLogger(__name__)

MIN_K_VALUES = 2
MAX_DISPLAY_ABS_VALUE = 1_000
SMALL_VALUE_THRESHOLD = 1e-3
HEADER_LUMINANCE_THRESHOLD = 0.6

CLUSTER_COLORS = [
    "#4E79A7",
    "#F28E2B",
    "#E15759",
    "#76B7B2",
    "#59A14F",
    "#EDC948",
    "#B07AA1",
    "#FF9DA7",
    "#9C755F",
    "#BAB0AC",
]


def create_cluster_map(
    gdf: gpd.GeoDataFrame,
    cluster_column: str,
    output_path: Path,
    *,
    figsize: tuple[float, float] = (9, 9),
    cmap: ListedColormap | str = "tab20",
    title: str | None = None,
    categories: list | None = None,
) -> None:
    """Generate and save a categorical choropleth of cluster assignments."""
    fig, ax = plt.subplots(1, figsize=figsize)
    plotted_gdf = gdf.copy()
    if categories is not None:
        plotted_gdf[cluster_column] = pd.Categorical(
            plotted_gdf[cluster_column], categories=categories, ordered=True
        )
    unique_clusters = sorted(plotted_gdf[cluster_column].dropna().unique())
    color_lookup = {
        cluster: CLUSTER_COLORS[idx % len(CLUSTER_COLORS)]
        for idx, cluster in enumerate(unique_clusters)
    }
    plotted_gdf["__color__"] = plotted_gdf[cluster_column].map(color_lookup)
    plotted_gdf.plot(color=plotted_gdf["__color__"], linewidth=0, ax=ax)

    handles = [
        plt.Rectangle((0, 0), 1, 1, color=color_lookup[cluster])
        for cluster in unique_clusters
    ]
    ax.legend(handles, [str(cluster) for cluster in unique_clusters], title="Cluster")
    ax.set_axis_off()
    if title:
        ax.set_title(title)
    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def create_cluster_comparison_map(
    gdf: gpd.GeoDataFrame,
    first_column: str,
    second_column: str,
    output_path: Path,
    *,
    titles: tuple[str, str] = ("K-means", "Ward"),
    cmap_first: ListedColormap | str | None = None,
    cmap_second: ListedColormap | str = "Set2",
    categories_first: list | None = None,
    categories_second: list | None = None,
) -> None:
    """Render a side-by-side comparison map of two clustering solutions."""
    fig, axs = plt.subplots(1, 2, figsize=(14, 6))

    plotted_gdf = gdf.copy()
    if cmap_first is None:
        cmap_first = ListedColormap(CLUSTER_COLORS)
    if isinstance(cmap_first, list):
        cmap_first = ListedColormap(cmap_first)
    if isinstance(cmap_second, list):
        cmap_second = ListedColormap(cmap_second)

    if categories_first is not None:
        plotted_gdf[first_column] = pd.Categorical(
            plotted_gdf[first_column], categories=categories_first, ordered=True
        )
    if categories_second is not None:
        plotted_gdf[second_column] = pd.Categorical(
            plotted_gdf[second_column], categories=categories_second, ordered=True
        )

    plotted_gdf.plot(
        column=first_column,
        categorical=True,
        legend=True,
        linewidth=0,
        ax=axs[0],
        cmap=cmap_first,
    )
    axs[0].set_axis_off()
    axs[0].set_title(titles[0])

    plotted_gdf.plot(
        column=second_column,
        categorical=True,
        legend=True,
        linewidth=0,
        ax=axs[1],
        cmap=cmap_second,
    )
    axs[1].set_axis_off()
    axs[1].set_title(titles[1])

    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def create_kmeans_elbow_plot(
    data: pd.DataFrame,
    *,
    k_range: range,
    random_state: int | None,
    output_path: Path,
) -> pd.DataFrame:
    """Generate an elbow plot for K-means and return inertia scores."""
    if len(k_range) < MIN_K_VALUES:
        msg = "Elbow plot requires at least two k values."
        raise ValueError(msg)

    inertias: list[float] = []
    for k in k_range:
        model = KMeans(
            n_clusters=k,
            random_state=random_state,
            n_init=10,
        )
        model.fit(data)
        inertias.append(float(model.inertia_))

    scores = pd.DataFrame({"k": list(k_range), "inertia": inertias}).set_index("k")

    plt.figure(figsize=(8, 5))
    plt.plot(scores.index, scores["inertia"], marker="o")
    plt.title("K-means Elbow Plot")
    plt.xlabel("Number of clusters (k)")
    plt.ylabel("Inertia (within-cluster sum of squares)")
    plt.xticks(list(k_range))
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    return scores


def dataframe_to_table_png(
    df: pd.DataFrame,
    output_path: Path,
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (10, 2.5),
    font_size: int = 10,
    col_width: float | None = None,
) -> None:
    """Render a DataFrame as a PNG table using Matplotlib."""
    if df.empty:
        logger.warning("DataFrame is empty; skipping table PNG for %s", output_path)
        return

    output_path = output_path.with_suffix(".png")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    def _fmt(val: object) -> str:
        if pd.isna(val):
            return ""
        if isinstance(val, str):
            return val
        if abs(val) > MAX_DISPLAY_ABS_VALUE:
            return f"{val:,.0f}"
        if abs(val) < SMALL_VALUE_THRESHOLD and val != 0:
            return f"{val:.2e}"
        return f"{val:.3f}"

    formatted_df = df.apply(lambda col: col.map(_fmt))
    formatted_df.index = formatted_df.index.astype(str)

    dynamic_width = max(figsize[0], 1.8 * len(formatted_df.columns) + 4)
    dynamic_height = max(figsize[1], 1.2 * len(formatted_df.index) + 1.5)
    fig, ax = plt.subplots(figsize=(dynamic_width, dynamic_height))
    ax.axis("off")

    if col_width is None:
        col_width = max(0.8, figsize[0] / max(len(formatted_df.columns), 1))

    table = ax.table(
        cellText=formatted_df.to_numpy(),
        rowLabels=formatted_df.index,
        colLabels=formatted_df.columns,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(font_size)
    table.scale(col_width / 1.0, 1.2)

    if title:
        ax.set_title(title, pad=10)

    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def render_cluster_summary_table(
    profiles: pd.DataFrame,
    sizes: pd.Series,
    output_path: Path,
    *,
    title: str | None = None,
    column_colors: dict[str, str] | None = None,
) -> None:
    """Render cluster profiles and sizes into a single table PNG."""
    if profiles.empty:
        logger.warning("Cluster profiles empty; skipping summary table.")
        return

    output_path = output_path.with_suffix(".png")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    profile_matrix = profiles.astype(float).T

    def _fmt(val: float) -> str:
        if pd.isna(val):
            return ""
        if abs(val) > MAX_DISPLAY_ABS_VALUE:
            return f"{val:,.0f}"
        if abs(val) < SMALL_VALUE_THRESHOLD and val != 0:
            return f"{val:.2e}"
        return f"{val:.3f}"

    formatted_profiles = profile_matrix.apply(lambda col: col.map(_fmt))

    fig_height = max(3.0, 0.4 * len(formatted_profiles.index) + 1.5)
    fig_width = max(12.0, 1.8 * len(formatted_profiles.columns) + 4)
    fig, ax_table = plt.subplots(figsize=(fig_width, fig_height))
    ax_table.axis("off")
    table = ax_table.table(
        cellText=formatted_profiles.values,
        rowLabels=formatted_profiles.index,
        colLabels=formatted_profiles.columns.astype(str),
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.2)

    if column_colors:
        for idx, col_name in enumerate(formatted_profiles.columns.astype(str)):
            color = column_colors.get(col_name)
            if color:
                header_cell = table[(0, idx + 1)]
                header_cell.set_facecolor(color)
                r, g, b = to_rgb(color)
                luminance = 0.299 * r + 0.587 * g + 0.114 * b
                text_color = (
                    "black" if luminance > HEADER_LUMINANCE_THRESHOLD else "white"
                )
                header_cell.get_text().set_color(text_color)

    if title:
        ax_table.set_title(title, pad=10)

    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def create_attribute_distribution_facets(
    cluster_data: pd.DataFrame,
    labels: pd.Series,
    output_path: Path,
    *,
    palette: str | list[str] | None = None,
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

    if palette is None:
        unique_clusters = sorted(labels.dropna().unique())
        palette = {
            cluster: CLUSTER_COLORS[idx % len(CLUSTER_COLORS)]
            for idx, cluster in enumerate(unique_clusters)
        }

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


def create_cluster_sizes_plot(
    sizes: pd.Series,
    output_path: Path,
    *,
    figsize: tuple[float, float] = (8, 5),
    title: str = "Cluster Sizes",
) -> None:
    """Create a bar chart showing the size of each cluster."""
    if sizes.empty:
        logger.warning("No size data provided for plotting; skipping bar chart.")
        return

    formatted_df = sizes.reset_index()
    formatted_df.columns = ["cluster", "count"]
    formatted_df["cluster"] = pd.Categorical(
        [f"Cluster {int(c)}" for c in formatted_df["cluster"]],
        ordered=True,
    )

    sns.set_theme(style="whitegrid", font_scale=1.0)
    plt.figure(figsize=figsize)
    ax = sns.barplot(
        data=formatted_df,
        x="cluster",
        y="count",
        hue="cluster",
        palette=CLUSTER_COLORS[: len(formatted_df)],
        legend=False,
    )

    for idx, count in enumerate(formatted_df["count"].values):
        ax.text(
            idx,
            count,
            f"{int(count)}",
            ha="center",
            va="bottom",
            fontweight="bold",
        )

    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
