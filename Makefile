
# general
mkfile_path := $(abspath $(firstword $(MAKEFILE_LIST)))
current_dir := $(notdir $(patsubst %/,%,$(dir $(mkfile_path))))
current_abs_path := $(subst Makefile,,$(mkfile_path))

# pipeline constants
# PROJECT_NAME
project_name := "2025-autumn-city-of-chicago-housing"
project_dir := "$(current_abs_path)"

# environment variables
include .env

# Check required environment variables
ifeq ($(DATA_DIR),)
    $(error DATA_DIR must be set in .env file)
endif


# Build Docker image 
# Global mount for data directory
mount_data := -v $(DATA_DIR):/project/data

.PHONY: build-only run-interactive run-notebooks test-pipeline clean

# Build Docker image 
build-only: 
	docker compose build

run-interactive: build-only	
	docker compose run -it --rm $(mount_data) $(project_name) /bin/bash

run-notebooks: build-only	
	docker compose run --rm -p 8888:8888 -t $(mount_data) $(project_name) uv run jupyter lab --port=8888 --ip='*' --NotebookApp.token='' --NotebookApp.password='' --no-browser --allow-root

test-pipeline: build-only
	docker compose run --rm $(mount_data) $(project_name) uv run python src/utils/pipeline_example.py

clean:
	docker compose down --rmi all --volumes --remove-orphans
	docker image prune -f


