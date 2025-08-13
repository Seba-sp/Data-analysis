# Segment Schedule Report Generator

A modular Python application for generating personalized PDF reports for educational assessment data. The application has been restructured into multiple files for better maintainability and readability.

## 📁 Project Structure

```
assessment-analysis-project/
├── utils.py                    # Utility functions and helpers
├── data_loader.py              # Data loading and caching logic
├── checklist_generator.py      # Checklist table generation
├── schedule_generator.py       # Schedule table generation
├── html_formatter.py           # HTML formatting and template handling
├── pdf_generator.py            # Main PDF generation orchestration
├── main.py                     # Command-line interface and main execution
├── segment_schedule_report_generator.py  # Original monolithic file (kept for reference)
└── README.md                   # This file
```

## 🏗️ Architecture Overview

### **utils.py**
- **Purpose**: Common utility functions used across the application
- **Key Functions**:
  - `find_col_case_insensitive()`: Find DataFrame columns by case-insensitive matching
  - `sanitize_filename()`: Convert filenames to safe characters
  - `find_user_row()`: Find user rows in DataFrames
  - `normalize_text()`: Normalize text by removing accents
  - `format_semana()`: Format week values
  - `level_to_index_*()`: Convert level values to numeric indices

### **data_loader.py**
- **Purpose**: Handle loading and caching of Excel workbooks and data
- **Key Features**:
  - Lazy loading of Excel files
  - Caching of analysis and segmentos data
  - Student lecture results extraction
  - Level distribution analysis
  - Checklist workbook management

### **checklist_generator.py**
- **Purpose**: Generate checklist tables for different student types and test types
- **Key Features**:
  - Support for both "Cuarto medio" and "Egresado" students
  - Different checklist formats based on test completion status
  - Column width optimization
  - Pagination for large tables
  - Conditional styling based on test results

### **schedule_generator.py**
- **Purpose**: Generate schedule tables for different segments and variants
- **Key Features**:
  - Complex column mapping logic for different segments
  - Support for morning/afternoon variants
  - Special handling for S7, S8, S15 segments
  - Fuzzy column matching
  - Fixed-layout table generation

### **html_formatter.py**
- **Purpose**: Handle HTML template loading and formatting
- **Key Features**:
  - Template loading and placeholder replacement
  - Value formatting for different data types
  - Conditional section inclusion
  - Results table population

### **pdf_generator.py**
- **Purpose**: Main orchestrator for PDF generation
- **Key Features**:
  - Single user PDF generation
  - Batch processing for multiple users
  - Existing PDF detection and skipping
  - Segment-specific logic handling
  - Error handling and logging

### **main.py**
- **Purpose**: Command-line interface and main execution
- **Key Features**:
  - Argument parsing
  - Logging setup
  - Error handling
  - Usage examples

## 🚀 Usage

### Basic Usage

```bash
# Generate all reports for all segments and student types
python main.py

# Generate reports only for specific segments
python main.py --segments S1 S2 S3

# Generate reports only for Egresado students
python main.py --student-types Egresado

# Generate reports with debug logging
python main.py --debug
```

### Advanced Usage

```bash
# Generate reports for specific segments with custom paths
python main.py --segments S1 S2 --analysis-path "custom/path/analisis.xlsx"

# Generate reports only for Cuarto medio students
python main.py --student-types "Cuarto medio"

# Generate reports with custom template
python main.py --template-path "custom/template.html"
```

### Command Line Options

- `--segments`: Specific segments to generate reports for (e.g., S1 S2 S3)
- `--student-types`: Student types to generate reports for (Egresado, Cuarto medio)
- `--analysis-path`: Path to the analysis Excel file
- `--segmentos-path`: Path to the segmentos Excel file
- `--template-path`: Path to the HTML template file
- `--debug`: Enable debug logging
- `--dry-run`: Show what would be generated without creating files

## 📊 Data Requirements

### Required Files

1. **Analysis Excel File** (`data/analysis/analisis de datos.xlsx`)
   - Sheet: "Reporte" with student data
   - Columns: user_id, email, nombre_y_apellido, Segmento, Nivel M1, Nivel CL, etc.

2. **Segmentos Excel File** (`templates/Segmentos.xlsx`)
   - Sheets: S1, S2, S3, etc. with schedule data
   - Columns: Semana, Día, Hora, M1 N1, M1 N2, etc.

3. **HTML Template** (`templates/plantilla_plan_de_estudio.html`)
   - Template with placeholders like `<<ALUMNO>>`, `<<PREPARAR_M1>>`, etc.

4. **Checklist Files** (`data/Checklist/`)
   - M1.xlsx, CL.xlsx, CIEN.xlsx, HYST.xlsx
   - Sheets with checklist data for different levels

## 🔧 Development

### Adding New Features

1. **New Utility Functions**: Add to `utils.py`
2. **New Data Loading Logic**: Add to `data_loader.py`
3. **New Checklist Types**: Extend `checklist_generator.py`
4. **New Schedule Logic**: Extend `schedule_generator.py`
5. **New HTML Formatting**: Extend `html_formatter.py`
6. **New PDF Generation Logic**: Extend `pdf_generator.py`

### Testing

```bash
# Test with debug logging
python main.py --debug --segments S1

# Test specific student type
python main.py --student-types Egresado --segments S1 S2
```

### Logging

The application uses Python's logging module with the following levels:
- **INFO**: General progress information
- **DEBUG**: Detailed debugging information
- **WARNING**: Non-critical issues
- **ERROR**: Critical errors

Logs are written to both console and `segment_schedule_generator.log` file.

## 🎯 Benefits of the New Structure

1. **Modularity**: Each file has a single responsibility
2. **Maintainability**: Easier to find and fix issues
3. **Testability**: Individual components can be tested separately
4. **Readability**: New developers can understand the codebase more easily
5. **Extensibility**: New features can be added without modifying existing code
6. **Reusability**: Components can be reused in other projects

## 🔄 Migration from Original File

The original `segment_schedule_report_generator.py` file is kept for reference. The new modular structure maintains all the original functionality while providing better organization and maintainability.

## 📝 Notes

- All imports are relative to the current directory
- The application maintains backward compatibility with existing data formats
- Error handling is comprehensive with detailed logging
- The modular structure makes it easy to add new segments or student types
