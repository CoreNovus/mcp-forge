# Shared Dockerfile for any mcp-forge-scaffolded server.
#
# Build context: one of the scaffolded server directories (e.g. ./search-mcp/).
# Build arg:     PKG_NAME = the underscored package name (e.g. search_mcp).
#
# Usage (from examples/multi-server/):
#   docker build -f Dockerfile --build-arg PKG_NAME=search_mcp ./search-mcp

FROM python:3.11-slim

ARG PKG_NAME
ENV PKG_NAME=${PKG_NAME}

WORKDIR /app

# Install the scaffolded server package. The generated pyproject.toml declares
# mcp-forge-core as a dependency, which pip will resolve from PyPI (or from a
# local wheel if you mount one — left as an exercise).
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

EXPOSE 8000

# run_server() reads MCP_SERVER_MODE / MCP_SERVER_HOST / MCP_SERVER_PORT from env.
CMD python -m ${PKG_NAME}.server
