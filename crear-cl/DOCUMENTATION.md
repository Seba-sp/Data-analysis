# Complete Documentation - PAES Multi-Agent Pipeline

Comprehensive setup, configuration, and workflow details for the PAES multi-agent pipeline.

## Table Of Contents
- Installation And Setup
- Configuration Guide
- Google Drive Setup
- PDF Context Setup
- Agent Architecture
- Data Flow And State Management
- Modes And CLI
- Document Formats
- Utility Scripts
- Performance Notes
- Troubleshooting

## Installation And Setup

### Prerequisites
- Python 3.9+
- Google Cloud account with Gemini API access
- Google Drive API enabled
- Microsoft Word (required by `docx2pdf` on Windows)

### Install
```bash
pip install -r requirements.txt
```

### Environment
Create `.env` in project root:
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

### GUI Launcher
```bash
python launcher.py
```

## Configuration Guide

### Agent 1 Mode
- `agent`: Deep Research agent (slow, multi-step, built-in Google Search)
- `model`: Fast model with explicit Google Search tool

Switch in `.env` or override at runtime:
```bash
python main.py --batches 2 --agent1-mode model
```

### Models
- Agent 1 model: `AGENT1_MODEL` (used only in `model` mode)
- Agents 2, 3, 4: `GEMINI_MODEL_AGENTS234`

## Google Drive Setup

1. Enable Google Drive API in Google Cloud Console.
2. Create OAuth Desktop credentials.
3. Download as `credentials.json` into project root.
4. First run will open a browser and create `token.json`.

If auth fails, delete `token.json` and re-run.

## PDF Context Setup

Place PAES guideline PDFs in `agent-3-context/`.
These are uploaded once (lazy) and reused by Agents 3 and 4.

If the folder is missing or empty, Agents 3/4 still run without guideline context.

## Agent Architecture

### Agent 1: Research
File: `agents/agent1_research.py`

- Uses Interactions API (`google-genai`)
- Output: `candidatos_YYYYMMDD_HHMMSS.tsv`
- Enforces 10-10-10 distribution
- Prevents duplicates by excluding previously processed URLs

### Agent 2: Validation
File: `agents/agent2_validation.py`

- Uses legacy API (`google-generativeai`)
- Produces an enriched audit TSV that includes all original fields plus:
  - `Estado`
  - `Decision`
  - `Motivo_Concreto`
  - `Accion_Recomendada`

### Agent 3: Question Generation
File: `agents/agent3_questions.py`

- DOCX-first workflow
- Converts article DOCX to PDF
- Uploads PDF to Gemini File API
- Generates PAES-format questions using:
  - Guideline PDFs (optional)
  - Article PDF (required)
- Writes debug files:
  - `data/debug_questions_{ID}.txt`
  - `data/debug_questions_improved_{ID}.txt`

### Agent 4: Review
File: `agents/agent4_review.py`

- Uploads article PDF to Gemini File API
- Uses guideline PDFs if available
- Returns DEMRE-style review with nota and fixes
- Writes debug file: `data/debug_review_{ID}.txt`

### Standalone Review Agent
File: `agents/agent4_standalone.py`

- Reviews local Word + Excel pairs
- Filters questions based on `Accion` column
- Skips if `Accion` has blanks

## Data Flow And State Management

### Workflow (Full Pipeline)
1. Agent 1 generates `candidatos_*.tsv`
2. Agent 2 validates and outputs `auditoria_*.tsv` (enriched)
3. For each approved row:
   - Agent 3 generates questions from DOCX->PDF upload
   - Agent 4 reviews questions
   - Agent 3 improves questions
   - Document generation produces Word + Excel
   - Drive upload (optional)

### State File
`data/processing_state.csv` is created and updated by `utils/state_manager.py`.
Key columns include:
- `article_id`
- `title`
- `url`
- `license_status`
- `processing_status`
- `questions_generated`
- `questions_improved`
- `uploaded_to_drive`
- `error_message`

### Duplicate Prevention
Processed URLs are loaded from state and passed to Agent 1 as exclusions.

## Modes And CLI

### Validate Configuration
```bash
python main.py --validate-only
```

### Full Pipeline
```bash
python main.py --batches 1
```

### Start From Agent 2 (skip research)
```bash
python main.py --start-from agent2 --tsv-file data/candidatos_YYYYMMDD.tsv
```

### Start From Agent 3 (skip research + validation)
Agent 3 start requires a CSV with DOCX paths.

Required columns:
- `ID`
- `Titulo`
- `Docx_Path`
- `Estado`

Only rows with `Estado` in `APROBADO` or `APROBADO_CONDICION` are processed.

```bash
python main.py --start-from agent3 --tsv-file data/articles_with_docx.csv
```

### Reverse Order (parallel processing)
```bash
python main.py --start-from agent3 --batches 1 --tsv-file data/articles_with_docx.csv --reverse
```

### Standalone Review
```bash
python main.py --review-standalone --folder "data/my_questions"
```

Expected filenames (flexible separators):
- `{ID} Preguntas+Texto.docx`
- `{ID} Preguntas Datos.xlsx`

### Debug TXT + DOCX Batch
```bash
python main.py --batch-debug --txt-folder "data/debug_txt" --docx-folder "data/source_docx"
```

### Debug TXT + DOCX Single
```bash
python main.py --single-debug --txt-file "debug_questions_improved_C001.txt" --docx-file "C001.docx"
```

## Document Formats

### Word Output
Produced by `utils/document_generator.py`:
- Base article text from source DOCX
- Questions appended after a page break
- One question per page
- No answer key in Word output

### Excel Output
Columns:
1. Numero de pregunta
2. Clave
3. Habilidad
4. Tarea lectora
5. Justificacion
6. Accion (blank by default)

## Utility Scripts

### Batch Document Generation
Script: `batch_generate_documents.py`

```bash
python batch_generate_documents.py <txt_folder> <docx_folder> [output_folder]
```

Input:
- `debug_questions_improved_{id}.txt`
- `{id}.docx`

Output:
- `{id}-Preguntas+Texto.docx`
- `{id}-Preguntas Datos.xlsx`

### Merge Excel Files
```bash
python merge_excel_files.py <folder_path> [output_filename]
```

## Performance Notes

### Agent 1
- `agent` mode is slower but higher quality
- `model` mode is faster with explicit Google Search tool

### PDF Context
PDF guideline uploads are cached by Gemini File API and reused.

## Troubleshooting

### "GEMINI_API_KEY is not set"
Create `.env` and ensure the key is present.

### "Google Drive credentials file not found"
Ensure `credentials.json` exists in project root and matches `.env`.

### "Permission denied" (Google Drive)
Delete `token.json` and re-authenticate.

### "Empty PDF Context"
Ensure `agent-3-context/` has at least one PDF.

### DOCX->PDF fails
`docx2pdf` requires Microsoft Word on Windows.

### Agent 3 start fails
Verify CSV columns `ID`, `Titulo`, `Docx_Path`, `Estado` and that Docx paths are valid.

---
Documentation Status: Current
