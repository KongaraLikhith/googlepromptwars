# Stage 1: Build
FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project definition
COPY pyproject.toml .

# Install dependencies into system environment (which is discarded later, we copy site-packages)
# We use --system to ensure they end up in the standard path
RUN uv pip install --system --no-cache .

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Copy python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source code
COPY ./app ./app

# Expose port
EXPOSE 8000

# Run uvicorn server
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
