"""ACS Distribution Visualization.

This module creates visualizations for acS results.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import seaborn as sns

from housing.components.utils import (
    create_histogram_with_median,
)
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class ACSDistribution(Visualizer):
    """Create visualizations for the ACS Distribution.

    How does ACS data look like
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the ACS visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "acs_distribution_visualization",
            "Create visualizations for ACS Distribution",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create distribution visualizations."""
        logger.info("Creating distribution visualizations...")

        correlation_matrix = context["tract_correlation_matrix"]
        tract_data = context["acs_tract_data"]

        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(
            "Data Analysis: Census Tract Demographic Data",
            fontsize=16,
            fontweight="bold",
        )

        logger.info("Check if subplots are made")

        # 1. Correlation heatmap
        sns.heatmap(
            correlation_matrix,
            annot=True,
            cmap="RdBu_r",
            center=0,
            square=True,
            ax=axes[0, 0],
        )
        axes[0, 0].set_xticklabels(axes[0, 0].get_xticklabels(), rotation=10)

        axes[0, 0].set_title("Correlation Matrix")

        # 2. Population Density Distribution
        if tract_data is not None:
            create_histogram_with_median(
                axes[0, 1],
                tract_data["population_density"],
                "Census Tract Level",
                "Population Density (per km2)",
                "Number of Census Tracts",
                color="steelblue",
                median_format="{:.0f} per km2",
            )

        # 3. Population DEensity vs Median Income scatter plot
        if (
            tract_data is not None
            and "population_density" in tract_data.columns
            and "median_house_income" in tract_data.columns
        ):
            box_data = tract_data[
                ["population_density", "median_house_income"]
            ].dropna()
            sns.regplot(
                data=box_data,
                x="population_density",
                y="median_house_income",
                ax=axes[1, 0],
                scatter_kws={"color": "purple", "alpha": 0.6, "s": 20},
                line_kws={"color": "purple", "linewidth": 2},
            )

            axes[1, 0].set_xlabel("Population Density (per km2)", fontsize=12)
            axes[1, 0].set_ylabel("Median Household Income ($)", fontsize=12)
            axes[1, 0].set_title("Population Density vs Median Income", fontsize=14)
            axes[1, 0].grid(True, alpha=0.3)

        # 4. Median Income Distribution
        if tract_data is not None:
            create_histogram_with_median(
                axes[1, 1],
                tract_data["median_house_income"],
                "Census Tract Level",
                "Median Household Income ($)",
                "Number of Census Tracts",
                color="steelblue",
                median_format="${:.0f}",
            )

        # Save the plot
        output_path = Path(self.output_dir) / "acs_distribution.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved visualization to: %s", output_path)

        plt.show()

        return {"visualization_path": str(output_path)}
