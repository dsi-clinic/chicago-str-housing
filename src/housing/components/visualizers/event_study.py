"""Event study visualizer.

This module creates visualizations specifically for event study analysis.
This is a specialized visualizer for event study analysis - students should create their
own visualizers for other data types.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class EventStudyVisualizer(Visualizer):
    """Create visualizations for event study analysis.

    This demonstrates how to create meaningful visualizations from event study data.
    Students should create their own visualizers for other data types (crime, housing violations, etc.).
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the event study visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "event_study_visualization",
            "Create visualizations for event study analysis",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the event study visualizer."""
        logger.info(
            "Visualizing the event study analysis..."
        )
        fig, ax = plt.subplots(figsize=(10, 6))

        coef_df = context["event_study_coef_df"]

        # Plot coefficients
        ax.plot(coef_df["relative_time"], coef_df["coefficient"], "o-", color="navy")

        # Plot confidence intervals
        ax.fill_between(
            coef_df["relative_time"],
            coef_df["ci_lower"],
            coef_df["ci_upper"],
            alpha=0.2,
            color="navy"
        )

        # Reference lines
        ax.axhline(0, color="black", linestyle="-", linewidth=0.5)
        ax.axvline(-0.5, color="red", linestyle="--", label="Treatment")

        ax.set_xlabel("Months Since Treatment")
        ax.set_ylabel("Effect on Rental Price ($)")
        ax.set_title("Event Study: Effect of STR Prohibition on Rents")
        ax.legend()

        # Save the plot
        output_path = Path(self.output_dir) / "event_study_plot.png"
        fig.savefig(output_path)
        logger.info(f"Event study plot saved to {output_path}")

        return {
            "event_study_plot_path": output_path
        }