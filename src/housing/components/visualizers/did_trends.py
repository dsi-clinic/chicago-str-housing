"""Module for visualizing DiD Trends."""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from housing.components.utils import (
    setup_figure_and_save,
)
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class DIDTrendsVisualizer(Visualizer):
    """Visualize DiD data and check for the parallel trends assumption."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the DiD trends visualizer."""
        super().__init__(
            "did_trends_visualizer",
            "Create DiD trend visualizations",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create DiD trend visualizations."""
        did_panel = context["did_panel"]

        fig, ax = plt.subplots(2, 2, figsize=(16, 12))

        # Count unique treated tracts over time
        treated_by_month = (
            did_panel[did_panel["treated"] == 1]
            .groupby("month")["tract_geoid"]
            .nunique()
        )

        treated_by_month.plot(ax=ax[0, 0])
        ax[0, 0].set_ylabel("Number of Treated Tracts")
        ax[0, 0].set_xlabel("Month")
        ax[0, 0].set_title("STR Prohibition Adoption Over Time")

        # Identify ever-treated vs never-treated tracts
        ever_treated = did_panel.groupby("tract_geoid")["treated"].max()
        ever_treated_tracts = ever_treated[ever_treated == 1].index

        did_panel["ever_treated"] = (
            did_panel["tract_geoid"].isin(ever_treated_tracts).astype(int)
        )

        # Average rental price by ever_treated status and month (from context)
        avg_by_group = context["average_rent_by_treatment_group"]

        # Plot average by group
        avg_by_group.plot(ax=ax[0, 1])
        ax[0, 1].set_ylabel("Average Rental Price ($)")
        ax[0, 1].set_xlabel("Month")
        ax[0, 1].set_title("Rental Price Trends: Treated vs. Control Tracts")
        ax[0, 1].legend(title="Group")

        # Define pre-treatment period (before any tract is treated)
        first_treatment = did_panel.loc[did_panel["treated"] == 1, "month"].min()

        # Plot parallel trends check:

        # Plot both groups
        avg_by_group.plot(ax=ax[1, 1], alpha=0.7)

        # Add vertical line at first treatment
        ax[1, 1].axvline(
            first_treatment, color="red", linestyle="--", label="First Treatment"
        )

        ax[1, 1].set_ylabel("Average Rental Price ($)")
        ax[1, 1].set_xlabel("Month")
        ax[1, 1].set_title("Parallel Trends Check -- Full Observed Period")
        ax[1, 1].legend()

        # zoom in on pre-treatment period
        pre_period = avg_by_group[:first_treatment]
        pre_period.plot(ax=ax[1, 0], alpha=0.7)

        ax[1, 0].set_xlabel("Month")
        ax[1, 0].set_ylabel("Average Rental Price ($)")
        ax[1, 0].set_title("Parallel Trends Check -- Zoomed In to Pre-Treatment Period")
        ax[1, 0].legend()

        # Save plots
        output_path = Path(self.output_dir) / "did_trends_plots.png"
        setup_figure_and_save(
            fig,
            output_path,
            title="DiD Trends Visual Analysis",
            logger=logger,
        )

        return {"did_trends_plots": str(output_path)}
