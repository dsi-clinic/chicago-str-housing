"""Event study plot visualizer.

This module creates a visualizations for the event study plot.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class EventStudyVisualizer(Visualizer):
    """Create visualizations for event study plot.

    Shows event study plot.
    """

    def __init__(
        self, output_dir: str | None = None, filename_suffix: str | None = None
    ) -> None:
        """Initialize the event study visualizer.

        Args:
            output_dir: Optional output directory for visualizations
            filename_suffix: Optional suffix for the filename
        """
        super().__init__(
            "event_study_plot",
            "Create visualizations for event study plot",
        )
        self.output_dir = output_dir or "/project/output"
        self.filename_suffix = filename_suffix

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create visualizations for event study plot."""
        logger.info("Creating visualizations for event study plot...")

        coef_df = context.get("coef_df")

        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot coefficients
        ax.plot(coef_df["relative_time"], coef_df["coefficient"], "o-", color="navy")

        ax.fill_between(
            coef_df["relative_time"],
            coef_df["ci_lower"],
            coef_df["ci_upper"],
            alpha=0.2,
            color="navy",
        )

        # Reference lines
        ax.axhline(0, color="black", linestyle="-", linewidth=0.5)
        ax.axvline(-0.5, color="red", linestyle="--", label="Treatment")

        ax.set_xlabel("Months Since Treatment")
        ax.set_ylabel("Effect on Rental Price ($)")
        ax.set_title("Event Study: Effect of STR Prohibition on Rents")
        ax.legend()

        # Save the plot
        base = "event_study_plot"
        name = (
            f"{base}{self.filename_suffix}.png"
            if self.filename_suffix
            else f"{base}.png"
        )
        output_path = Path(self.output_dir) / name
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved visualization to: %s", output_path)

        return {"event_study_plot": str(output_path)}
