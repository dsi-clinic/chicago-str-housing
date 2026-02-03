"""Time series STR map visualizer.

This module creates time series maps showing STR prohibition distributions
at census tract level.
"""

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap, LogNorm, hsv_to_rgb, rgb_to_hsv

from housing.components.utils import prepare_map_data
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class TimeSeriesSTRMapVisualizer(Visualizer):
    """Create time series maps for STR prohibitions.

    Shows STR prohibition data as time series maps at census tract level.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the time series STR map visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "time_series_str_map_visualization",
            "Create time series maps for STR prohibitions",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create time series STR map visualizations."""
        logger.info("Creating time series STR map visualizations...")

        tract_data = context.get("str_tract_data")
        tract_boundaries = context.get("tract_boundaries")
        city_boundaries = context.get("city_boundaries")
        airbnb_tract_data = context.get("airbnb_tract_data")

        # Log initial tract counts for debugging
        logger.info("=" * 70)
        logger.info("TRACT COUNT DEBUGGING")
        logger.info("=" * 70)
        if tract_boundaries is not None:
            logger.info("Initial tract_boundaries count: %d", len(tract_boundaries))
        if tract_data is not None:
            logger.info("Initial str_tract_data count: %d", len(tract_data))
            if "tract_geoid" in tract_data.columns:
                logger.info(
                    "  - str_tract_data with non-null tract_geoid: %d",
                    tract_data["tract_geoid"].notna().sum(),
                )
        if airbnb_tract_data is not None:
            logger.info("airbnb_tract_data count: %d", len(airbnb_tract_data))
            if "tract_geoid" in airbnb_tract_data.columns:
                logger.info(
                    "  - airbnb_tract_data with non-null tract_geoid: %d",
                    airbnb_tract_data["tract_geoid"].notna().sum(),
                )
                logger.info(
                    "  - Unique tract_geoids in airbnb_tract_data: %d",
                    airbnb_tract_data["tract_geoid"].nunique(),
                )

        if tract_data is None:
            logger.warning("No STR tract data available for mapping")
            return {}

        if tract_boundaries is None:
            logger.warning("No tract boundaries available, skipping map visualization")
            return {}

        # Filter tract boundaries to only include tracts within Chicago
        # First try using airbnb_tract_data (if available from other pipelines)
        # Otherwise use city_boundaries with centroid-based filtering
        if airbnb_tract_data is not None and "tract_geoid" in airbnb_tract_data.columns:
            # Get the tract_geoid values from airbnb_tract_data
            valid_tract_geoids = set(airbnb_tract_data["tract_geoid"].dropna().unique())

            # Filter tract_boundaries to only those tracts
            if "tract_geoid" in tract_boundaries.columns:
                initial_count = len(tract_boundaries)
                tract_boundaries = tract_boundaries[
                    tract_boundaries["tract_geoid"].isin(valid_tract_geoids)
                ].copy()
                logger.info(
                    "Filtered to tracts from airbnb_tract_data: %d tracts remaining (from %d)",
                    len(tract_boundaries),
                    initial_count,
                )
            else:
                logger.warning(
                    "tract_boundaries does not have tract_geoid column, cannot filter"
                )
        elif city_boundaries is not None:
            # Use centroid-based filtering to Chicago boundaries (for DiD pipeline)
            try:
                # Ensure same CRS
                if tract_boundaries.crs != city_boundaries.crs:
                    city_boundaries_filter = city_boundaries.to_crs(
                        tract_boundaries.crs
                    )
                else:
                    city_boundaries_filter = city_boundaries

                # Calculate centroids (use projected CRS for accuracy)
                tract_boundaries_projected = tract_boundaries.to_crs("EPSG:32616")
                centroids = tract_boundaries_projected.geometry.centroid.to_crs(
                    tract_boundaries.crs
                )

                # Create temporary GeoDataFrame with centroids for spatial join
                centroids_gdf = gpd.GeoDataFrame(
                    geometry=centroids,
                    index=tract_boundaries.index,
                    crs=tract_boundaries.crs,
                )

                # Spatial join to find which centroids are within Chicago
                tracts_within = gpd.sjoin(
                    centroids_gdf,
                    city_boundaries_filter,
                    how="inner",
                    predicate="within",
                )

                # Filter tract boundaries to only those whose centroids are within Chicago
                tract_boundaries = tract_boundaries.loc[tracts_within.index].copy()

                logger.info(
                    "Filtered to tracts with centroids within Chicago: %d tracts remaining",
                    len(tract_boundaries),
                )
            except Exception as e:
                logger.warning("Could not filter to Chicago boundaries: %s", e)

        # Prepare data for visualization
        tract_data = tract_data.copy()

        # Extract first year from prohibition date
        # Check for different possible column names
        date_column = None
        for col in [
            "first_prohibition_date",
            "prohibition_date_min",
            "prohibition_date",
        ]:
            if col in tract_data.columns:
                date_column = col
                break

        if date_column is None:
            logger.warning("No prohibition date column found in tract data")
            return {}

        # Extract year from the date column
        tract_data["first_prohibition_year"] = pd.to_datetime(
            tract_data[date_column], errors="coerce"
        ).dt.year

        # Get count column (check for different possible names)
        count_column = None
        for col in [
            "str_prohibition_count",
            "building_count",
            "str_prohibition_building_count",
        ]:
            if col in tract_data.columns:
                count_column = col
                break

        if count_column is None:
            logger.warning("No STR restriction count column found in tract data")
            return {}

        # Filter tract_data to only include tracts that are in airbnb_tract_data
        # This ensures we only use the same tracts as the airbnb visualizer
        if airbnb_tract_data is not None and "tract_geoid" in airbnb_tract_data.columns:
            valid_tract_geoids = set(airbnb_tract_data["tract_geoid"].dropna().unique())
            if "tract_geoid" in tract_data.columns:
                initial_tract_count = len(tract_data)
                tract_data = tract_data[
                    tract_data["tract_geoid"].isin(valid_tract_geoids)
                ].copy()
                logger.info(
                    "Filtered tract_data to airbnb_tract_data tracts: %d tracts remaining (from %d)",
                    len(tract_data),
                    initial_tract_count,
                )

        # Filter out O'Hare airport tracts before preparing map data
        OHARE_TRACT_IDS = ["17031980000", "17031760801", "17031760802", "17031760803"]
        if "tract_geoid" in tract_boundaries.columns:
            initial_tract_count = len(tract_boundaries)
            tract_boundaries = tract_boundaries[
                ~tract_boundaries["tract_geoid"].isin(OHARE_TRACT_IDS)
            ].copy()
            logger.info(
                "Filtered out O'Hare airport tracts: %d tracts remaining (from %d)",
                len(tract_boundaries),
                initial_tract_count,
            )
        if "tract_geoid" in tract_data.columns:
            initial_data_count = len(tract_data)
            tract_data = tract_data[
                ~tract_data["tract_geoid"].isin(OHARE_TRACT_IDS)
            ].copy()
            logger.info(
                "Filtered O'Hare tracts from tract_data: %d tracts remaining (from %d)",
                len(tract_data),
                initial_data_count,
            )

        # Prepare map data
        year_map_data = prepare_map_data(
            tract_data,
            tract_boundaries,
            ["first_prohibition_year"],
            city_boundaries,
            logger=logger,
        )
        count_map_data = prepare_map_data(
            tract_data,
            tract_boundaries,
            [count_column],
            city_boundaries,
            logger=logger,
        )

        if year_map_data is None or count_map_data is None:
            logger.warning("Failed to prepare map data")
            return {}

        # Log tract counts after prepare_map_data
        logger.info("-" * 70)
        logger.info("After prepare_map_data:")
        logger.info("  year_map_data total tracts: %d", len(year_map_data))
        logger.info(
            "  year_map_data with data (non-null): %d",
            year_map_data["first_prohibition_year"].notna().sum(),
        )
        logger.info(
            "  year_map_data with null/NA: %d",
            year_map_data["first_prohibition_year"].isna().sum(),
        )
        logger.info("  count_map_data total tracts: %d", len(count_map_data))
        logger.info(
            "  count_map_data with data (non-null): %d",
            count_map_data[count_column].notna().sum(),
        )
        logger.info(
            "  count_map_data with null/NA: %d",
            count_map_data[count_column].isna().sum(),
        )
        logger.info(
            "  count_map_data with zero: %d", (count_map_data[count_column] == 0).sum()
        )
        logger.info(
            "  count_map_data with non-zero: %d",
            (count_map_data[count_column] > 0).sum(),
        )

        # Log bounds
        if len(year_map_data) > 0:
            logger.info("  year_map_data bounds: %s", year_map_data.total_bounds)
        if len(count_map_data) > 0:
            logger.info("  count_map_data bounds: %s", count_map_data.total_bounds)

        # Get common bounds from tracts that have data, but keep all tracts for plotting
        # Filter to only tracts with data for bounds calculation
        year_map_data_with_data = year_map_data[
            year_map_data["first_prohibition_year"].notna()
        ]
        count_map_data_with_data = count_map_data[count_map_data[count_column].notna()]

        logger.info("-" * 70)
        logger.info("Tract counts for bounds calculation:")
        logger.info(
            "  year_map_data: %d total, %d with data",
            len(year_map_data),
            len(year_map_data_with_data),
        )
        logger.info(
            "  count_map_data: %d total, %d with data",
            len(count_map_data),
            len(count_map_data_with_data),
        )

        # Calculate bounds from tracts with data (to limit view), but keep all tracts for plotting
        if len(year_map_data_with_data) > 0 and len(count_map_data_with_data) > 0:
            # Get union of tract_geoids from both datasets that have data
            all_tract_geoids = set(
                year_map_data_with_data["tract_geoid"].unique()
            ) | set(count_map_data_with_data["tract_geoid"].unique())
            # Use year_map_data_with_data as base and add any missing tracts from count_map_data_with_data
            combined_data = pd.concat(
                [
                    year_map_data_with_data[["tract_geoid", "geometry"]],
                    count_map_data_with_data[["tract_geoid", "geometry"]].loc[
                        ~count_map_data_with_data["tract_geoid"].isin(
                            year_map_data_with_data["tract_geoid"]
                        )
                    ],
                ]
            )
            common_bounds = combined_data.total_bounds
            logger.info(
                "  Combined bounds from %d unique tracts with data: %s",
                len(all_tract_geoids),
                common_bounds,
            )
        elif len(year_map_data_with_data) > 0:
            common_bounds = year_map_data_with_data.total_bounds
            logger.info("  Using year_map_data_with_data bounds: %s", common_bounds)
        elif len(count_map_data_with_data) > 0:
            common_bounds = count_map_data_with_data.total_bounds
            logger.info("  Using count_map_data_with_data bounds: %s", common_bounds)
        elif city_boundaries is not None:
            common_bounds = city_boundaries.total_bounds
            logger.info("  Fallback to city_boundaries bounds: %s", common_bounds)
        else:
            common_bounds = tract_boundaries.total_bounds
            logger.info("  Fallback to tract_boundaries bounds: %s", common_bounds)

        logger.info("=" * 70)

        # Keep all tracts for plotting (including N/A tracts) - don't filter them out

        # Create figure with two subplots
        fig, axes = plt.subplots(1, 2, figsize=(22, 10))
        # No overarching title

        # LEFT MAP: First Year (Discrete Colors with Muted Rainbow Gradient)
        # Get unique years from data
        data_years = sorted(year_map_data["first_prohibition_year"].dropna().unique())

        # Ensure 2023 is included even if not in data (between 2022 and 2024)
        YEAR_TO_INCLUDE = 2023
        all_years = sorted(set(data_years) | {YEAR_TO_INCLUDE})
        unique_years = sorted(all_years)
        n_years = len(unique_years)

        if n_years == 0:
            logger.warning("No years found in data")
            return {}

        # Use rainbow colormap for distinct, linearly progressing colors
        # Create a mapping from year to color index
        year_to_index = {year: idx for idx, year in enumerate(unique_years)}

        # Create a copy for plotting with index column
        year_map_data_plot = year_map_data.copy()
        year_map_data_plot["year_index"] = year_map_data_plot[
            "first_prohibition_year"
        ].map(year_to_index)

        # Use rainbow colormap - colors progress linearly through the rainbow
        rainbow_cmap = plt.cm.get_cmap("rainbow")
        # Sample colors evenly across the rainbow for each year
        raw_colors = [rainbow_cmap(i / max(n_years - 1, 1)) for i in range(n_years)]

        # Make colors more muted by reducing saturation
        # Convert RGB to HSV, reduce saturation, convert back
        muted_colors = []
        SATURATION_FACTOR = 0.6  # Reduce saturation by 40%
        for color in raw_colors:
            # color is RGBA tuple, convert to RGB
            rgb = np.array(color[:3])
            hsv = rgb_to_hsv(rgb.reshape(1, 1, 3))
            # Reduce saturation
            hsv[0, 0, 1] *= SATURATION_FACTOR
            rgb_muted = hsv_to_rgb(hsv).reshape(3)
            # Convert back to RGBA
            muted_colors.append(tuple(rgb_muted) + (color[3],))

        discrete_rainbow = ListedColormap(muted_colors)

        # Plot with discrete colors
        year_map_data_plot.plot(
            column="year_index",
            ax=axes[0],
            legend=False,  # We'll create a custom discrete legend
            cmap=discrete_rainbow,
            vmin=0,
            vmax=n_years - 1,
            edgecolor="black",
            linewidth=0.1,
            missing_kwds={"color": "white", "label": "No Data"},
        )

        # Custom legend will be created after plotting to align with colorbar

        # Remove city boundaries overlay (no bold exterior border)

        axes[0].set_title(
            f"First Year of STR Restriction (n={year_map_data['first_prohibition_year'].notna().sum()})",
            fontsize=16,
        )
        axes[0].axis("off")
        if common_bounds is not None:
            axes[0].set_xlim(common_bounds[0], common_bounds[2])
            axes[0].set_ylim(common_bounds[1], common_bounds[3])

        # RIGHT MAP: Count (Logarithmic Scale)
        # Filter out zeros and negative values for log scale
        count_values = count_map_data[count_column].dropna()
        positive_counts = count_values[count_values > 0]

        # Initialize colorbar variable
        count_colorbar = None

        if len(positive_counts) > 0:
            # Create logarithmic normalization
            vmin = max(positive_counts.min(), 1)  # Ensure at least 1 for log
            vmax = positive_counts.max()
            log_norm = LogNorm(vmin=vmin, vmax=vmax)

            # Plot with logarithmic scale and YlOrRd colormap (yellow to red)
            count_map_data.plot(
                column=count_column,
                ax=axes[1],
                legend=False,  # We'll create a custom colorbar
                cmap="YlOrRd",  # Yellow to red gradient for count data
                edgecolor="black",
                linewidth=0.1,
                missing_kwds={"color": "white", "label": "No Data"},
                norm=log_norm,
            )

            # Create custom colorbar with actual numbers instead of exponents
            # Position it below the plot area to match legend positioning
            sm = plt.cm.ScalarMappable(cmap="YlOrRd", norm=log_norm)
            sm.set_array([])
            # Create colorbar - we'll reposition it after tight_layout
            cbar = plt.colorbar(sm, ax=axes[1], orientation="horizontal", pad=0.15)
            cbar.set_label("Number of Restrictions (log scale)", fontsize=12)
            # Store colorbar reference for later repositioning
            count_colorbar = cbar

            # Set tick locations and format them as actual numbers (not exponents)
            # Generate nice tick locations on log scale
            log_min = np.log10(vmin)
            log_max = np.log10(vmax)
            num_ticks = 5
            # Generate evenly spaced ticks on log scale
            log_ticks = np.linspace(log_min, log_max, num_ticks)
            tick_values = 10**log_ticks

            # Round to integers for cleaner display
            tick_values = np.round(tick_values).astype(int)
            # Ensure values are within bounds and unique
            tick_values = np.unique(np.clip(tick_values, vmin, vmax))

            cbar.set_ticks(tick_values)
            cbar.set_ticklabels([f"{int(t)}" for t in tick_values])
            cbar.ax.tick_params(labelsize=10)
        else:
            # Fallback if no positive values
            count_map_data.plot(
                column=count_column,
                ax=axes[1],
                legend=True,
                cmap="YlOrRd",  # Yellow to red gradient
                edgecolor="black",
                linewidth=0.1,
                missing_kwds={"color": "white", "label": "No Data"},
                legend_kwds={
                    "label": "Number of Restrictions",
                    "orientation": "horizontal",
                    "shrink": 0.8,
                    "pad": 0.05,
                },
            )

        # Remove city boundaries overlay (no bold exterior border)

        axes[1].set_title(
            f"Number of STR Restrictions (n={count_map_data[count_column].notna().sum()})",
            fontsize=16,
        )
        axes[1].axis("off")
        if common_bounds is not None:
            axes[1].set_xlim(common_bounds[0], common_bounds[2])
            axes[1].set_ylim(common_bounds[1], common_bounds[3])

        # Ensure both maps are EXACTLY the same size (excluding legends)
        # Define fixed positions that will be applied after all plotting
        # These are absolute positions that don't depend on current axis sizes
        map_width = 0.38  # Width of each map (as fraction of figure width)
        map_height = 0.7  # Height of each map (as fraction of figure height)
        map_x0_left = 0.08  # Left edge of left map
        map_y0 = 0.15  # Bottom edge of maps
        spacing = 0.05  # Spacing between maps

        # Set both axes to EXACTLY the same size and position them side by side
        axes[0].set_position([map_x0_left, map_y0, map_width, map_height])
        axes[1].set_position(
            [map_x0_left + map_width + spacing, map_y0, map_width, map_height]
        )

        # Ensure both axes have the same aspect ratio
        for ax in axes:
            ax.set_aspect("equal", adjustable="box")

        # Save the plot in multiple formats
        base_name = "str_restrictions_dual_map"
        output_dir = Path(self.output_dir)

        # Apply tight_layout (no title, so use full height)
        plt.tight_layout(rect=[0, 0.15, 1, 1.0])

        # CRITICAL: Re-apply the exact same positions after tight_layout
        # This ensures both maps remain exactly the same size regardless of legend/colorbar placement
        axes[0].set_position([map_x0_left, map_y0, map_width, map_height])
        axes[1].set_position(
            [map_x0_left + map_width + spacing, map_y0, map_width, map_height]
        )

        # Create custom legend for left map: colors above numbers, title below
        # Position it to align with the right map's colorbar (after tight_layout)
        ax0_pos = axes[0].get_position()

        # Create a custom axes for the legend (similar to colorbar)
        # Position it below the left map, aligned with right map's colorbar position
        legend_height = 0.03
        legend_y0 = ax0_pos.y0 - 0.15  # Same vertical position as colorbar
        legend_ax = fig.add_axes([ax0_pos.x0, legend_y0, ax0_pos.width, legend_height])
        legend_ax.axis("off")

        # Calculate spacing for legend items
        n_years_display = len(unique_years)

        # Calculate item width - distribute evenly across available width
        item_width = 1.0 / n_years_display if n_years_display > 0 else 0.05

        # Patch dimensions - match colorbar height
        # Colorbar height is 0.03 in figure coordinates, same as legend_ax height
        # So patches should take up most of the legend_ax height
        patch_width_rel = item_width * 0.7  # Width: 70% of item width
        patch_height_rel = (
            0.85  # Height: 85% of legend height (matches colorbar visual height)
        )

        # Spacing - spacing between patch and year number
        spacing_patch_to_text = 0.15  # Spacing between patch and year number

        # Draw colors (patches) on top, numbers below, title at bottom
        # Align patches and years with the right map's colorbar (which fills its height)
        # Years are already in sequential order (unique_years is sorted)
        for i, year in enumerate(unique_years):
            x_center = (i + 0.5) * item_width

            # Position patch at top of legend_ax to align with colorbar
            # Colorbar fills its entire height, so patches should start near top
            patch_y_top = 1.0  # Start at top of legend_ax
            patch_y0 = patch_y_top - patch_height_rel  # Bottom of patch
            patch_x0 = x_center - patch_width_rel / 2

            # Draw color patch - aligned with colorbar at top
            legend_ax.add_patch(
                plt.Rectangle(
                    (patch_x0, patch_y0),
                    patch_width_rel,
                    patch_height_rel,
                    facecolor=muted_colors[year_to_index[year]],
                    edgecolor="black",
                    linewidth=1.0,
                    transform=legend_ax.transAxes,
                )
            )

            # Add year label just below the patch - aligned with colorbar numbers
            text_y = patch_y0 - spacing_patch_to_text
            legend_ax.text(
                x_center,
                text_y,
                f"{int(year)}",
                ha="center",
                va="top",
                fontsize=9,
                transform=legend_ax.transAxes,
            )

        # Add title at the bottom - move much further down to avoid overlap
        title_y = -0.6  # Position well below the years to prevent overlap
        legend_ax.text(
            0.5,
            title_y,
            "Year",
            ha="center",
            va="top",
            fontsize=12,
            transform=legend_ax.transAxes,
        )

        # Reposition colorbar below the right map after axes positions are set
        # Check if colorbar was created and reposition it
        if count_colorbar is not None:
            ax1_pos = axes[1].get_position()
            count_colorbar.ax.set_position(
                [ax1_pos.x0, ax1_pos.y0 - 0.15, ax1_pos.width, 0.03]
            )

        # Verify positions are identical (for debugging)
        POSITION_TOLERANCE = 0.001
        final_pos_0 = axes[0].get_position()
        final_pos_1 = axes[1].get_position()
        if (
            abs(final_pos_0.width - final_pos_1.width) > POSITION_TOLERANCE
            or abs(final_pos_0.height - final_pos_1.height) > POSITION_TOLERANCE
        ):
            logger.warning(
                "Map sizes differ: left=(%.4f, %.4f), right=(%.4f, %.4f). Re-applying fixed positions.",
                final_pos_0.width,
                final_pos_0.height,
                final_pos_1.width,
                final_pos_1.height,
            )
            # Force them to be exactly the same
            axes[0].set_position([map_x0_left, map_y0, map_width, map_height])
            axes[1].set_position(
                [map_x0_left + map_width + spacing, map_y0, map_width, map_height]
            )

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save figure in all three formats: PDF, PNG, and SVG
        output_paths = {}

        # Save as PDF (vector format, no DPI needed)
        pdf_path = output_dir / f"{base_name}.pdf"
        fig.savefig(pdf_path, bbox_inches="tight", format="pdf")
        output_paths["pdf"] = str(pdf_path)
        logger.info("Saved visualization to: %s", pdf_path)

        # Save as PNG (raster format, high DPI)
        png_path = output_dir / f"{base_name}.png"
        fig.savefig(png_path, dpi=600, bbox_inches="tight", format="png")
        output_paths["png"] = str(png_path)
        logger.info("Saved visualization to: %s", png_path)

        # Save as SVG (vector format, no DPI needed)
        svg_path = output_dir / f"{base_name}.svg"
        fig.savefig(svg_path, bbox_inches="tight", format="svg")
        output_paths["svg"] = str(svg_path)
        logger.info("Saved visualization to: %s", svg_path)

        # Final check: re-apply positions one more time right before closing
        # This ensures they're identical even if savefig adjusted anything
        axes[0].set_position([map_x0_left, map_y0, map_width, map_height])
        axes[1].set_position(
            [map_x0_left + map_width + spacing, map_y0, map_width, map_height]
        )

        plt.close(fig)

        return {"str_restrictions_dual_map": output_paths}
