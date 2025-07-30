# Assessment Analysis Project

A comprehensive system for downloading, analyzing, and generating PDF reports for multiple assessments from LearnWorlds.

## Features

- **Multi-Assessment Support**: Analyzes 4 different assessment types (M1, CL, CIEN, HYST)
- **Flexible Analysis**: Different analysis methods for each assessment type
- **Comprehensive Reports**: Generates PDF reports with detailed tables for all assessments
- **Email Integration**: Sends reports via email with optional Google Drive links
- **Error Handling**: Robust error handling for missing data, network issues, etc.
- **Google Drive Integration**: Saves reports to "planes de estudios" folder
- **Multi-Page PDF Support**: Handles large datasets with proper page breaks and headers
- **Background Image Integration**: Custom background images for each assessment type

## Assessment Types

### M1 & HYST (Lecture-Based)
- Analyzes performance by lecture
- All questions in a lecture must be correct to pass
- Shows Aprobado/Reprobado status for each lecture
- Supports multi-page reports with proper headers

### CIEN (Lecture-Based with Materia)
- Groups lectures by "Materia" column
- Analyzes performance within each materia
- Shows detailed breakdown by materia and lecture
- Handles large datasets with 20 lectures per page
- Continuation pages with proper headers

### CL (Percentage-Based)
- Calculates percentage of correct answers per lecture
- Shows percentage scores instead of pass/fail
- Color-coded results based on performance level

## Project Structure

### Core Application Files (Production)

```
assessment-analysis-project/
├── main.py                    # Main orchestration script
├── assessment_downloader.py   # Downloads responses from LearnWorlds API
├── assessment_analyzer.py     # Analyzes different assessment types
├── report_generator.py        # Generates comprehensive PDF reports
├── email_sender.py           # Sends reports via email
├── storage.py                # Shared storage utilities
├── drive_service.py          # Google Drive integration
├── requirements.txt          # Python dependencies
├── sample_assessment_list.txt # Sample assessment configuration
├── templates/                # HTML templates for PDF generation
│   └── plantilla_plan_de_estudio.html  # Main template
└── data/                    # Data directory for assessment data
```

### Test Files (Development)

```
assessment-analysis-project/
├── test_pdf_generation.py    # Tests PDF generation with sample data
├── test_weasyprint_simple.py # Tests WeasyPrint installation
├── test_template_update.py   # Tests HTML template variable replacement
├── test_template_logic.py    # Tests template logic and calculations
├── test_template_integration.py # Tests full template integration
├── test_project.py          # Comprehensive project testing
├── test_monthly_plans.py    # Tests monthly study plan generation
├── show_pdf_info.py         # Utility to display PDF information
├── generate_all_cases_pdfs.py # Generates PDFs for all test cases
└── sample_pdfs/             # Generated test PDFs
```

## File Summary

### 🚀 **Core Application Files (Necessary to run the code)**

**Main Application Files:**
- `main.py` - Main entry point for the assessment analysis project
- `assessment_analyzer.py` - Core analysis logic for processing assessment data
- `report_generator.py` - PDF report generation functionality with multi-page support
- `assessment_downloader.py` - Downloads assessment responses from external APIs
- `email_sender.py` - Handles email notifications
- `drive_service.py` - Google Drive integration for file storage
- `storage.py` - File storage utilities

**Templates (Required):**
- `templates/plantilla_plan_de_estudio.html` - Main HTML template for PDF generation

**Configuration Files:**
- `requirements.txt` - Python dependencies
- `sample_assessment_list.txt` - Sample assessment configuration

**Data Directory:**
- `data/` - Directory for storing assessment data and question banks

### 🧪 **Test Files (Not necessary for production)**

**PDF Generation Tests:**
- `test_pdf_generation.py` - Tests PDF generation with sample data
- `test_weasyprint_simple.py` - Tests WeasyPrint installation and basic functionality
- `test_template_update.py` - Tests HTML template variable replacement
- `test_template_logic.py` - Tests template logic and calculations
- `test_template_integration.py` - Tests full template integration
- `test_project.py` - Comprehensive project testing
- `test_monthly_plans.py` - Tests monthly study plan generation
- `show_pdf_info.py` - Utility to display PDF information

**Additional Test Utilities:**
- `generate_all_cases_pdfs.py` - Generates PDFs for all test cases

## Setup

### 1. Environment Variables

Create a `.env` file with the following variables:

