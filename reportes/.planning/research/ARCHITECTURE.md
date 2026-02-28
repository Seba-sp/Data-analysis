# Architecture Research

**Domain:** Plugin-based Python report pipeline (LearnWorlds assessment reports)
**Researched:** 2026-02-28
**Confidence:** HIGH — derived directly from reading all five existing project codebases

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Entry Points Layer                          │
├──────────────────────────────┬──────────────────────────────────────┤
│   GCP Cloud Run Webhook      │        Local CLI (main.py)           │
│   webhook_service.py         │   python main.py --report diagnosticos│
│   POST /webhook              │   python main.py --report ensayos    │
│   GET  /process-batch        │                                      │
└──────────────┬───────────────┴──────────────────────────────────────┘
               │  Both entry points call the same Pipeline Runner
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Pipeline Runner                              │
│   Accepts: report_type (str) + run_context (local | webhook)        │
│   Orchestrates: download → process → analyze → generate → deliver   │
└──────┬──────────┬──────────────────────┬────────────────────────────┘
       │          │                      │
       ▼          ▼                      ▼
┌──────────┐ ┌──────────┐        ┌──────────────────────────────────┐
│  core/   │ │  core/   │        │         reports/ (plugins)        │
│assessment│ │assessment│        │  ┌────────────┐ ┌─────────────┐  │
│_downloader│ │_analyzer │        │  │diagnosticos│ │ensayos_gen. │  │
└──────────┘ └──────────┘        │  │/generator.py│ │/generator.py│  │
                                 │  └────────────┘ └─────────────┘  │
┌──────────┐ ┌──────────┐        │  ┌────────────┐ ┌─────────────┐  │
│  core/   │ │  core/   │        │  │diagnosticos│ │  [future]   │  │
│ storage  │ │  email   │        │  │_uim/gen.py │ │ /generator  │  │
│  .py     │ │_sender.py│        │  └────────────┘ └─────────────┘  │
└──────────┘ └──────────┘        └──────────────────────────────────┘
                                          │
┌──────────┐ ┌──────────┐                 ▼
│  core/   │ │  core/   │        ┌──────────────────────────────────┐
│  drive   │ │  slack   │        │     templates/ (per report type)  │
│_service.py│ │_service.py│       │  diagnosticos/  ensayos_gen./    │
└──────────┘ └──────────┘        │    *.html         *.html         │
                                 └──────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────┐
│              GCP-only: Firestore Queue + Cloud Tasks                │
│   firestore_service.py  │  task_service.py  │  batch_processor.py  │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Current Location (to migrate from) |
|-----------|---------------|-----------------------------------|
| `core/assessment_downloader.py` | LearnWorlds API pagination, JSON save, incremental merge | Each project root |
| `core/assessment_analyzer.py` | CSV analysis, lecture/skill/subject scoring | Each project root |
| `core/storage.py` | Local file I/O abstraction (read/write CSV, JSON, bytes) | `shared/storage.py` (partial) |
| `core/email_sender.py` | SMTP email with PDF attachments | `shared/email_sender.py` (partial) |
| `core/drive_service.py` | Google Drive folder/file CRUD, shared drive support | `shared/drive_service.py` (done) |
| `core/slack_service.py` | Slack notifications | `shared/slack_service.py` (done) |
| `reports/<type>/generator.py` | Report-type-specific PDF/HTML rendering logic | Each project's `report_generator.py` |
| `templates/<type>/` | HTML templates per report type | Each project's `templates/` folder |
| `entrypoints/webhook_service.py` | GCP Cloud Run handler: validates signature, queues students, triggers batch | `diagnosticos/webhook_service.py` |
| `entrypoints/main.py` | Local CLI: argparse driver, orchestrates pipeline steps | Each project's `main.py` |
| `entrypoints/gcp/` | Firestore, Cloud Tasks, batch processor (GCP-only) | `diagnosticos/firestore_service.py`, etc. |
| `data/<type>/` | Per-report-type data (questions CSV, raw JSON, processed CSV, analysis CSV) | Each project's `data/` |

---

## Recommended Project Structure

