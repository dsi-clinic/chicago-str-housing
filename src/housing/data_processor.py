"""Data processing module for house share prohibited buildings analysis."""

import warnings
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely import wkt
from shapely.geometry import Point

warnings.filterwarnings("ignore")


def load_buildings_data(file_path: str) -> gpd.GeoDataFrame:
    """Load and clean the house share prohibited buildings data.

    Args:
        file_path (str): Path to the CSV file

    Returns:
        gpd.GeoDataFrame: GeoDataFrame with building data and geometry
    """
    print("Loading buildings data...")

    # Load the CSV
    buildings_df = pd.read_csv(file_path)

    # Clean column names (remove quotes and spaces)
    buildings_df.columns = buildings_df.columns.str.strip().str.replace('"', "")

    # Convert latitude and longitude to numeric, handling any string formatting
    buildings_df["Latitude"] = pd.to_numeric(buildings_df["Latitude"], errors="coerce")
    buildings_df["Longitude"] = pd.to_numeric(
        buildings_df["Longitude"], errors="coerce"
    )

    # Convert Number of Units to numeric
    buildings_df["Number of Units"] = pd.to_numeric(
        buildings_df["Number of Units"], errors="coerce"
    )

    # Remove rows with missing coordinates
    buildings_df = buildings_df.dropna(subset=["Latitude", "Longitude"])

    # Create Point geometries
    geometry = [
        Point(lon, lat)
        for lon, lat in zip(buildings_df["Longitude"], buildings_df["Latitude"])
    ]

    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(buildings_df, geometry=geometry, crs="EPSG:4326")

    print(f"Loaded {len(gdf)} buildings with valid coordinates")
    print(f"Total units: {buildings_df['Number of Units'].sum():,.0f}")

    return gdf


def load_community_areas(file_path: str) -> gpd.GeoDataFrame:
    """Load and process community areas boundaries data.

    Args:
        file_path (str): Path to the CSV file

    Returns:
        gpd.GeoDataFrame: GeoDataFrame with community area boundaries
    """
    print("Loading community areas data...")

    # Load the CSV
    community_df = pd.read_csv(file_path)

    # Clean column names
    community_df.columns = community_df.columns.str.strip().str.replace('"', "")

    # Parse the geometry column (WKT format)
    community_df["geometry"] = community_df["the_geom"].apply(wkt.loads)

    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(community_df, geometry="geometry", crs="EPSG:4326")

    # Clean up the dataframe - keep only relevant columns
    gdf = gdf[
        ["AREA_NUMBE", "COMMUNITY", "AREA_NUM_1", "SHAPE_AREA", "SHAPE_LEN", "geometry"]
    ]

    # Convert area number to numeric
    gdf["AREA_NUMBE"] = pd.to_numeric(gdf["AREA_NUMBE"], errors="coerce")

    print(f"Loaded {len(gdf)} community areas")

    return gdf


def aggregate_buildings_by_community(
    buildings_gdf: gpd.GeoDataFrame, community_gdf: gpd.GeoDataFrame
) -> pd.DataFrame:
    """Aggregate building data by community areas using spatial joins.

    Args:
        buildings_gdf (gpd.GeoDataFrame): Buildings data with Point geometries
        community_gdf (gpd.GeoDataFrame): Community areas with Polygon geometries

    Returns:
        gpd.GeoDataFrame: Community areas with aggregated building statistics
    """
    print("Performing spatial aggregation...")

    # Ensure both GeoDataFrames are in the same CRS
    if buildings_gdf.crs != community_gdf.crs:
        buildings_gdf = buildings_gdf.to_crs(community_gdf.crs)

    # Perform spatial join
    joined = gpd.sjoin(buildings_gdf, community_gdf, how="inner", predicate="within")

    # Aggregate by community area
    agg_stats = (
        joined.groupby("AREA_NUMBE")
        .agg(
            {
                "Application ID": "count",  # Number of buildings
                "Number of Units": ["sum", "mean"],  # Total and average units
                "COMMUNITY": "first",  # Community name
                "SHAPE_AREA": "first",  # Area size
            }
        )
        .round(2)
    )

    # Flatten column names
    agg_stats.columns = [
        "building_count",
        "total_units",
        "avg_units",
        "community_name",
        "area_size",
    ]

    # Reset index to make AREA_NUMBE a column
    agg_stats = agg_stats.reset_index()

    # Merge back with community geometries
    result = community_gdf.merge(agg_stats, on="AREA_NUMBE", how="left")

    # Fill NaN values for areas with no buildings
    result["building_count"] = result["building_count"].fillna(0).astype(int)
    result["total_units"] = result["total_units"].fillna(0).astype(int)
    result["avg_units"] = result["avg_units"].fillna(0)

    print(f"Aggregated data for {len(result)} community areas")
    print(f"Areas with buildings: {(result['building_count'] > 0).sum()}")
    print(f"Total buildings across all areas: {result['building_count'].sum()}")
    print(f"Total units across all areas: {result['total_units'].sum()}")

    return result


def get_summary_statistics(aggregated_data: pd.DataFrame) -> dict[str, Any]:
    """Generate summary statistics for the aggregated data.

    Args:
        aggregated_data (gpd.GeoDataFrame): Aggregated building data by community

    Returns:
        dict: Dictionary of summary statistics
    """
    stats = {
        "total_community_areas": len(aggregated_data),
        "areas_with_buildings": (aggregated_data["building_count"] > 0).sum(),
        "areas_without_buildings": (aggregated_data["building_count"] == 0).sum(),
        "total_buildings": aggregated_data["building_count"].sum(),
        "total_units": aggregated_data["total_units"].sum(),
        "avg_buildings_per_area": aggregated_data["building_count"].mean(),
        "avg_units_per_area": aggregated_data["total_units"].mean(),
        "max_buildings_in_area": aggregated_data["building_count"].max(),
        "max_units_in_area": aggregated_data["total_units"].max(),
        "top_5_areas_by_buildings": aggregated_data.nlargest(5, "building_count")[
            ["COMMUNITY", "building_count", "total_units"]
        ].to_dict("records"),
        "top_5_areas_by_units": aggregated_data.nlargest(5, "total_units")[
            ["COMMUNITY", "building_count", "total_units"]
        ].to_dict("records"),
    }

    return stats


def process_all_data(
    buildings_file: str, community_file: str
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Complete data processing pipeline.

    Args:
        buildings_file (str): Path to buildings CSV
        community_file (str): Path to community areas CSV

    Returns:
        tuple: (buildings_gdf, community_gdf, aggregated_data, summary_stats)
    """
    # Load data
    buildings_gdf = load_buildings_data(buildings_file)
    community_gdf = load_community_areas(community_file)

    # Aggregate
    aggregated_data = aggregate_buildings_by_community(buildings_gdf, community_gdf)

    # Generate summary
    summary_stats = get_summary_statistics(aggregated_data)

    return buildings_gdf, community_gdf, aggregated_data, summary_stats
