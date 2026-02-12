# PAES Multi-Agent News Pipeline

Automated pipeline that discovers, validates, and processes news articles to generate PAES (Competencia Lectora) question sets, with Google Drive upload and local fallbacks.

## Key Features
- 4-agent workflow: Research, Validation, Question Generation, Review
- Deep Research or fast Google Search mode for Agent 1
- License validation and portfolio rules (Agent 2)
- DOCX-first workflow for Agent 3/4 with DOCX->PDF upload for Gemini File API
- PDF guideline context for Agent 3/4 (DEMRE/PAES reference PDFs)
- Document outputs: Word + Excel per article
- Standalone review mode and debug-file batch generation
- GUI launcher for all modes

## Quick Start

1. Install dependencies
```bash
pip install -r requirements.txt
```

2. Create `.env`
```env
GEMINI_API_KEY=your_gemini_api_key_here

GOOGLE_DRIVE_CREDENTIALS=credentials.json
DRIVE_MAIN_FOLDER_NAME=NewsArticlesProcessing

# Agent 1 mode: agent | model
AGENT1_MODE=agent

# Optional overrides
AGENT1_MODEL=gemini-3-pro-preview
GEMINI_MODEL_AGENTS234=gemini-2.0-flash-exp
```

3. Add reference PDFs
Place PAES guideline/example PDFs in `agent-3-context/`. If none exist, Agent 3/4 will run without guideline context.

4. Run the pipeline
```bash
# Full pipeline (Agent 1 -> 4)
python main.py --batches 1

# Validate configuration only
python main.py --validate-only
```

5. Optional GUI
```bash
python launcher.py
```

## Pipeline Overview

1. **Agent 1 (Research)**
   Uses Gemini Interactions API.
   Modes:
   - `agent`: Deep Research agent (slow, multi-step, built-in Google Search)
   - `model`: Fast model with explicit Google Search tool
   Output: `candidatos_YYYYMMDD_HHMMSS.tsv`

2. **Agent 2 (Validation)**
   Uses legacy Gemini API to audit licensing.
   Output: **enriched** `auditoria_YYYYMMDD_HHMMSS.tsv` (self-contained with all article fields + validation columns).

3. **Agent 3 (Question Generation)**
   Input: Approved articles with `docx_path`.
   Converts DOCX -> PDF, uploads to Gemini File API, then generates PAES-format questions using PDF context + guidelines.
   Saves debug files:
   - `data/debug_questions_{ID}.txt`
   - `data/debug_questions_improved_{ID}.txt`

4. **Agent 4 (Review)**
   Reviews questions using DOCX->PDF upload plus guideline PDFs.
   Saves debug file: `data/debug_review_{ID}.txt`

5. **Document Generation + Upload**
   Creates:
   - `{ID}-Preguntas+Texto (Inicial).docx`
   - `{ID}-Preguntas+Texto.docx`
   - `{ID}-Preguntas Datos (Inicial).xlsx`
   - `{ID}-Preguntas Datos.xlsx`
   Uploads to Google Drive (with local fallback in `data/` if upload fails).

## Running Modes

### Full Pipeline
```bash
python main.py --batches 3
```

### Start From Agent 2 (skip research)
```bash
python main.py --start-from agent2 --tsv-file data/candidatos_YYYYMMDD.tsv
```

### Start From Agent 3 (skip research + validation)
Agent 3 start requires a CSV with DOCX paths.

Required columns: `ID`, `Titulo`, `Docx_Path`, `Estado`
Only rows with `Estado` in `APROBADO` or `APROBADO_CONDICION` are processed.

```bash
python main.py --start-from agent3 --tsv-file data/articles_with_docx.csv
```

### Reverse Order (parallel processing)
```bash
python main.py --start-from agent3 --batches 1 --tsv-file data/articles_with_docx.csv --reverse
```

### Standalone Review (Agent 4)
Runs review from local Word+Excel pairs:
```bash
python main.py --review-standalone --folder "data/my_questions"
```
Expected filenames (flexible separators):
- `{ID} Preguntas+Texto.docx`
- `{ID} Preguntas Datos.xlsx`

### Debug TXT + DOCX Batch
Generates Word/Excel from `debug_questions_improved_{id}.txt` + `{id}.docx`:
```bash
python main.py --batch-debug --txt-folder "data/debug_txt" --docx-folder "data/source_docx"
```

### Debug TXT + DOCX Single
```bash
python main.py --single-debug --txt-file "debug_questions_improved_C001.txt" --docx-file "C001.docx"
```

## Output Structure
Local output defaults to `data/`:
```
data/
├── candidatos_YYYYMMDD_HHMMSS.tsv
├── auditoria_YYYYMMDD_HHMMSS.tsv
├── debug_questions_C001.txt
├── debug_questions_improved_C001.txt
├── debug_review_C001.txt
├── C001-Preguntas+Texto (Inicial).docx
├── C001-Preguntas+Texto.docx
├── C001-Preguntas Datos (Inicial).xlsx
└── C001-Preguntas Datos.xlsx
```

Google Drive upload (if enabled) creates a folder per article title under `DRIVE_MAIN_FOLDER_NAME`.

## Utility Scripts

### Batch Document Generation
```bash
python batch_generate_documents.py <txt_folder> <docx_folder> [output_folder]
```

### Merge Excel Files
```bash
python merge_excel_files.py <folder_path> [output_filename]
```

## DOCX -> PDF Requirement
Agents 3 and 4 upload the article DOCX as PDF to Gemini File API.
`docx2pdf` requires Microsoft Word on Windows.

## Requirements
- Python 3.9+
- Google Cloud account with Gemini API access
- Google Drive API enabled + OAuth credentials
- Microsoft Word (for DOCX->PDF via `docx2pdf`)

---
Status: Production Ready
Support: See `DOCUMENTATION.md`
