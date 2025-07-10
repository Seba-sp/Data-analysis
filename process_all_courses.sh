#!/bin/bash

# Batch processing script for all courses
# Usage: ./process_all_courses.sh

echo "Starting batch processing of all courses..."

# Check if cursos.txt exists
if [ ! -f "cursos.txt" ]; then
    echo "Error: cursos.txt not found"
    exit 1
fi

# Process each course
while IFS= read -r course_id; do
    # Skip empty lines and comments
    [[ -z "$course_id" || "$course_id" =~ ^[[:space:]]*# ]] && continue
    
    echo "=========================================="
    echo "Processing course: $course_id"
    echo "=========================================="
    
    # Download and process data
    echo "Downloading data..."
    # To force a full re-download of raw data for a course, add --reset-raw to the command below:
    # python descarga_procesa_datos.py --course "$course_id" --reset-raw
    python descarga_procesa_datos.py --course "$course_id"
    
    if [ $? -eq 0 ]; then
        echo "Download completed successfully"
        
        # Analyze data and generate reports
        echo "Analyzing data..."
        python analisis.py --course "$course_id"
        
        if [ $? -eq 0 ]; then
            echo "Analysis completed successfully"
        else
            echo "Error: Analysis failed for course $course_id"
        fi
    else
        echo "Error: Download failed for course $course_id"
    fi
    
    echo ""
done < cursos.txt

echo "Batch processing completed!" 