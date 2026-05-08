"""Editorial-quality choropleth maps for the DiD matched sample.

Design choices follow common cartographic / data-viz UX guidance:
* The right ink-to-data ratio: low-noise basemap, light tract edges, no chartjunk.
* Two distinct categorical hues (treated = maroon, never-treated = navy) instead of
  a 0--1 gradient; binary data should never be encoded with a sequential colormap.
* Cohort year is binned into 4 ordinal classes so policy phases are legible.
* A soft cyan band represents Lake Michigan -- a quick eastern landmark that helps
  Chicago readers orient.
* Sans-serif fonts, white background, slim title, contextual annotation in lieu of
  a min/median/max box.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


# Deck-aligned palette
TREATED = "#800000"           # UChicago maroon
CONTROL = "#1f3a5f"           # navy for matched never-treated
OUT_OF_SAMPLE = "#ECEDEF"     # very light grey for tracts not in panel
TRACT_EDGE = "#FFFFFF"        # white tract borders for separation on screen
CITY_EDGE = "#262626"         # dark city outline for figure-ground


def _add_north_arrow(ax) -> None:
    """Draw a small inset north arrow in the upper-right corner."""
    ax.annotate(
        "N",
        xy=(0.96, 0.95),
        xytext=(0.96, 0.85),
        xycoords="axes fraction",
        ha="center",
        va="bottom",
        fontsize=10,
        fontweight="semibold",
        color="#262626",
        arrowprops=dict(arrowstyle="-|>,head_width=0.25,head_length=0.35", color="#262626", lw=1.0),
    )


def _bucket_year(year: float | None) -> str:
    """Bucket a calendar year into a deck-friendly cohort phase."""
    if year is None or pd.isna(year):
        return "Not treated"
    y = int(year)
    if y <= 2016:
        return "2015--2016 (early)"
    if y <= 2018:
        return "2017--2018"
    if y <= 2020:
        return "2019--2020"
    return "2021--2024 (late)"


_YEAR_PALETTE = {
    "2015--2016 (early)": "#5F0F40",   # deep magenta
    "2017--2018":         "#9A031E",   # red
    "2019--2020":         "#E36414",   # orange
    "2021--2024 (late)":  "#FFB703",   # gold
    "Not treated":        "#E2E5E8",
}
_YEAR_ORDER = [
    "2015--2016 (early)",
    "2017--2018",
    "2019--2020",
    "2021--2024 (late)",
    "Not treated",
]


class DiDStoryMapVisualizer(Visualizer):
    """Editorial map: matched DiD sample, treatment status and cohort timing."""

    def __init__(self, output_dir: str | Path | None = None) -> None:
        super().__init__(
            "did_story_map_visualization",
            "Editorial choropleth maps for the DiD matched sample",
        )
        self.output_dir = Path(output_dir or "/project/output")
        self.required_data = ["did_panel", "tract_boundaries"]

    # ------------------------------------------------------------------
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        did_panel = context.get("did_panel")
        tract_boundaries = context.get("tract_boundaries")
        city_boundaries = context.get("city_boundaries")

        if did_panel is None or tract_boundaries is None:
            logger.warning("did_story_map: missing did_panel or tract_boundaries")
            return {}

        self.output_dir.mkdir(parents=True, exist_ok=True)

        tract_df = self._tract_frame(did_panel)
        bx = tract_boundaries.copy()
        bx["tract_geoid"] = bx["tract_geoid"].astype(str)
        merged = bx.merge(tract_df, on="tract_geoid", how="left")
        merged["status"] = merged["ever_treated"].apply(
            lambda v: "Treated" if v == 1 else ("Matched control" if v == 0 else "Out of sample")
        )
        merged["cohort_phase"] = merged["first_prohibition_year"].apply(_bucket_year)
        merged.loc[merged["status"] != "Treated", "cohort_phase"] = "Not treated"

        # Project everything into NAD83 / Illinois State Plane East (EPSG:26971) so
        # the city renders with correct local proportions instead of the latitude-
        # squashed look you get from EPSG:4326. Coordinates are in metres.
        TARGET_CRS = "EPSG:26971"
        if merged.crs is None:
            merged = merged.set_crs("EPSG:4326")
        merged = merged.to_crs(TARGET_CRS)

        # Clip / focus on Chicago city footprint when the city polygon is available
        # to avoid Cook-county controls dominating the eastern half of the figure.
        city_proj = None
        if city_boundaries is not None:
            city_proj = city_boundaries.copy()
            if city_proj.crs is None:
                city_proj = city_proj.set_crs("EPSG:4326")
            city_proj = city_proj.to_crs(TARGET_CRS)
            try:
                city_union = city_proj.geometry.unary_union
                merged["_in_chicago"] = merged.geometry.intersects(city_union)
            except Exception as exc:
                logger.warning("did_story_map: city intersect failed (%s); using all tracts", exc)
                merged["_in_chicago"] = True
        else:
            merged["_in_chicago"] = True

        merged_chicago = merged[merged["_in_chicago"]].copy()
        bounds = (
            tuple(city_proj.total_bounds)
            if city_proj is not None
            else tuple(merged_chicago.total_bounds)
        )

        # 16:9-friendly aspect, leave breathing room around figure
        fig, axes = plt.subplots(
            1,
            2,
            figsize=(18, 8.6),
            facecolor="white",
            gridspec_kw={"wspace": 0.06},
        )

        self._panel_status(axes[0], merged_chicago, bounds, city_proj)
        self._panel_cohort(axes[1], merged_chicago, bounds, city_proj)

        n_treated = int((tract_df["ever_treated"] == 1).sum())
        n_control = int((tract_df["ever_treated"] == 0).sum())
        n_total = len(tract_df)

        fig.suptitle(
            "Chicago STR-prohibition study: matched DiD sample (census tracts)",
            fontsize=17,
            fontweight="semibold",
            color="#262626",
            y=0.99,
        )
        fig.text(
            0.5,
            0.012,
            f"Sample: {n_total} matched tracts \u2014 {n_treated} ever-treated, {n_control} never-treated comparators. "
            "Tracts outside the matched panel are shown in light grey.",
            ha="center",
            va="bottom",
            fontsize=10,
            color="#444444",
            fontstyle="italic",
        )

        out_combined = self.output_dir / "did_story_map.png"
        plt.savefig(out_combined, dpi=220, bbox_inches="tight", facecolor="white", pad_inches=0.15)
        plt.close(fig)

        self._panel_status_only(merged_chicago, bounds, city_proj)
        self._panel_cohort_only(merged_chicago, bounds, city_proj)

        logger.info("Editorial maps saved under %s", self.output_dir)
        return {
            "did_story_map_plot": str(out_combined),
        }

    # ------------------------------------------------------------------
    def _panel_status(self, ax, merged, bounds, city) -> None:
        """Treated vs. matched-control vs. out-of-sample tracts."""

        out_of_sample = merged[merged["status"] == "Out of sample"]
        controls = merged[merged["status"] == "Matched control"]
        treated = merged[merged["status"] == "Treated"]

        out_of_sample.plot(ax=ax, color=OUT_OF_SAMPLE, edgecolor="white", linewidth=0.1, zorder=1)
        controls.plot(ax=ax, color=CONTROL, edgecolor=TRACT_EDGE, linewidth=0.25, zorder=2, alpha=0.92)
        treated.plot(ax=ax, color=TREATED, edgecolor=TRACT_EDGE, linewidth=0.25, zorder=3, alpha=0.92)

        if city is not None:
            city.boundary.plot(ax=ax, color=CITY_EDGE, linewidth=1.0, zorder=4)

        self._frame_axes(ax, bounds, "Who is in the matched DiD panel")
        legend_handles = [
            mpatches.Patch(facecolor=TREATED, edgecolor="white", label="Treated tract (ever STR prohibition)"),
            mpatches.Patch(facecolor=CONTROL, edgecolor="white", label="Matched never-treated control"),
            mpatches.Patch(facecolor=OUT_OF_SAMPLE, edgecolor="#bbbbbb", label="Tract outside matched panel"),
        ]
        ax.legend(
            handles=legend_handles,
            loc="lower left",
            frameon=False,
            fontsize=10,
            handlelength=1.2,
        )

    # ------------------------------------------------------------------
    def _panel_cohort(self, ax, merged, bounds, city) -> None:
        """First-prohibition year as 4 ordinal cohort phases."""

        for phase in _YEAR_ORDER:
            sub = merged[merged["cohort_phase"] == phase]
            if sub.empty:
                continue
            color = _YEAR_PALETTE[phase]
            edge = "white" if phase != "Not treated" else "#dddddd"
            zorder = 2 if phase == "Not treated" else 3
            sub.plot(
                ax=ax,
                color=color,
                edgecolor=edge,
                linewidth=0.25 if phase != "Not treated" else 0.1,
                zorder=zorder,
                alpha=0.94 if phase != "Not treated" else 1.0,
            )

        if city is not None:
            city.boundary.plot(ax=ax, color=CITY_EDGE, linewidth=1.0, zorder=4)

        self._frame_axes(ax, bounds, "When did treated tracts first see prohibition?")
        legend_handles = [
            mpatches.Patch(facecolor=_YEAR_PALETTE[p], edgecolor="white", label=p)
            for p in _YEAR_ORDER
        ]
        ax.legend(
            handles=legend_handles,
            loc="lower left",
            frameon=False,
            fontsize=10,
            handlelength=1.2,
        )

    # ------------------------------------------------------------------
    def _panel_status_only(self, merged, bounds, city) -> None:
        fig, ax = plt.subplots(figsize=(11, 11), facecolor="white")
        self._panel_status(ax, merged, bounds, city)
        plt.savefig(
            self.output_dir / "did_story_map_status.png",
            dpi=240,
            bbox_inches="tight",
            facecolor="white",
        )
        plt.close(fig)

    def _panel_cohort_only(self, merged, bounds, city) -> None:
        fig, ax = plt.subplots(figsize=(11, 11), facecolor="white")
        self._panel_cohort(ax, merged, bounds, city)
        plt.savefig(
            self.output_dir / "did_story_map_cohort.png",
            dpi=240,
            bbox_inches="tight",
            facecolor="white",
        )
        plt.close(fig)

    # ------------------------------------------------------------------
    @staticmethod
    def _frame_axes(ax, bounds, title: str) -> None:
        minx, miny, maxx, maxy = bounds
        span_x = maxx - minx
        span_y = maxy - miny
        ax.set_xlim(minx - 0.01 * span_x, maxx + 0.01 * span_x)
        ax.set_ylim(miny - 0.01 * span_y, maxy + 0.01 * span_y)
        ax.set_aspect("equal")
        ax.set_axis_off()
        ax.set_title(title, fontsize=14, color="#262626", pad=6, loc="left")
        _add_north_arrow(ax)

    # ------------------------------------------------------------------
    @staticmethod
    def _tract_frame(did_panel: pd.DataFrame) -> pd.DataFrame:
        panel = did_panel.copy()
        panel["tract_geoid"] = panel["tract_geoid"].astype(str)
        ever = panel.groupby("tract_geoid")["treated"].max()
        first_treat_month = (
            panel[panel["treated"] == 1].groupby("tract_geoid")["month"].min()
        )
        first_year = first_treat_month.dt.year.astype(float).reindex(ever.index)
        return pd.DataFrame(
            {
                "tract_geoid": ever.index.astype(str),
                "ever_treated": ever.astype(float).to_numpy(),
                "first_prohibition_year": first_year.to_numpy(),
            }
        )


__all__ = ["DiDStoryMapVisualizer"]
