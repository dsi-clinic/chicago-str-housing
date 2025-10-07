"""Concrete pipeline components for Chicago housing analysis.

This module contains specific implementations of pipeline components
for data loading, processing, analysis, and visualization.
"""

import warnings
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from pipeline.base import (
    Analyzer,
    DataLoader,
    DataProcessor,
    Visualizer,
    pipeline_component,
)

warnings.filterwarnings("ignore")

# ============================================================================
# CONSTANTS
# ============================================================================

# Correlation strength thresholds
CORRELATION_NEGLIGIBLE_THRESHOLD = 0.1
CORRELATION_WEAK_THRESHOLD = 0.3
CORRELATION_MODERATE_THRESHOLD = 0.5
CORRELATION_STRONG_THRESHOLD = 0.7

# ============================================================================
# DATA LOADERS
# ============================================================================


class RentalDataLoader(DataLoader):
    """Load rental price data from ZORI dataset."""

    def __init__(
        self, file_path: str = "/project/data/Zip_zori_uc_sfrcondomfr_sm_month.csv"
    ) -> None:
        super().__init__(
            "rental_data", file_path, "Load rental price data from ZORI dataset"
        )

    def execute(self, context: dict[str, Any]) -> pd.DataFrame:
        """Load and process rental data."""
        print(f"Loading rental data from: {self.file_path}")

        # Load the data
        rental_data = pd.read_csv(self.file_path)

        # Identify date columns (they start with 20)
        date_columns = [col for col in rental_data.columns if col.startswith("20")]
        print(f"Found {len(date_columns)} date columns")

        # Get the most recent data (last 12 months)
        recent_columns = date_columns[-12:]
        print(f"Using last 12 months: {recent_columns[0]} to {recent_columns[-1]}")

        # Calculate average rental price for each ZIP code over the last 12 months
        rental_data["avg_rental_price"] = rental_data[recent_columns].mean(axis=1)

        # Create a clean dataset with ZIP codes and average rental prices
        zip_rental_prices = rental_data[["RegionName", "avg_rental_price"]].copy()
        zip_rental_prices.columns = ["zip_code", "avg_rental_price"]
        zip_rental_prices = zip_rental_prices.dropna()

        print(f"Processed {len(zip_rental_prices)} ZIP codes with rental data")

        return zip_rental_prices


class ZipBoundariesLoader(DataLoader):
    """Load ZIP code boundaries."""

    def __init__(
        self, file_path: str = "/project/data/Boundaries_ZIP_Codes.csv"
    ) -> None:
        super().__init__("zip_boundaries", file_path, "Load ZIP code boundaries")

    def execute(self, context: dict[str, Any]) -> gpd.GeoDataFrame:
        """Load and process ZIP boundaries."""
        print(f"Loading ZIP boundaries from: {self.file_path}")

        # Load the data
        zip_boundaries = gpd.read_file(self.file_path)

        # Set CRS if not already set
        if zip_boundaries.crs is None:
            zip_boundaries = zip_boundaries.set_crs("EPSG:4326")

        # Check if we need to convert geometry from WKT strings
        if zip_boundaries.geometry.isna().all():
            print("ZIP boundaries geometry is empty. Checking for WKT column...")
            geom_cols = [
                col
                for col in zip_boundaries.columns
                if "geom" in col.lower() or "wkt" in col.lower()
            ]
            print(f"Potential geometry columns: {geom_cols}")

            if geom_cols:
                from shapely import wkt

                zip_boundaries["geometry"] = zip_boundaries[geom_cols[0]].apply(
                    wkt.loads
                )
                print("Converted WKT to geometry for ZIP boundaries")

        print(f"Loaded {len(zip_boundaries)} ZIP boundaries")
        print(
            f"Valid geometries: {zip_boundaries.geometry.is_valid.sum()}/{len(zip_boundaries)}"
        )

        return zip_boundaries