```env
# LearnWorlds API
CLIENT_ID=your_client_id
SCHOOL_DOMAIN=your_school_domain
ACCESS_TOKEN=your_access_token

# Email Configuration
EMAIL_FROM=your_email@gmail.com
EMAIL_PASS=your_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Optional
ADMIN_EMAIL=admin@example.com
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Question Bank Files

Place CSV files in `data/questions/` with the following structure:

**M1.csv, HYST.csv, CL.csv:**
```csv
question_number,correct_alternative,lecture
1,A,Lección 1
2,B,Lección 1
3,C,Lección 2
```

**CIEN.csv:**
```csv
question_number,correct_alternative,lecture,materia
1,A,Lección 1,Matemáticas
2,B,Lección 1,Matemáticas
3,C,Lección 2,Física
```

### 4. Assessment List File

Create a text file with assessment names and IDs:

```txt
M1,assessment_id_1
CL,assessment_id_2
CIEN,assessment_id_3
HYST,assessment_id_4
```

## Running the Application

### 🚀 **To Run the Main Application:**

```bash
# Install dependencies
pip install -r requirements.txt

# Run the main application
python main.py sample_assessment_list.txt
```

### 🧪 **To Run Tests:**

```bash
# Test PDF generation with multi-page support
python test_pdf_generation.py

# Test WeasyPrint installation
python test_weasyprint_simple.py

# Test project components
python test_project.py

# Test template integration
python test_template_integration.py
```

### 📋 **Minimum Required Files for Production:**

```bash
# Core application files
main.py
assessment_analyzer.py
report_generator.py
assessment_downloader.py
email_sender.py
drive_service.py
storage.py

# Templates
templates/plantilla_plan_de_estudio.html
templates/h30m.html
templates/m30m.html
templates/l30m.html
templates/c30m.html

# Configuration
requirements.txt
sample_assessment_list.txt

# Data directory
data/
```

## Usage

### Basic Usage

```bash
python main.py assessment_list.txt
```

### Send to Fixed Email

```bash
python main.py assessment_list.txt --fixed-email admin@example.com
```

### Debug Mode

```bash
python main.py assessment_list.txt --debug
```

## Recent Updates

### 🎯 **Multi-Page PDF Support (Latest)**

The system now supports comprehensive multi-page PDF generation with proper headers and background images:

#### **Key Features:**
- **20 lectures per page** for optimal content distribution
- **Proper page headers** on every page with assessment title and subtitle
- **Continuation indicators** for multi-page materias
- **Background image support** for all assessment types
- **Automatic page breaks** with proper section formatting

#### **Page Structure:**
- **First page**: Full header with title, subtitle, and materia name
- **Continuation pages**: Header with title, subtitle, and "(Continuación)" indicator
- **Background images**: Each page maintains proper CSS class for assessment-specific backgrounds

#### **Example Output:**
```
Page 1: "Resultados - CIEN" + "Química" + Lectures 1-20
Page 2: "Resultados - CIEN" + "Química (Continuación)" + Lectures 21-40
Page 3: "Resultados - CIEN" + "Biología" + Lectures 1-20
```

#### **Supported Assessments:**
- **CIEN**: Multi-page support with materia grouping
- **M1**: Multi-page support for large lecture datasets
- **HYST**: Multi-page support for large lecture datasets
- **CL**: Percentage-based with proper formatting

## Analysis Methods

### Lecture-Based Analysis (M1, HYST)
- Validates all questions in a lecture are answered correctly
- Status: "Aprobado" if all correct, "Reprobado" otherwise
- Overall percentage based on passed lectures

### Materia-Based Analysis (CIEN)
- Groups lectures by "Materia" column
- Analyzes each materia separately
- Shows breakdown by materia and lecture
- Overall percentage across all materias

### Percentage-Based Analysis (CL)
- Calculates percentage of correct answers per lecture
- Shows percentage scores (e.g., "75.0%")
- Color-coded: Green (≥80%), Yellow (60-79%), Red (<60%)

## Error Handling

The system handles various error scenarios:

- **Missing User Responses**: Skips users who haven't completed assessments
- **Missing Question Banks**: Logs warning and skips analysis
- **Network Issues**: Retries with delays, logs errors
- **Invalid Data**: Validates input and provides clear error messages
- **Email Failures**: Logs errors but continues processing other users

## Output

### PDF Reports
- Comprehensive report with all assessment results
- Separate tables for each assessment type
- Color-coded status indicators
- Professional formatting with CSS styling

### Email Delivery
- Personalized email with user's name
- PDF attachment with detailed results
- Optional Google Drive link
- Professional email template

### Google Drive Storage
- Saves reports to "planes de estudios" folder
- Consistent naming: `plan_estudio_{username}_{user_id}.pdf`
- Maintains organization and accessibility

## Example Output

### Email Subject
```
Plan de Estudio Completo - Juan Pérez
```

### Email Body
```
Hola Juan Pérez,

