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
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from esda.moran import Moran
from libpysal.weights import Queen
from sklearn.preprocessing import robust_scale

logger = logging.getLogger(__name__)

# Constants for number formatting
BILLION_THRESHOLD = 1e9
MILLION_THRESHOLD = 1e6
THOUSAND_THRESHOLD = 1e3

# Constants for visualization
MAX_POPULATION_DENSITY_DISPLAY = 100000  # Cap for choropleth map display (people/km²)


def load_clustering_data(
    file_path: str = "output/clustering_data.geojson",
) -> gpd.GeoDataFrame:
    """Load the clustering data prepared by the pipeline."""
    logger.info("Loading clustering data from %s", file_path)

    if not Path(file_path).exists():
        raise FileNotFoundError(
            f"Clustering data not found: {file_path}\n"
            "Please run the clustering pipeline first: python src/housing/scripts/clustering_pipeline.py"
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


def create_choropleth_maps(
    gdf: gpd.GeoDataFrame, variables: list[str], output_path: str | None = None
) -> None:
    """Create choropleth maps for each clustering variable."""
    # Create subplots
    n_vars = len(variables)
    ncols = 3
    nrows = (n_vars + ncols - 1) // ncols

    f, axs = plt.subplots(nrows=nrows, ncols=ncols, figsize=(15, 5 * nrows))
    axs = axs.flatten()

    # Plot each variable
    for i, col in enumerate(variables):
        ax = axs[i]

        # Replace -9999 (no-data marker) with NaN for better visualization
        plot_data = gdf.copy()
        if col in plot_data.columns:
            plot_data[col] = plot_data[col].replace(-9999, np.nan)

            # Cap population density for better map visualization (data analysis uses original values)
            if col == "population_density":
                valid_values = plot_data[col].dropna()
                if len(valid_values) > 0:
                    # Cap at 95th percentile or max display threshold for clear map visualization
                    percentile_95 = valid_values.quantile(0.95)
                    upper_bound = min(percentile_95, MAX_POPULATION_DENSITY_DISPLAY)
                    plot_data[col] = plot_data[col].clip(upper=upper_bound)

        # Plot map
        plot_data.plot(
            column=col,
            ax=ax,
            scheme="Quantiles",
            linewidth=0.1,
            cmap="RdPu",
            legend=True,
            legend_kwds={"loc": "lower left"},
            missing_kwds={"color": "lightgrey", "edgecolor": "none"},
        )

        # Remove axis clutter
        ax.set_axis_off()
        ax.set_title(col, fontsize=10)

    # Hide extra subplots
    for i in range(n_vars, len(axs)):
        axs[i].set_axis_off()

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved choropleth maps to %s", output_path)

    return f


def calculate_morans_i(gdf: gpd.GeoDataFrame, variables: list[str]) -> pd.DataFrame:
    """Calculate Moran's I for spatial autocorrelation."""
    # Create spatial weights matrix using Queen contiguity
    w = Queen.from_dataframe(gdf, use_index=True)

    # Transform weights to row-standardized form
    w.transform = "r"

    # Calculate Moran's I for each variable
    np.random.seed(123456)  # For reproducibility
    mi_results = []

    for variable in variables:
        values = gdf[variable].to_numpy()
        moran = Moran(values, w)
        mi_results.append(
            {"Variable": variable, "Moran's I": moran.I, "P-value": moran.p_sim}
        )

    # Create results dataframe
    results_df = pd.DataFrame(mi_results).set_index("Variable")

    logger.info("Moran's I Results:\n%s", results_df)

    return results_df


def create_correlation_matrix(
    data: pd.DataFrame, output_path: str | None = None
) -> None:
    """Create a pairwise scatterplot matrix to explore correlations."""
    # Create pairplot - each scatterplot panel has independent x and y scales
    fig = sns.pairplot(
        data,
        kind="reg",
        diag_kind="kde",
        plot_kws={
            "scatter_kws": {"alpha": 0.4, "s": 8},
            "line_kws": {"color": "red", "lw": 0.5},
        },
    )

    # Adjust axis labels and ticks for better readability
    def format_number(x: float) -> str:
        """Format numbers compactly for consistent label sizes."""
        abs_x = abs(x)
        if abs_x >= BILLION_THRESHOLD:
            return f"{x / BILLION_THRESHOLD:.1f}B"
        elif abs_x >= MILLION_THRESHOLD:
            return f"{x / MILLION_THRESHOLD:.1f}M"
        elif abs_x >= THOUSAND_THRESHOLD:
            return f"{x / THOUSAND_THRESHOLD:.1f}K"
        elif abs_x >= 1:
            return f"{x:.0f}"
        else:
            return f"{x:.2f}"

    for ax in fig.axes.flatten():
        if ax is not None:
            ax.tick_params(labelsize=5, rotation=45)
            # Use compact number formatting - create formatter outside loop
            try:
                ax.yaxis.set_major_formatter(
                    plt.FuncFormatter(lambda x, p: format_number(x))
                )
                ax.xaxis.set_major_formatter(
                    plt.FuncFormatter(lambda x, p: format_number(x))
                )
            except Exception as e:
                logger.warning("Could not format axis labels: %s", str(e))

    plt.suptitle(
        "Pairwise Relationships Between Clustering Variables", y=1.02, fontsize=14
    )

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved scatterplot matrix to %s", output_path)

    return fig


def standardize_data(data: pd.DataFrame) -> np.ndarray:
    """Standardize data using robust scaling."""
    logger.info("Standardizing data using robust scaling")

    scaled_data = robust_scale(data)

    logger.info("Scaled data shape: %s", scaled_data.shape)
    logger.info("Mean: %.3f, Std: %.3f", scaled_data.mean(), scaled_data.std())

    return scaled_data


def main() -> None:
    """Run the clustering analysis pipeline."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

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
    ]
    variables = [var for var in cluster_variables if var in gdf_full.columns]

    # Step 2: Create choropleth maps (includes all tracts, applies display capping for visualization)
    logger.info("\nStep 2: Creating choropleth maps")
    create_choropleth_maps(
        gdf_full, variables, output_path="output/choropleth_maps.png"
    )

    # Step 3: Select clustering variables and remove tracts with missing data
    logger.info("\nStep 3: Filtering data for statistical analysis")
    variables, cluster_data = select_cluster_variables(gdf_full)

    # Update gdf for analysis
    gdf_analysis = gdf_full.loc[cluster_data.index]

    # Step 4: Calculate Moran's I
    logger.info("\nStep 4: Calculating Moran's I")
    moran_results = calculate_morans_i(gdf_analysis, variables)
    moran_results.to_csv("output/morans_i_results.csv")

    # Step 5: Create correlation matrix
    logger.info("\nStep 5: Creating pairwise scatterplot matrix")
    create_correlation_matrix(cluster_data, output_path="output/scatterplot_matrix.png")

    # Step 6: Standardize data
    logger.info("\nStep 6: Standardizing data")
    scaled_data = standardize_data(cluster_data)

    # Save standardized data
    scaled_df = pd.DataFrame(scaled_data, columns=variables, index=cluster_data.index)
    scaled_df.to_csv("output/clustering_data_scaled.csv")

    logger.info("\n" + "=" * 50)
    logger.info("Clustering data preparation complete!")
    logger.info("Standardized data saved to: output/clustering_data_scaled.csv")

    return gdf_full, cluster_data, scaled_data, moran_results


if __name__ == "__main__":
    gdf_full, cluster_data, scaled_data, moran_results = main()
