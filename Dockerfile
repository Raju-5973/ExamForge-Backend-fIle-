FROM python:3.12-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app/

# Run migrations and collect static files at build time
RUN python manage.py collectstatic --no-input || true

EXPOSE 8000

# Copy and use entrypoint script (runs migrations + starts gunicorn)
RUN chmod +x /app/entrypoint.sh
CMD ["/bin/bash", "/app/entrypoint.sh"]
