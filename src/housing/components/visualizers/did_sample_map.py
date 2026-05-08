"""Choropleth maps for the DiD matched census-tract sample."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from housing.components.utils import (
    create_choropleth_map,
    prepare_map_data,
    setup_figure_and_save,
)
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class DiDSampleMapVisualizer(Visualizer):
    """Map ever-treated status and first prohibition year for tracts in the DiD panel."""

    def __init__(self, output_dir: str | Path | None = None) -> None:
        """Write maps and tract table beneath ``output_dir`` (defaults to `/project/output`)."""
        super().__init__(
            "did_sample_map_visualization",
            "Choropleth maps for matched DiD tract sample (treatment status and timing)",
        )
        self.output_dir = Path(output_dir or "/project/output")
        self.required_data = ["did_panel", "tract_boundaries"]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Build tract-level treatment maps for the current `did_panel` (matched sample)."""
        did_panel = context.get("did_panel")
        tract_boundaries = context.get("tract_boundaries")
        city_boundaries = context.get("city_boundaries")

        if did_panel is None or tract_boundaries is None:
            logger.warning("did_sample_map: missing did_panel or tract_boundaries")
            return {}

        self.output_dir.mkdir(parents=True, exist_ok=True)

        tract_df = self._tract_level_frame(did_panel)
        tract_df.to_csv(self.output_dir / "did_spatial_sample_tract_table.csv", index=False)

        common_bounds = (
            city_boundaries.total_bounds if city_boundaries is not None else None
        )

        map_ever = prepare_map_data(
            tract_df,
            tract_boundaries,
            ["ever_treated"],
            city_boundaries,
            logger=logger,
        )
        map_year = prepare_map_data(
            tract_df,
            tract_boundaries,
            ["first_prohibition_year"],
            city_boundaries,
            logger=logger,
        )

        if map_ever is None or map_year is None:
            logger.warning("did_sample_map: prepare_map_data returned None")
            return {}

        fig, axes = plt.subplots(1, 2, figsize=(20, 9))

        create_choropleth_map(
            axes[0],
            map_ever,
            "ever_treated",
            "Ever subject to STR prohibition (tract)",
            "Ever treated (1=yes)",
            cmap="Blues",
            bounds=common_bounds,
            stats_format="{:.0f}",
            logger=logger,
        )

        create_choropleth_map(
            axes[1],
            map_year,
            "first_prohibition_year",
            "Calendar year of first prohibition (if treated)",
            "First prohibition year",
            cmap="plasma",
            bounds=common_bounds,
            stats_format="{:.0f}",
            logger=logger,
        )

        out_combined = self.output_dir / "did_spatial_sample.png"
        setup_figure_and_save(
            fig,
            out_combined,
            title="DiD matched sample: treatment status and timing",
            logger=logger,
        )

        # Also save single-panel versions with stable names for Beamer / brief
        fig1, ax1 = plt.subplots(figsize=(10, 9))
        create_choropleth_map(
            ax1,
            map_ever,
            "ever_treated",
            "Ever subject to STR prohibition",
            "Ever treated (1=yes)",
            cmap="Blues",
            bounds=common_bounds,
            stats_format="{:.0f}",
            logger=logger,
        )
        setup_figure_and_save(
            fig1,
            self.output_dir / "did_spatial_sample_ever_treated.png",
            title="DiD sample: ever treated",
            logger=logger,
        )

        fig2, ax2 = plt.subplots(figsize=(10, 9))
        create_choropleth_map(
            ax2,
            map_year,
            "first_prohibition_year",
            "Year of first prohibition (treated tracts)",
            "First prohibition year",
            cmap="plasma",
            bounds=common_bounds,
            stats_format="{:.0f}",
            logger=logger,
        )
        setup_figure_and_save(
            fig2,
            self.output_dir / "did_spatial_sample_first_year.png",
            title="DiD sample: first prohibition year",
            logger=logger,
        )

        logger.info("DiD sample maps saved under %s", self.output_dir)
        return {
            "did_spatial_sample_plot": str(out_combined),
            "did_spatial_sample_ever_treated_plot": str(
                self.output_dir / "did_spatial_sample_ever_treated.png"
            ),
            "did_spatial_sample_first_year_plot": str(
                self.output_dir / "did_spatial_sample_first_year.png"
            ),
        }

    def _tract_level_frame(self, did_panel: pd.DataFrame) -> pd.DataFrame:
        """One row per tract: identifiers, ever-treated, first prohibition calendar year."""
        panel = did_panel.copy()
        panel["tract_geoid"] = panel["tract_geoid"].astype(str)

        ever = panel.groupby("tract_geoid")["treated"].max()
        first_treat_month = (
            panel[panel["treated"] == 1].groupby("tract_geoid")["month"].min()
        )
        first_year = first_treat_month.dt.year.astype(float).reindex(ever.index)

        out = pd.DataFrame(
            {
                "tract_geoid": ever.index.astype(str),
                "ever_treated": ever.astype(float).to_numpy(),
                "first_prohibition_year": first_year.to_numpy(),
            }
        )
        return out
