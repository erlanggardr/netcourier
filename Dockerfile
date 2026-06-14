# Use a lightweight Python base image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies if any were needed (none for this project)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Create necessary folders
RUN mkdir -p data logs storage web_ui

# Copy project files
COPY common/ ./common/
COPY gateway/ ./gateway/
COPY server/ ./server/
COPY client/ ./client/
COPY web_api/ ./web_api/
COPY web_ui/ ./web_ui/
COPY migrations/ ./migrations/

# Expose ports (will be overridden in compose)
EXPOSE 8080 9000 9001 9101 9102

# Default command (usually overridden in docker-compose)
CMD ["python", "-m", "gateway.main"]
