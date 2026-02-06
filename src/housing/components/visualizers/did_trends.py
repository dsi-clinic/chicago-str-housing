"""DiD trends visualizer.

This module creates an adoption curve, parallel trends plot, and pre-treatment balance comparison visualizations.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class DIDTrendsVisualizer(Visualizer):
    """Create visualizations for DID trends.

    Shows adoption curve, parallel trends plot, and pre-treatment balance comparison visualizations.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the DID trends visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "did_trends_visualizations",
            "Create visualizations for DID trends",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create visualizations for DID trends."""
        logger.info("Creating visualizations for DID trends...")

        treated_by_month = context.get("treated_by_month")
        avg_by_group = context.get("avg_by_group")
        first_treatment = context.get("first_treatment")
        pre_period = context.get("pre_period")
        pre_balance = context.get("pre_balance")

        # Plottting visualizations
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle("DID Trends Visualizations", fontsize=16, fontweight="bold")

        treated_by_month.plot(ax=ax1, label="Treated")
        ax1.set_ylabel("Number of Treated Tracts")
        ax1.set_xlabel("Month")
        ax1.set_title("STR Prohibition Adoption Over Time")

        avg_by_group.plot(ax=ax2)
        ax2.axvline(
            first_treatment, color="red", linestyle="--", label="First Treatment"
        )
        ax2.set_ylabel("Average Rental Price ($)")
        ax2.set_xlabel("Month")
        ax2.set_title("Parallel Trends Check")
        ax2.legend(title="Group")

        mean = pre_balance["mean"]
        std = pre_balance["std"]
        ax3.bar(
            ["Never Treated", "Eventually Treated"],
            mean,
            yerr=std,
            align="center",
            alpha=0.7,
            color="steelblue",
        )
        ax3.set_ylabel("Average Rental Price ($)")
        ax3.set_title("Pre-treatment Balance Comparison (Mean Rental Price)")

        never_treated = pre_period.loc[pre_period["ever_treated"] == 0, "rental_price"]
        eventually_treated = pre_period.loc[
            pre_period["ever_treated"] == 1, "rental_price"
        ]
        ax4.boxplot(
            [never_treated, eventually_treated],
            labels=["Never Treated", "Eventually Treated"],
        )
        ax4.set_ylabel("Rental Price ($)")
        ax4.set_xlabel("Group")
        ax4.set_title("Pre-treatment Balance Comparison (Mean Rental Distribution)")

        plt.tight_layout()

        # Save the plot
        output_path = Path(self.output_dir) / "did_trends_visualizations.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved visualization to: %s", output_path)

        return {"did_trends_visualizations": str(output_path)}
