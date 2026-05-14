"""Shared Matplotlib styling for DiD / white-paper figures (reusable, consistent)."""

from __future__ import annotations

import matplotlib.pyplot as plt

# UChicago-adjacent palette: maroon treated, teal control, warm accent
COLORS: dict[str, str] = {
    "treated": "#7B1111",
    "treated_light": "#B85C5C",
    "control": "#0D4F6B",
    "control_light": "#5A8FA8",
    "accent": "#C4742A",
    "neutral": "#2D2D2D",
    "muted": "#6B6B6B",
    "grid": "#E0E0E0",
    "before": "#6B6B6B",
    "after": "#7B1111",
}


def configure_did_matplotlib_style() -> None:
    """Apply a compact, print-friendly rcParams theme (call once per figure batch)."""
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "#FAFAFA",
            "axes.edgecolor": "#CCCCCC",
            "axes.labelcolor": COLORS["neutral"],
            "axes.titlecolor": COLORS["neutral"],
            "text.color": COLORS["neutral"],
            "xtick.color": "#444444",
            "ytick.color": "#444444",
            "font.family": "sans-serif",
            "font.sans-serif": [
                "Helvetica Neue",
                "Arial",
                "DejaVu Sans",
                "sans-serif",
            ],
            "font.size": 10.5,
            "axes.titlesize": 12,
            "axes.labelsize": 10.5,
            "axes.titleweight": "semibold",
            "axes.grid": True,
            "grid.color": COLORS["grid"],
            "grid.linestyle": "-",
            "grid.linewidth": 0.6,
            "grid.alpha": 1.0,
            "legend.frameon": False,
            "legend.fontsize": 9,
            "savefig.dpi": 200,
            "savefig.bbox": "tight",
            "savefig.facecolor": "white",
        },
    )
