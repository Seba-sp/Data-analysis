# Stack Research

**Domain:** Python report pipeline — LMS API ingestion, CSV/XLSX processing, docx report generation, email delivery, GCP Cloud Run webhook deployment
**Researched:** 2026-02-28
**Confidence:** MEDIUM (training data cutoff August 2025; web verification tools unavailable in this session — version numbers sourced from existing codebase pins and training knowledge)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11 | Runtime | LTS release, full support until Oct 2027; all GCP Cloud Run base images support it; existing codebase runs on 3.10/3.11 |
| Flask | 3.x | Webhook HTTP server | Already used in all 5 projects; `functions_framework` wraps Flask; zero migration cost; lightweight for a single-endpoint webhook receiver |
| functions-framework | 3.x | GCP Cloud Run entry point | The standard GCP adapter that wraps Flask handlers for Cloud Functions/Cloud Run; already present in all cloud requirements.txt files |
| python-dotenv | 1.x | Environment variable loading | Already used throughout; simple, zero-dependency; `python-dotenv==0.*` pins in existing files are behind — 1.0 added stable API |

### Data Ingestion

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| requests | 2.31+ | LearnWorlds API HTTP client | Already used in all projects for the LearnWorlds REST API; battle-tested, simple Bearer token auth; no need to switch to httpx for this use case |
| pandas | 2.2.x | CSV/XLSX processing and analysis | Already used; version 2.x is the stable modern branch (Copy-on-Write semantics, better nullable dtypes); existing `complete_deployment` already pins 2.2.2 |
| openpyxl | 3.1.x | XLSX read/write backend for pandas | Already used; required engine for `pd.read_excel`; 3.1.x is stable |

### Report Generation

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| python-docx | 1.1.x | docx generation (programmatic) | Standard library for creating .docx from scratch or modifying templates programmatically; well-maintained, Apache 2.0 license; used when report structure is generated from code |
| docxtpl | 0.17.x | docx template rendering | Wraps python-docx with Jinja2 templating; enables Word-native templates (.docx files with `{{ variable }}` placeholders) rather than HTML files; **this is the primary docx tool for this project** |
| Jinja2 | 3.1.x | Template engine (backing docxtpl) | Already present; docxtpl uses Jinja2 under the hood for `{{ }}` expressions in Word templates |

### Email Delivery

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| stdlib smtplib + email.message | stdlib | SMTP email sending | Already used in `shared/email_sender.py`; zero extra dependency; sufficient for Gmail SMTP + TLS (port 587); attaches .docx as binary |

### GCP Infrastructure

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| google-cloud-firestore | 2.x | Task queuing / batch state | Already used; persists webhook queue between Cloud Run cold starts; avoids in-memory queue loss |
| google-cloud-tasks | 2.x | Delayed batch trigger | Already used; schedules the 15-minute batch processing window after first webhook arrives |
| google-cloud-storage | 2.x | File storage backend | Already used in StorageClient; abstracts local vs. GCP storage; templates and data files stored here in cloud deployments |
| google-api-python-client | 2.x | Google Drive upload | Already used in drive_service.py; saves final reports to Drive |
| google-auth | 2.x | Service account authentication | Already used; handles credentials for all GCP clients |

---

## Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | 1.26.x or 2.x | Numerical support for pandas | Only needed if any report generator does numerical computations beyond pandas; existing code uses it as pandas backend in complete_deployment |
| protobuf | 4.x or 5.x | Required by google-cloud-firestore | Transitive dependency; pin to avoid conflict between gRPC and protobuf versions |
| pytest | 8.x | Unit testing | When writing tests for core modules and report generators |
| pytest-mock | 3.x | Mocking GCP clients in tests | Avoids real GCP calls during unit tests |

---

## Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| python-dotenv | `.env` file loading in local development | Use `.env.template` pattern already established in the repo |
| Docker + Cloud Run YAML | Container deployment | Cloud Run deploys the container; use `FROM python:3.11-slim` to keep image size down |
| Cloud Build or `gcloud run deploy` | CI/CD | `gcloud run deploy` from CLI is sufficient for this project size; no need for full CI/CD pipeline initially |

