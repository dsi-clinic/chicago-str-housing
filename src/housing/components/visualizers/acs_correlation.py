"""Correlation analysis visualizer.

This module creates visualizations for correlation analysis results.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class ACSCorrelationVisualizer(Visualizer):
    """Create visualizations for the correlation analysis.

    This demonstrates how to create meaningful visualizations from merged spatial data.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        super().__init__(
            "correlation_visualization",
            "Create visualizations for correlation analysis",
        )
        self.output_dir = output_dir or "/project/data/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create correlation visualizations."""
        logger.info("Creating correlation visualizations...")

        correlation_matrix = context["tract_correlation_matrix"]

        # Create figure with subplots
        fig, axes = plt.subplots(figsize=(16, 12))
        fig.suptitle(
            "Data Analysis: Census Tract Demographic Data",
            fontsize=16,
            fontweight="bold",
        )

        logger.info("Check if subplots are made")

        # 1. Correlation heatmap
        sns.heatmap(
            correlation_matrix,
            annot=True,
            cmap="RdBu_r",
            center=0,
            square=True,
            ax=axes,
        )
        axes.set_title("Correlation Matrix")

        # Save the plot
        output_path = Path(self.output_dir) / "correlation_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved visualization to: %s", output_path)

        plt.show()

        return {"visualization_path": str(output_path)}
