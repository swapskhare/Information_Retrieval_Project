# Multi-stage Dockerfile for Information Retrieval Chatbot
# Stage 1: Build stage - install dependencies and prepare environment
FROM python:3.11-slim as builder

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage - minimal image with only runtime dependencies
FROM python:3.11-slim

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    awscli \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser app.py scraper.py indexer.py doc_mapper.py ./
COPY --chown=appuser:appuser templates/ ./templates/
COPY --chown=appuser:appuser static/ ./static/

# Copy entrypoint script
COPY --chown=appuser:appuser entrypoint.sh ./
RUN chmod +x entrypoint.sh

# Create data directory (data files will be downloaded from S3 at runtime)
RUN mkdir -p /app/data && chown appuser:appuser /app/data

# Switch to non-root user
USER appuser

# Expose port 8000
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FORCE_CPU=1
ENV PYTHONDONTWRITEBYTECODE=1

# Use entrypoint script to download data from S3 and start the application
ENTRYPOINT ["./entrypoint.sh"]

