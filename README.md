# 2025-autumn-city-of-chicago-housing

## Project Background

[Please add project background]

## Project Goals

[Please add project goals]

## First Week
- Complete the quick start below, making sure that you can find the file `sample_output.csv`.
[Please add first week activities]

### Docker

## Quick Start

### 1. Setup Environment
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env to set your data directory path
# Example: DATA_DIR=/Users/yourname/project/data
```

### 2. Install Pre-commit Hooks
```bash
make run-interactive
# Inside container:
cd src
pre-commit install
exit
```

### 3. Test Your Setup
```bash
make test-pipeline
```

If successful, you should see `sample_output.csv` appear in your data directory.

## Technical Expectations

### Pre requisites:

We use Docker, Make and uv as part of our curriculum. If you are unfamiliar with them, it is strongly recommended you read over the following:
- [An introduction to Docker](https://docker-curriculum.com/)
- [An introduction to uv](https://realpython.com/python-uv/)

### Container-Based Development

**All code must be run inside the Docker container.** This ensures consistent environments across different machines and eliminates "works on my machine" issues.

### Environment Management with uv

We use [uv](https://docs.astral.sh/uv/) for Python environment and package management _inside the container_. uv handles:
- Virtual environment creation and management (replaces venv/pyenv)
- Package installation and dependency resolution (replaces pip)
- Project dependency management via `pyproject.toml`

**Important**: When running Python code, prefix commands with `uv run` to maintain the proper environment:

```bash
# Example: Running the pipeline
uv run python src/utils/pipeline_example.py

# Example: Running a notebook
uv run jupyter lab

# Example: Running tests
uv run pytest
```

### Container Volume Structure

```
Container: /project/
├── src/           # Your source code (mounted from host repo)
├── data/          # Data directory (mounted from HOST_DATA_DIR)
├── .venv/         # Python virtual environment (created in container)
├── pyproject.toml # Project configuration
└── ...
```


## Usage & Testing

- Set `DATA_DIR` in your `.env` file to specify where data lives on your host
- This directory is mounted to `/project/data` inside the container
- Keep data separate from code to avoid repository bloat and enable easy data sharing

Run the command `make test-pipeline`. If your setup is working you should see a file `sample_output.csv` appear in your data directory. 


### Docker & Make

We use `docker` and `make` to run our code. There are three built-in `make` commands:

* `make build-only`: This will build the image only. It is useful for testing and making changes to the Dockerfile.
* `make run-notebooks`: This will run a Jupyter server, which also mounts the current directory into `/program`.
* `make run-interactive`: This will create a container (with the current directory mounted as `/program`) and load an interactive session. 

The file `Makefile` contains details about the specific commands that are run when calling each `make` target.




## Style
We use [`ruff`](https://docs.astral.sh/ruff/) to enforce style standards and grade code quality. This is an automated code checker that looks for specific issues in the code that need to be fixed to make it readable and consistent with common standards. `ruff` is run before each commit via [`pre-commit`](https://pre-commit.com/). If it fails, the commit will be blocked and the user will be shown what needs to be changed.

Once you have followed the quick setup instructions above for installing dependencies, you can run:
```bash
pre-commit run --all-files
```

You can also run `ruff` directly:
```bash
ruff check
ruff format
```