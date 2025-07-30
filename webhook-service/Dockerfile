# Use the official Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for weasyprint only
RUN apt-get update && apt-get install -y \
    build-essential \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    libcairo2 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    shared-mime-info \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy templates directory into the container
COPY templates/ /app/templates/

# Copy only the essential Python files
COPY webhook_main.py .
COPY webhook_service.py .
COPY assessment_analyzer.py .
COPY report_generator.py .
COPY email_sender.py .
COPY storage.py .
COPY drive_service.py .

# Expose port
EXPOSE 8080

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=8080

# Run the application
CMD ["python", "webhook_main.py"]