```
reportes/                          # repo root (already exists)
├── core/                          # shared pipeline engine — single source of truth
│   ├── __init__.py
│   ├── assessment_downloader.py   # LearnWorlds API → JSON (merged from 5 copies)
│   ├── assessment_analyzer.py     # JSON/CSV → analysis CSV (merged from 5 copies)
│   ├── storage.py                 # file I/O abstraction (promote from shared/)
│   ├── email_sender.py            # SMTP delivery (promote from shared/)
│   ├── drive_service.py           # Google Drive (promote from shared/ — already good)
│   └── slack_service.py           # Slack (promote from shared/ — already good)
│
├── reports/                       # plugin directory — one subfolder per report type
│   ├── __init__.py
│   ├── base.py                    # BaseReportGenerator ABC (defines the interface)
│   ├── diagnosticos/
│   │   ├── __init__.py
│   │   ├── generator.py           # implements BaseReportGenerator
│   │   └── assessment_mapper.py   # diagnosticos-specific assessment ID mapping
│   ├── diagnosticos_uim/
│   │   ├── __init__.py
│   │   ├── generator.py
│   │   └── assessment_mapper.py
│   ├── ensayos_generales/
│   │   ├── __init__.py
│   │   └── generator.py
│   └── assessment_analysis/       # (from assessment-analysis-project)
│       ├── __init__.py
│       └── generator.py
│
├── templates/                     # HTML report templates, one subfolder per report type
│   ├── diagnosticos/
│   │   ├── M1.html
│   │   ├── CL.html
│   │   ├── CIEN.html
│   │   └── HYST.html
│   ├── diagnosticos_uim/
│   │   └── Portada.html
│   └── ensayos_generales/
│       └── Portada.html
│
├── data/                          # per-report-type runtime data (NOT committed except questions)
│   ├── diagnosticos/
│   │   ├── questions/             # M1.csv, CL.csv, CIEN.csv, HYST.csv (committed)
│   │   ├── raw/                   # API JSON downloads (gitignored)
│   │   ├── processed/             # CSV from raw (gitignored)
│   │   └── analysis/              # analysis CSV output (gitignored)
│   └── diagnosticos_uim/
│       └── questions/
│
├── entrypoints/
│   ├── __init__.py
│   ├── main.py                    # Local CLI: python entrypoints/main.py --report diagnosticos
│   ├── webhook_service.py         # GCP Cloud Run HTTP handler (functions_framework)
│   └── gcp/
│       ├── __init__.py
│       ├── firestore_service.py   # Firestore queue management
│       ├── task_service.py        # Cloud Tasks delayed processing
│       └── batch_processor.py     # Batch runner (calls pipeline for each student)
│
├── scripts/                       # one-off utilities (already exists, keep as-is)
│   ├── encode_service_account.py
│   ├── setup_environment.py
│   └── ...
│
├── shared/                        # DEPRECATED — migrate contents into core/
│   └── (kept briefly during migration, then deleted)
│
├── .env                           # local secrets (gitignored)
├── requirements.txt               # single requirements file for the whole repo
├── Dockerfile                     # single image for Cloud Run
└── .planning/
```

### Structure Rationale

- **`core/`** replaces the `shared/` folder and all per-project copies. One file, no drift. The `shared/` folder is promoted because it already has the right files; only `assessment_downloader.py` and `assessment_analyzer.py` need to be added (they currently live in each project root and have diverged).
- **`reports/<type>/generator.py`** is the plugin. Each file is a subclass of `BaseReportGenerator`. Adding a new report type means creating one new subfolder. No other file changes.
- **`templates/<type>/`** mirrors the plugin structure so each generator can resolve its own templates by convention: `templates/{report_type}/`.
- **`data/<type>/`** isolates runtime data per report type so running `diagnosticos` never touches `ensayos_generales` data.
- **`entrypoints/`** unifies both execution modes. The `main.py` CLI and `webhook_service.py` both import the same core pipeline — they differ only in how they receive inputs (CLI args vs. HTTP POST) and how they queue work (immediate vs. Firestore batch).
- **`entrypoints/gcp/`** groups all GCP-specific infrastructure (Firestore, Cloud Tasks) together. This code is not imported by `main.py` (local mode), only by `webhook_service.py`.

---

## Plugin Interface Design

This is the central design decision. Every report generator must implement this interface.

### BaseReportGenerator (Abstract Base Class)

