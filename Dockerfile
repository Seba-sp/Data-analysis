# Use the official Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed, e.g., for pandas, openpyxl, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your code
COPY . .

# Set environment variables (optional, can be overridden at deploy time)
# ENV STORAGE_BACKEND=gcp

# Set the default command to run your batch job
CMD ["python", "main.py"] 