class CommunityBoundariesLoader(DataLoader):
    """Load community area boundaries."""

    def __init__(
        self, file_path: str = "/project/data/Boundaries_Community_Areas.csv"
    ) -> None:
        super().__init__(
            "community_boundaries", file_path, "Load community area boundaries"
        )

    def execute(self, context: dict[str, Any]) -> gpd.GeoDataFrame:
        """Load and process community boundaries."""
        print(f"Loading community boundaries from: {self.file_path}")

        # Load the data
        community_boundaries = gpd.read_file(self.file_path)

        # Set CRS if not already set
        if community_boundaries.crs is None:
            community_boundaries = community_boundaries.set_crs("EPSG:4326")

        # Check if we need to convert geometry from WKT strings
        if community_boundaries.geometry.isna().all():
            print("Community boundaries geometry is empty. Checking for WKT column...")
            geom_cols = [
                col
                for col in community_boundaries.columns
                if "geom" in col.lower() or "wkt" in col.lower()
            ]
            print(f"Potential geometry columns: {geom_cols}")

            if geom_cols:
                from shapely import wkt

                community_boundaries["geometry"] = community_boundaries[
                    geom_cols[0]
                ].apply(wkt.loads)
                print("Converted WKT to geometry for community boundaries")

        print(f"Loaded {len(community_boundaries)} community boundaries")
        print(
            f"Valid geometries: {community_boundaries.geometry.is_valid.sum()}/{len(community_boundaries)}"
        )

        return community_boundaries


class HouseShareDataLoader(DataLoader):
    """Load house share prohibition data."""

    def __init__(
        self,
        file_path: str = "/project/data/aggregated_house_share_buildings_by_community.csv",
    ) -> None:
        super().__init__(
            "house_share_data", file_path, "Load house share prohibition data"
        )

    def execute(self, context: dict[str, Any]) -> pd.DataFrame:
        """Load and process house share data."""
        print(f"Loading house share data from: {self.file_path}")

        # Load the data
        house_share_data = pd.read_csv(self.file_path)

        # Clean up community names for merging
        house_share_data["community_area"] = (
            house_share_data["COMMUNITY"].str.upper().str.strip()
        )

        print(f"Loaded house share data for {len(house_share_data)} community areas")

        return house_share_data


# ============================================================================
# DATA PROCESSORS
# ============================================================================


class SpatialJoinProcessor(DataProcessor):
    """Create ZIP code to community area mapping using spatial joins."""

    def __init__(self) -> None:
        super().__init__("spatial_join", "Create ZIP code to community area mapping")
        self.dependencies = ["zip_boundaries", "community_boundaries"]
        self.required_data = ["zip_boundaries", "community_boundaries"]
        self.output_data = ["zip_community_mapping"]

    def execute(self, context: dict[str, Any]) -> pd.DataFrame:
        """Perform spatial join to map ZIP codes to community areas."""
        zip_boundaries = context["zip_boundaries"]
        community_boundaries = context["community_boundaries"]

        print("Performing spatial join to map ZIP codes to community areas...")

        # Ensure both GeoDataFrames have the same CRS
        if zip_boundaries.crs != community_boundaries.crs:
            community_boundaries = community_boundaries.to_crs(zip_boundaries.crs)

        # Perform spatial join to map ZIP codes to community areas
        zip_to_community_all = gpd.sjoin(
            zip_boundaries, community_boundaries, how="inner", predicate="intersects"
        )

        print(
            f"Initial spatial join results: {len(zip_to_community_all)} ZIP-Community mappings"
        )

        # Check for duplicate ZIP codes (multiple community area matches)
        duplicate_zips = zip_to_community_all["ZIP"].value_counts()
        duplicate_zips = duplicate_zips[duplicate_zips > 1]
        print(f"ZIP codes with multiple community area matches: {len(duplicate_zips)}")

        # For each ZIP code, find the community area with the largest intersection
        zip_to_community_fixed = []

        for zip_code in zip_to_community_all["ZIP"].unique():
            zip_matches = zip_to_community_all[zip_to_community_all["ZIP"] == zip_code]

            if len(zip_matches) == 1:
                # Only one match, use it
                zip_to_community_fixed.append(zip_matches.iloc[0])
            else:
                # Multiple matches, find the one with largest intersection
                zip_geom = zip_boundaries[
                    zip_boundaries["ZIP"] == zip_code
                ].geometry.iloc[0]
                best_match = None
                max_intersection = 0

                for _, row in zip_matches.iterrows():
                    community_geom = community_boundaries[
                        community_boundaries["COMMUNITY"] == row["COMMUNITY"]
                    ].geometry.iloc[0]
                    intersection_area = zip_geom.intersection(community_geom).area
                    if intersection_area > max_intersection:
                        max_intersection = intersection_area
                        best_match = row

                if best_match is not None:
                    zip_to_community_fixed.append(best_match)

        # Convert back to DataFrame
        zip_to_community = pd.DataFrame(zip_to_community_fixed)

        print(
            f"After resolving duplicates: {len(zip_to_community)} unique ZIP-Community mappings"
        )

        # Clean up the mapping
        zip_community_mapping = zip_to_community[["ZIP", "COMMUNITY"]].copy()
        zip_community_mapping.columns = ["zip_code", "community_area"]

        # Convert ZIP codes to string for consistent matching
        zip_community_mapping["zip_code"] = zip_community_mapping["zip_code"].astype(
            str
        )

        # Verify no duplicate ZIP codes
        duplicate_check = zip_community_mapping["zip_code"].value_counts()
        duplicates = duplicate_check[duplicate_check > 1]
        if len(duplicates) > 0:
            print(f"WARNING: Still have {len(duplicates)} duplicate ZIP codes!")
        else:
            print(
                f"✓ All {len(zip_community_mapping)} ZIP codes have unique community area assignments"
            )

        return zip_community_mapping


