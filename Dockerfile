# Stage 1: Lightweight base runtime container configuration environment
FROM python:3.13-slim AS base

# Prevent Python from writing bytecodes and ensure immediate stream logging printouts
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install native system optimization tools required for high-volume network compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Production execution environment builder profile
FROM base AS runner

# Copy dependency manifests first to maximize caching layers performance metrics
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application file layers into the working directory
COPY . .

# Instantiate secure, comprehensive data storage paths matching script persistence layouts
RUN mkdir -p data/vault

# Create a non-privileged system user profile and explicitly lock layout folder permissions
# Setting permission matrix thresholds to 775 mitigates local laptop disk volume mounting conflicts
RUN useradd -u 8888 civicuser && \
    chown -R civicuser:civicuser /app && \
    chmod -R 775 /app/data

USER civicuser

# Expose standard ASGI application network port profiles
EXPOSE 8000

# Automated container perimeter check rule captures execution failures instantly
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
