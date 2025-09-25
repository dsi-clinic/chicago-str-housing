"""Pipeline example"""

import os
from pathlib import Path

from utils.preprocess_util_lib_example import generate_random_dataframe

if __name__ == "__main__":
    # This is an example of running the code as a pipeline
    # Rather than through a notebook
    data_dir = Path(os.environ["DATA_DIR"])
    output_directory = data_dir / "output"
    output_file = "sample_output.csv"
    output_directory.mkdir(parents=True, exist_ok=True)

    random_df = generate_random_dataframe()
    random_df.to_csv(output_directory / output_file, index=False)
    print(f"Saved random dataframe to {output_directory / output_file}")
