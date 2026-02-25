"""Trend-matched Difference-in-Differences (DiD) pipeline.

This script:
1. Runs the standard DiD pipeline to construct the full did_panel
2. Runs a second pipeline that:
   - Applies trend matching on pre-treatment rent trends
   - Re-runs DiD descriptive analysis, DiD estimation, and event study
   - Produces matched-sample outputs with a `_matched` suffix
"""

from __future__ import annotations

import logging
from typing import Any

from housing.components.analyzers.did_analyzer import DIDAnalyzer
from housing.components.analyzers.did_descriptive import DIDDescriptiveAnalyzer
from housing.components.analyzers.event_study import EventStudyAnalyzer
from housing.components.processors.trend_matching import TrendMatchingProcessor
from housing.components.visualizers.did_trends import DIDTrendsVisualizer
from housing.components.visualizers.event_study import EventStudyVisualizer
from housing.scripts.did_pipeline import run_full_analysis
from pipeline import Pipeline, PipelineResult

logger = logging.getLogger(__name__)


def run_trend_matched_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Run the full DiD analysis followed by trend-matched re-analysis."""
    logger.info("Running baseline Housing DiD Analysis to obtain did_panel...")
    base_pipeline, _ = run_full_analysis()

    if "did_panel" not in base_pipeline.context:
        raise ValueError(
            "Base pipeline did not produce 'did_panel' in context. "
            "Ensure the standard DiD pipeline runs successfully first."
        )

    did_panel = base_pipeline.context["did_panel"]
    output_dir: str = base_pipeline.context.get("output_dir", "/project/output")

    logger.info("Starting trend-matched DiD analysis...")
    matched_pipeline = Pipeline("Housing DiD Trend-Matched Analysis")

    # Seed context with did_panel and output configuration
    matched_pipeline.add_to_context("did_panel", did_panel)
    matched_pipeline.add_to_context("output_dir", output_dir)
    # Used by analyzers/visualizers to avoid overwriting baseline outputs
    matched_pipeline.add_to_context("output_suffix", "_matched")

    # Register components in desired execution order
    trend_matching = TrendMatchingProcessor(k_neighbors=3, min_pre_periods=6)
    did_descriptive = DIDDescriptiveAnalyzer()
    did_estimator = DIDAnalyzer()
    event_study = EventStudyAnalyzer()
    did_trends_viz = DIDTrendsVisualizer(output_dir=output_dir)
    event_study_viz = EventStudyVisualizer(output_dir=output_dir)

    matched_pipeline.register_component(trend_matching)
    matched_pipeline.register_component(did_descriptive)
    matched_pipeline.register_component(did_estimator)
    matched_pipeline.register_component(event_study)
    matched_pipeline.register_component(did_trends_viz)
    matched_pipeline.register_component(event_study_viz)

    # Explicit execution order:
    # trend_matching → did_descriptive → did_estimation → event_study
    # → did_trends_visualization → event_study_visualization
    matched_pipeline.set_execution_order(
        [
            trend_matching.name,
            did_descriptive.name,
            did_estimator.name,
            event_study.name,
            did_trends_viz.name,
            event_study_viz.name,
        ]
    )

    results = matched_pipeline.execute()
    return matched_pipeline, results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Running trend-matched Housing DiD Analysis.")
    logger.info("=" * 70)

    pipeline, results = run_trend_matched_analysis()

    logger.info("\n" + "=" * 70)
    logger.info("Trend-matched analysis complete! Check the output/ directory for results.")

