# Dockerfile for P2P File Sharing System Performance Tests
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Copy backend requirements
COPY bklv-backend/requirements.txt ./backend-requirements.txt

# Copy test requirements
COPY tests/requirements.txt ./test-requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r backend-requirements.txt
RUN pip install --no-cache-dir -r test-requirements.txt

# Copy backend code
COPY bklv-backend/ ./bklv-backend/

# Copy test files
COPY tests/ ./tests/

# Create directories for test files and results
RUN mkdir -p /app/files /app/tests/results /app/logs

# Expose ports
# 9000 - Central server
# 5500 - Admin API
# 5501 - Client API
# 6000-7000 - Client peer servers (range)
EXPOSE 9000 5500 5501 6000-7000

# Default command (can be overridden)
CMD ["python", "bklv-backend/server.py"]