Has completado exitosamente todas las evaluaciones de diagnóstico. Adjuntamos tu plan de estudio completo con los resultados detallados.

En este informe encontrarás:
- Resultados de todas las evaluaciones (M1, CL, CIEN, HYST)
- Análisis por lección y materia
- Recomendaciones para tu plan de estudio

Evaluaciones incluidas:
- M1: Análisis de lecciones aprobadas/reprobadas
- CL: Porcentajes de acierto por lección
- CIEN: Análisis por materia y lección
- HYST: Análisis de lecciones aprobadas/reprobadas

Recuerda que para aprobar una lección en M1, CIEN y HYST debes responder correctamente todas las preguntas relacionadas con esa lección.

Si tienes alguna pregunta sobre tus resultados, no dudes en contactarnos.

Saludos,
Tu equipo de aprendizaje
```

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Check CLIENT_ID, SCHOOL_DOMAIN, and ACCESS_TOKEN
   - Verify network connectivity
   - Check API rate limits

2. **Email Not Sent**
   - Verify EMAIL_FROM and EMAIL_PASS
   - Check SMTP settings
   - Ensure app password is used for Gmail

3. **PDF Generation Failed**
   - Check HTML template exists
   - Verify weasyprint installation
   - Check file permissions

4. **Missing Question Banks**
   - Ensure CSV files are in `data/questions/`
   - Verify column names match expected format
   - Check file encoding (UTF-8)

### Debug Mode

Enable debug logging to see detailed information:

```bash
python main.py assessment_list.txt --debug
```

## Contributing

1. Follow the existing code structure
2. Add comprehensive error handling
3. Include logging for debugging
4. Test with various data scenarios
5. Update documentation as needed

## License

This project is part of the Data Analysis system and follows the same licensing terms.

---

# Template Integration Summary

## Overview
This document summarizes the integration of the new HTML template `plantilla_plan_de_estudio.html` into the assessment analysis project.

## Changes Made

### 1. Updated Report Generator (`report_generator.py`)

#### Template Path Update
- Changed template path from `/app/templates/plantilla_test_diagnostico.html` to `templates/plantilla_plan_de_estudio.html`

#### New Methods Added

##### `_add_second_page_content(html_content, user_results)`
- Adds the specific content requested for the second page
- Includes personalized greeting and study plan information
- Replaces placeholders with calculated levels and study plans

##### `_get_assessment_level(assessment_result)`
- Calculates the appropriate level (Nivel 1, 2, or 3) for each assessment
- Handles different assessment types:
  - **Percentage-based** (CL): Based on overall percentage
  - **Lecture-based with materia** (CIEN): Based on percentage of passed lectures
  - **Lecture-based** (M1, HYST): Based on percentage of passed lectures

##### `_generate_monthly_plan(user_results, month)`
- Generates study plans for each month (Agosto, Septiembre, Octubre)
- Currently provides placeholder content that can be customized based on assessment results

### 2. Second Page Content Structure

The second page now includes:

```html
<p>Hola <<Nombre>>,</p>
<p>Te entrego tu plan de estudio personalizado, elaborado a partir de los niveles que se te asignaron tras rendir el test de diagnóstico.</p>
<p>Te recomiendo seguir al pie de la letra las indicaciones que verás a continuación para que llegues con todo a la PAES regular 2025.</p>
<p><strong>¡VAMOS CON TODO!</strong></p>

<p>Estos son tus niveles asignados:</p>
<ul>
    <li>En M1: <<Nivel M1>></li>
    <li>En Competencia Lectora: <<Nivel CL>></li>
    <li>En Ciencias: <<Nivel Ciencias>></li>
    <li>En Historia y Cs. Sociales: <<Nivel Historia>></li>
</ul>

<p>Según estos niveles, te sugiero el siguiente itinerario:</p>
<ul>
    <li>Agosto: <<PlanAgosto>></li>
    <li>Septiembre: <<PlanSeptiembre>></li>
    <li>Octubre: <<PlanOctubre>></li>
