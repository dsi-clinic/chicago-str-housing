"""Difference-in-Differences  analyzer.

This module:
- gets the DiD panel from context
- sets up the panel index
- estimates the TWFE model
- extracts and returns key results (coefficient, SE, p-value, CI)
- logs a summary of findings
"""

import logging
from pathlib import Path
from typing import Any

from linearmodels import PanelOLS

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


class DIDAnalyzer(Analyzer):
    """Analyze difference-in-differences analysis on the panel data.

    This demonstrates the difference-in-differences analysis on the panel data.
    It returns the coefficient, SE, p-value, CI of the treatment effect.
    """

    def __init__(self) -> None:
        """Initialize the DID analyzer."""
        super().__init__(
            "did_analysis",
            "Analyze difference-in-differences analysis on the panel data",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform DID analysis."""
        logger.info("Performing difference-in-differences analysis on the panel data")

        did_panel = context["did_panel_data"]

        # Set multi-index: (entity, time)
        panel = did_panel.set_index(["tract_geoid", "month"])
        panel["treated"] = panel["treated"].astype(float)
        panel["rental_price"] = panel["rental_price"].astype(float)

        model = PanelOLS.from_formula(
            "rental_price ~ 1 + treated + EntityEffects + TimeEffects",
            data=panel,
        )
        results = model.fit(cov_type="clustered", cluster_entity=True)
        logger.info("Created and fit panel OLS model")

        output_dir = Path("/project/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / "did_analysis.txt"

        with Path(report_path).open("w") as f:
            f.write("DID Analysis\n")
            f.write("=" * 50 + "\n\n")
            f.write("Results\n")
            f.write(results.summary.as_text() + "\n\n")

        logger.info("Wrote analysis report to: %s", report_path)

        return {
            "did_results": results,
        }