class CommunityRentalProcessor(DataProcessor):
    """Calculate average rental prices by community area."""

    def __init__(self) -> None:
        super().__init__(
            "community_rental_processor",
            "Calculate average rental prices by community area",
        )
        self.dependencies = ["rental_data", "spatial_join"]
        self.required_data = ["rental_data", "spatial_join"]
        self.output_data = ["community_avg_rentals"]

    def execute(self, context: dict[str, Any]) -> pd.DataFrame:
        """Calculate average rental prices by community area."""
        zip_rental_prices = context["rental_data"]
        zip_community_mapping = context["spatial_join"]

        print("Calculating average rental prices by community area...")

        # Convert ZIP codes to string for consistent matching
        zip_rental_prices["zip_code"] = zip_rental_prices["zip_code"].astype(str)

        # Merge rental prices with ZIP-community mapping
        merged_data = zip_rental_prices.merge(
            zip_community_mapping, on="zip_code", how="inner"
        )

        print(f"Merged {len(merged_data)} ZIP codes with community areas")

        # Calculate average rental price by community area
        community_avg_rentals = (
            merged_data.groupby("community_area")
            .agg({"avg_rental_price": ["mean", "count", "std"]})
            .round(2)
        )

        # Flatten column names
        community_avg_rentals.columns = ["avg_rental_price", "zip_count", "price_std"]
        community_avg_rentals = community_avg_rentals.reset_index()

        print(
            f"Calculated average rental prices for {len(community_avg_rentals)} community areas"
        )

        return community_avg_rentals


class HouseShareMerger(DataProcessor):
    """Merge rental prices with house share prohibition data."""

    def __init__(self) -> None:
        super().__init__(
            "house_share_merger",
            "Merge rental prices with house share prohibition data",
        )
        self.dependencies = ["community_rental_processor", "house_share_data"]
        self.required_data = ["community_rental_processor", "house_share_data"]
        self.output_data = ["merged_analysis_data"]

    def execute(self, context: dict[str, Any]) -> pd.DataFrame:
        """Merge rental prices with house share prohibition data."""
        community_avg_rentals = context["community_rental_processor"]
        house_share_data = context["house_share_data"]

        print("Merging rental prices with house share prohibition data...")

        # Clean up community names for merging
        community_avg_rentals["community_area"] = (
            community_avg_rentals["community_area"].str.upper().str.strip()
        )

        # Merge rental prices with house share prohibition data
        merged_data = community_avg_rentals.merge(
            house_share_data[
                ["community_area", "building_count", "total_units", "avg_units"]
            ],
            on="community_area",
            how="inner",
        )

        print(f"Successfully merged {len(merged_data)} community areas")

        return merged_data


# ============================================================================
# ANALYZERS
# ============================================================================


