# ClauseVerify AI — Enterprise Production Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py /app/app.py
COPY server.py /app/server.py
COPY database.py /app/database.py
COPY integrations.py /app/integrations.py
COPY data /app/data
COPY static /app/static
COPY README.md /app/README.md

# Set environment
ENV PORT=8000
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/documents || exit 1

# Start Server with Uvicorn ASGI
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
