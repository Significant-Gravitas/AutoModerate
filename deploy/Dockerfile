FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY ./requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create instance directory for SQLite if needed (fallback)
RUN mkdir -p instance

# Run as a non-root user for defence in depth
RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

# Expose the port the app runs on
EXPOSE 6217

# Set environment variables
ENV FLASK_CONFIG=production
ENV PYTHONPATH=/app

# Serve via gunicorn with the gthread worker class. See wsgi.py for the
# full rationale — short version: eventlet + Flask async routes + standard
# decorators (Flask-Login, Flask-Limiter) don't compose. gthread avoids the
# asyncio.run() inside running-loop crash and still supports WebSockets via
# Flask-SocketIO's threading mode.
# A single worker is required because Flask-SocketIO clients need to stick
# to one process; scale horizontally by running multiple instances behind a
# load balancer with sticky sessions + a shared message queue.
CMD ["gunicorn", "--worker-class", "gthread", "--workers", "1", \
     "--threads", "50", "--bind", "0.0.0.0:6217", "--timeout", "120", \
     "--access-logfile", "-", "wsgi:app"]