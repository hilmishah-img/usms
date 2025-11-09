# syntax=docker/dockerfile:1

################################################################################
# Development Stage
################################################################################
FROM ghcr.io/astral-sh/uv:python3.10-bookworm AS dev

# Create and activate a virtual environment [1].
# [1] https://docs.astral.sh/uv/concepts/projects/config/#project-environment-path
ENV VIRTUAL_ENV=/opt/venv
ENV PATH=$VIRTUAL_ENV/bin:$PATH
ENV UV_PROJECT_ENVIRONMENT=$VIRTUAL_ENV

# Tell Git that the workspace is safe to avoid 'detected dubious ownership in repository' warnings.
RUN git config --system --add safe.directory '*'

# Create a non-root user and give it passwordless sudo access [1].
# [1] https://code.visualstudio.com/remote/advancedcontainers/add-nonroot-user
RUN --mount=type=cache,target=/var/cache/apt/ \
    --mount=type=cache,target=/var/lib/apt/ \
    groupadd --gid 1000 user && \
    useradd --create-home --no-log-init --gid 1000 --uid 1000 --shell /usr/bin/bash user && \
    chown user:user /opt/ && \
    apt-get update && apt-get install --no-install-recommends --yes sudo && \
    echo 'user ALL=(root) NOPASSWD:ALL' > /etc/sudoers.d/user && chmod 0440 /etc/sudoers.d/user
USER user

# Configure the non-root user's shell.
RUN mkdir ~/.history/ && \
    echo 'HISTFILE=~/.history/.bash_history' >> ~/.bashrc && \
    echo 'bind "\"\e[A\": history-search-backward"' >> ~/.bashrc && \
    echo 'bind "\"\e[B\": history-search-forward"' >> ~/.bashrc && \
    echo 'eval "$(starship init bash)"' >> ~/.bashrc

################################################################################
# Builder Stage (Production Dependencies)
################################################################################
FROM ghcr.io/astral-sh/uv:python3.10-bookworm-slim AS builder

# Build argument to control API installation
ARG INSTALL_API=true

# Set working directory
WORKDIR /build

# Copy dependency files and source code
COPY pyproject.toml ./
COPY README.md ./
COPY LICENSE ./
COPY src ./src

# Create virtual environment and install production dependencies
ENV VIRTUAL_ENV=/opt/venv
RUN uv venv ${VIRTUAL_ENV} && \
    if [ "$INSTALL_API" = "true" ]; then \
        uv pip install --no-cache-dir ".[api]"; \
    else \
        uv pip install --no-cache-dir .; \
    fi

################################################################################
# Runtime Stage (Production)
################################################################################
FROM python:3.10-slim-bookworm AS runtime

# Set metadata labels (OCI image spec)
LABEL org.opencontainers.image.title="USMS"
LABEL org.opencontainers.image.description="Unofficial Python library for Brunei's USMS platform"
LABEL org.opencontainers.image.version="0.9.2"
LABEL org.opencontainers.image.authors="AZ <102905929+azsaurr@users.noreply.github.com>"
LABEL org.opencontainers.image.url="https://github.com/azsaurr/usms"
LABEL org.opencontainers.image.source="https://github.com/azsaurr/usms"
LABEL org.opencontainers.image.licenses="MIT"

# Install runtime dependencies (tzdata for timezone support)
RUN --mount=type=cache,target=/var/cache/apt/ \
    --mount=type=cache,target=/var/lib/apt/ \
    apt-get update && \
    apt-get install --no-install-recommends --yes tzdata && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 usms && \
    useradd --create-home --no-log-init --gid 1000 --uid 1000 --shell /bin/bash usms

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application source code
COPY --chown=usms:usms src/ /app/src/

# Set up environment
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:$PATH"
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Create and set permissions for data directory
RUN mkdir -p /data && chown -R usms:usms /data

# Set working directory for data persistence
WORKDIR /data

# Switch to non-root user
USER usms

# Create volume for data persistence (for SQLite, CSV, cache)
VOLUME ["/data"]

# Expose API port (only used when running in server mode)
EXPOSE 8000

# Health check (checks if Python can import the module)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import usms" || exit 1

# Set entry point and default command
# Can be used as CLI: docker run usms -m meter --unit
# Or as API server: docker run usms serve --host 0.0.0.0
ENTRYPOINT ["python", "-m", "usms"]
CMD ["--help"]
