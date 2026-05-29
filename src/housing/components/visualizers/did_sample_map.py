"""Choropleth maps for the DiD matched census-tract sample."""

from __future__ import annotations

import os

# Shapely 2 is much faster than legacy PyGEOS on large tract plots.
os.environ.setdefault("USE_PYGEOS", "0")

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

from housing.components.utils import setup_figure_and_save
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)

# Publication defaults for map panels
_MAP_TITLE_FONTSIZE = 14
_MAP_LABEL_FONTSIZE = 12
_MAP_STATS_FONTSIZE = 11
_NEVER_TREATED_FILL = "#e8e8e8"
_EVER_TREATED_THRESHOLD = 0.5


def _normalize_tract_geoid(series: pd.Series) -> pd.Series:
    """11-digit GEOID strings for consistent shapefile merges."""
    return series.astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(11)


def _prepare_sample_geometries(
    tract_df: pd.DataFrame,
    tract_boundaries: gpd.GeoDataFrame,
    city_boundaries: gpd.GeoDataFrame | None,
    *,
    logger: logging.Logger | None = None,
) -> tuple[gpd.GeoDataFrame, tuple[float, float, float, float] | None]:
    """Inner-join sample tracts to boundaries; optional city clip."""
    sample = tract_df.copy()
    sample["tract_geoid"] = _normalize_tract_geoid(sample["tract_geoid"])

    bounds_gdf = tract_boundaries.copy()
    if "tract_geoid" not in bounds_gdf.columns:
        bounds_gdf["tract_geoid"] = _normalize_tract_geoid(bounds_gdf["GEOID"])
    else:
        bounds_gdf["tract_geoid"] = _normalize_tract_geoid(bounds_gdf["tract_geoid"])

    gdf = bounds_gdf.merge(sample, on="tract_geoid", how="inner")
    if "ALAND" in gdf.columns:
        gdf = gdf[gdf["ALAND"] > 0].copy()

    common_bounds = None
    if city_boundaries is not None:
        city = (
            city_boundaries.to_crs(gdf.crs)
            if city_boundaries.crs != gdf.crs
            else city_boundaries
        )
        common_bounds = city.total_bounds
        if logger:
            logger.info(
                "Using city bounds for map extent (%d sample tracts; no geometry clip)",
                len(gdf),
            )

    return gdf, common_bounds


def _apply_map_bounds(
    ax: plt.Axes, bounds: tuple[float, float, float, float] | None
) -> None:
    if bounds is not None:
        ax.set_xlim(bounds[0], bounds[2])
        ax.set_ylim(bounds[1], bounds[3])
    ax.set_axis_off()


def _plot_ever_treated_panel(
    ax: plt.Axes,
    gdf: gpd.GeoDataFrame,
    bounds: tuple[float, float, float, float] | None,
) -> None:
    """Binary ever-treated choropleth (sample tracts only)."""
    treated = (gdf["ever_treated"].fillna(0) >= _EVER_TREATED_THRESHOLD).astype(int)
    n_treated = int(treated.sum())
    n_sample = len(gdf)

    cmap = ListedColormap([_NEVER_TREATED_FILL, "#2171b5"])
    gdf.assign(_plot=treated).plot(
        column="_plot",
        ax=ax,
        cmap=cmap,
        vmin=0,
        vmax=1,
        linewidth=0.15,
        edgecolor="#666666",
        legend=False,
    )
    _apply_map_bounds(ax, bounds)

    sm = mpl.cm.ScalarMappable(cmap=cmap, norm=mpl.colors.Normalize(vmin=0, vmax=1))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, fraction=0.035, pad=0.02, ticks=[0, 1])
    cbar.ax.set_yticklabels(
        ["Never treated", "Ever treated"], fontsize=_MAP_LABEL_FONTSIZE
    )
    cbar.set_label("Treatment status", fontsize=_MAP_LABEL_FONTSIZE)

    ax.set_title(
        f"Ever subject to STR prohibition (n={n_sample} tracts; {n_treated} treated)",
        fontsize=_MAP_TITLE_FONTSIZE,
        pad=8,
    )
    stats = (
        f"Sample: {n_sample} tracts\n"
        f"Ever treated: {n_treated}\n"
        f"Never treated: {n_sample - n_treated}"
    )
    ax.text(
        0.02,
        0.98,
        stats,
        transform=ax.transAxes,
        fontsize=_MAP_STATS_FONTSIZE,
        va="top",
        bbox={"boxstyle": "round,pad=0.4", "facecolor": "white", "alpha": 0.92},
    )


