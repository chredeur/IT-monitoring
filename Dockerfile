FROM python:3.12-slim

WORKDIR /app

# Install git for pip git dependencies
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p data logs

# Expose port
EXPOSE 25567

# Environment variables
ENV DEV=False
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
