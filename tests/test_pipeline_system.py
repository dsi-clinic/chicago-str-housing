"""Test suite for the Spatial Data Analysis Pipeline System.

This test file demonstrates the arrange-act-assert pattern for testing
the pipeline components and integration.
"""

import os
from typing import Any

import geopandas as gpd
import pandas as pd
import pytest

from housing import (
    CommunityBoundariesLoader,
    RentalDataLoader,
    TimeSeriesRentalLoader,
    ZipBoundariesLoader,
)
from pipeline import Pipeline
from pipeline.base import PipelineComponent, PipelineResult
from pipeline.config import ConfigManager, PipelineConfig


class TestPipelineComponents:
    """Test individual pipeline components using arrange-act-assert pattern."""

    def test_rental_data_loader_success(self) -> None:
        """Test RentalDataLoader with valid data file."""
        # Arrange
        loader = RentalDataLoader()

        # Act
        result = loader.execute({})

        # Assert
        assert isinstance(result, dict)
        assert "rental_data" in result
        rental_df = result["rental_data"]
        assert isinstance(rental_df, pd.DataFrame)
        assert len(rental_df) > 0
        assert "zip_code" in rental_df.columns
        assert "rental_price" in rental_df.columns

    def test_zip_boundaries_loader_success(self) -> None:
        """Test ZipBoundariesLoader with valid data file."""
        # Arrange
        loader = ZipBoundariesLoader()

        # Act
        result = loader.execute({})

        # Assert
        assert isinstance(result, dict)
        assert "zip_boundaries" in result
        zip_gdf = result["zip_boundaries"]
        assert isinstance(zip_gdf, gpd.GeoDataFrame)
        assert len(zip_gdf) > 0
        assert "zip_code" in zip_gdf.columns
        assert zip_gdf.geometry is not None

    def test_community_boundaries_loader_success(self) -> None:
        """Test CommunityBoundariesLoader with valid data file."""
        # Arrange
        loader = CommunityBoundariesLoader()

        # Act
        result = loader.execute({})

        # Assert
        assert isinstance(result, dict)
        assert "community_boundaries" in result
        community_gdf = result["community_boundaries"]
        assert isinstance(community_gdf, gpd.GeoDataFrame)
        assert len(community_gdf) > 0
        assert "community_name" in community_gdf.columns  # Actual column name
        assert community_gdf.geometry is not None

    def test_timeseries_rental_loader_success(self) -> None:
        """Test TimeSeriesRentalLoader with valid data file."""
        # Arrange
        loader = TimeSeriesRentalLoader()

        # Act
        result = loader.execute({})

        # Assert
        assert isinstance(result, dict)
        assert "timeseries_rental_data" in result
        rental_df = result["timeseries_rental_data"]
        assert isinstance(rental_df, pd.DataFrame)
        assert len(rental_df) > 0
        assert "zip_code" in rental_df.columns
        assert "month" in rental_df.columns
        assert "rental_price" in rental_df.columns


class TestPipelineIntegration:
    """Test pipeline integration and execution flow."""

    def test_pipeline_creation_and_configuration(self) -> None:
        """Test pipeline creation with configuration."""
        # Arrange
        config = PipelineConfig()

        # Act
        pipeline = Pipeline("Test Pipeline", config=config)
        pipeline.load_config()

        # Assert
        assert pipeline.name == "Test Pipeline"
        assert pipeline.pipeline_config is not None
        assert len(pipeline.components) == 0  # No components registered yet

    def test_pipeline_component_registration(self) -> None:
        """Test registering components with the pipeline."""
        # Arrange
        config = PipelineConfig()
        pipeline = Pipeline("Test Pipeline", config=config)
        pipeline.load_config()

        # Act
        pipeline.register_component(RentalDataLoader())
        pipeline.register_component(ZipBoundariesLoader())
        pipeline.register_component(CommunityBoundariesLoader())

        # Assert
        assert len(pipeline.components) == 3  # noqa: PLR2004
        assert "rental_data" in pipeline.components
        assert "zip_boundaries" in pipeline.components
        assert "community_boundaries" in pipeline.components

    def test_pipeline_execution_flow(self) -> None:
        """Test complete pipeline execution flow."""
        # Arrange
        config = PipelineConfig()
        pipeline = Pipeline("Test Pipeline", config=config)
        pipeline.load_config()

        # Register components
        pipeline.register_component(RentalDataLoader())
        pipeline.register_component(ZipBoundariesLoader())
        pipeline.register_component(CommunityBoundariesLoader())

        # Act
        results = pipeline.execute()

        # Assert
        assert isinstance(results, list)
        assert len(results) == 3  # Three components executed # noqa: PLR2004

        # Check each result
        for result in results:
            assert isinstance(result, PipelineResult)
            assert result.success is True

        # Check that context was populated
        assert len(pipeline.context) > 0
        assert "rental_data" in pipeline.context
        assert "zip_boundaries" in pipeline.context
        assert "community_boundaries" in pipeline.context

    def test_pipeline_error_handling(self) -> None:
        """Test pipeline error handling with invalid component."""
        # Arrange
        config = PipelineConfig()
        pipeline = Pipeline("Test Pipeline", config=config)
        pipeline.load_config()

        # Create a mock component that will fail
        class FailingComponent(PipelineComponent):
            """A component that fails."""

            def __init__(self) -> None:
                super().__init__("failing_component", "A component that fails")

            def execute(self, context: dict[str, Any]) -> dict[str, Any]:
                raise Exception("Intentional failure for testing")

        pipeline.register_component(FailingComponent())

        # Act
        results = pipeline.execute()

        # Assert
        assert len(results) == 1
        result = results[0]
        assert isinstance(result, PipelineResult)
        assert result.success is False
        assert (
            "intentional failure" in result.error.lower()
        )  # Check for actual error message


