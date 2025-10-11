"""Correlation analysis visualizer.

This module creates visualizations for correlation analysis results.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class CorrelationVisualizer(Visualizer):
    """Create visualizations for the correlation analysis.

    This demonstrates how to create meaningful visualizations from merged spatial data.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the correlation visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "correlation_visualization",
            "Create visualizations for correlation analysis",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create correlation visualizations."""
        logger.info("Creating correlation visualizations...")

        correlation_matrix = context["correlation_matrix"]
        analysis_data = context["analysis_data"]
        summary_stats = context["summary_stats"]

        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(
            "Spatial Data Analysis: Community Area Rental Prices",
            fontsize=16,
            fontweight="bold",
        )

        # 1. Correlation heatmap
        sns.heatmap(
            correlation_matrix,
            annot=True,
            cmap="RdBu_r",
            center=0,
            square=True,
            ax=axes[0, 0],
        )
        axes[0, 0].set_title("Correlation Matrix")

        # 2. Area vs Average Rental Price
        axes[0, 1].scatter(
            analysis_data["area_km2"],
            analysis_data["avg_rental_price"],
            alpha=0.7,
            s=60,
        )
        axes[0, 1].set_xlabel("Area (km²)")
        axes[0, 1].set_ylabel("Average Rental Price ($)")
        axes[0, 1].set_title("Area vs Average Rental Price")
        axes[0, 1].grid(True, alpha=0.3)

        # Add trend line
        z = np.polyfit(analysis_data["area_km2"], analysis_data["avg_rental_price"], 1)
        p = np.poly1d(z)
        x_trend = np.linspace(
            analysis_data["area_km2"].min(), analysis_data["area_km2"].max(), 100
        )
        axes[0, 1].plot(x_trend, p(x_trend), "r--", alpha=0.8)

        # 3. Distribution of rental prices
        axes[1, 0].hist(
            analysis_data["avg_rental_price"],
            bins=20,
            alpha=0.7,
            color="skyblue",
            edgecolor="black",
        )
        axes[1, 0].set_xlabel("Average Rental Price ($)")
        axes[1, 0].set_ylabel("Number of Communities")
        axes[1, 0].set_title("Distribution of Average Rental Prices")
        axes[1, 0].grid(True, alpha=0.3)

        # 4. Statistical summary
        axes[1, 1].axis("off")
        stats_text = f"""
        Statistical Summary

        Total Communities: {summary_stats["total_communities"]}
        Communities with Data: {summary_stats["communities_with_data"]}

        Average Rental Price: ${summary_stats["avg_rental_price"]:,.0f}
        Standard Deviation: ${summary_stats["rental_price_std"]:,.0f}
        Average Area: {summary_stats["avg_area_km2"]:.1f} km²

        Key Correlations:
        • Area vs Avg Rent: {summary_stats["key_correlations"]["Area vs Average Rent"]:.3f}
        • Area vs Zip Count: {summary_stats["key_correlations"]["Area vs Zip Count"]:.3f}
        • Min vs Max Rent: {summary_stats["key_correlations"]["Min vs Max Rent"]:.3f}
        """

        axes[1, 1].text(
            0.05,
            0.95,
            stats_text,
            transform=axes[1, 1].transAxes,
            fontsize=10,
            verticalalignment="top",
            fontfamily="monospace",
            bbox={"boxstyle": "round,pad=0.5", "facecolor": "lightgray", "alpha": 0.8},
        )

        plt.tight_layout()

        # Save the plot
        output_path = Path(self.output_dir) / "correlation_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved visualization to: %s", output_path)

        plt.show()

        return {"visualization_path": str(output_path)}
