"""Outlier removal processor for tract-level density data.

This module provides a reusable processor for removing tracts with extreme density values
across different data types (Airbnb, STR prohibition, affordable development, etc.).
"""

import logging
from typing import Any, Literal

from housing.components.utils import remove_density_outliers
from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class DensityOutlierRemovalProcessor(DataProcessor):
    """Remove tracts with extreme density values - reusable across pipelines.

    This processor can be applied to any tract-level data with density columns
    to remove outliers that might skew analysis or clustering results.
    """

    def __init__(
        self,
        input_key: str,
        output_key: str,
        density_columns: str | list[str],
        method: Literal["iqr", "percentile", "zscore", "winsorize"] = "iqr",
        threshold: float = 1.5,
        percentile_threshold: float = 0.99,
        zscore_threshold: float = 3.0,
    ) -> None:
        """Initialize the density outlier removal processor.

        Args:
            input_key: Context key for input tract data
            output_key: Context key for output cleaned tract data
            density_columns: Single density column name or list of column names
            method: Outlier detection method ('iqr', 'percentile', or 'zscore')
            threshold: IQR multiplier or z-score threshold
            percentile_threshold: Percentile threshold (0.99 = remove top 1%)
            zscore_threshold: Z-score threshold for outlier detection
        """
        super().__init__(
            f"outlier_removal_{input_key}",
            f"Remove density outliers from {input_key}",
        )
        self.input_key = input_key
        self.output_key = output_key
        self.density_columns = (
            [density_columns] if isinstance(density_columns, str) else density_columns
        )
        self.method = method
        self.threshold = threshold
        self.percentile_threshold = percentile_threshold
        self.zscore_threshold = zscore_threshold

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Remove density outliers from tract data.

        Args:
            context: Pipeline context containing tract data

        Returns:
            Dictionary with cleaned tract data
        """
        tract_data = context[self.input_key]

        if tract_data is None:
            logger.warning(
                "No tract data found for key '%s', skipping outlier removal",
                self.input_key,
            )
            return {self.output_key: None}

        logger.info(
            "Processing density outliers using %s method",
            self.method,
        )

        # Apply outlier removal to each density column
        filtered_data = tract_data.copy()

        for density_col in self.density_columns:
            if density_col in filtered_data.columns:
                filtered_data = remove_density_outliers(
                    filtered_data,
                    density_col,
                    method=self.method,
                    threshold=self.threshold,
                    percentile_threshold=self.percentile_threshold,
                    zscore_threshold=self.zscore_threshold,
                )
            else:
                logger.warning("Density column '%s' not found in data", density_col)

        return {self.output_key: filtered_data}
