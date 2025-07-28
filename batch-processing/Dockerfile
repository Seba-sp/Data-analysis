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

# Copy only the necessary Python files for the application
COPY main.py .
COPY storage.py .
COPY descarga_procesa_datos.py .
COPY batch_process.py .
COPY analisis.py .

# Set the default command to run your batch job
CMD ["python", "main.py"] 