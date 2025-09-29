FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt* ./
RUN pip install --no-cache-dir \
    openai \
    matplotlib \
    pandas \
    seaborn \
    scipy \
    numpy \
    aiohttp \
    httpx

# Copy application code
COPY . .

# Ensure environment configuration files are present for network egress fix
RUN chmod +x setup_environment.sh

# Create necessary directories
RUN mkdir -p /app/reports /app/analysis_output

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV SANDBOX_FACTORY=local_sandbox_factory:create_local_sandbox

# Create a non-root user for security
RUN useradd -m -u 1000 mapta && \
    chown -R mapta:mapta /app
USER mapta

# Default command - can be overridden
CMD ["python", "main.py"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import main; print('MAPTA is ready')" || exit 1

# Labels for metadata
LABEL maintainer="MAPTA Security Tool" \
      description="AI-powered pentesting tool using OpenAI" \
      version="1.0.0"
