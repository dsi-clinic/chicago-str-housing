"""STR prohibition density map visualizer.

Creates spatial visualizations showing density patterns of STR prohibitions.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)

# Minimum land area in square meters to exclude water-only tracts
# 10,000 sq meters = ~2.5 acres
MIN_LAND_AREA_SQ_METERS = 10000


class STRDensityMapVisualizer(Visualizer):
    """Create density maps for STR prohibition analysis."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the STR density map visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "str_density_map_visualization",
            "Create density maps for STR prohibition analysis",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create STR prohibition density maps."""
        logger.info("Creating STR prohibition density maps...")

        # Get data from context
        str_data = context.get("str_prohibition_data")
        tract_boundaries = context.get("tract_boundaries")
        str_tract_analysis = context.get("str_tract_analysis")
        tract_rental_data = context.get("tract_rental_data")
        city_boundaries = context.get("city_boundaries")

        if str_data is None or len(str_data) == 0:
            logger.warning("No STR prohibition data available, skipping visualization")
            return {}

        if tract_boundaries is None:
            logger.warning("No tract boundaries available, skipping map visualization")
            return {}

        # Create figure with 2x2 grid
        fig = plt.figure(figsize=(16, 14))
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

        fig.suptitle(
            "Chicago Short-Term Rental Prohibition Density Analysis",
            fontsize=18,
            fontweight="bold",
        )

        # Top row
        # 1. STR Density Choropleth
        ax1 = fig.add_subplot(gs[0, 0])
        self._plot_str_density_choropleth(
            ax1, str_tract_analysis, tract_boundaries, city_boundaries
        )

        # 2. Airbnb Density Choropleth
        ax2 = fig.add_subplot(gs[0, 1])
        self._plot_airbnb_density_choropleth(
            ax2, str_tract_analysis, tract_boundaries, city_boundaries
        )

        # Bottom row
        # 3. Rental Price Choropleth
        ax3 = fig.add_subplot(gs[1, 0])
        self._plot_rental_price_choropleth(
            ax3, tract_rental_data, tract_boundaries, city_boundaries
        )

        # 4. High-density hotspots
        ax4 = fig.add_subplot(gs[1, 1])
        self._plot_hotspots(ax4, str_tract_analysis, tract_boundaries, city_boundaries)

        # Save the plot
        output_path = Path(self.output_dir) / "str_density_maps.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved STR density maps to: %s", output_path)

        plt.close()

        return {"str_density_maps_path": str(output_path)}

    def _plot_str_density_choropleth(
        self,
        ax: Any,  # noqa: ANN401 - matplotlib axes
        tract_analysis: Any,  # noqa: ANN401 - pandas DataFrame
        tract_boundaries: Any,  # noqa: ANN401 - geopandas GeoDataFrame
        city_boundaries: Any | None,  # noqa: ANN401 - geopandas GeoDataFrame
    ) -> None:
        """Plot choropleth of STR prohibition density (per km²)."""
        if (
            tract_analysis is None
            or len(tract_analysis) == 0
            or "str_prohibition_density" not in tract_analysis.columns
        ):
            ax.text(0.5, 0.5, "No STR density data", ha="center", va="center")
            ax.set_title("STR Prohibition Density")
            return

        # Filter out Lake Michigan and water-only tracts
        tract_boundaries_land = tract_boundaries.copy()
        if "ALAND" in tract_boundaries_land.columns:
            tract_boundaries_land = tract_boundaries_land[
                tract_boundaries_land["ALAND"] > MIN_LAND_AREA_SQ_METERS
            ].copy()

        # Merge tract analysis with boundaries
        tracts_merged = tract_boundaries_land.merge(
            tract_analysis[["tract_geoid", "str_prohibition_density"]],
            on="tract_geoid",
            how="left",
        )
        tracts_merged["str_prohibition_density"] = tracts_merged[
            "str_prohibition_density"
        ].fillna(0)

        # Clip to city boundaries if available
        if city_boundaries is not None:
            import geopandas as gpd

            # Ensure same CRS
            if tracts_merged.crs != city_boundaries.crs:
                city_boundaries = city_boundaries.to_crs(tracts_merged.crs)
            # Clip tracts to city boundary
            tracts_merged = gpd.clip(tracts_merged, city_boundaries)

        # Plot
        tracts_merged.plot(
            column="str_prohibition_density",
            ax=ax,
            legend=True,
            cmap="YlOrRd",
            edgecolor="black",
            linewidth=0.2,
            legend_kwds={"label": "Prohibitions/km²", "shrink": 0.8},
            missing_kwds={"color": "lightgrey"},
        )

        ax.set_title("STR Prohibition Density", fontsize=12)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_aspect("equal")

    def _plot_airbnb_density_choropleth(
        self,
        ax: Any,  # noqa: ANN401 - matplotlib axes
        tract_analysis: Any,  # noqa: ANN401 - pandas DataFrame
        tract_boundaries: Any,  # noqa: ANN401 - geopandas GeoDataFrame
        city_boundaries: Any | None,  # noqa: ANN401 - geopandas GeoDataFrame
    ) -> None:
        """Plot choropleth of Airbnb density (per km²)."""
        if (
            tract_analysis is None
            or len(tract_analysis) == 0
            or "airbnb_density" not in tract_analysis.columns
        ):
            ax.text(0.5, 0.5, "No Airbnb density data", ha="center", va="center")
            ax.set_title("Airbnb Density")
            return

        # Filter out Lake Michigan and water-only tracts
        tract_boundaries_land = tract_boundaries.copy()
        if "ALAND" in tract_boundaries_land.columns:
            tract_boundaries_land = tract_boundaries_land[
                tract_boundaries_land["ALAND"] > MIN_LAND_AREA_SQ_METERS
            ].copy()

        # Merge tract analysis with boundaries
        tracts_merged = tract_boundaries_land.merge(
            tract_analysis[["tract_geoid", "airbnb_density"]],
            on="tract_geoid",
            how="left",
        )
        tracts_merged["airbnb_density"] = tracts_merged["airbnb_density"].fillna(0)

        # Clip to city boundaries if available
        if city_boundaries is not None:
            import geopandas as gpd

            # Ensure same CRS
            if tracts_merged.crs != city_boundaries.crs:
                city_boundaries = city_boundaries.to_crs(tracts_merged.crs)
            # Clip tracts to city boundary
            tracts_merged = gpd.clip(tracts_merged, city_boundaries)

        # Plot
        tracts_merged.plot(
            column="airbnb_density",
            ax=ax,
            legend=True,
            cmap="Blues",
            edgecolor="black",
            linewidth=0.2,
            legend_kwds={"label": "Listings/km²", "shrink": 0.8},
            missing_kwds={"color": "lightgrey"},
        )

        ax.set_title("Airbnb Density", fontsize=12)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_aspect("equal")

    def _plot_rental_price_choropleth(
        self,
        ax: Any,  # noqa: ANN401 - matplotlib axes
        tract_rental_data: Any,  # noqa: ANN401 - GeoDataFrame with rental data
        tract_boundaries: Any,  # noqa: ANN401 - geopandas GeoDataFrame
        city_boundaries: Any | None,  # noqa: ANN401 - geopandas GeoDataFrame
    ) -> None:
        """Plot choropleth of average rental prices."""
        if (
            tract_rental_data is None
            or len(tract_rental_data) == 0
            or "avg_rental_price" not in tract_rental_data.columns
        ):
            ax.text(0.5, 0.5, "No rental price data", ha="center", va="center")
            ax.set_title("Rental Prices")
            return

        # Filter out Lake Michigan and water-only tracts
        tract_rental_filtered = tract_rental_data.copy()
        if "ALAND" in tract_rental_filtered.columns:
            tract_rental_filtered = tract_rental_filtered[
                tract_rental_filtered["ALAND"] > MIN_LAND_AREA_SQ_METERS
            ].copy()

        # Clip to city boundaries if available
        if city_boundaries is not None:
            import geopandas as gpd

            # Ensure same CRS
            if tract_rental_filtered.crs != city_boundaries.crs:
                city_boundaries = city_boundaries.to_crs(tract_rental_filtered.crs)
            # Clip tracts to city boundary
            tract_rental_filtered = gpd.clip(tract_rental_filtered, city_boundaries)

        # tract_rental_data is already a GeoDataFrame with geometry, just plot it directly
        # It already has all 801 tracts with interpolated values
        tract_rental_filtered.plot(
            column="avg_rental_price",
            ax=ax,
            legend=True,
            cmap="Greens",
            edgecolor="black",
            linewidth=0.2,
            legend_kwds={"label": "Avg Rent ($)", "shrink": 0.8},
            missing_kwds={"color": "lightgrey"},
        )

        ax.set_title("Average Rental Prices", fontsize=12)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_aspect("equal")

    def _plot_building_sizes(
        self,
        ax: Any,  # noqa: ANN401 - matplotlib axes
        str_data: Any,  # noqa: ANN401 - geopandas GeoDataFrame
        tract_boundaries: Any,  # noqa: ANN401 - geopandas GeoDataFrame
    ) -> None:
        """Plot buildings sized by number of units."""
        # Plot tract boundaries
        tract_boundaries.boundary.plot(ax=ax, linewidth=0.3, color="gray", alpha=0.5)

        # Filter and normalize sizes
        if "number_of_units" in str_data.columns:
            # Create size bins
            sizes = str_data["number_of_units"].to_numpy()
            # Normalize for visualization (sqrt for better visual scaling)
            normalized_sizes = np.sqrt(sizes) * 2

            # Create color map based on size
            colors = sizes
            scatter = ax.scatter(
                str_data.geometry.x,
                str_data.geometry.y,
                s=normalized_sizes,
                c=colors,
                cmap="viridis",
                alpha=0.6,
                edgecolors="black",
                linewidth=0.3,
            )

            plt.colorbar(scatter, ax=ax, label="Units per Building", shrink=0.8)
        else:
            str_data.plot(ax=ax, markersize=5, color="blue", alpha=0.5)

        ax.set_title("Buildings Sized by Unit Count", fontsize=12)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_aspect("equal")

    def _plot_hotspots(
        self,
        ax: Any,  # noqa: ANN401 - matplotlib axes
        tract_analysis: Any,  # noqa: ANN401 - pandas DataFrame
        tract_boundaries: Any,  # noqa: ANN401 - geopandas GeoDataFrame
        city_boundaries: Any | None,  # noqa: ANN401 - geopandas GeoDataFrame
    ) -> None:
        """Highlight high-density hotspots."""
        if (
            tract_analysis is None
            or len(tract_analysis) == 0
            or "str_prohibition_density" not in tract_analysis.columns
        ):
            ax.text(0.5, 0.5, "No hotspot data", ha="center", va="center")
            ax.set_title("High-Density Hotspots")
            return

        # Filter out Lake Michigan and water-only tracts
        tract_boundaries_land = tract_boundaries.copy()
        if "ALAND" in tract_boundaries_land.columns:
            tract_boundaries_land = tract_boundaries_land[
                tract_boundaries_land["ALAND"] > MIN_LAND_AREA_SQ_METERS
            ].copy()

        # Merge with boundaries
        tracts_merged = tract_boundaries_land.merge(
            tract_analysis[["tract_geoid", "str_prohibition_density"]],
            on="tract_geoid",
            how="left",
        )
        tracts_merged["str_prohibition_density"] = tracts_merged[
            "str_prohibition_density"
        ].fillna(0)

        # Clip to city boundaries if available
        if city_boundaries is not None:
            import geopandas as gpd

            # Ensure same CRS
            if tracts_merged.crs != city_boundaries.crs:
                city_boundaries = city_boundaries.to_crs(tracts_merged.crs)
            # Clip tracts to city boundary
            tracts_merged = gpd.clip(tracts_merged, city_boundaries)

        # Define hotspots (>90th percentile)
        threshold = tracts_merged["str_prohibition_density"].quantile(0.90)

        tracts_merged["is_hotspot"] = (
            tracts_merged["str_prohibition_density"] > threshold
        )

        # Plot all tracts in light gray
        tracts_merged.plot(
            ax=ax, color="white", edgecolor="gray", linewidth=0.3, alpha=0.5
        )

        # Highlight hotspots with a clear diverging colormap
        hotspots = tracts_merged[tracts_merged["is_hotspot"]]
        if len(hotspots) > 0:
            hotspots.plot(
                ax=ax,
                column="str_prohibition_density",
                cmap="RdYlBu_r",  # Red (high) to Blue (low) - reversed so red is high
                edgecolor="black",
                linewidth=0.5,
                legend=True,
                legend_kwds={"label": "Prohibitions/km²", "shrink": 0.8},
            )

        ax.set_title("High-Density Hotspots (>90th percentile)", fontsize=12)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_aspect("equal")