</ul>
```

### 3. Level Calculation Logic

#### Assessment Level Criteria:
- **Nivel 3**: ≥80% success rate
- **Nivel 2**: 60-79% success rate  
- **Nivel 1**: <60% success rate

#### Assessment-Specific Calculations:

**M1 & HYST (Lecture-based):**
- Percentage = (lectures_passed / lectures_analyzed) × 100

**CL (Percentage-based):**
- Uses overall_percentage directly

**CIEN (Lecture-based with materia):**
- Percentage = (total_lectures_passed / total_lectures) × 100

### 4. Monthly Study Plans

Currently provides placeholder content:
- **Agosto**: "Enfoque en fundamentos básicos y repaso de conceptos clave"
- **Septiembre**: "Desarrollo de habilidades intermedias y práctica intensiva"
- **Octubre**: "Refinamiento de técnicas avanzadas y preparación final"

## Testing

### Test Files Created:
1. `test_template_integration.py` - Full integration test with PDF generation
2. `test_template_logic.py` - Logic-only test without weasyprint dependency

### Test Coverage:
- Template file existence and loading
- Level calculation for all assessment types
- Monthly plan generation
- Second page content replacement
- HTML template modification

## Usage

The updated report generator will automatically:
1. Load the new HTML template
2. Calculate levels for each assessment
3. Generate monthly study plans
4. Add the personalized content to the second page
5. Generate the final PDF with all assessment tables

## Next Steps

1. **Customize Monthly Plans**: Implement more sophisticated study plan generation based on specific assessment results
2. **Add More Personalization**: Include more dynamic content based on user performance patterns
3. **Enhance Error Handling**: Add more robust error handling for edge cases
4. **Performance Optimization**: Optimize template processing for large numbers of users

## Files Modified

- `report_generator.py` - Main integration changes
- `test_template_integration.py` - Full integration test
- `test_template_logic.py` - Logic-only test
- `TEMPLATE_INTEGRATION_SUMMARY.md` - This summary document

## Template File

- `templates/plantilla_plan_de_estudio.html` - The new HTML template with the requested structure

---

# Template Update Summary

## Overview
This document summarizes the updates made to the HTML template `plantilla_plan_de_estudio.html` to include the specific content requested for the second page.

## Changes Made

### 1. Updated Second Page Content
The second page of the HTML template has been completely updated with the new content structure:

#### **Previous Content (Removed):**
- Generic assessment results explanation
- "Aprobada/Reprobada" explanation
- General motivation text
- Rocket emoji

#### **New Content (Added):**
- Personalized greeting with `<<Nombre>>`
- Study plan introduction text
- "¡VAMOS CON TODO!" motivation
- **Level assignments section:**
  - En M1: `<<Nivel M1>>`
  - En Competencia Lectora: `<<Nivel CL>>`
  - En Ciencias: `<<Nivel Ciencias>>`
  - En Historia y Cs. Sociales: `<<Nivel Historia>>`
- **Study itinerary section:**
  - Agosto: `<<PlanAgosto>>`
  - Septiembre: `<<PlanSeptiembre>>`
  - Octubre: `<<PlanOctubre>>`

### 2. Placeholder Integration
The template now includes all the required placeholders that will be replaced by the `_add_second_page_content` function:

- `<<Nombre>>` - Student name
- `<<Nivel M1>>` - M1 assessment level
- `<<Nivel CL>>` - CL assessment level  
- `<<Nivel Ciencias>>` - Ciencias assessment level
- `<<Nivel Historia>>` - Historia assessment level
- `<<PlanAgosto>>` - August study plan
- `<<PlanSeptiembre>>` - September study plan
- `<<PlanOctubre>>` - October study plan

### 3. Function Integration
The `_add_second_page_content` function in `report_generator.py` has been updated to:

- **Only replace variables** in the template (not add new content)
- Calculate appropriate levels for each assessment type
- Generate personalized study plans for each month
- Replace all placeholders with calculated values

## Testing

### Test Script Created
- `test_template_update.py` - Verifies template content and placeholder replacement
- All tests pass successfully ✅

### Test Results
- ✅ Template file loads correctly
- ✅ All required content found in template
- ✅ Placeholder replacement works correctly
- ✅ Template is ready for production use

## Usage

The updated template will now:

1. **Load the template** with the new second page content
2. **Replace placeholders** with calculated values from assessment results
3. **Generate personalized PDFs** with study plans and level assignments
4. **Maintain consistent formatting** with the existing template structure

## Files Modified

1. **`templates/plantilla_plan_de_estudio.html`** - Updated second page content
2. **`report_generator.py`** - Updated `_add_second_page_content` function
3. **`test_template_update.py`** - New test script for verification

## Next Steps

The template is now ready for use with the assessment analysis project. The `_add_second_page_content` function will automatically:

- Calculate levels based on assessment results
- Generate personalized study plans
- Replace all placeholders with appropriate values
- Generate comprehensive PDF reports

The integration is complete and tested! 🎉 