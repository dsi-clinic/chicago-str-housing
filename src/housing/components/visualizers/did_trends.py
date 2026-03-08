"""DiD trends visualizer for diagnostic pre-trends checks."""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class DIDTrendsVisualizer(Visualizer):
    """Visualize DiD panel to inspect treatment adoption and pre-trends."""

    def __init__(self, output_dir: str | None = None, file_suffix: str = "") -> None:
        """Initialize the visualizer with output path and optional file suffix."""
        super().__init__(
            "did_trends_visualizer",
            "Create DiD trend visualizations for treated and control tracts",
        )
        self.output_dir = output_dir or "output"
        self.file_suffix = file_suffix

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create DiD trend visualizations using panel and group means.

        Expected context keys:
            - did_panel: DiD panel DataFrame
            - avg_by_group_month: Average rental price by group and month
        """
        did_panel = context["did_panel"]
        avg_by_group = context["avg_by_group_month"]

        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        self._create_did_trends_plot(did_panel, avg_by_group, output_path)

        filename = f"did_trends_plots{self.file_suffix}.png"
        plot_path = output_path / filename
        logger.info("DiD trends plot saved to %s", plot_path)

        return {"did_trends_plot_path": str(plot_path)}

    def _create_did_trends_plot(
        self,
        did_panel: pd.DataFrame,
        avg_by_group: pd.DataFrame,
        output_path: Path,
    ) -> None:
        """Create 2x2 panel of DiD trend diagnostics."""
        fig, ax = plt.subplots(2, 2, figsize=(16, 12))

        # Count unique treated tracts over time
        treated_by_month = (
            did_panel[did_panel["treated"] == 1]
            .groupby("month")["tract_geoid"]
            .nunique()
        )

        treated_by_month.plot(
            ax=ax[0, 0],
            color="#2c3e50",
            marker="o",
            linewidth=1.5,
        )
        ax[0, 0].set_ylabel("Number of Treated Tracts")
        ax[0, 0].set_xlabel("Month")
        ax[0, 0].set_title("STR Prohibition Adoption Over Time")

        # Identify ever-treated vs never-treated tracts
        ever_treated = did_panel.groupby("tract_geoid")["treated"].max()
        ever_treated_tracts = ever_treated[ever_treated == 1].index
        did_panel = did_panel.copy()
        did_panel["ever_treated"] = (
            did_panel["tract_geoid"].isin(ever_treated_tracts).astype(int)
        )

        # Plot average by group
        avg_by_group.plot(ax=ax[0, 1])
        ax[0, 1].set_ylabel("Average Rental Price ($)")
        ax[0, 1].set_xlabel("Month")
        ax[0, 1].set_title("Rental Price Trends: Treated vs. Control Tracts")
        ax[0, 1].legend(title="Group")

        # Define pre-treatment period (before any tract is treated)
        first_treatment = did_panel.loc[did_panel["treated"] == 1, "month"].min()

        # Full-period parallel trends check
        avg_by_group.plot(ax=ax[1, 1], alpha=0.8)
        ax[1, 1].axvline(
            first_treatment,
            color="red",
            linestyle="--",
            linewidth=2,
            label="First Treatment",
        )
        ax[1, 1].set_ylabel("Average Rental Price ($)")
        ax[1, 1].set_xlabel("Month")
        ax[1, 1].set_title("Parallel Trends Check -- Full Observed Period")
        ax[1, 1].legend()

        # Zoomed pre-treatment period
        pre_period = avg_by_group[:first_treatment]
        pre_period.plot(ax=ax[1, 0], alpha=0.8)
        ax[1, 0].set_xlabel("Month")
        ax[1, 0].set_ylabel("Average Rental Price ($)")
        ax[1, 0].set_title("Parallel Trends Check -- Zoomed In to Pre-Treatment Period")
        ax[1, 0].legend()

        # Add grid to all subplots
        for axes_row in ax:
            for subplot_ax in axes_row:
                subplot_ax.grid(True, alpha=0.3)

        plt.tight_layout()
        filename = f"did_trends_plots{self.file_suffix}.png"
        fig.savefig(output_path / filename, dpi=300, bbox_inches="tight")
        plt.close(fig)
