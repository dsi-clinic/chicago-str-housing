"""Treatment time series map visualizer.

This module creates an html interactive choropleth map highlighting treated tracts
at the tract level over time.
"""

import logging
from pathlib import Path
from typing import Any

import plotly.express as px

from housing.components.utils import prepare_map_panel_data
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class TreatmentTimeSeriesMapVisualizer(Visualizer):
    """Create interactive time-series choropleth map for treatment and control groups."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the treatment map visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "treatment_time_series_map_visualization",
            "Create interactive choropleth map for treated tracts over time",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create treatment group map visualizations."""
        logger.info("Creating treatment group map visualizations...")

        panel_data = context.get("did_panel")
        tract_boundaries = context.get("tract_boundaries")
        city_boundaries = context.get("city_boundaries")

        if panel_data is None:
            logger.warning("No DiD data available for mapping")
            return {}

        if panel_data is not None and tract_boundaries is not None:
            map_data = prepare_map_panel_data(
                panel_data, tract_boundaries, ["month", "treated"], city_boundaries
            )

            # find the earliest treatment date to make plotly run smoothly
            first_treat = map_data.loc[map_data["treated"] == 1]["month"].min()

            # resample to quarterly data to make plotly run smoothly
            map_data = map_data.loc[
                (
                    (map_data["month"].dt.month % 3 == 0)
                    & (map_data["month"] >= first_treat)
                )
            ]

            # format data for a nice slider tool
            # sort old -> recent
            map_data = map_data.sort_values("month")
            # create slider labels
            map_data["month_str"] = map_data["month"].dt.strftime("%Y-%m")

            # convert treatment indicator to interpretable strings
            map_data["treated_str"] = map_data["treated"].map(
                {0: "control", 1: "treatment"}
            )

            # convert geometries to geojson for plotly
            geojson = tract_boundaries.__geo_interface__

            # orient the map
            center = {
                "lat": float(tract_boundaries.geometry.centroid.y.mean()),
                "lon": float(tract_boundaries.geometry.centroid.x.mean()),
            }

            # create choropleth

            fig = px.choropleth_mapbox(
                map_data,
                geojson=geojson,
                locations="tract_geoid",
                featureidkey="properties.tract_geoid",
                color="treated_str",
                animation_frame="month_str",
                color_discrete_map={
                    "control": "lightgray",
                    "treatment": "red",
                },
                mapbox_style="carto-positron",
                zoom=9,
                center=center,
                opacity=0.75,
            )

            logger.info("Created figure")

            # Save the plot
            output_path = Path(self.output_dir) / "treatment_time_series_map.html"
            fig.write_html(
                output_path,
                include_plotlyjs="cdn",  # or True for offline
                full_html=True,
            )

        return {"treatment_time_series_map_plot": str(output_path)}
