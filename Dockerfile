# SIPAP Batch Scraper - Fargate Container Image
# Multi-stage build for smaller image size

FROM python:3.12-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright browsers
RUN pip install playwright==1.40.0 && \
    playwright install chromium && \
    playwright install-deps chromium

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create app directory
WORKDIR /app

# Copy application code
COPY src/ /app/src/
COPY pyproject.toml /app/

# Install package in editable mode
RUN pip install -e .

# Create non-root user
RUN useradd -m -u 1000 scraper && \
    chown -R scraper:scraper /app
USER scraper

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/home/scraper/.cache/ms-playwright

# Default command (override in ECS task definition)
CMD ["python", "-m", "sipap_batch_scraper.jobs.daily_harvest"]
