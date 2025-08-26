# This is a basic docker image for use in the clinic
FROM python:3.12-slim

# Switch to root to update and install tools
USER root
RUN apt-get update && apt-get install -y curl

# Install uv
ARG uv=/root/.local/bin/uv
ADD https://astral.sh/uv/install.sh /install.sh
RUN chmod +x /install.sh && /install.sh && rm /install.sh

# Create working directory
WORKDIR /project

# Adjust permissions for everything within /project before switching back to $NB_UID
COPY --chown=$NB_UID:$NB_GID src ./src
COPY --chown=$NB_UID:$NB_GID pyproject.toml .
COPY --chown=$NB_UID:$NB_GID requirements.txt .

# Switch back to the non-root user before installing Python packages
USER $NB_UID

# Install Python 3 packages
RUN /root/.local/bin/uv pip install --no-cache-dir -r requirements.txt --system

# Install project as an editable package
RUN /root/.local/bin/uv pip install -e . --system

CMD ["/bin/bash"]