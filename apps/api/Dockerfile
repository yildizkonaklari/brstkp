FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seed data
COPY data/seed /app/data/seed

# Copy app code
COPY apps/api .

CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
