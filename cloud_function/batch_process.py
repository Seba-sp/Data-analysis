#!/usr/bin/env python3
"""
Batch processing script for multiple courses
Reads course configuration from cursos.yml and processes each course
"""

import yaml
from pathlib import Path
from descarga_procesa_datos import run_full_pipeline as run_download_pipeline
from analisis import run_analysis_pipeline as run_analysis_pipeline

def load_course_config(config_path: str = "cursos.yml"):
    """Load course configuration from YAML file"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def run_batch_pipeline(config_path: str, specific_courses: list = None, 
                      download_only: bool = False, analysis_only: bool = False,
                      upload_reports: bool = False):
    """Run pipeline for multiple courses"""
    
    # Load configuration
    config = load_course_config(config_path)
    courses = config.get('courses', {})
    
    # Determine which courses to process
    if specific_courses:
        courses_to_process = {course_id: courses[course_id] 
                            for course_id in specific_courses 
                            if course_id in courses}
    else:
        courses_to_process = courses
    
    if not courses_to_process:
        print("No courses found to process")
        return
    
    print(f"Processing {len(courses_to_process)} courses:")
    for course_id in courses_to_process:
        print(f"  - {course_id}: {courses_to_process[course_id].get('name', 'Unknown')}")
    
    # Process each course
    for course_id, course_config in courses_to_process.items():
        print(f"\n{'='*50}")
        print(f"Processing course: {course_id}")
        print(f"Name: {course_config.get('name', 'Unknown')}")
        print(f"{'='*50}")
        
        try:
            # Download phase
            if not analysis_only:
                print(f"Downloading data for {course_id}...")
                run_download_pipeline(course_id)
                print(f"Download completed for {course_id}")
            
            # Analysis phase
            if not download_only:
                print(f"Analyzing data for {course_id}...")
                run_analysis_pipeline(course_id, upload_reports)
                print(f"Analysis completed for {course_id}")
                
        except Exception as e:
            print(f"Error processing course {course_id}: {str(e)}")
            continue
    
    print(f"\n{'='*50}")
    print("Batch processing completed!") 