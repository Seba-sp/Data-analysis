# Complete Documentation - Multi-Agent News Processing Pipeline

Comprehensive setup, configuration, and technical documentation for the PAES Multi-Agent Pipeline.

---

## Table of Contents

- [Installation & Setup](#installation--setup)
- [Configuration Guide](#configuration-guide)
- [Agent Configuration](#agent-configuration)
- [Testing & Troubleshooting](#testing--troubleshooting)
- [Technical Architecture](#technical-architecture)
- [API Details](#api-details)
- [Data Flow & State Management](#data-flow--state-management)
- [Performance & Optimization](#performance--optimization)

---

# Installation & Setup

## Prerequisites

- Python 3.9 or higher
- Google Cloud account
- Gemini API access
- Google Drive API enabled

## Installation Steps

### 1. Clone Repository

```bash
git clone <repository-url>
cd crear-cl
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `google-generativeai>=0.3.0` - Legacy API (Agent 2, PDF loader)
- `google-genai>=1.55.0` - Interactions API (Agents 1, 3, 4)
- `google-api-python-client` - Google Drive API
- `pandas`, `openpyxl` - Data handling
- `python-docx` - Word documents
- `python-dotenv` - Environment variables

### 3. Environment Configuration

Create `.env` in project root:

```env
# ====================================================================
# Required: Gemini API Key
# ====================================================================
GEMINI_API_KEY=your_gemini_api_key_here

# ====================================================================
# Required: Google Drive Configuration
# ====================================================================
GOOGLE_DRIVE_CREDENTIALS=credentials.json
DRIVE_MAIN_FOLDER_NAME=NewsArticlesProcessing

# ====================================================================
# Agent 1: Text Curation Mode
# ====================================================================

# Mode: 'agent' (Deep Research, slow) or 'model' (balanced, fast)
# Both modes have Google Search for production use
AGENT1_MODE=agent

# Model for model mode (only used if AGENT1_MODE=model)
AGENT1_MODEL=gemini-3-flash-preview

# ====================================================================
# Agents 2, 3, 4: Standard Model
# ====================================================================
GEMINI_MODEL_AGENTS234=gemini-2.0-flash-exp
```

### 4. Get Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create or select project
3. Generate API key
4. Copy to `.env` file

---

# Configuration Guide

## Agent 1 Mode Configuration

### Option 1: `agent` (Deep Research)
- Comprehensive, slow (4-5 minutes)
- Built-in Google Search (multi-step research)
- Best for maximum quality
- Deep license validation
- Production-ready (highest quality)

### Option 2: `model` (Fast Search)
- Fast (30-60 seconds)
- Explicit Google Search tool (single-pass)
- Best for balanced speed/quality
- Basic license verification
- Production-ready (faster processing)

### Switching Modes

```bash
# In .env file
AGENT1_MODE=agent  # for deep research
# or
AGENT1_MODE=model  # for fast processing

# Temporary override (Linux/Mac)
AGENT1_MODE=model python main.py --batches 3

# Temporary override (Windows PowerShell)
$env:AGENT1_MODE="model"; python main.py --batches 3
```

### Mode Comparison

| Feature | Agent Mode | Model Mode |
|---------|-----------|------------|
| Speed | 4-5 min | 30-60 sec |
| Quality | Highest (multi-pass) | High (single-pass) |
| Google Search | ✅ Built-in | ✅ Explicit tool |
| Best For | Max quality production | Balanced production |
| Cost | Higher | Lower |
| License Verification | Deep, cross-domain | Basic, single-pass |

## Model Selection

### Agent 1 Model (AGENT1_MODEL)

Only used when `AGENT1_MODE=model`. Available options:

- `gemini-3-flash-preview` (default) - Fast, efficient
- `gemini-3-pro-preview` - More capable, slower
- `gemini-2.5-flash` - Alternative fast option
- `gemini-2.5-pro` - Alternative powerful option

### Agents 2-4 Model (GEMINI_MODEL_AGENTS234)

Options:
- `gemini-2.0-flash-exp` (default)
- `gemini-1.5-pro` - More powerful
- `gemini-1.5-flash` - Faster

---

## Google Drive Setup

### 1. Enable Google Drive API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select project
3. Navigate to "APIs & Services" > "Library"
4. Search for "Google Drive API"
5. Click "Enable"

### 2. Create OAuth Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure OAuth consent screen:
   - User Type: External
   - Add your email as test user
   - Scopes: Keep default
4. Choose "Desktop app" as application type
5. Download credentials JSON
6. Save as `credentials.json` in project root

### 3. First-Run Authentication

On first run, the system will:
1. Open browser for Google authentication
2. Request Drive access permissions
3. Save token to `token.json` (auto-renewal)

**Troubleshooting:**
- Delete `token.json` to force re-authentication
- Ensure you grant all requested permissions
- Check that `credentials.json` is valid

---

## PDF Context Setup

### 1. Create Context Folder

The `agent-3-context/` folder should contain PAES reference documents.

```
agent-3-context/
├── guidelines.pdf      # PAES design guidelines
├── example1.pdf        # Example questions
├── example2.pdf        # Example questions
└── example3.pdf        # Example questions
```

### 2. Add Your PDFs

Place 4 PDF files:
1. **Guidelines** - PAES/DEMRE standards
2. **Examples** - 3+ sample question sets

Requirements:
- Must have `.pdf` extension
- Text-based (not scanned images)
- Recommend < 10MB total for faster loading

### 3. How It Works

- PDFs uploaded to Gemini File API at Agent 3 initialization
- Content attached to every question generation request
- Gemini processes PDFs natively (preserves formatting, tables, images)
- No manual text extraction needed

**Console Output:**
```
[PDF Loader] Uploading 4 PDF reference documents to Gemini...
[PDF Loader] OK Uploaded: example1.pdf (URI: https://...)
[PDF Loader] OK Uploaded: example2.pdf (URI: https://...)
[PDF Loader] OK Uploaded: example3.pdf (URI: https://...)
[PDF Loader] OK Uploaded: guidelines.pdf (URI: https://...)
[PDF Loader] Total: 4 PDFs uploaded successfully
```

---

# Agent Configuration

## Custom Prompts

All agent behavior is controlled by prompts in `prompts/` folder:

- `agent1_prompt.txt` - Research and curation rules
- `agent2_prompt.txt` - License validation criteria
- `agent3_prompt.txt` - Question generation format
- `agent4_prompt.txt` - Review standards

**Edit these files to customize agent behavior.**

## Agent 1: Research Configuration

**Deep Research Agent Mode:**
```python
# Uses deep-research-pro-preview-12-2025 agent
# Google Search built-in (no tools parameter needed)
# Background execution (async polling)
# Store=True for conversation context
```

**Model with Google Search Mode:**
```python
# Uses gemini-3-flash-preview (or custom model)
# Google Search via explicit tools parameter
# Synchronous execution
# Store=False for privacy
```

## Agent 2: Validation

Uses Legacy API (`google-generativeai`) for structured validation.

**Migration Note:** Agent 2 will be migrated to Interactions API in future updates for consistency.

## Agents 3 & 4: Questions and Review

Use Interactions API (`google-genai`) with:
- Model: `gemini-3-flash-preview`
- Better multimodal handling (PDFs)
- Improved context caching
- Structured output generation

---

# Testing & Troubleshooting

## Testing

### 1. Validate Configuration

```bash
python main.py --validate-only
```

Expected output:
```
[Config] All configuration checks passed!
[Config] Gemini API key: Configured
[Config] Google Drive credentials: Found
[Config] Agent 1 mode: agent
[Config] PDF context folder: agent-3-context/
```

### 2. Test Mode (Single Batch)

```bash
python main.py --test-mode
```

This will:
- Process 1 batch of 10 articles
- Generate 30 candidates (Agent 1)
- Validate licenses (Agent 2) → ~18-24 approved
- Generate questions (Agent 3) with PDF context
- Review questions (Agent 4)
- Improve questions (Agent 3)
- Upload to Google Drive

Expected time:
- Agent mode: ~30-40 minutes total
- Model mode: ~10-15 minutes total

### 3. Production Batches

```bash
# Process 5 batches
python main.py --batches 5

# With topic filter
python main.py --batches 3 --topic "inteligencia artificial"

# Check progress
# Monitor console output for batch completion
# Check Google Drive for uploaded files
```

## Troubleshooting

### Configuration Errors

**"GEMINI_API_KEY is not set"**
- Create `.env` file with your API key
- Ensure file is in project root
- No spaces around `=` in `.env`

**"Google Drive credentials file not found"**
- Download `credentials.json` from Google Cloud Console
- Place in project root directory
- Check filename matches `.env` setting

**"Permission denied" (Google Drive)**
- Delete `token.json` file
- Run again to re-authenticate
- Grant all requested permissions in browser

### Agent Issues

**Agent 1 too slow**
```env
# Switch to model mode
AGENT1_MODE=model
```

**Agent 1 results not thorough enough**
```env
# Switch to agent mode
AGENT1_MODE=agent
```

**Few articles approved by Agent 2**
- Check `auditoria_*.tsv` for rejection reasons
- Ensure `AGENT1_MODE=agent` for better license finding
- Edit `prompts/agent2_prompt.txt` to adjust criteria

**"Empty PDF Context"**
- Add at least 1 PDF to `agent-3-context/` folder
- Check PDFs are text-based (not scans)
- Verify `.pdf` file extension

### API Errors

**"Model not found: gemini-3-flash-preview"**
```bash
pip install --upgrade google-genai
```

**"Agent not found: deep-research-pro-preview-12-2025"**
- Verify API key has access to Deep Research agent
- Check [documentation](https://ai.google.dev/gemini-api/docs/deep-research) for latest agent name

**"ModuleNotFoundError: No module named 'google.genai'"**
```bash
pip install google-genai>=1.55.0
```

### Processing Issues

**Duplicate articles across batches**
- Check `data/processing_state.csv` is being updated
- Verify state manager is tracking URLs
- Look for "Excluding N already processed articles" in console

**No articles found**
- Check internet connection
- Verify API key is valid
- Try different topic: `--topic "science"`
- Check Agent 1 console output for errors

### Output Issues

**No files in Google Drive**
- Check Google Drive permissions granted
- Verify `DRIVE_MAIN_FOLDER_NAME` in `.env`
- Look for "Upload to Drive" messages in console
- Check local `data/` folder for backups

**Word documents empty or malformed**
- Check Agent 3 output for errors
- Verify PDF context loaded successfully
- Review `prompts/agent3_prompt.txt` format

---

# Technical Architecture

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Orchestrator                         │
│                  (orchestrator.py)                           │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Agent 1    │──▶│   Agent 2    │──▶│   Agent 3    │
│  Research    │   │ Validation   │   │  Questions   │
│              │   │              │   │              │
│ Deep Research│   │ CC License   │   │ PAES Format  │
│ Google Search│   │ Audit        │   │ + PDF Context│
└──────────────┘   └──────────────┘   └──────────────┘
                                               │
                                               ▼
                                      ┌──────────────┐
                                      │   Agent 4    │
                                      │   Review     │
                                      │              │
                                      │ DEMRE Audit  │
                                      └──────────────┘
                                               │
        ┌──────────────────────────────────────┘
        ▼
┌─────────────────────────────────────────────────────────────┐
│                   Storage & Drive Manager                     │
│            (storage.py, drive_manager.py)                     │
└─────────────────────────────────────────────────────────────┘
```

## Agent Architecture

### Agent 1: Research

**File:** `agents/agent1_research.py`

**Dual Mode Architecture:**

```python
# Mode 1: Deep Research Agent
if AGENT1_MODE == 'agent':
    interaction = client.interactions.create(
        agent="deep-research-pro-preview-12-2025",
        input=prompt,
        background=True,  # Async execution
        store=True        # Conversation context
    )

# Mode 2: Model with Google Search
elif AGENT1_MODE == 'model':
    interaction = client.interactions.create(
        model="gemini-3-flash-preview",
        input=prompt,
        tools=[{"google_search": {}}],  # Explicit tool
        store=False       # Privacy
    )
```

**Key Features:**
- Duplicate prevention via `exclude_urls` parameter
- TSV parsing with 28-column validation (includes ID_RANDOM)
- Automatic ID continuation (C001, C002, ...)
- Robust fallback parsing for malformed TSV

**Output Format (TSV):**
```
ID	ID_RANDOM	Tipo	Tema	Autor	Titulo	Ano	Fuente	URL	URL_Canonica	Licencia	Tipo_Evidencia_Licencia	Evidencia_Licencia_Quote	Evidencia_Licencia_Ubicacion	Palabras_Fragmento_Estimadas	Palabras_Fragmento_Real	Inicio_Fragmento	Fin_Fragmento	Alertas	Recurso_Discontinuo	URL_Recurso	Licencia_Recurso	Tipo_Evidencia_Recurso	Evidencia_Recurso_Quote	Evidencia_Recurso_Ubicacion	Linea_Cita_PAES	Clave_Dedup	Riesgos
```

### Agent 2: Validation

**File:** `agents/agent2_validation.py`

**API:** Legacy API (`google-generativeai`)

**Validation Phases:**
1. PHASE 1: Basic license check (CC-BY, CC-BY-SA, PD)
2. PHASE 2: Evidence in same domain
3. PHASE 3: No syndication from prohibited sources
4. PHASE 4: Visual resource dependencies
5. PHASE 5-6: Special rules (Memoria Chilena, SINC)
6. PHASE 7: Portfolio rules (4/4/4 distribution, max 2/source)

### Agent 3: Question Generation

**File:** `agents/agent3_questions.py`

**API:** Interactions API with Gemini File API integration

**PDF Context Loading:**

```python
from google import genai

# Upload PDFs at initialization
pdf_files = []
for pdf_path in pdf_folder:
    file = genai.upload_file(pdf_path)
    # Wait for processing
    while file.state.name == "PROCESSING":
        time.sleep(2)
        file = genai.get_file(file.name)
    pdf_files.append(file)

# Attach to generation request
interaction = client.interactions.create(
    model="gemini-3-flash-preview",
    input=[
        instruction_text,
        pdf_file_1,  # Native PDF processing
        pdf_file_2,
        pdf_file_3,
        pdf_file_4
    ],
    store=False
)
```

**PAES Question Format:**

```
LECTURA {ID_LECTURA}
{Autor}, "{Título}" ({Año}). (Fragmento).
Fuente: {Fuente/Medio}. URL: {URL}
Tipo de texto: {tipo}

[Fragmento del texto]

PREGUNTAS

1. [Localizar-a] Pregunta 1
A) Alternativa A
B) Alternativa B
C) Alternativa C
D) Alternativa D ✓

2. [Interpretar-d] Pregunta 2
...

CLAVES
1-D, 2-B, 3-A, ...

JUSTIFICACIÓN
P1: Microevidencia: "..." (líneas X-Y)
...
```

### Agent 4: Review

**File:** `agents/agent4_review.py`

**API:** Interactions API

**DEMRE Rubric:**

```
9.0-10.0: Nivel prueba oficial DEMRE
8.0-8.9:  Muy bueno, mejoras menores
7.0-7.9:  Correcto, debilidades leves
6.0-6.9:  Usable, riesgos de reclamo
<6.0:     Requiere reescritura
```

---

# API Details

## Interactions API vs Legacy API

| Feature | Interactions API | Legacy API |
|---------|------------------|------------|
| **Agents** | Agent 1, 3, 4 | Agent 2 |
| **Package** | `google-genai` | `google-generativeai` |
| **Status** | Beta | Stable |
| **Google Search** | ✅ Built-in (agent) / Explicit (model) | ❌ |
| **File Upload** | ✅ Native PDF processing | ❌ |
| **State Management** | ✅ Conversation tracking | ❌ |
| **Background Execution** | ✅ Deep Research | ❌ |

## Why Two APIs?

**Interactions API (Agents 1, 3, 4):**
- Better state management (conversation context)
- Tool orchestration (Google Search, Code Execution, File Search)
- Background execution (long-running Deep Research)
- Native multimodal (PDF, images)
- Better caching (performance optimization)

**Legacy API (Agent 2):**
- Stable and well-tested
- Sufficient for structured validation
- No complex tools needed
- Migration planned for consistency

---

# Data Flow & State Management

## Workflow Sequence

```
1. Orchestrator starts batch N
   │
   ├─▶ Load processed URLs (duplicate prevention)
   │
2. Agent 1: Research
   │
   ├─▶ Mode check (agent vs model)
   ├─▶ Deep Research OR Fast Search with Google
   ├─▶ Generate 30 candidate texts
   ├─▶ Output: TSV with 28 columns
   │
3. Agent 2: Legal Validation
   │
   ├─▶ Input: TSV from Agent 1
   ├─▶ Validate licenses (CC-BY, CC-BY-SA, PD)
   ├─▶ Check evidence in same domain
   ├─▶ Apply portfolio rules (4/4/4, max 2/source)
   ├─▶ Output: Audit TSV (APROBADO/RECHAZADO)
   │
4. For each APROBADO article:
   │
   ├─▶ Agent 3: Generate Questions
   │   │
   │   ├─▶ Upload 4 PDF references to Gemini
   │   ├─▶ Attach PDFs to generation request
   │   ├─▶ Generate 10 PAES questions (2-5-3 distribution)
   │   ├─▶ Output: Questions with metadata
   │   │
   ├─▶ Agent 4: Review Questions
   │   │
   │   ├─▶ Input: Article + questions
   │   ├─▶ Apply DEMRE standards
   │   ├─▶ Generate nota (0-10) + feedback
   │   ├─▶ Output: Veredicto + parches
   │   │
   ├─▶ Agent 3: Improve Questions
   │   │
   │   ├─▶ Input: Original + feedback
   │   ├─▶ Apply suggested fixes
   │   ├─▶ Output: Improved questions
   │   │
   ├─▶ Document Generation
   │   │
   │   ├─▶ preguntas_iniciales.docx (includes article text)
   │   └─▶ preguntas_mejoradas.docx (includes article text)
   │   │
   └─▶ Upload to Google Drive
       │
       └─▶ Update processing state
```

## State Management

### Processing State CSV

**File:** `data/processing_state.csv`

**Columns:**
```csv
article_id,title,url,source,license_status,license_type,processing_status,date_found,date_completed
```

**Status Values:**
- `new` - Just discovered
- `validated` - Passed Agent 2
- `rejected` - Failed Agent 2
- `questions_generated` - Agent 3 complete
- `completed` - Full pipeline complete
- `error` - Processing failed

### Duplicate Prevention

```python
# Before batch
processed_urls = state_manager.get_processed_urls()
# Returns: set(['url1', 'url2', ...])

# Agent 1 filtering
articles = find_articles(exclude_urls=processed_urls)

# Double-check filter
filtered = [a for a in articles if a['url'] not in processed_urls]

# After processing
state_manager.mark_as_processed(article_url)
```

## Storage and Outputs

### Local Storage Structure

```
data/
├── processing_state.csv           # State tracking
├── candidatos_YYYYMMDD_HHMMSS.tsv # Agent 1 output
├── auditoria_YYYYMMDD_HHMMSS.tsv  # Agent 2 output
└── temp/                           # Temporary files
```

### Google Drive Structure

```
NewsArticlesProcessing/
├── validated_articles.csv          # Master CSV
├── candidatos_20260108.tsv        # Batch TSVs
├── auditoria_20260108.tsv         # Audit TSVs
├── Texto_C001_La_Inteligencia_Artificial/
│   ├── preguntas_iniciales.docx   # Includes article text + questions
│   └── preguntas_mejoradas.docx   # Includes article text + improved questions
├── Texto_C002_El_Cambio_Climatico/
│   └── ...
└── ...
```

---

# Performance & Optimization

## Agent 1 Performance

| Mode | Time | Quality | Cost | Use Case |
|------|------|---------|------|----------|
| Agent | 4-5 min | Highest | Higher | Max quality |
| Model | 30-60 sec | High | Lower | Fast iteration |

## Optimization Strategies

**For Speed:**
- Use model mode (`AGENT1_MODE=model`)
- Use flash models (`gemini-3-flash-preview`)
- Process smaller batches more frequently

**For Quality:**
- Use agent mode (`AGENT1_MODE=agent`)
- Use pro models (`gemini-3-pro-preview`)
- Allow longer processing times

**For Cost:**
- Use model mode with flash models
- Reduce batch sizes
- Cache PDF uploads (already implemented)

## Caching

**Gemini File API:**
- PDFs cached after first upload
- Reused across all questions in batch
- Auto-deleted after 48 hours (or manual delete)

**Interactions API:**
- Automatic context caching (beta)
- Improves performance for repeated queries
- Reduces token usage

---

## Security Best Practices

1. **Never commit sensitive files:**
   - `.env`
   - `credentials.json`
   - `token.json`
   - All in `.gitignore`

2. **Rotate API keys:**
   - If key exposed, regenerate immediately
   - Update `.env` file

3. **OAuth token management:**
   - `token.json` auto-renews
   - Delete to force re-authentication
   - Never share token file

4. **Environment variables:**
   - Use `.env` for all secrets
   - Never hardcode keys in code
   - Keep `.env.example` as template (without actual keys)

---

**Documentation Status:** ✅ Complete  
**Last Updated:** January 2026  
**Version:** Production Ready
