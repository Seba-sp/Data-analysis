# Word Template Variables Guide

## How the Template System Works

The webhook service now uses your Word template (`plantilla_test_diagnostico.docx`) and replaces variables in the format `<<variable_name>>` with actual values.

## Available Variables

The following variables are automatically replaced in your Word template:

### Basic Information
- `<<ALUMNO>>` - Student's username or email
- `<<Nombre>>` - Student's username or email (alternative)
- `<<PRUEBA>>` - Name of the assessment/test
- `<<Prueba>>` - Name of the assessment/test (alternative)
- `<<PD%>>` - Percentage of lectures passed (e.g., "75.0%")
- `<<Nivel>>` - Student's level based on performance:
  - "Nivel 3" (80% or higher)
  - "Nivel 2" (60-79%)
  - "Nivel 1" (below 60%)
- `<<NIVEL>>` - Alternative format for student's level

### Detailed Statistics
- `<<total_questions>>` - Total number of questions in the test
- `<<lectures_analyzed>>` - Number of lectures analyzed
- `<<lectures_passed>>` - Number of lectures the student passed

## How to Use Variables in Your Word Template

Your Word template already contains the correct variables! The system will automatically replace:

- `<<ALUMNO>>` with the student's name
- `<<PRUEBA>>` with the test name
- `<<PD%>>` with the percentage score
- `<<Nivel>>` with the student's level

## Third Page - Lecture Results Table

The system automatically adds a third page with:
- **Title**: "Resultados por Lección"
- **Table with 2 columns**:
  - "Lección" - Lecture name
  - "Estado" - Status ("Aprobada" in green or "Reprobada" in red)

## Example Template Structure

Your Word template should have:
- **Page 1**: Cover page with student info and test details
- **Page 2**: Detailed results and analysis (your existing template)
- **Page 3**: Automatically added with lecture results table

## Testing the Template

To test how your template looks with real data:

1. Run the debug test: `python debug_test.py`
2. Check the generated PDF: `data/webhook_reports/informe_test_student_Test de diagnóstico Parte 1.pdf`

## Customizing the Template

You can modify your Word template (`templates/plantilla_test_diagnostico.docx`) anytime:
- The variables are already in place and working
- Change formatting, fonts, colors
- Add logos, headers, footers
- The system will automatically replace variables when generating reports

## Adding New Variables

If you need additional variables, you can modify the `_load_and_fill_template` method in `report_generator.py` to add more variables to the `variables` dictionary. 