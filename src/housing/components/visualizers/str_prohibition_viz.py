"""STR prohibition visualization module.

Creates visualizations for short-term rental prohibition analysis.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from housing.components.utils import (
    add_statistical_summary_to_plot,
    calculate_pairwise_correlation_matrix,
    create_correlation_heatmap,
    create_scatter_with_trend,
    setup_figure_and_save,
)
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class STRProhibitionVisualizer(Visualizer):
    """Create visualizations for STR prohibition analysis."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the STR prohibition visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "str_prohibition_visualization",
            "Create visualizations for STR prohibition analysis",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create STR prohibition visualizations."""
        logger.info("Creating STR prohibition visualizations...")

        # Get data from context
        str_tract_analysis = context.get("str_tract_analysis")
        str_correlations = context.get("str_correlations", {})
        str_summary = context.get("str_summary", {})

        if str_tract_analysis is None or len(str_tract_analysis) == 0:
            logger.warning(
                "No STR tract analysis data available, skipping visualization"
            )
            return {}

        # Create figure with subplots
        fig = plt.figure(figsize=(16, 10))
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

        # 1. STR Density vs Rental Price
        ax1 = fig.add_subplot(gs[0, 0])
        if (
            "str_prohibition_density" in str_tract_analysis.columns
            and "avg_rental_price" in str_tract_analysis.columns
        ):
            # Cap extreme values at 99th percentile for readability
            x_data = str_tract_analysis["str_prohibition_density"].dropna()
            y_data = str_tract_analysis["avg_rental_price"].dropna()

            if len(x_data) > 0 and len(y_data) > 0:
                x_cap = np.percentile(x_data, 99)
                y_cap = np.percentile(y_data, 99)
                x_clipped = x_data.clip(upper=x_cap)
                y_clipped = y_data.clip(upper=y_cap)

                create_scatter_with_trend(
                    ax1,
                    x_clipped,
                    y_clipped,
                    "STR Units Density vs Rental Price",
                    "STR Units Density (per km²)",
                    "Average Rental Price ($)",
                    color="purple",
                )

        # 2. STR Density vs Airbnb Density
        ax2 = fig.add_subplot(gs[0, 1])
        if (
            "str_prohibition_density" in str_tract_analysis.columns
            and "airbnb_density" in str_tract_analysis.columns
        ):
            # Cap extreme values at 99th percentile for readability
            x_data = str_tract_analysis["str_prohibition_density"].dropna()
            y_data = str_tract_analysis["airbnb_density"].dropna()

            if len(x_data) > 0 and len(y_data) > 0:
                x_cap = np.percentile(x_data, 99)
                y_cap = np.percentile(y_data, 99)
                x_clipped = x_data.clip(upper=x_cap)
                y_clipped = y_data.clip(upper=y_cap)

                create_scatter_with_trend(
                    ax2,
                    x_clipped,
                    y_clipped,
                    "STR Units Density vs Airbnb Units Density",
                    "STR Units Density (per km²)",
                    "Airbnb Units Density (per km²)",
                    color="green",
                )

        # 3. Comprehensive Correlation Matrix
        ax3 = fig.add_subplot(gs[1, 0])
        # Build correlation matrix using pairwise correlations (same logic as analyzer)
        corr_cols = []
        corr_labels = []

        # Select available columns for correlation matrix - density metrics only
        if "str_prohibition_density" in str_tract_analysis.columns:
            corr_cols.append("str_prohibition_density")
            corr_labels.append("STR Units\nDensity")
        if "avg_rental_price" in str_tract_analysis.columns:
            corr_cols.append("avg_rental_price")
            corr_labels.append("Rental\nPrice")
        if "airbnb_density" in str_tract_analysis.columns:
            corr_cols.append("airbnb_density")
            corr_labels.append("Airbnb Units\nDensity")

        min_corr_vars = 2  # Minimum variables for correlation matrix
        min_data_points = 10  # Minimum data points for reliable correlations

        if len(corr_cols) >= min_corr_vars:
            # Calculate pairwise correlation matrix to match analyzer logic
            corr_matrix = calculate_pairwise_correlation_matrix(
                str_tract_analysis, corr_cols, min_data_points
            )

            # Create correlation heatmap using utility function
            create_correlation_heatmap(
                ax3,
                corr_matrix,
                corr_labels,
                "Correlation Matrix: STR, Airbnb & Rental",
            )
        else:
            ax3.text(
                0.5,
                0.5,
                "Insufficient variables",
                ha="center",
                va="center",
                transform=ax3.transAxes,
            )
            ax3.set_title("Correlation Matrix")
            ax3.axis("off")

        # 4. Summary statistics
        ax4 = fig.add_subplot(gs[1, 1])

        data_sections = [
            {
                "section_title": "OVERVIEW",
                "stats": [
                    ("Total Buildings", str_summary.get("total_buildings", "N/A")),
                    (
                        "Tracts with Prohibitions",
                        str_summary.get("tracts_with_prohibitions", "N/A"),
                    ),
                ],
            }
        ]

        if "avg_rent_with_prohibitions" in str_summary:
            data_sections.append(
                {
                    "section_title": "AVERAGE RENT COMPARISON",
                    "stats": [
                        (
                            "With Prohibitions",
                            f"${str_summary['avg_rent_with_prohibitions']:,.0f}",
                        ),
                        (
                            "Without Prohibitions",
                            f"${str_summary['avg_rent_without_prohibitions']:,.0f}",
                        ),
                        ("Difference", f"${str_summary['rent_difference']:,.0f}"),
                    ],
                }
            )

        if str_correlations:
            correlation_stats = []
            for name, corr in str_correlations.items():
                if "Density" in name:
                    correlation_stats.append((name, f"{corr:.3f}"))

            if correlation_stats:
                data_sections.append(
                    {
                        "section_title": "KEY CORRELATIONS (DENSITY METRICS)",
                        "stats": correlation_stats,
                    }
                )

        add_statistical_summary_to_plot(
            ax4,
            "Statistical Summary",
            data_sections,
            bgcolor="lightgray",
        )

        # Save the plot
        output_path = Path(self.output_dir) / "str_correlation_analysis.png"
        setup_figure_and_save(
            fig,
            output_path,
            "Chicago Short-Term Rental Prohibition Correlation Analysis",
            logger=logger,
        )

        return {"str_visualization_path": str(output_path)}
