"""Utilities example"""

import os

import numpy as np
import pandas as pd

REPO_ROOT = os.environ["REPO_ROOT"]


def generate_random_dataframe(no_rows: int = 10) -> pd.DataFrame:
    """Generates a random dataframe.

    Args:
        no_rows: number of rows to generate

    Returns: dataframe with 4 columns and no_rows rows.
    """
    random_df = pd.DataFrame(
        np.random.randint(0, no_rows, size=(no_rows, 4)), columns=list("ABCD")
    )

    return random_df
