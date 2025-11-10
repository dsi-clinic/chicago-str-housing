"""Created a visualizer that would compare different schemes for choropleth mapping for STR Prohibition data"""

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt

from housing.components.utils import prepare_map_data
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class STRChoroplethSchemesVisualizer(Visualizer):
    """Visualize STR choropleths using different classification schemes."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initializing choropleth map visualizer for different schemes"""
        super().__init__(
            "str_choropleth_schemes_visualization",
            "Choropleth maps comparing classification schemes",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Creating visualizations for different schemes"""
        logger.info("Generating tract-level STR choropleths under multiple schemes...")

        # Getting the data
        tract_data = context.get("str_tract_data")
        tract_boundaries = context.get("tract_boundaries")
        city_boundaries = context.get("city_boundaries")

        if tract_data is None or tract_boundaries is None:
            logger.warning("Missing STR tract data or boundaries.")
            return {}

        # Prepare tract data
        tract_map_data = prepare_map_data(
            tract_data,
            tract_boundaries,
            ["str_prohibition_density"],
            city_boundaries,
            logger=logger,
        )

        # Clip to city boundaries
        if city_boundaries is not None:
            if tract_map_data.crs != city_boundaries.crs:
                city_boundaries = city_boundaries.to_crs(tract_map_data.crs)
            tract_map_data = gpd.clip(tract_map_data, city_boundaries)
            logger.info("Clipped tract data to city boundaries.")

        # Scehems that are being compared
        schemes = ["Quantiles", "EqualInterval", "FisherJenks", "NaturalBreaks"]
        variable = "str_prohibition_density"

        # Creating 4 side by side maps
        fig, axes = plt.subplots(1, len(schemes), figsize=(5 * len(schemes), 8))

        for i, scheme in enumerate(schemes):
            ax = axes[i]
            tract_map_data.plot(
                column=variable,
                ax=ax,
                scheme=scheme,
                k=5,
                cmap="YlOrRd",
                linewidth=0.1,
                edgecolor="black",
                legend=True,
                legend_kwds={"loc": "lower left"},
                missing_kwds={"color": "lightgrey", "edgecolor": "none"},
            )
            ax.set_title(scheme, fontsize=12)
            ax.set_axis_off()

        fig.suptitle(
            "STR Prohibitions Choropleth Mapping with Different Schemes", fontsize=16
        )

        plt.tight_layout()
        output_path = (
            Path(self.output_dir) / "str_choropleth_tract_schemes_comparison.png"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(
            f"Saved STR tract classification schemes comparison to {output_path}"
        )

        return {"str_choropleth_tract_schemes_map": str(output_path)}
