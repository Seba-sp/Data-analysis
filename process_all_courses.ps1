# Batch processing script for all courses (PowerShell version)
# Usage: .\process_all_courses.ps1

Write-Host "Starting batch processing of all courses..." -ForegroundColor Green

# Check if cursos.txt exists
if (-not (Test-Path "cursos.txt")) {
    Write-Host "Error: cursos.txt not found" -ForegroundColor Red
    exit 1
}

# Read and process each course
Get-Content "cursos.txt" | ForEach-Object {
    $course_id = $_.Trim()
    
    # Skip empty lines and comments
    if ([string]::IsNullOrWhiteSpace($course_id) -or $course_id.StartsWith("#")) {
        return
    }
    
    Write-Host "==========================================" -ForegroundColor Yellow
    Write-Host "Processing course: $course_id" -ForegroundColor Yellow
    Write-Host "==========================================" -ForegroundColor Yellow
    
    # Download and process data
    Write-Host "Downloading data..." -ForegroundColor Cyan
    # To force a full re-download of raw data for a course, add --reset-raw to the command below:
    # $download_result = python descarga_procesa_datos.py --course $course_id --reset-raw
    $download_result = python descarga_procesa_datos.py --course $course_id
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Download completed successfully" -ForegroundColor Green
        
        # Analyze data and generate reports
        Write-Host "Analyzing data..." -ForegroundColor Cyan
        $analysis_result = python analisis.py --course $course_id
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Analysis completed successfully" -ForegroundColor Green
        } else {
            Write-Host "Error: Analysis failed for course $course_id" -ForegroundColor Red
        }
    } else {
        Write-Host "Error: Download failed for course $course_id" -ForegroundColor Red
    }
    
    Write-Host ""
}

Write-Host "Batch processing completed!" -ForegroundColor Green 