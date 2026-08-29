FROM ubuntu:26.10

# Add support for build timestamp (to be set in podman run)
ARG BUILD_TIMESTAMP="-unknown-"

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set a default port
ENV FLASK_RUN_PORT=6022

# Install curl (needed for uv installation)
RUN apt-get update && \
    apt-get install -y curl ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install uv (and make available to both root and appuser)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv  /usr/local/bin/ && \
    mv /root/.local/bin/uvx /usr/local/bin/
ENV PATH="/usr/local/bin:$PATH"

# Set working directory
WORKDIR /app

# Setup dedicated user to run the app
RUN useradd -m -u 1001 appuser && \
    chown appuser:appuser /app

# Force the use of our dedicated user
USER appuser

# Copy and install (now as appuser)
COPY --chown=appuser:appuser pyproject.toml uv.lock* ./

# Add build timestamp
RUN echo "${BUILD_TIMESTAMP}" > /app/VERSION

# Install Python 3.14 and dependencies via uv
RUN uv python install 3.14 && \
    uv sync --frozen --no-dev --no-editable

# Copy application code and fix ownership
COPY --chown=appuser:appuser . .

EXPOSE ${FLASK_RUN_PORT}

# Run Flask app using uv
CMD ["sh", "-c", "uv run gunicorn -w 1 -b 0.0.0.0:${FLASK_RUN_PORT} --timeout 120 --access-logfile - wsgi:app"]
