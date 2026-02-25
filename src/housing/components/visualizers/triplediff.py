"""Triple-difference visualizer.

Plots average rental price by treatment x group over time (four lines)
and optional DDD coefficient summary.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class TripleDiffVisualizer(Visualizer):
    """Visualize triple-difference analysis: outcomes by treatment and group."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the triple-diff visualizer.

        Args:
            output_dir: Directory for saving plots.
        """
        super().__init__(
            "triplediff_visualization",
            "Plot DDD outcomes by treatment and census group",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Produce DDD plots and return paths."""
        ddd_panel = context["ddd_panel"]
        group_name = context.get("ddd_group_name", "high_income")

        output_dir = Path(context.get("output_dir", self.output_dir))
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1) Average rental price by month, treated, and group (4 lines)
        agg = (
            ddd_panel.groupby(["month", "treated", group_name])["rental_price"]
            .mean()
            .reset_index()
        )
        agg["treated_label"] = agg["treated"].map({0: "Control", 1: "Treated"})
        agg["group_label"] = agg[group_name].map({0: "Low", 1: "High"})
        agg["series"] = agg["treated_label"] + " / " + agg["group_label"]

        fig1, ax1 = plt.subplots(figsize=(10, 6))
        for name, sub in agg.groupby("series"):
            sub = sub.sort_values("month")
            ax1.plot(sub["month"], sub["rental_price"], label=name)

        first_treatment = ddd_panel.loc[ddd_panel["treated"] == 1, "month"].min()
        ax1.axvline(first_treatment, color="gray", linestyle="--", alpha=0.7)
        ax1.set_xlabel("Month")
        ax1.set_ylabel("Average Rental Price ($)")
        ax1.set_title("Triple-Diff: Average Rent by Treatment and Group")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        path1 = output_dir / "triplediff_trends_by_group.png"
        fig1.savefig(path1)
        plt.close(fig1)
        logger.info("Saved %s", path1)

        # 2) Bar plot of DDD coefficients if results in context
        path2 = None
        if "triplediff_results" in context:
            results = context["triplediff_results"]
            params = results.params
            # Prefer interaction term (DDD estimator); else all non-Intercept
            interaction_params = [
                (k, float(v)) for k, v in params.items()
                if ":" in str(k)
            ]
            if not interaction_params:
                interaction_params = [
                    (k, float(v)) for k, v in params.items()
                    if k != "Intercept"
                ]
            if interaction_params:
                fig2, ax2 = plt.subplots(figsize=(8, 4))
                names = [p[0] for p in interaction_params]
                vals = [p[1] for p in interaction_params]
                colors = ["#2e86ab" if v >= 0 else "#e94f37" for v in vals]
                ax2.barh(names, vals, color=colors)
                ax2.axvline(0, color="black", linewidth=0.5)
                ax2.set_xlabel("Coefficient ($)")
                ax2.set_title("Triple-Diff Coefficients")
                path2 = output_dir / "triplediff_coefficients.png"
                fig2.savefig(path2)
                plt.close(fig2)
                logger.info("Saved %s", path2)

        return {
            "triplediff_trends_plot": str(path1),
            "triplediff_coefficients_plot": str(path2) if path2 else None,
        }
