"""Test file to verify housing package imports and functionality."""

import pandas as pd

from housing.preprocess_util_lib_example import generate_random_dataframe


def test_generate_random_dataframe() -> None:
    """Test that generate_random_dataframe creates a valid DataFrame."""
    # Test with default parameters
    df = generate_random_dataframe()  # noqa: PD901

    # Check that it returns a DataFrame
    assert isinstance(df, pd.DataFrame)  # noqa: S101

    # Check default shape (10 rows, 4 columns)
    assert df.shape == (10, 4)  # noqa: S101

    # Check column names
    assert list(df.columns) == ["A", "B", "C", "D"]  # noqa: S101

    # Check that all values are integers
    assert df.dtypes.apply(lambda x: pd.api.types.is_integer_dtype(x)).all()  # noqa: S101


def test_generate_random_dataframe_custom_rows() -> None:
    """Test generate_random_dataframe with custom number of rows."""
    # Test with custom number of rows
    df = generate_random_dataframe(no_rows=5)  # noqa: PD901

    # Check shape
    assert df.shape == (5, 4)  # noqa: S101

    # Check column names
    assert list(df.columns) == ["A", "B", "C", "D"]  # noqa: S101


def test_package_import() -> None:
    """Test that we can successfully import from the housing package."""
    # This test just verifies the import works

    # If we get here without an ImportError, the test passes
    assert callable(generate_random_dataframe)  # noqa: S101
