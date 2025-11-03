"""STR EDA visualizer.

This module creates visualizations showing STR EDA at tract and community levels.
"""

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class STRUnitsTop10(Visualizer):
    """Create visualizations for Top 10 STR unit-Dense Communities"""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the STR Units Top 10 Visualizer

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "str_units_top_10_visualization",
            "Create visualizations for Top 10 STR Unit-Dense areas",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create and save visualizations for STR units data.

        Expects 'str_units_community_data' in context.
        """
        logger.info("Starting STR Units EDA visualizations...")

        community_data = context.get("str_units_community_data")

        if community_data is None or not isinstance(community_data, gpd.GeoDataFrame):
            logger.error("No valid community data found in context.")
            return {}

        # Creating figure
        fig, axes = plt.subplots(
            1, 2, figsize=(12, 8), gridspec_kw={"width_ratios": [1, 0.8]}
        )
        plt.subplots_adjust(wspace=0.3)

        fig.suptitle(
            "Top 10 STR Unit-Dense Communities in Chicago",
            fontsize=18,
            fontweight="bold",
            y=0.98,
        )

        logger.info("Creating STR units density map and Top 10 bar chart...")

        # Map: STR Units Density by Community Area
        community_data.plot(
            column="str_units_density",
            ax=axes[0],
            legend=True,
            cmap="RdYlGn_r",
            edgecolor="black",
            linewidth=0.2,
            missing_kwds={"color": "lightgrey", "label": "No Data"},
            legend_kwds={
                "label": "STR Density (listings/km²)",
                "orientation": "horizontal",
                "shrink": 0.7,
                "pad": 0.05,
            },
        )

        axes[0].set_title(
            f"STR Units Density by Community Area (n={community_data['str_units_density'].notna().sum()})",
            fontsize=14,
        )
        axes[0].set_aspect("equal", adjustable="datalim")
        axes[0].autoscale()
        axes[0].axis("off")

        # Add density summary stats
        density = community_data["str_units_density"].dropna()
        stats_text = (
            f"Min: {density.min():.2f}\n"
            f"Median: {density.median():.2f}\n"
            f"Max: {density.max():.2f}"
        )
        axes[0].text(
            0.02,
            0.98,
            stats_text,
            transform=axes[0].transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox={"boxstyle": "round,pad=0.5", "facecolor": "white", "alpha": 0.8},
        )

        # Bar Chart: Top 10 Communities by Density
        top10 = (
            community_data[["community_name", "str_units_density"]]
            .dropna()
            .sort_values(by="str_units_density", ascending=False)
            .head(10)
        )

        sns.barplot(
            data=top10,
            y="community_name",
            x="str_units_density",
            ax=axes[1],
        )

        axes[1].set_title("Top 10 Communities by STR Units Density", fontsize=14)
        axes[1].set_xlabel("STR Units Density (listings per km²)", fontsize=12)
        axes[1].set_ylabel("Community Area", fontsize=12)
        axes[1].grid(True, axis="x", alpha=0.3)
        axes[1].set_yticklabels(
            axes[1].get_yticklabels(),
            rotation=0,
            ha="right",
            fontsize=9,
        )

        plt.tight_layout(rect=[0, 0, 1, 0.95])

        # Save the Plot
        output_path = Path(self.output_dir) / "str_units_top10_visualization.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved visualization to: %s", output_path)
        plt.close(fig)

        return {"str_units_top10_plot": str(output_path)}