---

## Installation

```bash
# Core pipeline
pip install \
  flask==3.* \
  functions-framework==3.* \
  requests==2.* \
  pandas==2.2.* \
  openpyxl==3.1.* \
  python-dotenv==1.* \
  Jinja2==3.1.*

# Report generation (docx)
pip install \
  python-docx==1.1.* \
  docxtpl==0.17.*

# GCP integration
pip install \
  google-cloud-firestore==2.* \
  google-cloud-tasks==2.* \
  google-cloud-storage==2.* \
  google-api-python-client==2.* \
  google-auth==2.* \
  protobuf==4.*

# Dev / test
pip install -D pytest==8.* pytest-mock==3.*
```

---

## Alternatives Considered

| Category | Recommended | Alternative | When to Use Alternative |
|----------|-------------|-------------|-------------------------|
| HTTP client | `requests` | `httpx` | If LearnWorlds API calls ever need async batching (httpx has async support); not needed now — the existing synchronous pipeline is straightforward |
| Report format | `docxtpl` (docx) | `weasyprint` (PDF via HTML) | weasyprint is what all existing projects use today; keep it if any report generator must stay PDF; migrate to docxtpl for new report types going forward since the PROJECT.md specifies docx as the target format |
| Report format | `docxtpl` (docx) | `reportlab` (PDF) | reportlab is already in some requirements.txt but appears unused in code; skip it |
| Email | stdlib `smtplib` | `sendgrid` / `mailgun` SDK | Only if volume grows to thousands of emails per run or if deliverability (SPF/DKIM management) becomes a concern |
| Queueing | Firestore + Cloud Tasks | Cloud Pub/Sub | Pub/Sub is appropriate if you need fan-out or multiple consumers; current batch model is a single consumer and Firestore/Tasks already works |
| Web framework | Flask | FastAPI | FastAPI makes sense if the webhook API grows to many endpoints or needs OpenAPI docs; Flask is simpler and already proven here |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `weasyprint` for new report types | Heavy system dependency (Pango, Cairo, libffi); increases Docker image size by ~300MB; HTML template editing is harder for non-developers; PROJECT.md explicitly targets docx | `docxtpl` + Word templates |
| `reportlab` | Present in some requirements.txt but unused in actual code; low-level PDF drawing API, not a templating system; requires separate designer tooling | `docxtpl` for docx; `weasyprint` only if existing PDF reports cannot be migrated |
| Wildcard version pins (`==2.*`) in production | Wildcards allow silent major/minor bumps that break compatibility; existing requirements.txt files use them out of convenience | Exact pins in `requirements.txt` (`==2.2.2`); use `~=` (compatible release) only for patch updates |
| `pandas==1.*` | Pandas 1.x reached end of support in January 2024; missing Copy-on-Write, nullable types, and performance improvements in 2.x | `pandas==2.2.*` — already used in `complete_deployment` |
| In-memory student queue (without Firestore) | Cloud Run instances are ephemeral and can be terminated mid-batch; queue is lost on cold start | Keep Firestore as the queue backend as currently implemented |
| Per-project `complete_deployment/` subfolders | The entire problem being solved — duplication causes drift; currently 2 projects (diagnosticos, diagnosticos_uim) have this pattern | Single unified codebase with report type as parameter |
| `google-cloud-firestore==2.*` with `protobuf==5.*` | Known compatibility conflict: google-cloud-firestore 2.x requires protobuf 3.x or 4.x; protobuf 5.x has breaking API changes | Pin `protobuf==4.*` when using firestore 2.x |

---

## Stack Patterns by Variant

**If deploying to Cloud Run with webhook trigger (diagnosticos, diagnosticos_uim pattern):**
- Use `functions-framework` as entry point (already proven)
- Use Firestore for queue + Cloud Tasks for delayed batch trigger
- Set `STORAGE_BACKEND=gcp` and `GCP_BUCKET_NAME` in environment
- Docker image: `FROM python:3.11-slim` + system deps only if weasyprint is included