```python
# reports/base.py
from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


class BaseReportGenerator(ABC):
    """
    Contract every report plugin must fulfill.

    The pipeline runner calls generate_pdf() per student.
    The generator is responsible for loading its own templates
    and data files relative to its report_type.
    """

    @property
    @abstractmethod
    def report_type(self) -> str:
        """
        Unique identifier for this report type.
        Used to resolve templates/ and data/ subdirectories.
        Example: "diagnosticos", "ensayos_generales"
        """
        ...

    @property
    def assessment_types(self) -> list[str]:
        """
        List of assessment codes this report handles.
        Example: ["M1", "CL", "CIEN", "HYST"]
        Override in subclass.
        """
        return []

    @abstractmethod
    def generate_pdf(
        self,
        user_info: dict,
        analysis_result: dict,
        analysis_df: Optional[pd.DataFrame] = None,
    ) -> Optional[bytes]:
        """
        Generate a PDF report for one student.

        Args:
            user_info:       {"email": ..., "username": ..., "id": ...}
            analysis_result: per-user analysis dict from AssessmentAnalyzer
            analysis_df:     full analysis DataFrame (for incremental/webhook mode)

        Returns:
            PDF bytes if successful, None on failure.
        """
        ...

    def get_template_path(self, template_name: str) -> str:
        """Resolve template path by convention: templates/{report_type}/{name}"""
        return f"templates/{self.report_type}/{template_name}"

    def get_data_path(self, *parts: str) -> str:
        """Resolve data path by convention: data/{report_type}/{parts}"""
        return f"data/{self.report_type}/{'/'.join(parts)}"
```

### Plugin Registration

Use a simple registry dict in `reports/__init__.py`. No magic auto-discovery — explicit is better here because the number of report types is small and controlled.

```python
# reports/__init__.py
from reports.diagnosticos.generator import DiagnosticosReportGenerator
from reports.diagnosticos_uim.generator import DiagnosticosUimReportGenerator
from reports.ensayos_generales.generator import EnsayosGeneralesReportGenerator

REGISTRY: dict[str, type] = {
    "diagnosticos":      DiagnosticosReportGenerator,
    "diagnosticos_uim":  DiagnosticosUimReportGenerator,
    "ensayos_generales": EnsayosGeneralesReportGenerator,
}

def get_generator(report_type: str) -> "BaseReportGenerator":
    """Instantiate the correct generator for a report type."""
    cls = REGISTRY.get(report_type)
    if cls is None:
        raise ValueError(
            f"Unknown report type '{report_type}'. "
            f"Available: {list(REGISTRY.keys())}"
        )
    return cls()
```

Adding a new report type = create `reports/new_type/generator.py` + add one line to `REGISTRY`. Nothing else changes.

---

## How Local Mode and GCP Webhook Mode Share the Same Core

The key insight from reading the existing code: the pipeline steps (download → process → analyze → generate → deliver) are identical in both modes. Only the *trigger* and *queuing* differ.

```
LOCAL MODE                          GCP WEBHOOK MODE
──────────────────────────          ──────────────────────────
entrypoints/main.py                 entrypoints/webhook_service.py
    │                                   │
    │  argparse: --report X              │  POST /webhook (LearnWorlds event)
    │  --download --analyze --reports    │  → validate signature
    │                                    │  → extract assessment_type, user_email
    │                                    │  → queue in Firestore
    │                                    │  → schedule Cloud Task (15 min delay)
    │                                    │
    │                                    │  GET /process-batch?batch_id=X
    │                                    │  → batch_processor loads queue
    ▼                                    ▼
  PipelineRunner.run(                  PipelineRunner.run(
    report_type="diagnosticos",          report_type=assessment_type,
    mode="local",                        mode="webhook",
    assessment_type=args.assessment,     user_emails=[...from queue],
    user_emails=None,  # all users       incremental=True
    incremental=False                  )
  )
    │                                    │
    └──────────────┬─────────────────────┘
                   ▼
         core/assessment_downloader.py
         core/assessment_analyzer.py
         reports/<type>/generator.py
         core/email_sender.py
         core/drive_service.py
```

### PipelineRunner (the shared orchestrator)