class TestConfigurationManagement:
    """Test configuration management system."""

    def test_default_configuration_creation(self) -> None:
        """Test creating default configuration."""
        # Arrange & Act
        config = PipelineConfig()

        # Assert
        assert config.data.rental_data_path is not None
        assert config.data.zip_boundaries_path is not None
        assert config.data.community_boundaries_path is not None
        assert config.output.output_dir is not None

    def test_configuration_file_validation(self) -> None:
        """Test configuration file validation."""
        # Arrange
        config = PipelineConfig()

        # Act & Assert
        # Test that required paths exist (or are URLs)
        assert config.data.rental_data_path.exists()

        # ZIP and Community boundaries can be URLs or file paths
        zip_path_str = str(config.data.zip_boundaries_path)
        if zip_path_str.startswith("http://") or zip_path_str.startswith("https://"):
            assert "cityofchicago.org" in zip_path_str  # Verify it's a valid URL
        else:
            assert config.data.zip_boundaries_path.exists()

        community_path_str = str(config.data.community_boundaries_path)
        if community_path_str.startswith("http://") or community_path_str.startswith(
            "https://"
        ):
            assert "cityofchicago.org" in community_path_str  # Verify it's a valid URL
        else:
            assert config.data.community_boundaries_path.exists()

    def test_config_manager_loading(self) -> None:
        """Test ConfigManager loading configuration."""
        # Arrange
        config_manager = ConfigManager()

        # Act
        config = config_manager.load_config()

        # Assert
        assert isinstance(config, PipelineConfig)
        assert config.data.rental_data_path is not None

    def test_environment_variable_override(self) -> None:
        """Test configuration override with environment variables."""
        # Arrange
        original_data_dir = os.environ.get("DATA_DIR")

        # Act
        os.environ["DATA_DIR"] = "/project/data"  # Use existing path
        config = PipelineConfig()

        # Assert
        assert str(config.data.rental_data_path).startswith("/project/data")

        # Cleanup
        if original_data_dir:
            os.environ["DATA_DIR"] = original_data_dir
        else:
            del os.environ["DATA_DIR"]


class TestDataValidation:
    """Test data validation and quality checks."""

    def test_rental_data_validation(self) -> None:
        """Test rental data validation."""
        # Arrange
        loader = RentalDataLoader()

        # Act
        result = loader.execute({})

        # Assert
        if isinstance(result, dict) and "rental_data" in result:
            rental_df = result["rental_data"]
            assert len(rental_df) > 0
            assert rental_df["rental_price"].min() > 0
            assert (
                rental_df["rental_price"].max() < 100000  # noqa: PLR2004
            )  # Reasonable upper bound
            assert (
                rental_df["zip_code"].str.len().min() >= 5  # noqa: PLR2004
            )  # Valid zip code length

    def test_spatial_data_validation(self) -> None:
        """Test spatial data validation."""
        # Arrange
        zip_loader = ZipBoundariesLoader()
        community_loader = CommunityBoundariesLoader()

        # Act
        zip_result = zip_loader.execute({})
        community_result = community_loader.execute({})

        # Assert
        if isinstance(zip_result, dict) and "zip_boundaries" in zip_result:
            zip_gdf = zip_result["zip_boundaries"]
            assert zip_gdf.crs is not None
            assert zip_gdf.geometry.is_valid.all()

        if (
            isinstance(community_result, dict)
            and "community_boundaries" in community_result
        ):
            community_gdf = community_result["community_boundaries"]
            assert community_gdf.crs is not None
            assert community_gdf.geometry.is_valid.all()


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
