"""Difference-in-Differences trends visualizer."""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from housing.components.utils import setup_figure_and_save
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class DIDTrendsVisualizer(Visualizer):
    """Difference-in-Differences trends visualizer."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the Difference-in-Differences trends visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "did_trends_visualization",
            "Visualize the trends in the Difference-in-Differences analysis",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the Difference-in-Differences trends visualizer."""
        logger.info(
            "Visualizing the trends in the Difference-in-Differences analysis..."
        )
        did_panel = context["did_panel"]
        treated_by_month = context["treated_by_month"]
        avg_by_group = context["avg_by_group"]

        # Calculate first treatment month
        first_treatment = did_panel.loc[did_panel["treated"] == 1, "month"].min()

        # Get output directory from context if available, otherwise use instance variable
        output_dir = Path(context.get("output_dir", self.output_dir))
        output_dir.mkdir(parents=True, exist_ok=True)

        # Visualization 1: STR Prohibition Adoption Over Time
        fig1, ax1 = plt.subplots(figsize=(10, 5))
        treated_by_month.plot(ax=ax1)
        ax1.set_ylabel("Number of Treated Tracts")
        ax1.set_xlabel("Month")
        ax1.set_title("STR Prohibition Adoption Over Time")
        ax1.grid(True, alpha=0.3)

        output_path1 = output_dir / "did_str_adoption_over_time.png"
        setup_figure_and_save(
            fig1,
            output_path1,
            title="STR Prohibition Adoption Over Time",
            logger=logger,
        )

        # Visualization 2: Rental Price Trends: Treated vs. Control Tracts
        fig2, ax2 = plt.subplots(figsize=(10, 5))
        avg_by_group.plot(ax=ax2)
        ax2.set_ylabel("Average Rental Price ($)")
        ax2.set_xlabel("Month")
        ax2.set_title("Rental Price Trends: Treated vs. Control Tracts")
        ax2.legend(title="Group")
        ax2.grid(True, alpha=0.3)

        output_path2 = output_dir / "did_rental_price_trends.png"
        setup_figure_and_save(
            fig2,
            output_path2,
            title="Rental Price Trends: Treated vs. Control Tracts",
            logger=logger,
        )

        # Visualization 3: Parallel Trends Check
        fig3, ax3 = plt.subplots(figsize=(10, 5))
        avg_by_group.plot(ax=ax3, alpha=0.7)
        ax3.axvline(
            first_treatment, color="red", linestyle="--", label="First Treatment"
        )
        ax3.set_ylabel("Average Rental Price ($)")
        ax3.set_xlabel("Month")
        ax3.set_title("Parallel Trends Check")
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        output_path3 = output_dir / "did_parallel_trends_check.png"
        setup_figure_and_save(
            fig3,
            output_path3,
            title="Parallel Trends Check",
            logger=logger,
        )

        return {
            "did_str_adoption_plot": str(output_path1),
            "did_rental_price_trends_plot": str(output_path2),
            "did_parallel_trends_plot": str(output_path3),
        }
