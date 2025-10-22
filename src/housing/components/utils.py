"""Utility functions for housing analysis.

This module contains helper functions and utilities used across housing components.
"""

import logging
from pathlib import Path
from typing import Any, Literal

import geopandas as gpd
import matplotlib.axes
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

logger = logging.getLogger(__name__)


def calculate_pairwise_correlations(
    df: pd.DataFrame, pairs: list[tuple[str, str, str]], min_sample_size: int = 10
) -> dict[str, float]:
    """Calculate pairwise correlations between specified column pairs.

    Args:
        df: DataFrame containing the data
        pairs: List of tuples (col1, col2, label) defining correlation pairs
        min_sample_size: Minimum number of samples required for correlation

    Returns:
        Dictionary mapping correlation labels to correlation coefficients
    """
    correlations = {}

    for col1, col2, label in pairs:
        if col1 in df.columns and col2 in df.columns:
            # Filter to rows with both values
            subset = df[[col1, col2]].dropna()
            if len(subset) > min_sample_size:
                corr = subset[col1].corr(subset[col2])
                correlations[label] = corr

    return correlations


def calculate_pairwise_correlation_matrix(
    df: pd.DataFrame, columns: list[str], min_sample_size: int = 10
) -> np.ndarray:
    """Calculate a correlation matrix using pairwise correlations.

    This ensures that each correlation is calculated using the maximum available data
    for that specific pair, rather than dropping rows where any column is missing.

    Args:
        df: DataFrame containing the data
        columns: List of column names to include in correlation matrix
        min_sample_size: Minimum number of samples required for correlation

    Returns:
        Numpy array containing the correlation matrix
    """
    n_cols = len(columns)
    corr_matrix = np.full((n_cols, n_cols), np.nan)

    for i, col1 in enumerate(columns):
        for j, col2 in enumerate(columns):
            if i == j:
                corr_matrix[i, j] = 1.0  # Perfect correlation with itself
            else:
                # Use pairwise logic - only require both columns to have values
                subset = df[[col1, col2]].dropna()
                if len(subset) > min_sample_size:
                    corr_matrix[i, j] = subset[col1].corr(subset[col2])

    return corr_matrix


# =============================================================================
# VISUALIZATION UTILITIES
# =============================================================================