**If running locally / manually (assessment-analysis-project, ensayos_generales pattern):**
- Use `main.py` with argparse: `python main.py --report-type diagnosticos`
- Set `STORAGE_BACKEND=local` in `.env`
- No Firestore or Cloud Tasks needed

**If adding a new report type (the primary use case for the unified framework):**
- Create `reports/my_report/generator.py` implementing the `ReportGenerator` interface
- Create `templates/my_report/template.docx` as the Word template
- Register the report type in the `reports/__init__.py` plugin registry
- No changes to core pipeline (downloader, analyzer, email sender, storage)

**If the report generator pattern uses Python module discovery:**
- Use Python's `importlib.import_module` with a naming convention (`reports.{report_type}.generator`)
- This is simpler and more explicit than `pkg_resources` entry points for a closed, internal plugin system
- Avoid `pkgutil.walk_packages` — it scans too broadly and has surprising behavior with namespace packages

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `google-cloud-firestore==2.*` | `protobuf==4.*` | protobuf 5.x breaks firestore 2.x; if upgrading firestore to 3.x, protobuf 5.x becomes usable |
| `pandas==2.2.*` | `numpy>=1.23,<2.0` (safe) or `numpy>=2.0` (experimental) | pandas 2.2 officially supports numpy 1.x; numpy 2.0 support landed in pandas 2.2.2 but may have edge cases |
| `docxtpl==0.17.*` | `python-docx>=1.0` and `Jinja2>=3.0` | docxtpl 0.17 requires python-docx 1.x (breaking change from 0.x); do not mix docxtpl with python-docx 0.8.x |
| `functions-framework==3.*` | `flask==3.*` | functions-framework 3.x was updated to support Flask 3.x; Flask 2.x still works but Flask 3.x is current |
| `weasyprint==66.*` (if kept) | Python 3.11 only if system libs present | weasyprint requires Pango, Cairo, libffi; must be installed in the Docker image with `apt-get install -y libpango-1.0-0 libcairo2` |

---

## Key Architectural Decision: docx vs PDF

The PROJECT.md specifies **docx reports**, but all 5 existing projects currently generate **PDF reports via weasyprint + HTML templates**. This is the most significant stack decision.

**Recommendation: Adopt docxtpl for all new report generators; keep weasyprint for existing ones during migration.**

Rationale:
1. Word templates (`.docx`) are editable by non-developers — the client can adjust layout without touching code
2. docxtpl uses the same Jinja2 `{{ variable }}` syntax already present in the codebase
3. Docker images without weasyprint are ~300MB smaller, reducing cold start time on Cloud Run
4. Email attachment of `.docx` is universally accepted; PDF is also fine but .docx is the stated goal
5. During migration: existing `report_generator.py` classes remain unchanged; new reports use docxtpl

**Risk:** Some existing reports use complex HTML tables (lecture status grids, skill percentage tables). These need to be reproduced in Word table format using python-docx table API or docxtpl `{% for %}` loops. This is feasible but requires care during migration.

---

## Sources

- Existing codebase analysis (5 projects): `diagnosticos/`, `diagnosticos_uim/`, `assessment-analysis-project/`, `ensayos_generales/`, `reportes de test de diagnostico/` — HIGH confidence for what is currently used
- `diagnosticos/complete_deployment/requirements.txt` and `diagnosticos_uim/complete_deployment/requirements.txt`: pinned versions `pandas==2.2.2`, `openpyxl==3.1.5`, `weasyprint==66.0`, `reportlab==4.4.3`, `jinja2==3.1.4` — HIGH confidence (most recent pins in codebase)
- Training knowledge (cutoff August 2025) for `python-docx 1.1.x`, `docxtpl 0.17.x`, `Flask 3.x`, `python-dotenv 1.x` version ranges — MEDIUM confidence (verify with `pip index versions <package>` before pinning)
- `PROJECT.md` requirement: "docx reports" and "pluggable generator modules" — HIGH confidence (authoritative project spec)

---

*Stack research for: Python report pipeline — LearnWorlds API + docx generation + GCP Cloud Run*
*Researched: 2026-02-28*
