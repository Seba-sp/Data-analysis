# Multi-Agent News Processing Pipeline (PAES)

Automated pipeline using Gemini API to discover, validate, and process news articles for educational content creation following Chilean PAES (Competencia Lectora) standards.

## 🚀 Key Features

- **Multi-Agent Workflow**: Four specialized AI agents (Research, Validation, Questions, Review)
- **PAES Compliance**: Custom prompts for Chilean DEMRE standards (10 questions, A-D format, 2-5-3 distribution)
- **Deep Research**: Gemini's Deep Research agent with built-in Google Search for current articles
- **Batch Processing**: Process N batches with automatic duplicate prevention
- **PDF Context**: Reference documents guide question generation via Gemini File API
- **Google Drive Integration**: Organized output folders with automated uploads

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

### 5. Run Test

```bash
# Process 1 batch of 10 articles
python main.py --test-mode

# Process multiple batches
python main.py --batches 5

# Custom topic
python main.py --batches 3 --topic "inteligencia artificial"
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
- **Output**: 10 PAES-format questions (A-D alternatives) in Word documents
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
│   ├── preguntas_iniciales.docx   # Initial questions (includes article text)
│   └── preguntas_mejoradas.docx   # Improved questions (includes article text)
└── ...
```

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

### Model Selection

All models are configurable via environment variables:

```env
# Agent 1 Model (only used in model mode)
AGENT1_MODEL=gemini-3-flash-preview

# Agents 2, 3, 4 Model
GEMINI_MODEL_AGENTS234=gemini-2.0-flash-exp
```

## 📊 Batch Processing

```bash
# Single batch (test)
python main.py --test-mode

# Multiple batches
python main.py --batches 5

# With topic filter
python main.py --batches 3 --topic "cambio climático"

# Validate configuration
python main.py --validate-only
```

### Flexible Pipeline Starts

You can start the pipeline from any agent, useful for resuming after errors:

```bash
# Start from Agent 1 (default - full pipeline)
python main.py --test-mode

# Start from Agent 2 (skip research, use existing candidatos TSV)
python main.py --test-mode --start-from agent2
python main.py --test-mode --start-from agent2 --tsv-file data/candidatos_20260109.tsv

# Start from Agent 3 (skip to question generation, requires both TSV files)
python main.py --test-mode --start-from agent3 --tsv-file data/auditoria_20260109.tsv --candidatos-file data/candidatos_20260109.tsv
```

**Use cases:**
- **Agent 2**: Already have candidate texts from Agent 1, want to re-validate
- **Agent 3**: Agent 1 & 2 completed successfully, but Agent 3 failed (API errors, PDF issues, etc.) - requires both audit and candidatos TSV files

### Duplicate Prevention

- All processed URLs tracked in `data/processing_state.csv`
- Agent 1 excludes previously processed articles
- Double-check filtering after API call

## 🔧 Troubleshooting

### "GEMINI_API_KEY is not set"
Add your API key to `.env` file.

### "Permission denied" (Google Drive)
Delete `token.json` and re-authenticate.

### "Empty PDF Context"
Add at least one PDF to `agent-3-context/` folder.

### Agent 1 too slow?
Switch to model mode: `AGENT1_MODE=model` in `.env`

### Few articles approved?
- Check `auditoria_*.tsv` for rejection reasons
- Ensure Agent 1 mode is set to `agent` for better license verification

## 📖 Documentation

- **SETUP.md** - Detailed setup and configuration guide
- **ARCHITECTURE.md** - Technical details about agents, models, and APIs

## 🔐 Security

- Keep `.env` and `credentials.json` private (both in `.gitignore`)
- Never commit API keys or OAuth tokens
- Use environment variables for all sensitive data

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
**Support**: See SETUP.md for detailed troubleshooting
