import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from pipeline.base import Visualizer
from housing.components.utils import (
    setup_figure_and_save,
    add_statistical_summary_to_plot,
)

logger = logging.getLogger(__name__)


class ForeclosedDistributionVisualizer(Visualizer):
    """Visualize foreclosed property distributions across Chicago communities."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the foreclosed property distribution visualizer."""
        super().__init__(
            "foreclosed_distribution_visualization",
            "Create visualization of top 10 communities by foreclosure count",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create a bar chart of top 10 Chicago communities by foreclosure count."""
        logger.info("Creating Top 10 Foreclosed Communities visualization...")

        community_data = context.get("foreclosed_community_data")

        if community_data is None or community_data.empty:
            logger.warning("No community-level foreclosure data available for visualization.")
            return {}

        # Sort and select top 10
        top10 = (
            community_data[["community_name", "foreclosed_count"]]
            .sort_values(by="foreclosed_count", ascending=False)
            .head(10)
        )

        # --- Create figure ---
        fig, ax = plt.subplots(figsize=(12, 8))
        bars = ax.barh(
            top10["community_name"],
            top10["foreclosed_count"],
            color="darkred",
            alpha=0.8,
        )
        ax.invert_yaxis()

        ax.set_title("Top 10 Chicago Communities by Foreclosure Count", fontsize=16, weight="bold")
        ax.set_xlabel("Foreclosed Property Count", fontsize=12)
        ax.set_ylabel("Community Area", fontsize=12)
        ax.grid(axis="x", alpha=0.3)

        # Add value labels on bars
        for bar in bars:
            width = bar.get_width()
            ax.text(width + 1, bar.get_y() + bar.get_height() / 2, f"{int(width)}", va="center")

        # --- Statistical Summary ---
        stats = [
            ("Total Communities", len(community_data)),
            ("Total Foreclosures", int(community_data["foreclosed_count"].sum())),
            ("Mean", f"{community_data['foreclosed_count'].mean():.2f}"),
            ("Median", f"{community_data['foreclosed_count'].median():.2f}"),
            ("Max", f"{community_data['foreclosed_count'].max():.0f}"),
        ]
        # add_statistical_summary_to_plot(
        #     ax,
        #     "Foreclosure Statistics",
        #     [{"section_title": "COMMUNITY AREA LEVEL", "stats": stats}],
        #     bgcolor="lightgray",
        #     x=0.65,
        #     y=0.05,
        # )

        # --- Save the figure ---
        output_path = Path(self.output_dir) / "foreclosed_top10_distribution.png"
        setup_figure_and_save(
            fig,
            output_path,
            "Top 10 Chicago Communities by Foreclosure Count",
            logger=logger,
        )

        return {"foreclosed_distribution_plot": str(output_path)}