def create_histogram_with_median(
    ax: matplotlib.axes.Axes,
    data: pd.Series,
    title: str,
    xlabel: str,
    ylabel: str,
    color: str = "steelblue",
    bins: int = 30,
    show_median: bool = True,
    median_color: str = "red",
    median_format: str = "${:.0f}",
) -> None:
    """Create a histogram with median line and standard formatting.

    Args:
        ax: Matplotlib axes to plot on
        data: Data series to plot
        title: Plot title
        xlabel: X-axis label
        ylabel: Y-axis label
        color: Histogram color
        bins: Number of bins
        show_median: Whether to show median line
        median_color: Color for median line
        median_format: Format string for median label
    """
    clean_data = data.dropna()

    if len(clean_data) == 0:
        ax.text(
            0.5,
            0.5,
            "No data available",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_title(title)
        return

    # Create histogram
    ax.hist(clean_data, bins=bins, alpha=0.7, color=color, edgecolor="black")

    # Add median line
    if show_median:
        median_val = clean_data.median()
        ax.axvline(
            median_val,
            color=median_color,
            linestyle="--",
            linewidth=2,
            label=f"Median: {median_format.format(median_val)}",
        )
        ax.legend()

    # Set labels and formatting
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(f"{title} (n={len(clean_data)})", fontsize=14)
    ax.grid(True, alpha=0.3)


def create_scatter_with_trend(
    ax: matplotlib.axes.Axes,
    x_data: pd.Series,
    y_data: pd.Series,
    title: str,
    xlabel: str,
    ylabel: str,
    color: str = "purple",
    alpha: float = 0.6,
    size: int = 20,
    show_trend: bool = True,
    trend_color: str = "red",
) -> None:
    """Create a scatter plot with optional trend line.

    Args:
        ax: Matplotlib axes to plot on
        x_data: X-axis data
        y_data: Y-axis data
        title: Plot title
        xlabel: X-axis label
        ylabel: Y-axis label
        color: Scatter point color
        alpha: Scatter point transparency
        size: Scatter point size
        show_trend: Whether to show trend line
        trend_color: Color for trend line
    """
    # Align data by removing NaN values from both series
    aligned_data = pd.DataFrame({"x": x_data, "y": y_data}).dropna()

    if len(aligned_data) == 0:
        ax.text(
            0.5,
            0.5,
            "No data available",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_title(title)
        return

    # Create scatter plot
    ax.scatter(aligned_data["x"], aligned_data["y"], alpha=alpha, color=color, s=size)

    # Add trend line
    if show_trend and len(aligned_data) > 1:
        z = np.polyfit(aligned_data["x"], aligned_data["y"], 1)
        p = np.poly1d(z)
        x_trend = np.linspace(aligned_data["x"].min(), aligned_data["x"].max(), 100)
        ax.plot(x_trend, p(x_trend), color=trend_color, linestyle="--", alpha=0.8)

    # Set labels and formatting
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.grid(True, alpha=0.3)


def create_statistical_summary_text(
    title: str,
    data_sections: list[dict[str, Any]],
    section_separator: str = "=",
    section_separator_length: int = 40,
) -> str:
    """Create formatted statistical summary text.

    Args:
        title: Main title for the summary
        data_sections: List of dictionaries with section data
        section_separator: Character to use for section separators
        section_separator_length: Length of separator line

    Returns:
        Formatted statistical summary text

    Example:
        data_sections = [
            {
                "section_title": "PRICE ANALYSIS",
                "stats": [
                    ("Count", len(data)),
                    ("Mean", f"${data.mean():.2f}"),
                    ("Median", f"${data.median():.2f}"),
                ]
            }
        ]
    """
    lines = [f"{title}\n" + section_separator * section_separator_length + "\n"]

    for section in data_sections:
        lines.append(f"{section['section_title']}:")
        for label, value in section["stats"]:
            lines.append(f"  {label}: {value}")
        lines.append("")  # Empty line between sections

    return "\n".join(lines)


def add_statistical_summary_to_plot(
    ax: matplotlib.axes.Axes,
    title: str,
    data_sections: list[dict[str, Any]],
    fontsize: int = 11,
    bgcolor: str = "lightgray",
    alpha: float = 0.8,
) -> None:
    """Add a statistical summary text box to a plot.

    Args:
        ax: Matplotlib axes to add text to
        title: Title for the summary
        data_sections: List of data sections (see create_statistical_summary_text)
        fontsize: Font size for text
        bgcolor: Background color for text box
        alpha: Transparency for background
    """
    ax.axis("off")

    stats_text = create_statistical_summary_text(title, data_sections)

    ax.text(
        0.05,
        0.95,
        stats_text,
        transform=ax.transAxes,
        fontsize=fontsize,
        verticalalignment="top",
        fontfamily="monospace",
        bbox={"boxstyle": "round,pad=0.8", "facecolor": bgcolor, "alpha": alpha},
    )


def create_correlation_heatmap(
    ax: matplotlib.axes.Axes,
    corr_matrix: np.ndarray,
    labels: list[str],
    title: str = "Correlation Matrix",
    cmap: str = "RdBu_r",
    center: float = 0.0,
    fmt: str = ".3f",
) -> None:
    """Create a correlation heatmap with standard formatting.

    Args:
        ax: Matplotlib axes to plot on
        corr_matrix: Correlation matrix as numpy array
        labels: Labels for matrix rows/columns
        title: Plot title
        cmap: Colormap name
        center: Center value for colormap
        fmt: Number format for annotations
    """
    if np.isnan(corr_matrix).all():
        ax.text(
            0.5,
            0.5,
            "No valid correlations",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_title(title)
        return

    sns.heatmap(
        corr_matrix,
        annot=True,
        fmt=fmt,
        cmap=cmap,
        center=center,
        square=True,
        ax=ax,
        cbar_kws={"shrink": 0.7, "label": "Correlation"},
        vmin=-1,
        vmax=1,
        linewidths=0.5,
        linecolor="white",
    )

    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticklabels(labels, rotation=0)
    ax.set_title(title, fontsize=11, pad=10)


def setup_figure_and_save(
    fig: plt.Figure,
    output_path: Path,
    title: str = None,
    title_y: float = 0.98,
    dpi: int = 300,
    logger: logging.Logger | None = None,
) -> None:
    """Setup figure with title and save to file.

    Args:
        fig: Matplotlib figure
        output_path: Path to save the figure
        title: Figure title (optional)
        title_y: Y position for title (default 0.98)
        dpi: Resolution for saved figure
        logger: Logger instance for logging save message
    """
    if title:
        fig.suptitle(title, fontsize=16, fontweight="bold", y=title_y)

    plt.tight_layout()
    if title:
        plt.subplots_adjust(top=0.85)  # Make space for title

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save figure
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")

    if logger:
        logger.info("Saved visualization to: %s", output_path)

    plt.close(fig)


# =============================================================================
# CHOROPLETH MAP UTILITIES
# =============================================================================

# Minimum land area in square meters to exclude water-only tracts
MIN_LAND_AREA_SQ_METERS = 10000


def prepare_map_data(
    tract_data: pd.DataFrame,
    tract_boundaries: gpd.GeoDataFrame,
    data_columns: list[str],
    city_boundaries: gpd.GeoDataFrame | None = None,
    min_land_area: float = MIN_LAND_AREA_SQ_METERS,
    logger: logging.Logger | None = None,
) -> gpd.GeoDataFrame | None:
    """Prepare map data by merging, filtering, and clipping tract data.

    Args:
        tract_data: DataFrame with tract-level data
        tract_boundaries: GeoDataFrame with tract boundaries
        data_columns: List of columns to include from tract_data
        city_boundaries: Optional city boundaries for clipping
        min_land_area: Minimum land area to filter out water tracts
        logger: Optional logger for logging messages

    Returns:
        Prepared GeoDataFrame ready for mapping, or None if no data
    """
    if tract_data is None or tract_boundaries is None:
        return None

    # Merge tract data with boundaries
    tract_map_data = tract_boundaries.merge(
        tract_data[["tract_geoid"] + data_columns],
        on="tract_geoid",
        how="left",
    )

    # Filter out water-only tracts
    if "ALAND" in tract_map_data.columns:
        initial_count = len(tract_map_data)
        tract_map_data = tract_map_data[tract_map_data["ALAND"] > min_land_area].copy()
        filtered_count = len(tract_map_data)

        if logger and initial_count != filtered_count:
            logger.info("Filtered to %d tracts with land area", filtered_count)

    # Clip to city boundaries if available
    if city_boundaries is not None:
        # Ensure same CRS
        if tract_map_data.crs != city_boundaries.crs:
            city_boundaries = city_boundaries.to_crs(tract_map_data.crs)

        # Clip tracts to city boundary
        tract_map_data = gpd.clip(tract_map_data, city_boundaries)

        if logger:
            logger.info("Clipped tract data to city boundaries")

    return tract_map_data


def create_choropleth_map(
    ax: matplotlib.axes.Axes,
    map_data: gpd.GeoDataFrame,
    column: str,
    title: str,
    legend_label: str,
    cmap: str = "viridis",
    bounds: tuple[float, float, float, float] | None = None,
    show_stats: bool = True,
    stats_format: str = "${:.0f}",
    edge_color: str = "black",
    edge_width: float = 0.1,
    missing_color: str = "lightgrey",
    logger: logging.Logger | None = None,
) -> None:
    """Create a choropleth map with standard formatting.

    Args:
        ax: Matplotlib axes to plot on
        map_data: GeoDataFrame with map data
        column: Column name to use for coloring
        title: Plot title
        legend_label: Label for the colorbar
        cmap: Colormap name
        bounds: Optional bounds tuple (minx, miny, maxx, maxy) for setting plot limits
        show_stats: Whether to show statistics text box
        stats_format: Format string for statistics values
        edge_color: Color for tract boundaries
        edge_width: Width of tract boundaries
        missing_color: Color for tracts with missing data
        logger: Optional logger for logging messages
    """
    if map_data is None or column not in map_data.columns:
        ax.text(
            0.5,
            0.5,
            "No data available",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_title(title)
        return

    # Create choropleth
    map_data.plot(
        column=column,
        ax=ax,
        legend=True,
        cmap=cmap,
        edgecolor=edge_color,
        linewidth=edge_width,
        missing_kwds={"color": missing_color, "label": "No Data"},
        legend_kwds={
            "label": legend_label,
            "orientation": "horizontal",
            "shrink": 0.8,
            "pad": 0.05,
        },
    )

    # Set title and formatting
    data_count = map_data[column].notna().sum()
    ax.set_title(f"{title} (n={data_count})", fontsize=16)
    ax.axis("off")

    # Set bounds if provided
    if bounds is not None:
        ax.set_xlim(bounds[0], bounds[2])
        ax.set_ylim(bounds[1], bounds[3])

    # Add statistics text
    if show_stats:
        data_values = map_data[column].dropna()
        if len(data_values) > 0:
            stats_text = (
                f"Min: {stats_format.format(data_values.min())}\n"
                f"Median: {stats_format.format(data_values.median())}\n"
                f"Max: {stats_format.format(data_values.max())}"
            )
            ax.text(
                0.02,
                0.98,
                stats_text,
                transform=ax.transAxes,
                fontsize=12,
                verticalalignment="top",
                bbox={"boxstyle": "round,pad=0.5", "facecolor": "white", "alpha": 0.8},
            )


def create_dual_choropleth_maps(
    tract_data: pd.DataFrame,
    tract_boundaries: gpd.GeoDataFrame,
    map_configs: list[dict[str, Any]],
    city_boundaries: gpd.GeoDataFrame | None = None,
    figsize: tuple[int, int] = (20, 10),
    title: str = "Dual Choropleth Analysis",
    logger: logging.Logger | None = None,
) -> tuple[plt.Figure, list[matplotlib.axes.Axes]]:
    """Create a figure with two choropleth maps side by side.

    Args:
        tract_data: DataFrame with tract-level data
        tract_boundaries: GeoDataFrame with tract boundaries
        map_configs: List of two configuration dictionaries for each map
        city_boundaries: Optional city boundaries for clipping
        figsize: Figure size tuple
        title: Overall figure title
        logger: Optional logger for logging messages

    Returns:
        Tuple of (figure, axes_list)

    Example:
        map_configs = [
            {
                "column": "price_numeric_mean",
                "title": "Airbnb Price Distribution",
                "legend_label": "Average Airbnb Price ($)",
                "cmap": "viridis",
                "stats_format": "${:.0f}"
            },
            {
                "column": "point_density",
                "title": "Airbnb Units Density",
                "legend_label": "Airbnb Units Density (per km²)",
                "cmap": "Blues",
                "stats_format": "{:.1f} units/km²"
            }
        ]
    """
    # Create figure
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    fig.suptitle(title, fontsize=20, fontweight="bold", y=0.98)

    # Get common bounds for consistent zoom
    if city_boundaries is not None:
        common_bounds = city_boundaries.total_bounds
    else:
        common_bounds = tract_boundaries.total_bounds

    # Create each map
    for i, config in enumerate(map_configs):
        # Prepare data for this map
        data_columns = [config["column"]]
        map_data = prepare_map_data(
            tract_data,
            tract_boundaries,
            data_columns,
            city_boundaries,
            logger=logger,
        )

        # Create the choropleth map
        create_choropleth_map(
            axes[i],
            map_data,
            config["column"],
            config["title"],
            config["legend_label"],
            cmap=config.get("cmap", "viridis"),
            bounds=common_bounds,
            show_stats=config.get("show_stats", True),
            stats_format=config.get("stats_format", "${:.0f}"),
            logger=logger,
        )

    return fig, axes


# =============================================================================
# OUTLIER REMOVAL UTILITIES
# =============================================================================


def remove_density_outliers(
    tract_data: pd.DataFrame,
    density_column: str,
    method: Literal["iqr", "percentile", "zscore", "winsorize"] = "iqr",
    threshold: float = 1.5,
    percentile_threshold: float = 0.99,
    zscore_threshold: float = 3.0,
) -> pd.DataFrame:
    """Remove tracts with extreme density values.

    Args:
        tract_data: Tract-level data with density columns
        density_column: Name of density column to filter on
        method: Outlier detection method
        threshold: IQR multiplier or z-score threshold
        percentile_threshold: Percentile threshold (0.99 = remove top 1%)
        zscore_threshold: Z-score threshold for outlier detection

    Returns:
        Filtered tract data with outliers removed
    """
    if density_column not in tract_data.columns:
        logger.warning(
            "Density column '%s' not found, skipping outlier removal", density_column
        )
        return tract_data

    if method == "iqr":
        q1 = tract_data[density_column].quantile(0.25)
        q3 = tract_data[density_column].quantile(0.75)
        iqr = q3 - q1
        upper_bound = q3 + (threshold * iqr)

    elif method == "percentile":
        upper_bound = tract_data[density_column].quantile(percentile_threshold)

    elif method == "zscore":
        mean_density = tract_data[density_column].mean()
        std_density = tract_data[density_column].std()
        upper_bound = mean_density + (zscore_threshold * std_density)

    elif method == "winsorize":
        upper_bound = tract_data[density_column].quantile(percentile_threshold)
        # For winsorization, we cap values instead of removing them
        filtered = tract_data.copy()
        filtered[density_column] = tract_data[density_column].clip(upper=upper_bound)

        capped_count = (tract_data[density_column] > upper_bound).sum()
        if capped_count > 0:
            logger.info(
                "Winsorized %d tracts with extreme %s (capped at %.2f)",
                capped_count,
                density_column,
                upper_bound,
            )

        return filtered

    else:
        raise ValueError(f"Unknown outlier method: {method}")

    outliers = tract_data[tract_data[density_column] > upper_bound]
    filtered = tract_data[tract_data[density_column] <= upper_bound].copy()

    if len(outliers) > 0:
        logger.info(
            "Removed %d tracts with extreme %s (threshold: %.2f)",
            len(outliers),
            density_column,
            upper_bound,
        )

    return filtered


def remove_multiple_density_outliers(
    tract_data: pd.DataFrame,
    density_columns: list[str],
    method: Literal["iqr", "percentile", "zscore"] = "iqr",
    threshold: float = 1.5,
) -> pd.DataFrame:
    """Remove outliers from multiple density columns.

    Args:
        tract_data: Tract-level data
        density_columns: List of density columns to filter
        method: Outlier detection method
        threshold: Threshold parameter

    Returns:
        Filtered tract data
    """
    filtered_data = tract_data.copy()

    for density_col in density_columns:
        if density_col in filtered_data.columns:
            filtered_data = remove_density_outliers(
                filtered_data, density_col, method=method, threshold=threshold
            )

    return filtered_data
