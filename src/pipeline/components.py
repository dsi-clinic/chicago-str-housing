"""Core pipeline components for spatial data analysis demo.

This module demonstrates the key concepts students need to learn:
1. Loading different data formats (CSV, GeoJSON)
2. Spatial joins and geometry transformations
3. Merging datasets with different geometries
4. Analysis on merged spatial data
"""

import logging
import warnings
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from shapely import wkt

from pipeline.base import (
    Analyzer,
    DataLoader,
    DataProcessor,
    Visualizer,
    pipeline_component,
)

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")

# ============================================================================
# CONSTANTS
# ============================================================================

# Correlation strength thresholds
CORRELATION_NEGLIGIBLE_THRESHOLD = 0.1
CORRELATION_WEAK_THRESHOLD = 0.3
CORRELATION_MODERATE_THRESHOLD = 0.5
CORRELATION_STRONG_THRESHOLD = 0.7

# Statistical thresholds for correlation strength classification
STRONG_CORRELATION_THRESHOLD = 0.7
MODERATE_CORRELATION_THRESHOLD = 0.5

# ============================================================================
# DATA LOADERS
# ============================================================================


class RentalDataLoader(DataLoader):
    """Load rental price data from ZORI dataset.

    This demonstrates loading CSV data with geographic identifiers (zip codes).
    """

    def __init__(self, file_path: str | None = None) -> None:
        super().__init__(
            "rental_data",
            file_path or "/project/data/Zip_zori_uc_sfrcondomfr_sm_month.csv",
            "Load rental price data from ZORI dataset",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load and clean rental data."""
        logger.info("Loading rental data from: %s", self.file_path)

        # Load the CSV data
        rental_df = pd.read_csv(self.file_path)

        # Clean and prepare the data
        rental_df = rental_df.rename(columns={"RegionName": "zip_code"})
        rental_df["zip_code"] = rental_df["zip_code"].astype(str).str.zfill(5)

        # Get the most recent month's data
        date_columns = [col for col in rental_df.columns if col.startswith("20")]
        if date_columns:
            latest_month = sorted(date_columns)[-1]
            rental_df = rental_df[["zip_code", latest_month]].copy()
            rental_df = rental_df.rename(columns={latest_month: "rental_price"})
            rental_df = rental_df.dropna()

        logger.info("Loaded %d zip codes with rental data", len(rental_df))
        logger.info(
            "Rental price range: $%.0f - $%.0f",
            rental_df["rental_price"].min(),
            rental_df["rental_price"].max(),
        )

        return {"rental_data": rental_df}


class ZipBoundariesLoader(DataLoader):
    """Load zip code boundary data.

    This demonstrates loading GeoJSON data with polygon geometries.
    """

    def __init__(self, file_path: str | None = None) -> None:
        super().__init__(
            "zip_boundaries",
            file_path or "/project/data/Boundaries_ZIP_Codes.csv",
            "Load zip code boundary data",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load zip code boundaries."""
        logger.info("Loading zip boundaries from: %s", self.file_path)

        # Load CSV with polygon coordinates
        zip_df = pd.read_csv(self.file_path)

        # Convert to GeoDataFrame
        zip_df["geometry"] = zip_df["the_geom"].apply(wkt.loads)
        gdf = gpd.GeoDataFrame(zip_df, geometry="geometry")

        # Set CRS
        gdf = gdf.set_crs("EPSG:4326")

        # Clean zip code column
        if "ZIP" in gdf.columns:
            gdf = gdf.rename(columns={"ZIP": "zip_code"})
        gdf["zip_code"] = gdf["zip_code"].astype(str).str.zfill(5)

        logger.info("Loaded %d zip code boundaries", len(gdf))
        logger.info("CRS: %s", gdf.crs)

        return {"zip_boundaries": gdf}


class CommunityBoundariesLoader(DataLoader):
    """Load community area boundary data.

    This demonstrates loading CSV data with polygon coordinates that need
    to be converted to GeoDataFrame.
    """

    def __init__(self, file_path: str | None = None) -> None:
        super().__init__(
            "community_boundaries",
            file_path or "/project/data/Boundaries_Community_Areas.csv",
            "Load community area boundary data",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load community area boundaries."""
        logger.info("Loading community boundaries from: %s", self.file_path)

        # Load CSV with polygon coordinates
        community_df = pd.read_csv(self.file_path)

        # Convert to GeoDataFrame
        community_df["geometry"] = community_df["the_geom"].apply(wkt.loads)
        gdf = gpd.GeoDataFrame(community_df, geometry="geometry")

        # Set CRS
        gdf = gdf.set_crs("EPSG:4326")

        # Clean column names
        gdf = gdf.rename(columns={"COMMUNITY": "community_name"})

        logger.info("Loaded %d community area boundaries", len(gdf))
        logger.info("CRS: %s", gdf.crs)

        return {"community_boundaries": gdf}


# ============================================================================
# DATA PROCESSORS
# ============================================================================


class SpatialJoinProcessor(DataProcessor):
    """Perform spatial join to transform data from zip codes to community areas.

    This is the CORE CONCEPT students need to understand:
    - How to join data with different geometries
    - How to aggregate data when geometries don't align perfectly
    - How to handle overlapping boundaries
    """

    def __init__(self) -> None:
        super().__init__(
            "spatial_join", "Transform rental data from zip codes to community areas"
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform spatial join and aggregation."""
        logger.info("Performing spatial join: zip codes -> community areas")

        # Get the data from context
        rental_data = context["rental_data"]
        zip_boundaries = context["zip_boundaries"]
        community_boundaries = context["community_boundaries"]

        # Step 1: Join rental data with zip boundaries
        logger.info("Step 1: Joining rental data with zip boundaries...")
        zip_rental = zip_boundaries.merge(rental_data, on="zip_code", how="inner")
        logger.info("Joined %d zip codes with rental data", len(zip_rental))

        # Step 2: Spatial join - zip codes to community areas
        logger.info("Step 2: Performing spatial join (zip codes -> community areas)...")

        # Ensure same CRS for spatial operations
        if zip_rental.crs != community_boundaries.crs:
            community_boundaries = community_boundaries.to_crs(zip_rental.crs)

        # Perform spatial join
        # This is the key concept: how to handle overlapping geometries
        spatial_join = gpd.sjoin(
            zip_rental, community_boundaries, how="inner", predicate="intersects"
        )

        logger.info(
            "Spatial join resulted in %d zip-community pairs", len(spatial_join)
        )

        # Step 3: Aggregate rental prices by community area
        logger.info("Step 3: Aggregating rental prices by community area...")

        # Calculate area-weighted average rental price
        # This is another key concept: how to properly aggregate spatial data
        spatial_join["zip_area"] = spatial_join.geometry.area
        spatial_join["weighted_rent"] = (
            spatial_join["rental_price"] * spatial_join["zip_area"]
        )

        community_rental = (
            spatial_join.groupby("community_name")
            .agg(
                {
                    "weighted_rent": "sum",
                    "zip_area": "sum",
                    "rental_price": ["mean", "min", "max", "count"],
                }
            )
            .reset_index()
        )

        # Flatten column names
        community_rental.columns = [
            "community_name",
            "total_weighted_rent",
            "total_area",
            "avg_rental_price",
            "min_rental_price",
            "max_rental_price",
            "zip_count",
        ]

        # Calculate area-weighted average
        community_rental["area_weighted_avg_rent"] = (
            community_rental["total_weighted_rent"] / community_rental["total_area"]
        )

        # Step 4: Join back with community boundaries for final result
        final_result = community_boundaries.merge(
            community_rental, on="community_name", how="left"
        )

        logger.info("Final result: %d community areas", len(final_result))
        logger.info(
            "Areas with rental data: %d", final_result["avg_rental_price"].notna().sum()
        )

        return {"community_rental_data": final_result}


# ============================================================================
# ANALYZERS
# ============================================================================


class CorrelationAnalyzer(Analyzer):
    """Analyze correlations in the merged spatial dataset.

    This demonstrates how to perform statistical analysis on merged spatial data.
    """

    def __init__(self) -> None:
        super().__init__(
            "correlation_analysis", "Analyze correlations in community rental data"
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform correlation analysis."""
        logger.info("Performing correlation analysis on community rental data...")

        data = context["community_rental_data"]

        # Calculate area statistics
        data["area_km2"] = data.geometry.area / 1_000_000  # Convert to km²

        # Prepare numeric columns for analysis
        numeric_cols = [
            "area_weighted_avg_rent",
            "avg_rental_price",
            "min_rental_price",
            "max_rental_price",
            "zip_count",
            "area_km2",
        ]

        # Remove rows with missing data
        analysis_data = data[numeric_cols].dropna()

        logger.info(
            "Analyzing %d community areas with complete data", len(analysis_data)
        )

        # Calculate correlation matrix
        correlation_matrix = analysis_data.corr()

        # Key correlations to highlight
        key_correlations = {
            "Area vs Average Rent": correlation_matrix.loc[
                "area_km2", "avg_rental_price"
            ],
            "Area vs Zip Count": correlation_matrix.loc["area_km2", "zip_count"],
            "Min vs Max Rent": correlation_matrix.loc[
                "min_rental_price", "max_rental_price"
            ],
            "Average vs Area-Weighted Rent": correlation_matrix.loc[
                "avg_rental_price", "area_weighted_avg_rent"
            ],
        }

        # Statistical summary
        summary_stats = {
            "total_communities": len(data),
            "communities_with_data": len(analysis_data),
            "avg_rental_price": analysis_data["avg_rental_price"].mean(),
            "rental_price_std": analysis_data["avg_rental_price"].std(),
            "avg_area_km2": analysis_data["area_km2"].mean(),
            "key_correlations": key_correlations,
        }

        logger.info("Key Correlations Found:")
        for name, corr in key_correlations.items():
            strength = self._get_correlation_strength(abs(corr))
            logger.info("  %s: %.3f (%s)", name, corr, strength)

        return {
            "correlation_matrix": correlation_matrix,
            "analysis_data": analysis_data,
            "summary_stats": summary_stats,
        }

    def _get_correlation_strength(self, abs_corr: float) -> str:
        """Classify correlation strength."""
        if abs_corr >= CORRELATION_STRONG_THRESHOLD:
            return "Strong"
        elif abs_corr >= CORRELATION_MODERATE_THRESHOLD:
            return "Moderate"
        elif abs_corr >= CORRELATION_WEAK_THRESHOLD:
            return "Weak"
        else:
            return "Negligible"


# ============================================================================
# VISUALIZERS
# ============================================================================


class CorrelationVisualizer(Visualizer):
    """Create visualizations for the correlation analysis.

    This demonstrates how to create meaningful visualizations from merged spatial data.
    """

    def __init__(self, output_dir: str | None = None) -> None:
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


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


@pipeline_component(
    name="summary_reporter", description="Generate a summary report of the analysis"
)
def summary_reporter(context: dict[str, Any]) -> dict[str, Any]:
    """Generate a summary report of the analysis.

    This demonstrates how to create summary reports from pipeline results.
    """
    logger.info("Generating summary report...")
    print("\n" + "=" * 60)
    print("SPATIAL DATA ANALYSIS SUMMARY REPORT")
    print("=" * 60)

    # Get summary stats
    summary_stats = context.get("summary_stats", {})

    print("\nDataset Overview:")
    print(f"  • Total Community Areas: {summary_stats.get('total_communities', 'N/A')}")
    print(
        f"  • Areas with Rental Data: {summary_stats.get('communities_with_data', 'N/A')}"
    )

    print("\nRental Price Statistics:")
    print(f"  • Average: ${summary_stats.get('avg_rental_price', 0):,.0f}")
    print(f"  • Standard Deviation: ${summary_stats.get('rental_price_std', 0):,.0f}")

    print("\nKey Insights:")
    correlations = summary_stats.get("key_correlations", {})
    for name, corr in correlations.items():
        strength = (
            "Strong"
            if abs(corr) >= STRONG_CORRELATION_THRESHOLD
            else "Moderate"
            if abs(corr) >= MODERATE_CORRELATION_THRESHOLD
            else "Weak"
        )
        print(f"  • {name}: {corr:.3f} ({strength})")

    return {"report_generated": True}
