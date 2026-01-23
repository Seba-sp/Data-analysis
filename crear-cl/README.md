# Multi-Agent News Processing Pipeline (PAES)

Automated pipeline using Gemini API to discover, validate, and process news articles for educational content creation following Chilean PAES (Competencia Lectora) standards.

## 🚀 Key Features

- **Multi-Agent Workflow**: Four specialized AI agents (Research, Validation, Questions, Review)
- **PAES Compliance**: Custom prompts for Chilean DEMRE standards (10 questions, A-D format, 2-5-3 distribution)
- **Deep Research**: Gemini's Deep Research agent with built-in Google Search for current articles
- **Batch Processing**: Process N batches with automatic duplicate prevention
- **PDF Context**: Reference documents guide question generation via Gemini File API
- **Google Drive Integration**: Organized output folders with automated uploads
- **Document Generation**: Word (clean format) + Excel (metadata) files per article
- **Utility Scripts**: Batch document generation and Excel merging tools

## 📋 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```env
# Required: Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Required: Google Drive Configuration
GOOGLE_DRIVE_CREDENTIALS=credentials.json
DRIVE_MAIN_FOLDER_NAME=NewsArticlesProcessing

# Agent 1 Mode: 'agent' (Deep Research, 4-5 min) or 'model' (Fast, 30-60s)
AGENT1_MODE=agent
```

### 3. Setup Google Drive

- Enable Google Drive API in Google Cloud Console
- Create OAuth 2.0 credentials (Desktop app)
- Download as `credentials.json` and place in project root

### 4. Add Reference PDFs

Place PAES reference documents in `agent-3-context/` folder:
- Guidelines for question design
- Example questions (3+ files recommended)

### 5. Run Pipeline

```bash
# Process 1 batch of 10 articles
python main.py --test-mode

# Process multiple batches
python main.py --batches 5

# Custom topic
python main.py --batches 3 --topic "inteligencia artificial"

# Validate configuration
python main.py --validate-only
```

## 🤖 Agent Pipeline

### Agent 1: Text Curation
- **Modes**: 
  - `agent` - Deep Research (4-5 min, thorough, built-in Google Search)
  - `model` - Fast Search (30-60s, balanced, explicit Google Search)
- **Output**: TSV with 30 columns, 30 candidate texts
- **Rules**: 10-10-10 distribution (literario/expositivo/argumentativo), CC-BY/CC-BY-SA/PD only

### Agent 2: Legal Validation
- **Input**: TSV from Agent 1
- **Output**: Audit TSV (APROBADO/RECHAZADO decisions)
- **Validates**: License evidence, syndication, portfolio rules (4/4/4, max 2/source)

### Agent 3: Question Generation
- **Input**: Approved articles + 4 reference PDF documents
- **Output**: 10 PAES-format questions (A-D alternatives) in Word + Excel
- **Standards**: 2-5-3 distribution (Localizar/Interpretar/Evaluar), microevidencia, distractores plausibles

### Agent 4: Question Review
- **Input**: Generated questions
- **Output**: DEMRE audit (nota 0-10, veredicto, diagnostico, parches)
- **Validates**: Única correcta, anclaje textual, paralelismo, distribución correcta

## 📂 Output Structure

```
NewsArticlesProcessing/
├── validated_articles.csv          # Master list
├── candidatos_YYYYMMDD.tsv        # Agent 1 candidates
├── auditoria_YYYYMMDD.tsv         # Agent 2 audit
├── Texto_C001_Titulo/             # Per article folder
│   ├── questions_initial_C001.docx   # Initial questions (clean format)
│   ├── questions_initial_C001.xlsx   # Initial metadata
│   ├── questions_improved_C001.docx  # Improved questions (clean format)
│   └── questions_improved_C001.xlsx  # Improved metadata
└── ...
```

## 🛠️ Utility Scripts

### Batch Document Generation

Process all debug files in a folder:

```bash
# Generate Word + Excel for all debug_questions*.txt files
python batch_generate_documents.py <folder_path>

# Example
python batch_generate_documents.py data/Batch1/
```

**Output:** 2 files per article (Word + Excel) for both initial and improved versions

### Excel Files Merger

Merge multiple Excel files into one:

```bash
# Merge all .xlsx files in folder
python merge_excel_files.py <folder_path>

# Example
python merge_excel_files.py data/Batch1/
```

**Output:** Single merged Excel with source filename as first column

## ⚙️ Configuration

### Agent 1 Modes

| Feature | Agent Mode | Model Mode |
|---------|-----------|-----------|
| Speed | 4-5 minutes | 30-60 seconds |
| Research Depth | Comprehensive | Balanced |
| Google Search | ✅ Built-in | ✅ Explicit tool |
| Best For | Max quality | Fast iteration |
| Cost | Higher | Lower |

Configure in `.env`:
```env
AGENT1_MODE=agent  # or 'model'
AGENT1_MODEL=gemini-3-flash-preview  # only for model mode
```

### Flexible Pipeline Starts

```bash
# Start from Agent 1 (default - full pipeline)
python main.py --test-mode

# Start from Agent 2 (skip research, use existing candidatos TSV)
python main.py --test-mode --start-from agent2 --tsv-file data/candidatos_20260109.tsv

# Start from Agent 3 (skip to question generation, only needs enriched audit file)
python main.py --test-mode --start-from agent3 --tsv-file data/auditoria_20260109.tsv
```

## 🔧 Common Issues

### "GEMINI_API_KEY is not set"
Add your API key to `.env` file.

### "Permission denied" (Google Drive)
Delete `token.json` and re-authenticate.

### "Empty PDF Context"
Add at least one PDF to `agent-3-context/` folder.

### Agent 1 too slow?
Switch to model mode: `AGENT1_MODE=model` in `.env`

## 📖 Documentation

See **DOCUMENTATION.md** for complete technical details:
- Installation & setup
- Configuration guide
- Agent architecture
- API details
- Batch processing guides
- Excel merging guide
- Troubleshooting
- Performance optimization

## 📝 Requirements

- Python 3.9+
- Google Cloud account with Gemini API access
- Google Drive API enabled
- OAuth 2.0 credentials for Drive

## 🌐 Spanish Locale

The system uses Spanish number formatting (decimal: `,`, thousands: `.`) for Chilean DEMRE compatibility.

---

**Status**: ✅ Production Ready  
**License**: See project license  
**Support**: See DOCUMENTATION.md for detailed help
