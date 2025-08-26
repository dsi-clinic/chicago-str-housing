"""Pipeline example"""

from utils.preprocess_util_lib_example import REPO_ROOT, save_random_dataframe

if __name__ == "__main__":
    # This is an example of running the code as a pipeline
    # Rather than through a notebook
    output_directory = REPO_ROOT / "output"
    output_file = "sample_output.csv"
    output_directory.mkdir(parents=True, exist_ok=True)

    save_random_dataframe(
        output_directory,
        output_file,
    )
