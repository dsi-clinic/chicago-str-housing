"""Cohort choropleth visualizer for Callaway & Sant'Anna analysis.

Creates choropleth maps showing which census tracts belong to each
treatment cohort that produced an ATT estimate in the CS estimator.
One standalone figure is produced per cohort, plus a combined overview.
"""

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from housing.components.constants import MIN_LAND_AREA_SQ_METERS
from housing.components.utils import setup_figure_and_save
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)

# Same gray for "other tracts" in single-cohort maps and "never treated" in combined map
# Fairly light gray, but not as light as the original background.
OTHER_TRACT_GRAY = "#d0d0d0"

# Red→blue gradient for cohort colors, passing through warm and green hues.
# Approximate path: red → orange → yellow → green → blue.
COHORT_GRADIENT_CMAP = LinearSegmentedColormap.from_list(
    "red_to_blue_warm",
    [
        "#d73027",  # red
        "#fc8d59",  # orange
        "#fee090",  # yellow
        "#91cf60",  # green
        "#4575b4",  # blue
    ],
)


def _cohort_colors_from_gradient(n_cohorts: int) -> list[str]:
    """Return n_cohorts equidistant hex colors from the gradient colormap."""
    if n_cohorts <= 0:
        return []
    # Equidistant positions from 0 to 1 (inclusive ends for first and last)
    positions = np.linspace(0.0, 1.0, n_cohorts)
    return [mcolors.to_hex(COHORT_GRADIENT_CMAP(x)) for x in positions]


