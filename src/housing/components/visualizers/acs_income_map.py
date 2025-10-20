import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)

# Minimum land area in square meters to exclude water-only tracts
# 10,000 sq meters = ~2.5 acres
MIN_LAND_AREA_SQ_METERS = 10000


class ACSIncomeVisualizer(Visualizer):
    """Create choropleth maps for the tract acs data"""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the rental map visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "acs_map_visualization",
            "Create choropleth maps for the tract ACS",
        )
        self.output_dir = output_dir or "/project/data/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create tract acs map visualizations."""
        logger.info("Creating tract acs map visualizations...")

        acs_tract_data = context["acs_tract_data"]
        rental_tract_data = context["tract_rental_data"]
        community_boundaries = context.get("community_boundaries")

        if acs_tract_data is None:
            logger.warning("No acs data available for mapping")
            return {}

        # Excluding the Lake Michigan GEOID
        acs_tract_data = acs_tract_data[acs_tract_data["GEOID"] != "17031990000"]
        rental_tract_data = rental_tract_data[
            rental_tract_data["GEOID"] != "17031990000"
        ]

        # Excluding the Outlier GEOID
        acs_tract_data = acs_tract_data[acs_tract_data["GEOID"] != "17031030702"]

        # Create figure with subplots
        fig, axes = plt.subplots(1, 2, figsize=(20, 10))
        fig.suptitle(
            "Census Tract Median Income & Rental Price by Geography",
            fontsize=20,
            fontweight="bold",
        )

        # 1. Census ACS Tract Level Map for Median Income
        # Create choropleth
        acs_tract_data.plot(
            column="median_house_income_density",
            ax=axes[0],
            legend=True,
            cmap="RdYlGn_r",  # Red (dense) to Green (sparse)
            edgecolor="black",
            linewidth=0.1,
            missing_kwds={"color": "lightgrey", "label": "No Data"},
            legend_kwds={
                "label": "Median Household Income ($)",
                "orientation": "horizontal",
                "shrink": 0.8,
                "pad": 0.05,
            },
        )

        axes[0].set_title(
            f"Median Household Income(n={acs_tract_data['median_house_income_density'].notna().sum()})",
            fontsize=16,
        )
        axes[0].axis("off")

        tract_income = acs_tract_data["median_house_income_density"].dropna()

        # Add statistics text
        stats_text = (
            f"Min: ${tract_income.min():.0f}\n"
            f"Median: ${tract_income.median()/1000:.01f} k \n"
            f"Max: ${tract_income.max()/1000:.01f} k "
        )
        axes[0].text(
            0.02,
            0.98,
            stats_text,
            transform=axes[0].transAxes,
            fontsize=12,
            verticalalignment="top",
            bbox={"boxstyle": "round,pad=0.5", "facecolor": "white", "alpha": 0.8},
        )

        # 2. Census Rental Tract Level Map for Median Income
        # Create choropleth
        rental_tract_data.plot(
            column="avg_rental_price",
            ax=axes[1],
            legend=True,
            cmap="RdYlGn_r",  # Red (expensive) to Green (affordable)
            edgecolor="black",
            linewidth=0.1,
            missing_kwds={"color": "lightgrey", "label": "No Data"},
            legend_kwds={
                "label": "Average Rental Price ($)",
                "orientation": "horizontal",
                "shrink": 0.8,
                "pad": 0.05,
            },
        )

        axes[1].set_title(
            f"Rental Price(n={rental_tract_data["avg_rental_price"].notna().sum()})",
            fontsize=16,
        )
        axes[1].axis("off")

        rental_tract_income = rental_tract_data["avg_rental_price"].dropna()

        # Add statistics text
        stats_text = (
            f"Min: ${rental_tract_income.min():.0f}\n"
            f"Median: ${rental_tract_income.median()/1000:.01f} k \n"
            f"Max: ${rental_tract_income.max()/1000:.01f} k "
        )
        axes[1].text(
            0.02,
            0.98,
            stats_text,
            transform=axes[1].transAxes,
            fontsize=12,
            verticalalignment="top",
            bbox={"boxstyle": "round,pad=0.5", "facecolor": "white", "alpha": 0.8},
        )
        plt.tight_layout()

        # Save the plot
        output_path = Path(self.output_dir) / "acs_income_map.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved map visualization to: %s", output_path)

        plt.close()

        return {"rental_map_plot": str(output_path)}