class CorrelationAnalyzer(Analyzer):
    """Analyze correlation between rental prices and house share prohibitions."""

    def __init__(self) -> None:  # noqa: ANN204
        super().__init__(
            "correlation_analyzer",
            "Analyze correlation between rental prices and house share prohibitions",
        )
        self.dependencies = ["house_share_merger"]
        self.required_data = ["house_share_merger"]
        self.output_data = ["correlation_results"]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform correlation analysis."""
        merged_data = context["house_share_merger"]

        print("Performing correlation analysis...")

        # Calculate correlation coefficients
        correlation_buildings = merged_data["avg_rental_price"].corr(
            merged_data["building_count"]
        )
        correlation_units = merged_data["avg_rental_price"].corr(
            merged_data["total_units"]
        )
        correlation_avg_units = merged_data["avg_rental_price"].corr(
            merged_data["avg_units"]
        )

        # Determine correlation strength
        def get_correlation_strength(corr: float) -> str:
            abs_corr = abs(corr)
            if abs_corr < CORRELATION_NEGLIGIBLE_THRESHOLD:
                return "negligible"
            elif abs_corr < CORRELATION_WEAK_THRESHOLD:
                return "weak"
            elif abs_corr < CORRELATION_MODERATE_THRESHOLD:
                return "moderate"
            elif abs_corr < CORRELATION_STRONG_THRESHOLD:
                return "strong"
            else:
                return "very strong"

        # Statistical significance (rough approximation)
        n = len(merged_data)
        t_stat = correlation_buildings * np.sqrt(
            (n - 2) / (1 - correlation_buildings**2)
        )

        # Summary statistics
        areas_with_prohibitions = len(merged_data[merged_data["building_count"] > 0])
        areas_without_prohibitions = len(
            merged_data[merged_data["building_count"] == 0]
        )
        avg_price_with_prohibitions = merged_data[merged_data["building_count"] > 0][
            "avg_rental_price"
        ].mean()
        avg_price_without_prohibitions = merged_data[
            merged_data["building_count"] == 0
        ]["avg_rental_price"].mean()

        results = {
            "correlations": {
                "buildings": correlation_buildings,
                "total_units": correlation_units,
                "avg_units": correlation_avg_units,
            },
            "correlation_strength": {
                "buildings": get_correlation_strength(correlation_buildings),
                "total_units": get_correlation_strength(correlation_units),
                "avg_units": get_correlation_strength(correlation_avg_units),
            },
            "statistical_test": {"t_statistic": t_stat, "sample_size": n},
            "summary_stats": {
                "areas_with_prohibitions": areas_with_prohibitions,
                "areas_without_prohibitions": areas_without_prohibitions,
                "avg_price_with_prohibitions": avg_price_with_prohibitions,
                "avg_price_without_prohibitions": avg_price_without_prohibitions,
            },
            "top_prohibitions": merged_data.nlargest(10, "building_count")[
                ["community_area", "avg_rental_price", "building_count", "total_units"]
            ].to_dict("records"),
        }

        print("Correlation analysis completed:")
        print(
            f"- Rental Price vs Prohibited Buildings: {correlation_buildings:.3f} ({get_correlation_strength(correlation_buildings)})"
        )
        print(f"- Areas with prohibitions: {areas_with_prohibitions}")
        print(f"- Areas without prohibitions: {areas_without_prohibitions}")

        return results


# ============================================================================
# VISUALIZERS
# ============================================================================


class CorrelationVisualizer(Visualizer):
    """Create visualizations for correlation analysis."""

    def __init__(self) -> None:
        super().__init__(
            "correlation_visualizer", "Create visualizations for correlation analysis"
        )
        self.dependencies: list[str] = ["correlation_analyzer", "house_share_merger"]
        self.required_data: list[str] = ["correlation_analyzer", "house_share_merger"]
        self.output_data: list[str] = ["correlation_plots"]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create correlation visualizations."""
        merged_data: pd.DataFrame = context["house_share_merger"]
        correlation_results: dict[str, Any] = context["correlation_analyzer"]

        print("Creating correlation visualizations...")

        # Set up the plot style
        plt.style.use("default")
        sns.set_palette("husl")

        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(
            "Rental Prices vs House Share Prohibitions Analysis",
            fontsize=16,
            fontweight="bold",
        )

        correlations = correlation_results["correlations"]

        # 1. Scatter plot: Rental Price vs Number of Prohibited Buildings
        axes[0, 0].scatter(
            merged_data["building_count"],
            merged_data["avg_rental_price"],
            alpha=0.7,
            s=60,
        )
        axes[0, 0].set_xlabel("Number of Prohibited Buildings")
        axes[0, 0].set_ylabel("Average Rental Price ($)")
        axes[0, 0].set_title(
            f'Rental Price vs Prohibited Buildings\n(Correlation: {correlations["buildings"]:.3f})'
        )
        axes[0, 0].grid(True, alpha=0.3)

        # Add trend line
        z = np.polyfit(
            merged_data["building_count"], merged_data["avg_rental_price"], 1
        )
        p = np.poly1d(z)
        axes[0, 0].plot(
            merged_data["building_count"],
            p(merged_data["building_count"]),
            "r--",
            alpha=0.8,
        )

        # 2. Scatter plot: Rental Price vs Total Prohibited Units
        axes[0, 1].scatter(
            merged_data["total_units"],
            merged_data["avg_rental_price"],
            alpha=0.7,
            s=60,
            color="orange",
        )
        axes[0, 1].set_xlabel("Total Prohibited Units")
        axes[0, 1].set_ylabel("Average Rental Price ($)")
        axes[0, 1].set_title(
            f'Rental Price vs Total Prohibited Units\n(Correlation: {correlations["total_units"]:.3f})'
        )
        axes[0, 1].grid(True, alpha=0.3)

        # Add trend line
        z = np.polyfit(merged_data["total_units"], merged_data["avg_rental_price"], 1)
        p = np.poly1d(z)
        axes[0, 1].plot(
            merged_data["total_units"], p(merged_data["total_units"]), "r--", alpha=0.8
        )

        # 3. Box plot: Rental prices by prohibition status
        prohibition_status = merged_data["building_count"].apply(
            lambda x: "With Prohibitions" if x > 0 else "Without Prohibitions"
        )
        box_data = [
            merged_data[prohibition_status == "With Prohibitions"]["avg_rental_price"],
            merged_data[prohibition_status == "Without Prohibitions"][
                "avg_rental_price"
            ],
        ]

        axes[1, 0].boxplot(
            box_data, labels=["With Prohibitions", "Without Prohibitions"]
        )
        axes[1, 0].set_ylabel("Average Rental Price ($)")
        axes[1, 0].set_title("Rental Price Distribution by Prohibition Status")
        axes[1, 0].grid(True, alpha=0.3)

        # 4. Histogram: Distribution of prohibited buildings
        axes[1, 1].hist(
            merged_data["building_count"],
            bins=20,
            alpha=0.7,
            color="green",
            edgecolor="black",
        )
        axes[1, 1].set_xlabel("Number of Prohibited Buildings")
        axes[1, 1].set_ylabel("Number of Community Areas")
        axes[1, 1].set_title("Distribution of House Share Prohibitions")
        axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()

        # Save the plot
        output_path = Path("/project/output/correlation_analysis.png")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.show()

        print(f"Correlation visualizations saved to: {output_path}")

        return {"plot_path": str(output_path), "figure": fig}