class CohortChoroplethVisualizer(Visualizer):
    """Create per-cohort choropleth maps for cohorts with ATT estimates."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the visualizer with output directory for choropleth maps."""
        super().__init__(
            "cohort_choropleth_visualizer",
            "Choropleth maps of treatment cohort membership by census tract",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create one choropleth per ATT-producing cohort plus a combined overview."""
        logger.info("Creating cohort choropleth visualizations...")

        cs_cohort_info = context.get("cs_cohort_info")
        tract_boundaries = context.get("tract_boundaries")
        city_boundaries = context.get("city_boundaries")

        if cs_cohort_info is None:
            logger.warning("No CS cohort info available. Skipping.")
            return {}
        if tract_boundaries is None:
            logger.warning("No tract boundaries available. Skipping.")
            return {}

        treated_cohorts = cs_cohort_info.get("treated_cohorts")
        cohort_sizes = cs_cohort_info.get("cohort_sizes")

        if treated_cohorts is None or treated_cohorts.empty:
            logger.warning("No treated cohorts found. Skipping.")
            return {}

        cohort_df = treated_cohorts[["tract_geoid", "first_treatment_month"]].copy()
        cohort_df = cohort_df.rename(columns={"first_treatment_month": "cohort"})
        cohorts_sorted = sorted(cohort_sizes.index)
        n_cohorts = len(cohorts_sorted)

        logger.info("Plotting %d cohorts (those with ATT estimates):", n_cohorts)
        for cohort in cohorts_sorted:
            logger.info(
                "  %s: %d tracts",
                pd.Timestamp(cohort).strftime("%Y-%m-%d"),
                int(cohort_sizes[cohort]),
            )

        # Cohort colors from gradient, equidistant, decided only after n_cohorts is known
        cohort_hex_colors = _cohort_colors_from_gradient(n_cohorts)
        color_map = {
            cohort: cohort_hex_colors[i] for i, cohort in enumerate(cohorts_sorted)
        }

        base = self._prepare_map_base(tract_boundaries, city_boundaries)
        merged = base.merge(cohort_df, on="tract_geoid", how="left")

        choropleth_dir = Path(self.output_dir) / "cohort-choropleths"
        choropleth_dir.mkdir(parents=True, exist_ok=True)

        output_paths = {}

        for idx, cohort in enumerate(cohorts_sorted):
            path = self._plot_single_cohort(
                merged,
                cohort,
                color_map[cohort],
                int(cohort_sizes[cohort]),
                output_dir=choropleth_dir,
            )
            if path:
                output_paths[f"cohort_map_{idx}"] = path

        combined_path = self._plot_combined_cohorts(
            merged,
            cohorts_sorted,
            color_map,
            output_dir=choropleth_dir,
        )
        if combined_path:
            output_paths["cohort_combined_map"] = combined_path

        return output_paths

    def _prepare_map_base(
        self,
        tract_boundaries: gpd.GeoDataFrame,
        city_boundaries: gpd.GeoDataFrame | None,
    ) -> gpd.GeoDataFrame:
        """Filter and clip tract geometries to Chicago."""
        gdf = tract_boundaries.copy()
        if "ALAND" in gdf.columns:
            gdf = gdf[gdf["ALAND"] > MIN_LAND_AREA_SQ_METERS].copy()
        if city_boundaries is not None:
            if gdf.crs != city_boundaries.crs:
                city_boundaries = city_boundaries.to_crs(gdf.crs)
            gdf = gpd.clip(gdf, city_boundaries)
        return gdf

    def _plot_single_cohort(
        self,
        merged: gpd.GeoDataFrame,
        cohort: pd.Timestamp,
        color: str,
        n_tracts: int,
        output_dir: Path,
    ) -> str | None:
        """Create a standalone choropleth for one cohort."""
        fig, ax = plt.subplots(figsize=(10, 12))

        merged.plot(
            ax=ax,
            color=OTHER_TRACT_GRAY,
            edgecolor="white",
            linewidth=0.2,
        )

        cohort_tracts = merged[merged["cohort"] == cohort]
        if not cohort_tracts.empty:
            cohort_tracts.plot(
                ax=ax,
                color=color,
                edgecolor="white",
                linewidth=0.3,
            )

        legend_patches = [
            mpatches.Patch(color=color, label=f"Cohort tracts  (n={n_tracts})"),
            mpatches.Patch(color=OTHER_TRACT_GRAY, label="Other tracts"),
        ]
        ax.legend(
            handles=legend_patches,
            loc="lower left",
            fontsize=10,
            frameon=True,
            facecolor="white",
            edgecolor="gray",
        )

        cohort_label_display = pd.Timestamp(cohort).strftime("%B %Y")
        ax.set_title(
            f"Treatment Cohort: {cohort_label_display}\n({n_tracts} tracts)",
            fontsize=14,
            fontweight="bold",
            pad=15,
        )
        ax.axis("off")

        safe_label = pd.Timestamp(cohort).strftime("%Y_%m_%d")
        out_path = output_dir / f"did_cohort_choropleth_{safe_label}.png"
        setup_figure_and_save(fig, out_path, logger=logger)
        logger.info(
            "Saved cohort choropleth for %s to %s",
            cohort_label_display,
            out_path,
        )
        return str(out_path)

    def _plot_combined_cohorts(
        self,
        merged: gpd.GeoDataFrame,
        cohorts_sorted: list,
        color_map: dict[pd.Timestamp, str],
        output_dir: Path,
    ) -> str | None:
        """Create a single overview map with all cohorts in distinct colors.

        Legend uses exact cohort colors (discrete patches), not a gradient.
        """
        fig, ax = plt.subplots(figsize=(12, 14))

        never_treated = merged[merged["cohort"].isna()]
        if not never_treated.empty:
            never_treated.plot(
                ax=ax,
                color=OTHER_TRACT_GRAY,
                edgecolor="white",
                linewidth=0.3,
            )

        for cohort in cohorts_sorted:
            cohort_data = merged[merged["cohort"] == cohort]
            if not cohort_data.empty:
                cohort_data.plot(
                    ax=ax,
                    color=color_map[cohort],
                    edgecolor="white",
                    linewidth=0.3,
                )

        # Legend: exact colors (patches) next to month-year labels and counts
        legend_patches = [
            mpatches.Patch(
                color=color_map[c],
                label=(
                    f"{pd.Timestamp(c).strftime('%B %Y')}"
                    f"  (n={int((merged['cohort'] == c).sum())})"
                ),
            )
            for c in cohorts_sorted
        ]
        legend_patches.append(
            mpatches.Patch(
                color=OTHER_TRACT_GRAY,
                label=f"Never treated  (n={int(merged['cohort'].isna().sum())})",
            )
        )
        ax.legend(
            handles=legend_patches,
            loc="lower left",
            fontsize=9,
            frameon=True,
            facecolor="white",
            edgecolor="gray",
            title="Treatment Cohorts",
            title_fontsize=10,
        )

        ax.set_title(
            "STR Prohibition Treatment Cohorts by Census Tract",
            fontsize=14,
            fontweight="bold",
            pad=15,
        )
        ax.axis("off")

        out_path = output_dir / "did_cohort_choropleth_combined.png"
        setup_figure_and_save(fig, out_path, logger=logger)
        logger.info("Saved combined cohort choropleth to %s", out_path)
        return str(out_path)
