"""Airbnb, ACS, and Rental price distribution visualizer.

This module creates visualizations showing Airbnb, ACS, and Rental price distributions
at both tract and community area levels.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import seaborn as sns

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class IncomePriceDistributionVisualizer(Visualizer):
    """Create visualizations for Airbnb, ACS, and Rental price distributions.

    Shows Airbnb, ACS, and Rental prices aggregated at  census tract levels
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the Airbnb, ACS, and Rental distribution visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "airbnb_acs_rental distribution_visualization",
            "Create visualizations for Airbnb, ACS, and Rental price distributions",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create Airbnb, ACS, and Rental distribution visualizations."""
        logger.info("Creating Airbnb, ACS, and Rental distribution visualizations...")

        airbnb_tract_data = context.get("airbnb_tract_data")
        acs_tract_data = context.get("acs_tract_data")
        rental_tract_data = context.get("tract_rental_data")

        if airbnb_tract_data is None:
            logger.warning("No Airbnb tract data available for visualizations")
            return {}

        if acs_tract_data is None:
            logger.warning("No ACS tract data available for visualizations")
            return {}

        if rental_tract_data is None:
            logger.warning("No Rental tract data available for visualizations")
            return {}

        acs_tract_data["monthly_income"] = acs_tract_data["median_house_income"] / 12
        airbnb_tract_data["monthly_airbnb_price"] = (
            airbnb_tract_data["price_numeric_mean"] * 30
        )

        acs_airbnb_merge = acs_tract_data.merge(
            airbnb_tract_data, how="inner", on="tract_geoid"
        )
        all_data = acs_airbnb_merge.merge(
            rental_tract_data, how="inner", on="tract_geoid"
        )

        data = all_data[["monthly_income", "avg_rental_price", "monthly_airbnb_price"]]

        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(
            "Chicago Airbnb Price Distribution Analysis",
            fontsize=18,
            fontweight="bold",
            y=0.98,  # Move title higher
        )

        # 1. Correlation Map
        corr_matrix = data.corr()
        labels = ["monthly_income", "avg_rental_price", "monthly_airbnb_price"]
        # Create correlation heatmap

        sns.heatmap(
            corr_matrix,
            annot=True,
            fmt=".3f",
            cmap="RdBu_r",
            center=0.0,
            square=True,
            ax=axes[0, 0],
            cbar_kws={"shrink": 0.7, "label": "Correlation"},
            vmin=-1,
            vmax=1,
            linewidths=0.5,
            linecolor="white",
        )

        axes[0, 0].set_xticklabels(labels, rotation=45, ha="right")
        axes[0, 0].set_yticklabels(labels, rotation=0)
        axes[0, 0].set_title(
            "Correlation Matrix: ACS , Airbnb & Rental", fontsize=11, pad=10
        )

        # 2. Monthly Income VS Rental Price scatter plot
        if (
            data is not None
            and "monthly_income" in data.columns
            and "avg_rental_price" in data.columns
        ):
            box_data = data[["monthly_income", "avg_rental_price"]].dropna()

            axes[0, 1].scatter(
                box_data["monthly_income"],
                box_data["avg_rental_price"],
                alpha=0.6,
                color="purple",
                s=20,
            )
            axes[0, 1].set_xlabel("Monthly Household Income ($)", fontsize=12)
            axes[0, 1].set_ylabel("Average Rental Price ($)", fontsize=12)
            axes[0, 1].set_title("Monthly Income vs Rental Price", fontsize=14)
            axes[0, 1].grid(True, alpha=0.3)
        # 3. Boxplot of Montly Income, Airbnb Price, and Rental Price
        if data is not None:
            box_data = data.dropna()

            bp = axes[1, 0].boxplot(
                box_data,
                labels=[
                    "Household Income",
                    "Average Rental Price",
                    "Average Airbnb Price",
                ],
                patch_artist=True,
                showmeans=True,
                meanline=True,
            )
            # Color the boxes
            bp["boxes"][0].set_facecolor("steelblue")
            bp["boxes"][1].set_facecolor("forestgreen")
            bp["boxes"][2].set_facecolor("darkorange")

            axes[1, 0].set_ylabel("Average Income or Price($)", fontsize=12)
            axes[1, 0].set_title("Month Income and Price Comparison", fontsize=14)
            axes[1, 0].grid(True, alpha=0.3, axis="y")

        # 4. Statistical summary
        axes[1, 1].axis("off")
        stats_lines = [
            "Monthly Income and Price Analysis Statistics\n" + "=" * 40 + "\n"
        ]

        if data is not None:
            if "monthly_income" in data.columns:
                tract_income = data["monthly_income"].dropna()
                stats_lines.append("HOUSEHOLD INCOME ANALYSIS:")
                stats_lines.append(f"  Count: {len(tract_income)}")
                stats_lines.append(f"  Mean: ${tract_income.mean():.2f}")
                stats_lines.append(f"  Median: ${tract_income.median():.2f}")
                stats_lines.append(f"  Std Dev: ${tract_income.std():.2f}")
                stats_lines.append(f"  Min: ${tract_income.min():.2f}")
                stats_lines.append(f"  Max: ${tract_income.max():.2f}")
                stats_lines.append("")

            if "avg_rental_price" in data.columns:
                tract_rental = data["avg_rental_price"].dropna()
                stats_lines.append("RENTAL PRICE ANALYSIS:")
                stats_lines.append(f"  Count: {len(tract_rental)}")
                stats_lines.append(f"  Mean: ${tract_rental.mean():.2f}")
                stats_lines.append(f"  Median: ${tract_rental.median():.2f}")
                stats_lines.append(f"  Std Dev: ${tract_rental.std():.2f}")
                stats_lines.append(f"  Min: ${tract_rental.min():.2f}")
                stats_lines.append(f"  Max: ${tract_rental.max():.2f}")
                stats_lines.append("")

            if "monthly_airbnb_price" in data.columns:
                tract_airbnb = data["monthly_airbnb_price"].dropna()
                stats_lines.append("AIRBNB PRICE COUNTS:")
                stats_lines.append(f"  Count: {len(tract_airbnb)}")
                stats_lines.append(f"  Mean: ${tract_airbnb.mean():.2f}")
                stats_lines.append(f"  Median: ${tract_airbnb.median():.2f}²")
                stats_lines.append(f"  Std Dev: ${tract_airbnb.std():.2f}")
                stats_lines.append(f"  Min: ${tract_airbnb.min():.2f}")
                stats_lines.append(f"  Max: ${tract_airbnb.max():.2f}")
                stats_lines.append("")

        stats_text = "\n".join(stats_lines)

        axes[1, 1].text(
            0.05,
            0.95,
            stats_text,
            transform=axes[1, 1].transAxes,
            fontsize=11,
            verticalalignment="top",
            fontfamily="monospace",
            bbox={"boxstyle": "round,pad=0.8", "facecolor": "lightblue", "alpha": 0.8},
        )

        plt.tight_layout()
        plt.subplots_adjust(top=0.85)  # Increase space for title

        # Save the plot
        output_path = (
            Path(self.output_dir) / "airbnb_acs_rental_distribution_analysis.png"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved visualization to: %s", output_path)

        plt.close()

        return {"airbnb_acs_rental_distribution_plot": str(output_path)}