```python
# entrypoints/pipeline_runner.py  (new file — extracts logic from each main.py)
from core.assessment_downloader import AssessmentDownloader
from core.assessment_analyzer import AssessmentAnalyzer
from core.email_sender import EmailSender
from core.drive_service import DriveService
from reports import get_generator


class PipelineRunner:
    def __init__(self, report_type: str):
        self.report_type = report_type
        self.generator = get_generator(report_type)
        self.downloader = AssessmentDownloader()
        self.analyzer = AssessmentAnalyzer()
        self.email_sender = EmailSender()
        self.drive_service = DriveService()

    def run(self, mode: str, assessment_type: str = None,
            user_emails: list = None, incremental: bool = False):
        """
        Full pipeline: download → process → analyze → generate → deliver.
        mode: "local" or "webhook"
        """
        downloaded = self.downloader.run(
            assessment_types=self.generator.assessment_types,
            filter_type=assessment_type,
            filter_emails=user_emails,
            incremental=incremental,
        )
        processed = self.downloader.to_csv(downloaded)
        analysis = self.analyzer.analyze(processed, self.report_type)

        for user_info in analysis["users"]:
            pdf_bytes = self.generator.generate_pdf(
                user_info=user_info,
                analysis_result=analysis["per_user"][user_info["email"]],
                analysis_df=analysis["df"],
            )
            if pdf_bytes:
                self.email_sender.send(user_info["email"], pdf_bytes)
                self.drive_service.upload_file_content(
                    pdf_bytes,
                    filename=f"resultados_{user_info['email']}.pdf",
                )
```

The `webhook_service.py` calls `PipelineRunner` from inside `batch_processor.process_batch()`. The local `main.py` calls it directly. Same class, same logic.

---

## Data Flow

### Local Mode (Manual Run)

```
LearnWorlds API
    ↓ (AssessmentDownloader — paginated GET requests)
data/{type}/raw/{assessment}.json
    ↓ (AssessmentDownloader.to_csv — filter, normalize)
data/{type}/processed/{assessment}.csv
    ↓ (AssessmentAnalyzer.analyze — lecture/skill/subject scoring)
data/{type}/analysis/{assessment}.csv
    ↓ (ReportGenerator.generate_pdf — HTML template + weasyprint)
PDF bytes (in memory)
    ├──→ EmailSender.send()  →  Student inbox
    └──→ DriveService.upload_file_content()  →  Google Drive folder
```

### GCP Webhook Mode (Incremental, Per-Student)

```
LearnWorlds → POST /webhook
    ↓ validate HMAC signature
    ↓ extract {assessment_type, user_email, assessment_id}
Firestore queue (student_data document)
    ↓ (15-minute delay via Cloud Tasks)
GET /process-batch?batch_id=X
    ↓ batch_processor loads all queued students
    ↓ for each student: AssessmentDownloader (incremental, filtered by email)
    ↓ AssessmentAnalyzer (incremental, filtered by email)
    ↓ ReportGenerator.generate_pdf()
PDF bytes (in memory)
    ├──→ EmailSender.send()
    └──→ DriveService.upload_file_content()
Firestore: clear processed students, reset batch state
```

### Key Data Flow Rules

1. **PDF bytes never touch disk** — they flow in memory from `generate_pdf()` to `email_sender` and `drive_service`. The existing code already does this correctly; the unified design preserves it.
2. **Templates are resolved by convention** — `templates/{report_type}/{name}.html`. The generator's `get_template_path()` helper enforces this.
3. **Analysis data is scoped per report type** — `data/{report_type}/analysis/` prevents cross-contamination between report runs.
4. **Incremental mode passes DataFrames in memory** — the webhook batch path passes `analysis_df` directly to `generate_pdf()` rather than re-reading files. This pattern already exists in `diagnosticos/report_generator.py` and must be preserved.

---

## Architectural Patterns

### Pattern 1: Template Method Pattern (pipeline steps)

**What:** `PipelineRunner.run()` defines the fixed sequence of steps. Each step delegates to a core service. The only variable is which `ReportGenerator` is plugged in.

**When to use:** The pipeline order (download → process → analyze → generate → deliver) never changes. Only the generation step varies per report type.

**Example:** See `PipelineRunner` above. `main.py` and `webhook_service.py` both call `runner.run()` with different arguments — they never re-implement pipeline steps.

### Pattern 2: Strategy Pattern (report generators as plugins)

**What:** `BaseReportGenerator` defines the interface; each report type provides its own implementation of `generate_pdf()`. The `REGISTRY` maps string keys to classes.

**When to use:** Each report type has substantially different rendering logic (the existing `diagnosticos/report_generator.py` has lecture-status tables; `ensayos_generales/report_generator.py` has question-answer comparison tables). Config-driven approaches cannot express this variation.

**Trade-off:** Adding a new report type requires a new Python file. This is intentional — it keeps each generator self-contained and testable, and avoids a sprawling config schema.

