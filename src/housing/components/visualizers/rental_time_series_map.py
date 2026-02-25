"""Rental price time series map visualizer.

This module creates an html interactive choropleth map showing rental price distributions
at the tract level over time.
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px

from housing.components.utils import prepare_map_panel_data
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class RentalTimeSeriesMapVisualizer(Visualizer):
    """Create choropleth maps for rental prices.

    Shows rental prices as geographic maps at both census tract and
    community area levels.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the rental map visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "rental_time_series_map_visualization",
            "Create interactive choropleth map for rental prices over time",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create rental price map visualizations."""
        logger.info("Creating rental price map visualizations...")

        panel_data = context.get("tract_panel_data")
        tract_boundaries = context.get("tract_boundaries")
        city_boundaries = context.get("city_boundaries")

        if panel_data is None:
            logger.warning("No rental data available for mapping")
            return {}

        if panel_data is not None and tract_boundaries is not None:
            map_data = prepare_map_panel_data(
                panel_data,
                tract_boundaries,
                ["month", "rental_price"],
                city_boundaries,
                simplify=True,
            )

            # Make discrete quantiles for each date (include quantile order for mapping)
            k = 4

            def quantile_labels(s: pd.Series, k: int) -> pd.DataFrame:
                # ranks handle ties safely
                r = s.rank(method="first")

                cats, bins = pd.qcut(
                    r, q=k, labels=False, retbins=True, duplicates="drop"
                )

                # compute true bounds using original values
                bounds = s.groupby(cats).agg(["min", "max"]).sort_index()

                label_map = {}
                for i, (lo, hi) in bounds.iterrows():
                    label_map[i] = f"${lo:,.0f} - ${hi:,.0f}"

                return pd.DataFrame(
                    {
                        "q_idx": cats.astype(int) + 1,  # 1..k
                        "q_label": cats.map(label_map),
                    }
                )

            labels = map_data.groupby("month", group_keys=False)["rental_price"].apply(
                lambda s: quantile_labels(s, k)
            )

            map_data = map_data.join(labels)
            logger.info("Added quantile labels to map data")

            # format data for a nice slider tool
            # sort old -> recent
            map_data = map_data.sort_values("month")
            # create slider labels
            map_data["month_str"] = map_data["month"].dt.strftime("%Y-%m")

            # ensure correct quantile sorting in plotly
            label_order = map_data.sort_values("q_idx")["q_label"].tolist()

            # ensure a standard color map across dates
            palette = px.colors.sequential.RdPu
            idx = [int(0.8 * i * (len(palette) - 1) / (k - 1)) for i in range(k)]
            quantile_colors = [palette[i] for i in idx]

            quantile_color_map = {
                f"Q{i}": quantile_colors[i - 1] for i in range(1, k + 1)
            }

            quantile_map = (
                map_data.drop_duplicates(subset="q_label")
                .set_index("q_label")["q_idx"]
                .to_dict()
            )

            color_map = {
                q_label: quantile_color_map[f"Q{quantile_map[q_label]}"]
                for q_label in map_data["q_label"].unique()
            }

            # convert geometries to geojson for plotly
            geojson = map_data.__geo_interface__

            # orient plotly map area
            center = {
                "lat": float(tract_boundaries.centroid.y.mean()),
                "lon": float(tract_boundaries.centroid.x.mean()),
            }

            # create choropleth

            fig = px.choropleth_mapbox(
                map_data,
                geojson=geojson,
                locations="tract_geoid",
                featureidkey="properties.tract_geoid",
                color="q_label",  # DISPLAY labels
                animation_frame="month_str",
                category_orders={"q_label": label_order},
                color_discrete_map=color_map,
                mapbox_style="carto-positron",
                zoom=9,
                center=center,
                opacity=0.75,
            )

            fig.update_layout(legend_title_text="Monthly rental quantiles")

            logger.info("Created figure")

        # Save the plot
        output_path = Path(self.output_dir) / "rental_price_time_series_map.html"
        fig.write_html(
            output_path,
            include_plotlyjs="cdn",  # or True for offline
            full_html=True,
        )

        return {"rental_time_series_map_plot": str(output_path)}
