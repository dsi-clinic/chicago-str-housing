"""Event study visualizer for dynamic DiD effects."""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class EventStudyVisualizer(Visualizer):
    """Create an event-study coefficient plot from pre-computed coef_df."""

    def __init__(self, output_dir: str | None = None) -> None:
        super().__init__(
            "event_study_visualizer",
            "Visualize dynamic DiD effects from event-study coefficients",
        )
        self.output_dir = output_dir or "output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create event-study plot using coef_df from EventStudyAnalyzer.

        Args:
            - event_study_coef_df: DataFrame with columns
              [relative_time, coefficient, std_error, ci_lower, ci_upper]
        """
        coef_df = context.get("event_study_coef_df")

        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        self._create_event_study_plot(coef_df, output_path)

        plot_path = output_path / "event_study_effects.png"
        logger.info("Event study plot saved to %s", plot_path)

        return {"event_study_plot_path": str(plot_path)}

    def _create_event_study_plot(self, coef_df: pd.DataFrame, output_path: Path) -> None:
        """Create event-study plot."""
        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot coefficients
        ax.plot(
            coef_df["relative_time"],
            coef_df["coefficient"],
            "o-",
            color="navy",
            label="Estimated Effect",
        )

        # Plot confidence intervals
        ax.fill_between(
            coef_df["relative_time"],
            coef_df["ci_lower"],
            coef_df["ci_upper"],
            alpha=0.2,
            color="navy",
        )

        # Reference lines
        ax.axhline(0, color="black", linestyle="-", linewidth=0.8)
        # Vertical line at treatment (months_since_treatment = 0)
        ax.axvline(0, color="red", linestyle="--", label="Treatment")

        ax.set_xlabel("Months Since Treatment")
        ax.set_ylabel("Effect on Rental Price ($)")
        ax.set_title("Event Study: Effect of STR Prohibition on Rental Prices")
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        fig.savefig(output_path / "event_study_effects.png", dpi=300, bbox_inches="tight")
        plt.close(fig)