### Pattern 3: Lazy Service Initialization (GCP entry point)

**What:** The webhook service uses lazy initialization (`SERVICES_AVAILABLE` flag, `initialize_services()`) to avoid import-time failures when GCP environment variables are not yet set during cold start.

**When to use:** Any code that imports GCP libraries (`functions_framework`, `google-cloud-firestore`) must keep this pattern. Core pipeline code should NOT import GCP libraries.

**Example:** Already implemented in `diagnosticos/webhook_service.py` — preserve exactly.

---

## Anti-Patterns

### Anti-Pattern 1: Copy Entire Project for Each New Report Type

**What people do:** Duplicate the entire `diagnosticos/` folder, rename it, change a few files.

**Why it's wrong:** Creates 5-6 copies of `assessment_downloader.py`, `storage.py`, etc. Each copy diverges independently. The current codebase already has this problem — `assessment_downloader.py` exists in at least 5 locations with different versions.

**Do this instead:** Add a new subfolder under `reports/`, implement `BaseReportGenerator`, add one line to `REGISTRY`. Core files are shared, not duplicated.

### Anti-Pattern 2: `complete_deployment/` Subfolder Duplication

**What people do:** Maintain a `complete_deployment/` subfolder inside each project that is a near-copy of the parent with GCP-specific tweaks. Currently: `diagnosticos/complete_deployment/` and `diagnosticos_uim/complete_deployment/`.

**Why it's wrong:** Three-way drift: parent project, `complete_deployment/` copy, and the `shared/` folder. Any bug fix must be applied to all three. This is the most acute pain point in the current codebase.

**Do this instead:** A single `Dockerfile` and single `entrypoints/webhook_service.py` serve all report types. The report type is passed as an environment variable (`REPORT_TYPE=diagnosticos`) at Cloud Run deployment time. One image, multiple Cloud Run services.

### Anti-Pattern 3: Relative Imports Without `__init__.py`

**What people do:** Each project uses `from storage import StorageClient` (bare import), relying on Python finding the file in the same directory.

**Why it's wrong:** When `core/` becomes a package, bare imports break. Every file that currently does `from storage import StorageClient` must change to `from core.storage import StorageClient`.

**Do this instead:** Add `__init__.py` to `core/` and `reports/` from the start. Update all internal imports as part of migration, not after.

### Anti-Pattern 4: Assessment Mapper Logic Embedded in Webhook

**What people do:** `assessment_mapper.py` (maps LearnWorlds assessment URL → assessment type code) lives inside each project alongside `webhook_service.py`.

**Why it's wrong:** Each report type needs its own mapping (diagnosticos maps to M1/CL/CIEN/HYST; a future report type maps to different IDs). If the mapper is hardcoded globally, a single webhook can only serve one report type.

**Do this instead:** Move `assessment_mapper.py` into `reports/<type>/assessment_mapper.py`. The webhook reads `REPORT_TYPE` env var, instantiates the correct generator, which owns its own mapper.

---

## Build Order (Phase Dependencies)

These dependencies are hard — each layer must be in place before the next can be built.

```
Phase 1: Core foundation
    core/storage.py         ← promote from shared/storage.py
    core/drive_service.py   ← promote from shared/drive_service.py (already good)
    core/email_sender.py    ← promote from shared/email_sender.py
    core/slack_service.py   ← promote from shared/slack_service.py
    → No other component can use core/ until this is done

Phase 2: Plugin interface
    reports/base.py         ← define BaseReportGenerator ABC
    reports/__init__.py     ← REGISTRY (empty at first)
    → Must exist before any generator can be written

Phase 3: Core pipeline (biggest work — merging diverged files)
    core/assessment_downloader.py  ← reconcile 5 diverged versions
    core/assessment_analyzer.py    ← reconcile 5 diverged versions
    entrypoints/pipeline_runner.py ← new orchestrator
    → Must be done before any entry point works end-to-end

Phase 4: First migrated report type (diagnosticos — most complex, best test)
    reports/diagnosticos/generator.py    ← port from diagnosticos/report_generator.py
    reports/diagnosticos/assessment_mapper.py
    templates/diagnosticos/*.html
    data/diagnosticos/questions/*.csv
    → Proves the plugin pattern works before migrating others

Phase 5: Local entry point
    entrypoints/main.py             ← unified CLI using PipelineRunner
    → Can be done once Phase 3 + Phase 4 are working

Phase 6: GCP entry point
    entrypoints/webhook_service.py  ← port from diagnosticos/webhook_service.py
    entrypoints/gcp/firestore_service.py
    entrypoints/gcp/task_service.py
    entrypoints/gcp/batch_processor.py
    → Must come after Phase 5 (same pipeline_runner, different trigger)

Phase 7: Remaining report type migrations
    reports/diagnosticos_uim/generator.py
    reports/ensayos_generales/generator.py
    reports/assessment_analysis/generator.py
    → Each migration follows the pattern proven in Phase 4
```