# ============================================================================
# DECORATOR-BASED COMPONENTS (Alternative approach)
# ============================================================================


@pipeline_component(
    name="summary_reporter",
    description="Generate summary report of analysis results",
    dependencies=["correlation_analyzer"],
    required_data=["correlation_analyzer"],
)
def summary_reporter(context: dict[str, Any]) -> dict[str, Any]:
    """Generate a summary report of the analysis."""
    correlation_results = context["correlation_analyzer"]

    print("=" * 60)
    print("CHICAGO HOUSING ANALYSIS SUMMARY REPORT")
    print("=" * 60)

    correlations = correlation_results["correlations"]
    summary_stats = correlation_results["summary_stats"]

    print("\nCorrelation Analysis Results:")
    print(f"- Rental Price vs Prohibited Buildings: {correlations['buildings']:.3f}")
    print(
        f"- Rental Price vs Total Prohibited Units: {correlations['total_units']:.3f}"
    )
    print(
        f"- Rental Price vs Average Units per Building: {correlations['avg_units']:.3f}"
    )

    print("\nSummary Statistics:")
    print(
        f"- Community areas with house share prohibitions: {summary_stats['areas_with_prohibitions']}"
    )
    print(
        f"- Community areas without house share prohibitions: {summary_stats['areas_without_prohibitions']}"
    )
    print(
        f"- Average rental price in areas with prohibitions: ${summary_stats['avg_price_with_prohibitions']:.2f}"
    )
    print(
        f"- Average rental price in areas without prohibitions: ${summary_stats['avg_price_without_prohibitions']:.2f}"
    )

    print("\nTop 5 Areas with Most House Share Prohibitions:")
    for i, area in enumerate(correlation_results["top_prohibitions"][:5], 1):
        print(
            f"{i}. {area['community_area']}: {area['building_count']} buildings, ${area['avg_rental_price']:.2f} avg rent"
        )

    return {"report_generated": True, "timestamp": pd.Timestamp.now().isoformat()}
