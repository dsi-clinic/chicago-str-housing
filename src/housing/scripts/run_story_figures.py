"""Generate did_story_*.png figures without running the full CS pipeline.

Loads required data from existing CSVs, calls DIDStoryGraphicsVisualizer,
and writes a supplementary crosswalk-coverage figure.

Usage:
  export PYTHONPATH=src
  python src/housing/scripts/run_story_figures.py [--dir binary|threshold]

Reads from: output/did-cs-whitepaper-<dir>/
Writes to:  output/did-cs-whitepaper-<dir>/  (did_story_*.png)
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from housing.components.visualizers.did_matplotlib_theme import (
    COLORS,
    configure_did_matplotlib_style,
)
from housing.components.visualizers.did_story_graphics import DIDStoryGraphicsVisualizer

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_context(out_dir: Path) -> dict:
    """Build visualizer context dict from CSV files in *out_dir*."""
    ctx: dict = {}

    # sample lineage
    p = out_dir / "did_descriptive_sample_lineage.csv"
    if p.exists():
        ctx["sample_lineage"] = pd.read_csv(p)
        log.info("Loaded sample_lineage (%d rows)", len(ctx["sample_lineage"]))

    # matching diagnostics + control reuse table
    pd_path = out_dir / "did_matching_diagnostics.csv"
    cr_path = out_dir / "did_matching_control_reuse.csv"
    if pd_path.exists():
        row = pd.read_csv(pd_path).iloc[0]
        diag = dict(row)
        if cr_path.exists():
            diag["control_reuse_table"] = pd.read_csv(cr_path)
            log.info(
                "Loaded control_reuse_table (%d rows)", len(diag["control_reuse_table"])
            )
        ctx["matching_diagnostics"] = diag
        log.info("Loaded matching_diagnostics")

    # did_panel (large — needed for violin + trends scatter)
    panel_path = out_dir / "did_panel_data.csv"
    if panel_path.exists():
        log.info("Loading did_panel_data.csv (may take a moment)...")
        ctx["did_panel"] = pd.read_csv(panel_path, parse_dates=["month"])
        log.info("Loaded did_panel (%d rows)", len(ctx["did_panel"]))
    else:
        log.warning(
            "did_panel_data.csv not found — violin and scatter plots will be skipped"
        )

    return ctx


def _plot_crosswalk_coverage(out_dir: Path) -> str | None:
    """Histogram of tract coverage share (not produced by DIDStoryGraphicsVisualizer)."""
    cov_path = out_dir / "did_crosswalk_tract_coverage.csv"
    diag_path = out_dir / "did_crosswalk_diagnostics.csv"
    if not cov_path.exists():
        log.warning(
            "did_crosswalk_tract_coverage.csv not found — skipping coverage figure"
        )
        return None

    cov = pd.read_csv(cov_path)
    configure_did_matplotlib_style()
    fig, ax = plt.subplots(figsize=(8, 4.2))
    coverage_pct = cov["tract_coverage_share"].dropna() * 100

    ax.hist(
        coverage_pct,
        bins=25,
        color=COLORS.get("accent", "#2563EB"),
        alpha=0.85,
        edgecolor="white",
    )
    ax.axvline(
        95,
        color=COLORS.get("treated", "#8B0000"),
        lw=1.8,
        ls="--",
        label="95% threshold",
    )
    ax.axvline(
        50, color=COLORS.get("before", "#D97706"), lw=1.4, ls=":", label="50% threshold"
    )

    if diag_path.exists():
        d = pd.read_csv(diag_path).iloc[0]
        n = int(d["n_tracts"])
        ge95 = int(d["tracts_with_coverage_ge_95pct"])
        lt50 = int(d["tracts_with_coverage_lt_50pct"])
        ax.axvline(
            95,
            color=COLORS.get("treated", "#8B0000"),
            lw=1.8,
            ls="--",
            label=f"≥ 95% covered: {ge95}/{n} ({ge95/n*100:.0f}%)",
        )
        ax.axvline(
            50,
            color=COLORS.get("before", "#D97706"),
            lw=1.4,
            ls=":",
            label=f"< 50% covered: {lt50}/{n} ({lt50/n*100:.0f}%)",
        )

    ax.set_xlabel(
        "Tract coverage share (% of tract area inside a ZORI ZIP)", fontsize=10
    )
    ax.set_ylabel("Number of tracts", fontsize=10)
    ax.set_title(
        "ZIP → Tract Crosswalk Coverage Distribution\n"
        "(higher = more of the tract is inside a ZORI-covered ZIP code)",
        fontsize=12,
        fontweight="semibold",
        pad=10,
    )
    ax.legend(fontsize=9, framealpha=0.85)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    out = out_dir / "did_story_crosswalk_coverage.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    log.info("✓ did_story_crosswalk_coverage.png")
    return str(out)


def run(run_dir: str = "binary") -> None:
    """Regenerate story figures from an existing whitepaper pipeline output directory."""
    out_dir = REPO_ROOT / "output" / f"did-cs-whitepaper-{run_dir}"
    if not out_dir.exists():
        raise FileNotFoundError(f"Output directory not found: {out_dir}")

    log.info("Generating story figures in %s", out_dir)

    ctx = _load_context(out_dir)
    viz = DIDStoryGraphicsVisualizer(output_dir=out_dir)
    results = viz.execute(ctx)

    for name, _path in results.items():
        log.info("✓ %s", name)

    _plot_crosswalk_coverage(out_dir)

    total = len(results) + (
        1 if (out_dir / "did_story_crosswalk_coverage.png").exists() else 0
    )
    log.info("Done — %d figure(s) written to %s", total, out_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir",
        default="binary",
        choices=["binary", "threshold"],
        help="Which whitepaper output directory to use",
    )
    args = parser.parse_args()
    run(args.dir)
