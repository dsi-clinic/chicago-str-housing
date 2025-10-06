# This is a basic docker image for use in the clinic
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Switch to root to update and install tools
RUN apt-get update && apt-get install -y curl git

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    gcc \
    g++ \
    make \
    pkg-config && \
    rm -rf /var/lib/apt/lists/*

# Set environment variables so GDAL is found
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal
ENV GDAL_CONFIG=/usr/bin/gdal-config

# Create working directory
WORKDIR /project

COPY pyproject.toml .

# Resolve and install Python packages from pyproject/uv.lock
RUN /usr/local/bin/uv venv
ENV VIRTUAL_ENV=/project/.venv
ENV PATH="/project/.venv/bin:$PATH"
ENV PYTHONPATH=/project
RUN uv sync

CMD ["/bin/bash"]