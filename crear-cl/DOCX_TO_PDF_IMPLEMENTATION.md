# DOCX to PDF Conversion Implementation

## Summary

Successfully implemented DOCX to PDF conversion for Agent 3 & 4 to work with Gemini File API.

## Problem Discovered

Gemini File API **does not support DOCX files** (MIME type `application/vnd.openxmlformats-officedocument.wordprocessingml.document`).

Error encountered:
```
400 Unsupported MIME type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
```

## Solution Implemented

Convert DOCX files to PDF before uploading to Gemini File API:

1. **Agent 3 - `generate_questions()`**:
   - Convert DOCX → PDF using `docx2pdf`
   - Upload PDF to Gemini File API
   - Pass PDF reference along with PAES guideline PDFs
   - Model reads full content (text + images)
   - Clean up temporary files after generation

2. **Agent 3 - `improve_questions()`**:
   - Convert DOCX → PDF
   - Upload to Gemini for improvement context
   - Pass file reference to model
   - Clean up after improvement

3. **Agent 4 - `review_questions()`**:
   - Convert DOCX → PDF
   - Upload to Gemini for review
   - Pass file reference to model
   - Clean up after review

## Key Features

✅ **Preserves images** - PDF format maintains visual content
✅ **No hallucination** - Uses real article content from DOCX files
✅ **Automatic cleanup** - Temporary PDF files are deleted after use
✅ **Error handling** - Skips articles with missing DOCX files
✅ **CSV support** - Handles both comma and semicolon delimiters
✅ **Path flexibility** - Supports relative and absolute DOCX paths

## Dependencies Added

- `docx2pdf>=0.1.8` - For DOCX to PDF conversion (Windows-compatible)

## Code Changes

### Agent 3 (`agents/agent3_questions.py`)
- Import: `from docx2pdf import convert`, `import tempfile`
- Generate: Convert → Upload → Generate → Cleanup
- Improve: Convert → Upload → Improve → Cleanup

### Agent 4 (`agents/agent4_review.py`)
- Import: `from docx2pdf import convert`, `import tempfile`
- Review: Convert → Upload → Review → Cleanup

### Orchestrator (`orchestrator.py`)
- CSV loading with semicolon delimiter fallback
- FileNotFoundError handling for missing DOCX files

### Main (`main.py`)
- Fixed Unicode console output issues (Windows compatibility)
- Updated help text to reflect CSV input format

## Usage

```bash
# Create CSV with DOCX paths
python -c "import pandas as pd; df = pd.read_csv('data/audit.tsv', sep='\t'); df['Docx_Path'] = df['ID'].apply(lambda x: f'data/articles/{x}.docx'); df.to_csv('data/articles.csv', index=False)"

# Run pipeline from Agent 3
python main.py --start-from agent3 --batches 1 --tsv-file data/agent2_mj.csv
```

## CSV Format Expected

```csv
ID,ID_RANDOM,Tipo,Tema,Autor,Titulo,Ano,Fuente,Licencia,URL,URL_Canonica,Inicio_Fragmento,Fin_Fragmento,Recurso_Discontinuo,Estado,Decision,Motivo_Concreto,Accion_Recomendada,Docx_Path
C001,X9J2k3,Argumentativo,Topic,Author,Title,2025,Source,CC BY,url,url,start,end,No,APROBADO,OK,Verified,None,data/articles/C001.docx
```

**Note**: Also supports semicolon (`;`) delimiter for European locales.

## Workflow

```
DOCX File (with images)
    ↓
Convert to PDF (docx2pdf)
    ↓
Upload to Gemini File API
    ↓
Model reads PDF (text + images)
    ↓
Generate questions
    ↓
Delete temporary PDF
    ↓
Merge source DOCX + questions → Final Word document
```

## Testing

Tested with 11 articles from `data/agent2_mj.csv`:
- ✅ CSV loading (semicolon delimiter)
- ✅ DOCX to PDF conversion
- ✅ PDF upload to Gemini
- ✅ Question generation with image support
- ✅ File cleanup

## Benefits Over Text Extraction

| Feature | Text Extraction | DOCX→PDF Upload |
|---------|----------------|-----------------|
| Preserves images | ❌ | ✅ |
| Preserves formatting | ❌ | ✅ |
| Preserves tables | ❌ | ✅ |
| Model sees visual context | ❌ | ✅ |
| Prevents hallucination | ✅ | ✅ |
| Faster execution | ✅ | ❌ (conversion overhead) |

## Notes

- `docx2pdf` requires Microsoft Word to be installed on Windows
- Temporary PDF files are created in system temp directory
- Files are auto-deleted after generation (with fallback to 48h Gemini expiry)
- Compatible with existing PAES guideline PDF uploads
