"""Create the third-difference group for triple-difference analysis.

Uses a census variable (e.g. median_income) to define high vs low group per tract.
"""

from __future__ import annotations

import logging
from typing import Any

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TripleDiffGroupProcessor(DataProcessor):
    """Add a binary group variable to ddd_panel based on a census variable."""

    def __init__(
        self,
        group_variable: str = "median_income",
        group_type: str = "median",
        threshold: float | None = None,
        group_name: str | None = None,
    ) -> None:
        """Initialize the triple-diff group processor.

        Args:
            group_variable: Census column to use for grouping (e.g. median_income).
            group_type: 'median' = above/below median; 'threshold' = above/below threshold.
            threshold: Used when group_type='threshold'.
            group_name: Name for the 0/1 column (e.g. high_income). Default: high_{group_variable}.
        """
        super().__init__(
            "triplediff_group",
            "Create high/low group for triple-difference analysis",
        )
        self.group_variable = group_variable
        self.group_type = group_type
        self.threshold = threshold
        self.group_name = group_name or f"high_{group_variable}"
        self.required_data = ["ddd_panel"]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Add group indicator to ddd_panel."""
        ddd_panel = context["ddd_panel"].copy()

        if self.group_variable not in ddd_panel.columns:
            raise ValueError(
                f"Group variable '{self.group_variable}' not in ddd_panel. "
                "Ensure CensusPanelMerger ran and included this column."
            )

        # One value per tract; use first non-null per tract if needed
        tract_vals = ddd_panel.groupby("tract_geoid")[self.group_variable].transform(
            "first"
        )

        if self.group_type == "median":
            cut = tract_vals.median()
            ddd_panel[self.group_name] = (tract_vals >= cut).astype(int)
            logger.info(
                "Group '%s': median(%s)=%s, high=1",
                self.group_name,
                self.group_variable,
                cut,
            )
        elif self.group_type == "threshold":
            if self.threshold is None:
                raise ValueError("group_type='threshold' requires threshold=...")
            ddd_panel[self.group_name] = (tract_vals >= self.threshold).astype(int)
            logger.info(
                "Group '%s': %s >= %s",
                self.group_name,
                self.group_variable,
                self.threshold,
            )
        else:
            raise ValueError(
                f"group_type must be 'median' or 'threshold', got {self.group_type!r}"
            )

        # Drop rows with missing group (missing census for that tract)
        before = len(ddd_panel)
        ddd_panel = ddd_panel.dropna(subset=[self.group_name])
        ddd_panel[self.group_name] = ddd_panel[self.group_name].astype(int)
        if len(ddd_panel) < before:
            logger.info(
                "Dropped %d rows with missing census/group",
                before - len(ddd_panel),
            )

        n_high = ddd_panel[self.group_name].eq(1).sum()
        logger.info(
            "ddd_panel rows=%d, %s=1: %d",
            len(ddd_panel),
            self.group_name,
            n_high,
        )

        return {"ddd_panel": ddd_panel, "ddd_group_name": self.group_name}