def _plot_first_year_panel(
    ax: plt.Axes,
    gdf: gpd.GeoDataFrame,
    bounds: tuple[float, float, float, float] | None,
) -> None:
    """Calendar year of first prohibition; never-treated tracts neutral."""
    treated_mask = gdf["ever_treated"].fillna(0) >= _EVER_TREATED_THRESHOLD
    years = gdf.loc[treated_mask, "first_prohibition_year"].dropna()
    n_treated = int(treated_mask.sum())

    plot_gdf = gdf.copy()
    plot_gdf["_year"] = np.where(
        treated_mask,
        plot_gdf["first_prohibition_year"],
        np.nan,
    )

    plot_gdf.loc[~treated_mask].plot(
        ax=ax,
        color=_NEVER_TREATED_FILL,
        linewidth=0.15,
        edgecolor="#666666",
    )
    treated_gdf = plot_gdf[treated_mask]
    if not treated_gdf.empty and years.notna().any():
        vmin, vmax = int(years.min()), int(years.max())
        treated_gdf.plot(
            column="_year",
            ax=ax,
            cmap="plasma",
            vmin=vmin,
            vmax=vmax,
            linewidth=0.15,
            edgecolor="#666666",
            legend=False,
        )
        sm = mpl.cm.ScalarMappable(
            cmap="plasma", norm=mpl.colors.Normalize(vmin=vmin, vmax=vmax)
        )
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, fraction=0.035, pad=0.02)
        cbar.set_label("First prohibition year", fontsize=_MAP_LABEL_FONTSIZE)
        cbar.ax.tick_params(labelsize=_MAP_LABEL_FONTSIZE - 1)
        year_range = f"{vmin}--{vmax}"
    else:
        year_range = "n/a"

    _apply_map_bounds(ax, bounds)
    ax.set_title(
        f"Calendar year of first prohibition (n={n_treated} treated tracts)",
        fontsize=_MAP_TITLE_FONTSIZE,
        pad=8,
    )
    legend_handles = [
        Patch(
            facecolor=_NEVER_TREATED_FILL, edgecolor="#666666", label="Never treated"
        ),
    ]
    ax.legend(
        handles=legend_handles,
        loc="lower left",
        fontsize=_MAP_STATS_FONTSIZE,
        framealpha=0.92,
    )
    stats = f"Treated tracts: {n_treated}\nYear range: {year_range}"
    ax.text(
        0.02,
        0.98,
        stats,
        transform=ax.transAxes,
        fontsize=_MAP_STATS_FONTSIZE,
        va="top",
        bbox={"boxstyle": "round,pad=0.4", "facecolor": "white", "alpha": 0.92},
    )


def _save_stacked_maps(
    gdf: gpd.GeoDataFrame,
    bounds: tuple[float, float, float, float] | None,
    out_path: Path,
    *,
    suptitle: str | None = None,
) -> None:
    """Two-panel vertical layout (better for print than side-by-side)."""
    fig, axes = plt.subplots(2, 1, figsize=(9, 14))
    _plot_ever_treated_panel(axes[0], gdf, bounds)
    _plot_first_year_panel(axes[1], gdf, bounds)
    if suptitle:
        fig.suptitle(suptitle, fontsize=16, fontweight="bold", y=0.99)
    fig.subplots_adjust(hspace=0.12, top=0.96 if suptitle else 0.98)
    setup_figure_and_save(fig, out_path, title=None, dpi=300, logger=logger)


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
        tract_df.to_csv(
            self.output_dir / "did_spatial_sample_tract_table.csv", index=False
        )

        gdf, common_bounds = _prepare_sample_geometries(
            tract_df,
            tract_boundaries,
            city_boundaries,
            logger=logger,
        )
        if gdf.empty:
            logger.warning("did_sample_map: no geometries after merge")
            return {}

        out_combined = self.output_dir / "did_spatial_sample.png"
        _save_stacked_maps(
            gdf,
            common_bounds,
            out_combined,
            suptitle="DiD matched sample: treatment status and timing",
        )

        fig1, ax1 = plt.subplots(figsize=(9, 10))
        _plot_ever_treated_panel(ax1, gdf, common_bounds)
        setup_figure_and_save(
            fig1,
            self.output_dir / "did_spatial_sample_ever_treated.png",
            title=None,
            logger=logger,
        )

        fig2, ax2 = plt.subplots(figsize=(9, 10))
        _plot_first_year_panel(ax2, gdf, common_bounds)
        setup_figure_and_save(
            fig2,
            self.output_dir / "did_spatial_sample_first_year.png",
            title=None,
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
        panel["tract_geoid"] = _normalize_tract_geoid(panel["tract_geoid"])

        if "treatment_start_month" in panel.columns:
            start = pd.to_datetime(panel["treatment_start_month"], errors="coerce")
            tract_start = start.groupby(panel["tract_geoid"]).min()
            ever = tract_start.notna().astype(float)
            first_year = tract_start.dt.year.astype(float)
        else:
            ever = panel.groupby("tract_geoid")["treated"].max()
            first_treat_month = (
                panel[panel["treated"] == 1].groupby("tract_geoid")["month"].min()
            )
            first_year = first_treat_month.dt.year.astype(float).reindex(ever.index)
            ever = ever.astype(float)

        out = pd.DataFrame(
            {
                "tract_geoid": ever.index.astype(str),
                "ever_treated": ever.to_numpy(),
                "first_prohibition_year": first_year.reindex(ever.index).to_numpy(),
            }
        )
        out["tract_geoid"] = _normalize_tract_geoid(out["tract_geoid"])
        return out
