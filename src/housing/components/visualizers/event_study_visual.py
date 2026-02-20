"""Visualize event study data to check the parallel trends assumption."""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from housing.components.utils import (
    setup_figure_and_save,
)
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class EventStudyVisualizer(Visualizer):
    """Visualize event study data to check the parallel trends assumption."""

    def __init__(
        self, output_dir: str | None = None, output_suffix: str | None = None
    ) -> None:
        """Initialize the event study visualizer."""
        super().__init__(
            "event_study_visualizer",
            "Create parallel trends event study visualization",
        )
        self.output_dir = output_dir or "/project/output"
        self.output_name = "event_study_plot" + (output_suffix or "") + ".png"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create event study visualization to evaluate parallel trends assumption."""
        coef_df = context["event_study_coefficients"]

        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot coefficients
        ax.plot(coef_df["relative_time"], coef_df["coefficient"], "o-", color="navy")

        # Plot confidence intervals
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

        # Save plot
        output_path = Path(self.output_dir) / self.output_name
        setup_figure_and_save(
            fig,
            output_path,
            title="DiD Parallel Trends Event Study",
            logger=logger,
        )

        return {"event_study_plot": str(output_path)}
