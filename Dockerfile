# Use a lightweight Python base image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Set work directory
WORKDIR /app

# Install system dependencies if any were needed (none for this project)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Create necessary folders
RUN mkdir -p data logs storage

# Copy project files
COPY src/ ./src/
COPY run.py ./

# Expose ports (will be overridden in compose)
EXPOSE 8080 9000 9001 9101 9102

# Default command (usually overridden in docker-compose)
CMD ["python", "-m", "gateway.main"]