**Critical path:** Phase 1 → Phase 2 → Phase 3 → Phase 4 → (Phase 5 and Phase 6 can overlap) → Phase 7.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| LearnWorlds API | REST, paginated GET, API key in header | `AssessmentDownloader` handles pagination; key from env var `LEARNWORLDS_API_KEY` |
| Google Drive | `google-api-python-client`, service account JSON (base64-encoded in env) | `DriveService` already handles shared drives and upsert; no changes needed |
| Gmail / SMTP | `smtplib` via `EmailSender` | Credentials from env vars |
| GCP Firestore | `google-cloud-firestore` | Only imported in `entrypoints/gcp/` — never in core or reports |
| GCP Cloud Tasks | `google-cloud-tasks` | Only imported in `entrypoints/gcp/` |
| weasyprint | In-process HTML-to-PDF | System dependency (requires libpango); already used by all generators |

### Internal Boundaries

| Boundary | Communication | Rule |
|----------|---------------|------|
| `core/` ↔ `reports/` | Direct Python import | Reports import from core; core never imports from reports |
| `core/` ↔ `entrypoints/` | Direct Python import | Entrypoints import from core; core never imports from entrypoints |
| `reports/` ↔ `entrypoints/` | Through `get_generator()` registry | Entrypoints never import a specific generator class directly |
| `entrypoints/gcp/` ↔ `entrypoints/main.py` | No coupling | GCP modules are never imported by the local CLI |
| `PipelineRunner` ↔ `BaseReportGenerator` | `generate_pdf()` contract only | Runner passes standardized dicts; generator interprets them |

---

## Scaling Considerations

This is a batch reporting system, not a high-concurrency web service. Scaling concerns are different.

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-400 students/batch | Current Cloud Run approach is sufficient; Firestore queue handles batching; 512MB RAM per instance |
| 400-1500 students/batch | Increase Cloud Run memory to 1-2GB; adjust `MAX_QUEUE_SIZE` env var; weasyprint is the bottleneck (PDF generation is CPU/memory-intensive) |
| Multiple concurrent report types | Deploy separate Cloud Run services, each with `REPORT_TYPE` env var set; they share the same Docker image |
| Local processing at scale | Pipeline runner supports `--assessment` filter to process one type at a time; no architectural change needed |

**First bottleneck:** weasyprint PDF generation is CPU and memory bound. At ~400 students, a single 512MB instance approaches its limit. Mitigation: increase Cloud Run memory before doing anything else.

**Second bottleneck:** LearnWorlds API rate limits on `AssessmentDownloader`. Mitigation: add exponential backoff (already partially present in existing code).

---

## Sources

- Direct code inspection: `diagnosticos/webhook_service.py` (GCP entry point pattern)
- Direct code inspection: `diagnosticos/report_generator.py` (multi-assessment-type plugin pattern)
- Direct code inspection: `ensayos_generales/report_generator.py` (simpler single-template plugin pattern)
- Direct code inspection: `shared/drive_service.py` (shared service pattern — already project-agnostic)
- Direct code inspection: `diagnosticos/main.py` (pipeline orchestration, CLI flags, incremental mode)
- Direct code inspection: `diagnosticos/firestore_service.py`, `task_service.py`, `batch_processor.py` (GCP queue architecture)
- Direct code inspection: project file tree (duplication evidence: 5+ copies of `assessment_downloader.py`, `storage.py`, etc.)
- Python ABC documentation: `abc.ABC`, `@abstractmethod` — standard library, HIGH confidence
- Python plugin registry pattern: explicit dict over auto-discovery (justified by small, controlled set of report types)

---

*Architecture research for: Plugin-based Python report pipeline (LearnWorlds assessment reports)*
*Researched: 2026-02-28*
