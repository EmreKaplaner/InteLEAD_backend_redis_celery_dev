FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    build-essential \
    curl \
    net-tools \
    lsof \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY backend/requirements.txt /app/backend/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy the entire project into the container
COPY . .

# Set the PYTHONPATH environment variable
ENV PYTHONPATH=/app

# Expose necessary ports
EXPOSE 8000

# Copy the start script for backend
COPY start_backend.sh /app/start_backend.sh

# Ensure the start script is executable
RUN chmod +x /app/start_backend.sh

# Install Gunicorn
RUN pip install gunicorn

# Default command to run the backend with Gunicorn
CMD ["/app/start_backend.sh"]
