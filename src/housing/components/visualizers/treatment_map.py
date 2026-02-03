"""Treatment map visualizer.

This module creates choropleth maps showing treatment distributions
at census tract level.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from housing.components.utils import (
    create_choropleth_map,
    prepare_map_data,
    setup_figure_and_save,
)
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class TreatmentMapVisualizer(Visualizer):
    """Create choropleth maps for treatment distributions.

    Shows treatment data as geographic maps at census tract level.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the treatment map visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "treatment_map_visualization",
            "Create choropleth maps for treatment distributions",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create treatment map visualizations."""
        logger.info("Creating treatment map visualizations...")

        did_panel = context.get("did_panel_data")
        community_data = context.get("community_rental_data")
        tract_boundaries = context.get("tract_boundaries")
        city_boundaries = context.get("city_boundaries")

        if did_panel is None and community_data is None:
            logger.warning("No DID panel data available for mapping")
            return {}

        fig, axes = plt.subplots(1, 3, figsize=(20, 10))
        fig.suptitle("Treatment Maps", fontsize=20, fontweight="bold", y=0.98)

        # Get common bounds for consistent zoom
        if city_boundaries is not None:
            common_bounds = city_boundaries.total_bounds
        else:
            common_bounds = None

        if did_panel is None or tract_boundaries is None:
            logger.warning(
                "No DID panel data or tract boundaries available for mapping"
            )
            return {}

        common_bounds = (
            city_boundaries.total_bounds if city_boundaries is not None else None
        )
        fig, axes = plt.subplots(1, 3, figsize=(20, 10))
        fig.suptitle("Treatment Maps", fontsize=20, fontweight="bold", y=0.98)

        # Map 1: First adoption date (binary map,colored if treated)
        first_treatment = did_panel.loc[did_panel["treated"] == 1, "month"].min()
        first_snapshot = did_panel[did_panel["month"] == first_treatment][
            ["tract_geoid", "treated"]
        ].drop_duplicates(subset="tract_geoid")
        map_first = prepare_map_data(
            first_snapshot,
            tract_boundaries,
            ["treated"],
            city_boundaries,
            logger=logger,
        )
        create_choropleth_map(
            axes[0],
            map_first,
            "treated",
            f"First Adoption Date Snapshot ({first_treatment.strftime('%Y-%m')})",
            "Treated (1) vs Never Treated (0)",
            cmap="Blues",
            bounds=common_bounds,
            show_stats=False,
            logger=logger,
        )

        # Map 2: Most recent date (binary map, colored if treated)
        last_month = did_panel["month"].max()
        last_snapshot = did_panel[did_panel["month"] == last_month][
            ["tract_geoid", "treated", "months_since_treatment"]
        ].drop_duplicates(subset="tract_geoid")
        last_snapshot = last_snapshot.copy()
        last_snapshot["months_since_treatment"] = (
            last_snapshot["months_since_treatment"].fillna(0).clip(lower=0)
        )
        last_binary = last_snapshot[["tract_geoid", "treated"]].copy()
        map_last = prepare_map_data(
            last_binary,
            tract_boundaries,
            ["treated"],
            city_boundaries,
            logger=logger,
        )
        create_choropleth_map(
            axes[1],
            map_last,
            "treated",
            f"Most Recent Date Snapshot ({last_month.strftime('%Y-%m')})",
            "Treated (1) vs Never Treated (0)",
            cmap="Blues",
            bounds=common_bounds,
            show_stats=False,
            logger=logger,
        )

        # Map 3: Months since treatment (darker = longer treated)
        map_months = prepare_map_data(
            last_snapshot,
            tract_boundaries,
            ["months_since_treatment"],
            city_boundaries,
            logger=logger,
        )
        create_choropleth_map(
            axes[2],
            map_months,
            "months_since_treatment",
            "Months Since Treatment (0 = Never Treated)",
            "Months Since Treatment",
            cmap="Blues",
            bounds=common_bounds,
            show_stats=True,
            stats_format="{:.0f}",
            logger=logger,
        )

        # Save the plot
        output_path = Path(self.output_dir) / "treatment_maps.png"
        setup_figure_and_save(
            fig,
            output_path,
            title="Chicago Treatment Maps",
            logger=logger,
        )

        return {"treatment_map_plot": str(output_path)}
