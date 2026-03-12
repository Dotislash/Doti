FROM python:3.12-slim AS base

# System dependencies: common dev tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl jq tree build-essential gcc g++ make \
    && rm -rf /var/lib/apt/lists/*

# Node.js LTS
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# RTK (Rust Token Killer) for output compression
RUN curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh

# Python tools
RUN pip install --no-cache-dir uv ruff

# Install executor
COPY pyproject.toml /opt/doti-executor/
COPY executor/ /opt/doti-executor/executor/
RUN pip install --no-cache-dir /opt/doti-executor

WORKDIR /workspace
EXPOSE 8811

# Run as non-root (UID/GID mapped at runtime via --user)
ENTRYPOINT ["doti-executor"]
