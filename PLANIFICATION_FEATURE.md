# Planification Feature - Up-to-Date Student Filtering

## Overview

The planification feature allows you to filter course analysis to only include students who are up to date with their assessments based on a predefined schedule. This is useful for identifying students who need intervention and analyzing the performance of engaged students.

## How It Works

### Date Logic
- Since data is downloaded in the morning, the system considers assessments due until **yesterday** as "up to date"
- For example, if today is July 14, 2025, students should have completed all assessments due until July 13, 2025

### Student Filtering
- Only students who have completed **ALL** assessments due until yesterday are included in the analysis
- Students missing any due assessment are excluded from the filtered analysis
- This creates a focused view of students who are following the schedule

### Report Generation
- Reports with up-to-date filtering have the suffix `_up_to_date` to distinguish them from regular reports
- Both regular and filtered reports are generated, allowing comparison between all students and engaged students

## Setup

### 1. Create Planification Directory
```bash
mkdir -p data/planification
```

### 2. Create Planification Files
Create CSV files in `data/planification/` with the following structure:

**Filename**: `{course_id}.csv` (e.g., `nivel-1-m30m.csv`)

**Format**: CSV with semicolon separator

**Columns**:
- `assessment_name`: Name of the assessment (must match exactly with assessment names in the course)
- `date`: Due date in format `DD-MM-YYYY`

### Example Planification File
```csv
assessment_name;date
Test [M30M-CNE1];08-07-2025
Test [M30M-CNE2];08-07-2025
Test [M30M-CNE3];08-07-2025
Test [M30M-CNE4];09-07-2025
Test [M30M-CNE5];09-07-2025
Guía acumulativa 1;08-07-2025
Guía acumulativa 2;09-07-2025
```

## Usage

### Single Course Analysis

#### Regular Analysis (All Students)
```bash
python analisis.py --course nivel-1-m30m
```

#### Up-to-Date Analysis (Filtered Students)
```bash
python analisis.py --course nivel-1-m30m --up-to-date
```

#### Up-to-Date Analysis with Upload
```bash
python analisis.py --course nivel-1-m30m --up-to-date --upload
```

### Batch Processing

#### All Courses with Up-to-Date Filtering
```bash
python batch_process.py --up-to-date
```

#### Specific Courses with Up-to-Date Filtering
```bash
python batch_process.py --courses nivel-1-m30m lecciones-m0m --up-to-date
```

### Cloud Function

The Cloud Function supports up-to-date filtering via HTTP request:

```bash
# Regular execution (all students)
curl -X POST https://your-function-url

# Up-to-date filtering
curl -X POST https://your-function-url \
  -H "Content-Type: application/json" \
  -d '{"up_to_date": true}'
```

## Output Files

### Regular Analysis
- `data/metrics/kpi/{course_id}.csv`
- `data/reports/{course_id}/reporte_{course_id}_{date}.pdf`
- `data/reports/{course_id}/reporte_{course_id}_{date}.xlsx`

### Up-to-Date Analysis
- `data/metrics/kpi/{course_id}_up_to_date.csv`
- `data/reports/{course_id}/reporte_{course_id}_up_to_date_{date}.pdf`
- `data/reports/{course_id}/reporte_{course_id}_up_to_date_{date}.xlsx`

## Use Cases

### 1. Student Intervention Planning
- Identify students who are falling behind
- Focus intervention efforts on students who need support
- Track progress of students who are following the schedule

### 2. Performance Analysis
- Compare performance between all students and engaged students
- Analyze the effectiveness of course materials with engaged students
- Identify patterns in student engagement and performance

### 3. Course Improvement
- Understand what works well for engaged students
- Identify potential issues with course materials or assessments
- Plan improvements based on successful student patterns

## Example Workflow

### Step 1: Create Planification File
Create `data/planification/nivel-1-m30m.csv` with assessment schedule.

### Step 2: Download and Process Data
```bash
python descarga_procesa_datos.py --course nivel-1-m30m
```

### Step 3: Run Regular Analysis
```bash
python analisis.py --course nivel-1-m30m
```

### Step 4: Run Up-to-Date Analysis
```bash
python analisis.py --course nivel-1-m30m --up-to-date
```

### Step 5: Compare Results
- Review regular reports to see overall course performance
- Review up-to-date reports to see performance of engaged students
- Identify students who need intervention (in regular reports but not in up-to-date reports)

## Testing

Run the test script to verify functionality:

```bash
python test_up_to_date_filtering.py
```

This will test:
- Planification file loading
- Due assessment calculation
- Student filtering logic
- Integration with real data

## Troubleshooting

### Common Issues

1. **No planification file found**
   - Ensure the file exists at `data/planification/{course_id}.csv`
   - Check file permissions and format

2. **No assessments due yet**
   - This is normal if the course hasn't started
   - Check the dates in your planification file

3. **Assessment names don't match**
   - Ensure assessment names in planification file exactly match course assessment names
   - Check for typos, extra spaces, or different naming conventions

4. **No students up to date**
   - This indicates students are falling behind
   - Consider adjusting the schedule or providing additional support

### Debug Information

The system provides detailed logging:
- Number of assessments loaded from planification
- Number of assessments due until yesterday
- Number of students up to date vs total students
- File paths for generated reports

## Integration with Existing Workflow

The planification feature integrates seamlessly with existing functionality:

- **Google Drive Upload**: Up-to-date reports are uploaded with distinct names
- **Slack Notifications**: Include links to both regular and up-to-date reports
- **Batch Processing**: Supports up-to-date filtering for all courses
- **Cloud Function**: Supports up-to-date filtering via HTTP requests

## Best Practices

1. **Keep planification files updated** as course schedules change
2. **Use consistent assessment naming** between planification files and course data
3. **Review both regular and up-to-date reports** for comprehensive analysis
4. **Set up automated processing** with Cloud Functions for regular monitoring
5. **Document schedule changes** and their impact on analysis results

## Future Enhancements

Potential improvements for the planification feature:

1. **Multiple schedule support** for different student groups
2. **Dynamic schedule adjustment** based on course progress
3. **Student-specific schedules** for personalized learning paths
4. **Integration with learning management systems** for automatic schedule updates
5. **Advanced filtering options** (e.g., minimum completion percentage) 