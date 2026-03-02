# Phase 2: Core Package - Research

**Researched:** 2026-02-28
**Domain:** Python package architecture, ABC plugin pattern, pandas 2.2.2 compatibility, flat-to-package import migration
**Confidence:** HIGH — primary findings verified against existing codebase + official documentation

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- `BaseReportGenerator` ABC defines a **fixed multi-step lifecycle**: `download()` -> `analyze()` -> `render()`, each overridable by report plugins
- `generate()` (or the final render step) returns a **file path** to the produced report on disk
- **Email sending is NOT part of the generator** — a separate PipelineRunner/entry point handles email delivery after report generation
- Plugin registry in `reports/__init__.py` uses **explicit imports** mapping report type name strings to generator classes
- Core `AssessmentAnalyzer` **keeps diagnosticos config as default** (diagnosticos is the canonical base for `_get_default_config`)
- Per-report **assessment ID env vars are loaded in each report module** — each `generator.py` defines its own `load_assessment_list_from_env()`
- **Ensayos generales keeps its own analyzer module** in `reports/ensayos_generales/` as a report-specific helper
- Data directories **auto-created at runtime** — no pre-created dirs or .gitkeep files
- Each report type is a **package directory**: `reports/<type>/__init__.py`, `reports/<type>/generator.py`, etc.
- `core/__init__.py` does **NOT re-export classes** — all imports are explicit
- Files **copied as-is to core/, only fixing import paths** — no refactoring during promotion
- **All shared/ files promoted**: storage.py, email_sender.py, drive_service.py, slack_service.py, upload_folder_to_gcs.py
- Core versions built from **best copy per Phase 1 merge decisions**, not from the dead `shared/` folder
- `shared/` folder **deleted in Phase 2**

### Claude's Discretion

- Exact `generate()` return type details (file path string vs Path object)
- `BaseReportGenerator.__init__` signature and what common state it initializes
- How `PipelineRunner` orchestrates the lifecycle steps (Phase 4 concern but base class should anticipate it)
- Registry population approach (explicit dict vs explicit imports in `__init__.py`)
- Whether `upload_folder_to_gcs.py` becomes a class or stays a script-style module in core/
- Internal organization of core/ (single flat directory vs sub-packages)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CORE-02 | Unified `core/assessment_downloader.py` canonical version reconciling all diverged methods | Method matrix and resolution decisions in MERGE-DECISIONS.md are complete — copy-merge per decisions, fix import paths |
| CORE-03 | Unified `core/assessment_analyzer.py` canonical version reconciling all diverged methods | Same pattern as CORE-02; diagnosticos is base for all methods |
| CORE-04 | `core/` package includes canonical storage.py, email_sender.py, drive_service.py promoted from shared/ | Flat import fix is the entire task — `from storage import` → `from core.storage import` |
| CORE-05 | All project files use package imports — no bare flat-directory imports remain | Import rewrite pattern documented in Code Examples section |
| PLUG-01 | `BaseReportGenerator` ABC in `reports/base.py` with `generate()` returning file path | ABC pattern with `@abstractmethod` for `download()`, `analyze()`, `render()` — examples below |
| PLUG-03 | Explicit plugin registry dict mapping report type strings to generator classes | Explicit dict in `reports/__init__.py` — simpler and type-safe, examples below |
| ORG-01 | Templates organized under `templates/<report_type>/` | Directory rename only — no code change needed |
| ORG-02 | Runtime data namespaced per report type under `data/<report_type>/` | `os.makedirs(..., exist_ok=True)` at runtime; path helpers in `BaseReportGenerator` |
| ORG-03 | Per-report-type duplicate email suppression at `data/<report_type>/processed_emails.csv` | Path helper in base class; CSV-based tracking pattern already established |

</phase_requirements>

---

## Summary

Phase 2 involves three distinct technical operations: (1) assembling the canonical `core/` package by copying-and-merging from 6 source copies per MERGE-DECISIONS.md, (2) creating the `BaseReportGenerator` ABC and plugin registry scaffold in `reports/`, and (3) migrating all flat bare imports to `from core.X import Y` package imports across the codebase. These operations are well-understood and low-risk individually, but the import migration (CORE-05) is a broad find-and-replace across every .py file in the project that requires care to avoid partial migrations.

The primary technical risk is the **pandas 2.x breaking changes concern** flagged in STATE.md. Code review of the existing diagnosticos and ensayos_generales source confirms: all `.append()` calls are on Python lists, not DataFrames — the codebase already uses `pd.concat([df, pd.DataFrame([row])], ignore_index=True)` for row-append operations. No `DataFrame.append()` calls were found. The remaining pandas 2.x concern is `FutureWarning` for `.fillna()` downcasting behavior in 2.2.x — this is a warning, not an error, at 2.2.2 and becomes breaking only in 3.0. It does not block Phase 2.

The `BaseReportGenerator` ABC lifecycle (`download()` -> `analyze()` -> `render()`) matches the established pattern in all existing report modules. The ABC should use `@abstractmethod` for all three lifecycle methods. The `generate()` orchestration method should be concrete in the base class (calling the three abstract methods in order), providing the hook-based extension model that makes dry-run and email-gating trivial for Phase 4.

**Primary recommendation:** Build core/ by mechanical copy-merge per MERGE-DECISIONS.md, fix all imports with grep/sed, then scaffold the ABC and registry. Do not refactor business logic during promotion — fix paths only. Validate pandas 2.2.2 compatibility after assembly with a smoke test of `analyze_assessment_from_csv()`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `abc` | 3.x built-in | `ABC`, `abstractmethod` decorators for `BaseReportGenerator` | Built-in; no dependency; the only correct tool for enforcing interface contracts |
| Python stdlib `pathlib` | 3.x built-in | `Path` objects for file path returns and directory creation | Preferred over `os.path` since Python 3.6; works with all stdlib and third-party APIs that accept `os.PathLike` |
| Python stdlib `os` | 3.x built-in | `os.makedirs(..., exist_ok=True)` for runtime data dir creation | Race-condition-safe directory creation; one-liner |
| python-dotenv | `==0.*` | `load_dotenv()` for per-report `.env` file loading | Project decision — already in all requirements.txt |
| pandas | `==2.2.2` | DataFrame operations in downloader and analyzer | Exact production pin from complete_deployment/ — must match |
| numpy | `==1.26.4` | pandas companion pin for stable ABI | Required by pandas 2.2.2 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typing | stdlib | `Dict`, `Any`, `List`, `Optional`, `Union`, `Type` type hints | All public method signatures in core/ |
| google-cloud-storage | `==2.*` | GCS backend in StorageClient | When `STORAGE_BACKEND=gcs` |
| google-api-python-client | `==2.*` | Google Drive API in DriveService | When Drive upload is used |
| google-auth | `==2.*` | Service account auth for Drive and GCS | All GCP operations |
| smtplib | stdlib | SMTP email sending in EmailSender | Email delivery in PipelineRunner (Phase 4) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `abc.ABC` + `@abstractmethod` | Protocol (PEP 544) | Protocol is structural (duck-typed); ABC is nominal — ABC is correct here because we want an explicit inheritance contract that enforces implementation at class definition time, not at call time |
| Explicit registry dict | Metaclass auto-registration | Metaclass is more complex and opaque; explicit dict in `reports/__init__.py` is transparent, version-controllable, and requires a deliberate edit to add a new report type — this is desirable for a single-developer internal tool |
| Explicit registry dict | `pkg_resources` entry points | Entry points are for third-party plugin distribution; this project has 5 known report types in a single repo — entry points are YAGNI |
| `pathlib.Path` return | `str` return | Both work; `Path` is the modern standard and is accepted everywhere `str` was; use `Path` for new code, be consistent |
| `os.makedirs(exist_ok=True)` | Check-then-create | `makedirs(exist_ok=True)` is atomic — no race condition. Check-then-create has a TOCTOU race |

**Installation:**
```bash
pip install -r requirements.txt
```
(Requirements already defined in MERGE-DECISIONS.md Section 5)

---

## Architecture Patterns

### Recommended Project Structure

```
reportes/
├── core/
│   ├── __init__.py                  # Empty — no re-exports
│   ├── assessment_downloader.py     # Canonical merged version
│   ├── assessment_analyzer.py       # Canonical merged version
│   ├── storage.py                   # Promoted from shared/
│   ├── email_sender.py              # Promoted from shared/
│   ├── drive_service.py             # Promoted from shared/
│   ├── slack_service.py             # Promoted from shared/
│   └── upload_folder_to_gcs.py      # Promoted from shared/
├── reports/
│   ├── __init__.py                  # REGISTRY dict only
│   ├── base.py                      # BaseReportGenerator ABC
│   └── diagnosticos/                # Example report package
│       ├── __init__.py              # Empty
│       └── generator.py             # Extends BaseReportGenerator
├── templates/
│   └── <report_type>/               # Templates per report type
├── data/
│   └── <report_type>/               # Auto-created at runtime
│       ├── raw/
│       ├── processed/
│       ├── analysis/
│       ├── questions/
│       └── processed_emails.csv
├── shared/                          # DELETED in Phase 2
├── requirements.txt                 # Unified requirements
└── .env.example                     # From MERGE-DECISIONS.md Section 6
```

### Pattern 1: BaseReportGenerator ABC

**What:** Abstract base class with a fixed `download()` -> `analyze()` -> `render()` lifecycle. Concrete `generate()` method orchestrates the lifecycle and returns the output file path. Each step is independently overridable.

**When to use:** Every report type extends this. The base class handles common state (report_type, data dirs, storage), enforces the lifecycle contract, and provides path helper methods.

**Example:**
```python
# core/reports/base.py — canonical pattern for this project
import os
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class BaseReportGenerator(ABC):
    """
    Abstract base class for all report generators.

    Subclasses MUST implement: download(), analyze(), render()
    Subclasses MAY override: generate() (not recommended)

    The generate() method calls the three lifecycle steps in order
    and returns the path to the produced report file.
    """

    def __init__(self, report_type: str):
        """
        Initialize with report type string.
        Sets up data directory paths and ensures directories exist at runtime.

        Args:
            report_type: String identifier matching the REGISTRY key
                         (e.g., "diagnosticos", "diagnosticos_uim")
        """
        self.report_type = report_type

        # Per-report namespaced data paths
        self.data_dir = Path("data") / report_type
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.analysis_dir = self.data_dir / "analysis"
        self.questions_dir = self.data_dir / "questions"

        # Per-report template path
        self.templates_dir = Path("templates") / report_type

        # Processed emails tracking (per-report deduplication)
        self.processed_emails_path = self.data_dir / "processed_emails.csv"

        # Ensure runtime directories exist
        self._ensure_data_dirs()

    def _ensure_data_dirs(self) -> None:
        """Create data directories at runtime if they don't exist."""
        for directory in [self.raw_dir, self.processed_dir,
                          self.analysis_dir, self.questions_dir]:
            os.makedirs(directory, exist_ok=True)

    @abstractmethod
    def download(self) -> Any:
        """
        Download raw assessment responses from LearnWorlds API.

        Returns:
            Implementation-defined — typically a list of responses or DataFrame
        """
        ...

    @abstractmethod
    def analyze(self, download_result: Any) -> Any:
        """
        Analyze downloaded assessment data.

        Args:
            download_result: Output from download()

        Returns:
            Implementation-defined — typically a DataFrame or analysis dict
        """
        ...

    @abstractmethod
    def render(self, analysis_result: Any) -> Path:
        """
        Render report file(s) from analysis data.

        Args:
            analysis_result: Output from analyze()

        Returns:
            Path to the produced report file on disk
        """
        ...

    def generate(self) -> Path:
        """
        Orchestrate the full pipeline: download -> analyze -> render.

        Returns:
            Path to the produced report file on disk.
            Callers (PipelineRunner) use this path for email attachment.
        """
        logger.info(f"[{self.report_type}] Starting report generation")

        download_result = self.download()
        logger.info(f"[{self.report_type}] Download complete")

        analysis_result = self.analyze(download_result)
        logger.info(f"[{self.report_type}] Analysis complete")

        output_path = self.render(analysis_result)
        logger.info(f"[{self.report_type}] Report rendered: {output_path}")

        return output_path
```

### Pattern 2: Plugin Registry

**What:** A plain dict in `reports/__init__.py` mapping string keys to generator classes. Import-time registration — no magic, no discovery.

**When to use:** Always. The registry is the single point of extension for adding new report types.

**Example:**
```python
# reports/__init__.py
from typing import Dict, Type
from reports.base import BaseReportGenerator

# Import each generator explicitly — adding a new report type means adding one line here
from reports.diagnosticos.generator import DiagnosticosGenerator

REGISTRY: Dict[str, Type[BaseReportGenerator]] = {
    "diagnosticos": DiagnosticosGenerator,
    # Phase 3+ adds: "diagnosticos_uim": DiagnosticosUimGenerator, etc.
}


def get_generator(report_type: str) -> Type[BaseReportGenerator]:
    """
    Look up a generator class by report type string.

    Args:
        report_type: String key from REGISTRY

    Returns:
        Generator class (not instance) for the requested report type

    Raises:
        KeyError: if report_type is not registered
    """
    if report_type not in REGISTRY:
        available = list(REGISTRY.keys())
        raise KeyError(
            f"Unknown report type '{report_type}'. "
            f"Available types: {available}"
        )
    return REGISTRY[report_type]
```

### Pattern 3: Package Import Migration (CORE-05)

**What:** All existing `from storage import StorageClient` bare imports become `from core.storage import StorageClient`. This applies to every .py file in every report project directory.

**When to use:** During Phase 2 import fix pass — systematic grep-and-replace for all bare imports.

**Bare imports to replace (complete list):**
```
from storage import          → from core.storage import
from email_sender import     → from core.email_sender import
from drive_service import    → from core.drive_service import
from slack_service import    → from core.slack_service import
from assessment_downloader import → from core.assessment_downloader import
from assessment_analyzer import   → from core.assessment_analyzer import
import storage               → import core.storage as storage (rare case)
```

**Example migration:**
```python
# Before (flat import — only works when CWD = the flat project directory)
from storage import StorageClient
from assessment_downloader import AssessmentDownloader

# After (package import — works from any CWD with the package on sys.path)
from core.storage import StorageClient
from core.assessment_downloader import AssessmentDownloader
```

### Pattern 4: Runtime Data Directory Creation

**What:** `os.makedirs(path, exist_ok=True)` called in `BaseReportGenerator.__init__()` creates `data/<report_type>/raw/`, `processed/`, `analysis/`, `questions/` on first run.

**Why:** Avoids committing empty directories with .gitkeep, avoids `FileNotFoundError` on first run, handles concurrent processes safely (exist_ok=True is atomic).

**Example:**
```python
# Correct — atomic, no race condition
os.makedirs(self.raw_dir, exist_ok=True)

# Wrong — TOCTOU race condition
if not os.path.exists(self.raw_dir):
    os.makedirs(self.raw_dir)
```

### Pattern 5: Per-Report Env Loading

**What:** Each report's `generator.py` calls `load_dotenv()` for its own `.env` file and defines its own `load_assessment_list_from_env()`.

**Why:** Locked decision from CONTEXT.md — assessment ID env var names are per-report and cannot be unified.

**Example:**
```python
# reports/diagnosticos/generator.py
import os
from dotenv import load_dotenv
from core.assessment_downloader import AssessmentDownloader
from reports.base import BaseReportGenerator

load_dotenv()  # Loads .env from CWD (or path can be explicit)


def load_assessment_list_from_env():
    """Load diagnosticos-specific assessment IDs from environment."""
    assessments = []
    for name, env_var in [
        ("M1", "M1_ASSESSMENT_ID"),
        ("CL", "CL_ASSESSMENT_ID"),
        ("CIEN", "CIEN_ASSESSMENT_ID"),
        ("HYST", "HYST_ASSESSMENT_ID"),
    ]:
        assessment_id = os.getenv(env_var)
        if assessment_id:
            assessments.append({"name": name, "assessment_id": assessment_id})
    return assessments


class DiagnosticosGenerator(BaseReportGenerator):
    def __init__(self):
        super().__init__("diagnosticos")
        # Report-specific initialization here
```

### Anti-Patterns to Avoid

- **Bare imports in core/ itself:** `from storage import StorageClient` inside `core/assessment_downloader.py` is wrong — must be `from core.storage import StorageClient` after promotion.
- **Re-exporting from `core/__init__.py`:** Do NOT add `from core.storage import StorageClient` to `core/__init__.py`. All imports must be explicit: `from core.storage import StorageClient`.
- **`report_type` hardcoded inside generator:** The report type string must flow from the REGISTRY key through `BaseReportGenerator.__init__()` — never hardcode it in a subclass method.
- **Lazy directory creation (creating dirs in methods, not `__init__`):** Creates `FileNotFoundError` if a method is called before the directory is created. Create all dirs in `_ensure_data_dirs()` from `__init__`.
- **`df.append()` pattern:** This was removed in pandas 2.0. Use `pd.concat([df, pd.DataFrame([row])], ignore_index=True)`. NOTE: Code review confirms no `DataFrame.append()` calls exist in the current codebase — this is already clean.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Abstract interface enforcement | Custom `raise NotImplementedError` in base | `abc.ABC` + `@abstractmethod` | ABCs raise `TypeError` at class instantiation time (not at method call time) — catches missing implementations before any code runs |
| Recursive directory creation | Manual `os.path.exists()` check + `os.mkdir()` | `os.makedirs(path, exist_ok=True)` | Atomic, race-condition-safe, creates all intermediate parents |
| Plugin lookup with fallback | Custom if-else chains or switch on string | Plain `dict` with `KeyError` on miss | `dict.get()` / `dict[]` is O(1), readable, and the error message can be informative |
| Import path rewriting | Manual sed/grep/replace scripts | Systematic grep for each pattern + verify with `python -c "from core.storage import StorageClient"` | The import list is finite and known; scripted replacement with per-file verification is sufficient |
| Env var loading | Custom `.env` file parser | `python-dotenv` `load_dotenv()` | Already in all requirements.txt; handles override behavior, encoding, and multi-line values |

**Key insight:** The core challenge in this phase is organizational (correct file placement, correct imports, correct boundary rules) not algorithmic. Custom solutions add complexity without solving a real problem.

---

## Common Pitfalls

### Pitfall 1: Circular Import in core/

**What goes wrong:** `core/email_sender.py` imports `from core.storage import StorageClient`. If `core/__init__.py` tried to import everything (which it must NOT), a circular dependency would occur. Even with an empty `__init__.py`, if `core/assessment_downloader.py` and `core/assessment_analyzer.py` both import `from core.storage import StorageClient`, there is no circular dependency — they are leaf consumers of storage.

**Why it happens:** Developers add re-exports to `__init__.py` "for convenience" and create import cycles.

**How to avoid:** `core/__init__.py` stays empty. All imports are explicit point-to-point: `from core.storage import StorageClient`.

**Warning signs:** `ImportError: cannot import name 'X' from partially initialized module 'core'`.

### Pitfall 2: StorageClient Backend String Bug

**What goes wrong:** `shared/storage.py` checks `if self.backend == 'gcp':` but the env var documentation shows `STORAGE_BACKEND=gcs`. The check is `'gcp'` but the documented value is `'gcs'` — this means the GCS backend never actually activates when using the env var.

**Why it happens:** The shared/ copy has a typo. The working copies in each project directory may have fixed this inconsistently.

**How to avoid:** When promoting `storage.py` to `core/`, verify the canonical source copy uses `'gcs'` consistently (matching the env var documentation). Check the production copy in `diagnosticos/complete_deployment/storage.py` — it is the source of truth.

**Warning signs:** GCS uploads silently fall back to local storage with no error.

### Pitfall 3: GOOGLE_CLOUD_PROJECT Env Var Collision

**What goes wrong:** The `diagnosticos/` and `diagnosticos_uim/` source code reads `GOOGLE_CLOUD_PROJECT` for the GCP project ID. On Cloud Run, the runtime automatically sets `GOOGLE_CLOUD_PROJECT` to the current project. If the application also sets this variable in `.env`, the runtime value overwrites the application's value — silently using the wrong project ID.

**Why it happens:** Naming conflict between GCP runtime-injected variable and application variable.

**How to avoid:** MERGE-DECISIONS.md Section 6 mandates `GCP_PROJECT_ID` as the canonical name. During Phase 2, update all `os.getenv('GOOGLE_CLOUD_PROJECT')` calls in diagnosticos and diagnosticos_uim source files to `os.getenv('GCP_PROJECT_ID')`.

**Warning signs:** Cloud Firestore or Cloud Tasks operations fail with "project not found" errors only when deployed to Cloud Run (not locally).

### Pitfall 4: Import Path Not Updated Inside Promoted Files

**What goes wrong:** `core/email_sender.py` still contains `from storage import StorageClient` (the old bare import). The file was copied to `core/` but its internal import was not fixed.

**Why it happens:** Phase 2 involves two separate passes: (A) copy files to `core/`, and (B) fix all imports. If pass B is not applied to the files created in pass A, the internal imports inside `core/` remain broken.

**How to avoid:** After assembling `core/`, run: `grep -r "^from storage\|^from email_sender\|^from drive_service\|^from assessment_downloader\|^from assessment_analyzer" core/` — the result MUST be empty. Any match is a broken import.

**Warning signs:** `ModuleNotFoundError: No module named 'storage'` when running from the repo root.

### Pitfall 5: pandas 2.2.2 FutureWarnings Treated as Errors

**What goes wrong:** `analyze_assessment_from_csv()` uses `.fillna()` on object dtype columns. pandas 2.2.x emits a `FutureWarning` about downcasting. If the runtime environment has `PYTHONWARNINGS=error` or `warnings.filterwarnings("error")` set, this warning becomes an exception and aborts analysis.

**Why it happens:** pandas 2.2.x deprecates automatic dtype downcasting in `.fillna()`. This becomes a hard error in pandas 3.0.

**How to avoid:** Do not suppress warnings globally. After assembling `core/assessment_analyzer.py`, run a smoke test. If `FutureWarning` appears, fix with explicit casting: `df[col] = df[col].fillna(default).infer_objects(copy=False)`. At pandas 2.2.2, these are warnings only — not breaking.

**Warning signs:** `FutureWarning: Downcasting object dtype arrays on .fillna, .ffill, .bfill is deprecated`.

### Pitfall 6: Partial Merge — Missing Methods

**What goes wrong:** `core/assessment_downloader.py` is assembled from the diagnosticos base, but methods that only exist in ensayos_generales (`download_users`, `save_temp_responses_to_csv`, `get_temp_csv_file_path`, etc.) are not added.

**Why it happens:** The implementer copies the diagnosticos file and stops, missing the "also include from eg" additions listed in MERGE-DECISIONS.md Section 2.

**How to avoid:** Use MERGE-DECISIONS.md Section 2 as a checklist. Every row with `Destination = core/` and a non-diagnosticos `Canonical Base` is a method that must be added from a secondary source. Count the methods in the assembled `core/assessment_downloader.py` against the method matrix row count.

**Warning signs:** Method matrix has 36 rows with `Destination = core/`; the assembled file has fewer methods.

---

## Code Examples

Verified patterns from official sources and existing codebase:

### ABC Definition (Python stdlib abc)
```python
# Source: https://docs.python.org/3/library/abc.html
from abc import ABC, abstractmethod

class BaseReportGenerator(ABC):
    @abstractmethod
    def download(self) -> Any:
        ...

    @abstractmethod
    def analyze(self, download_result: Any) -> Any:
        ...

    @abstractmethod
    def render(self, analysis_result: Any) -> Path:
        ...

    # Concrete method — NOT abstract — enforces lifecycle order
    def generate(self) -> Path:
        return self.render(self.analyze(self.download()))
```

### TypeError at Class Definition (ABC enforcement)
```python
# ABC raises TypeError when instantiated WITHOUT implementing abstract methods
# This happens at instantiation, not at method call time

class BadGenerator(BaseReportGenerator):
    pass  # Missing download(), analyze(), render()

gen = BadGenerator()  # Raises: TypeError: Can't instantiate abstract class BadGenerator
                      # without an implementation for abstract methods 'analyze', 'download', 'render'
```

### Explicit Registry Lookup
```python
# reports/__init__.py
from reports.diagnosticos.generator import DiagnosticosGenerator

REGISTRY = {
    "diagnosticos": DiagnosticosGenerator,
}

# Usage at call site
generator_class = REGISTRY["diagnosticos"]  # Returns the class, not an instance
generator = generator_class()               # Instantiate — TypeError if ABC not implemented
output_path = generator.generate()          # Run the pipeline
```

### Runtime Directory Creation
```python
# Pattern: create all needed dirs in __init__ — never create lazily in methods
import os
from pathlib import Path

class BaseReportGenerator(ABC):
    def __init__(self, report_type: str):
        self.report_type = report_type
        self.data_dir = Path("data") / report_type
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.analysis_dir = self.data_dir / "analysis"
        self.questions_dir = self.data_dir / "questions"
        self._ensure_data_dirs()

    def _ensure_data_dirs(self) -> None:
        for d in [self.raw_dir, self.processed_dir, self.analysis_dir, self.questions_dir]:
            os.makedirs(d, exist_ok=True)
```

### Package Import Pattern (after migration)
```python
# All imports across the unified codebase use this form:
from core.storage import StorageClient
from core.assessment_downloader import AssessmentDownloader
from core.assessment_analyzer import AssessmentAnalyzer
from core.email_sender import EmailSender
from core.drive_service import DriveService

# core/__init__.py is EMPTY — no re-exports
```

### Import Fix Verification Command
```bash
# Run from repo root after assembling core/ and fixing imports.
# Output MUST be empty — any match is a broken bare import.
grep -r "^from storage import\|^from email_sender import\|^from drive_service import\|^from assessment_downloader import\|^from assessment_analyzer import" core/ reports/
```

### pandas 2.2.2 — Safe Row Accumulation (already in codebase)
```python
# This pattern is ALREADY used in diagnosticos/main.py — no change needed
# pd.concat replaces the removed DataFrame.append()
import pandas as pd

# Build list of dicts, create DataFrame once — already the pattern in use
rows = []
for record in records:
    rows.append({"col1": record["a"], "col2": record["b"]})
df = pd.DataFrame(rows)

# If appending to existing DataFrame (also in use):
df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `DataFrame.append()` | `pd.concat([df, pd.DataFrame([row])], ignore_index=True)` | pandas 2.0 (April 2023) — removed | ALREADY FIXED in existing codebase — no action needed |
| Flat directory imports (`from storage import`) | Package imports (`from core.storage import`) | This phase | Requires systematic import rewrite across all project files |
| `.gitkeep` empty directory files | `os.makedirs(exist_ok=True)` at runtime | This phase | No pre-created dirs in repo |
| `GOOGLE_CLOUD_PROJECT` env var | `GCP_PROJECT_ID` env var | This phase (MERGE-DECISIONS.md decision) | Avoids Cloud Run runtime variable collision |

**Deprecated/outdated:**
- `cleanup_incremental_files`: Renamed to `cleanup_temp_files` per MERGE-DECISIONS.md Section 2. All callers must use the new name.
- `shared/` folder: Deleted in Phase 2 — all its files are promoted to `core/` with import paths fixed.

---

## Open Questions

1. **StorageClient backend string: `'gcp'` vs `'gcs'`**
   - What we know: `shared/storage.py` checks `if self.backend == 'gcp':` but `.env.example` documents `STORAGE_BACKEND=local` or `STORAGE_BACKEND=gcs`
   - What's unclear: Whether the production copies in `diagnosticos/complete_deployment/storage.py` use `'gcs'` (the env var value) or `'gcp'` (the check string)
   - Recommendation: During CORE-04 task, verify `diagnosticos/complete_deployment/storage.py` (the production canonical source) and use whichever string it uses for the `if self.backend ==` check

2. **`Path` vs `str` for `generate()` return type**
   - What we know: Both work with weasyprint, docxtpl, and smtplib. Claude's Discretion area per CONTEXT.md.
   - What's unclear: Whether existing callers in Phase 4 scope (PipelineRunner) will need `str` specifically
   - Recommendation: Return `pathlib.Path` — it is the modern standard, accepted by all relevant libraries, and can always be coerced to `str` with `str(path)` at call sites that need it

3. **`upload_folder_to_gcs.py` — class or module?**
   - What we know: It is a script-style utility in `shared/`, never used by any report. Claude's Discretion per CONTEXT.md.
   - What's unclear: Whether Phase 5 will use it as-is or refactor
   - Recommendation: Promote as-is to `core/upload_folder_to_gcs.py` without refactoring (consistent with the "copy as-is, fix imports only" decision)

---

## Validation Architecture

The config.json does not have a `workflow.nyquist_validation` key. The project uses `"workflow": {"research": true, "plan_check": true, "verifier": true}` — no automated test framework is configured or in use.

**Existing test files:** The files named `test_webhook.py` and `test_function.py` in diagnosticos/ and diagnosticos_uim/ are Cloud Functions stubs, not pytest test cases. There is no pytest infrastructure (no `pytest.ini`, no `conftest.py`, no `tests/` directory).

**Phase 2 verification approach:** Manual smoke tests are the only feasible validation:
- After assembling `core/`, verify no bare imports remain (grep command in Code Examples)
- After import migration, run `python -c "from core.storage import StorageClient"` etc. for each module
- Verify ABC enforcement: `python -c "from reports.base import BaseReportGenerator; BaseReportGenerator()"` must raise `TypeError`

---

## Sources

### Primary (HIGH confidence)
- Existing codebase — `diagnosticos/assessment_analyzer.py`, `diagnosticos/assessment_downloader.py`, `diagnosticos/main.py`, `ensayos_generales/assessment_analyzer.py`, `shared/storage.py`, `shared/email_sender.py`, `shared/drive_service.py` — direct code inspection
- `.planning/phases/01-consolidation-audit/MERGE-DECISIONS.md` — authoritative method decision source
- `.planning/phases/02-core-package/02-CONTEXT.md` — locked user decisions
- [Python stdlib `abc` module docs](https://docs.python.org/3/library/abc.html) — ABC and abstractmethod patterns
- [Python stdlib `os.makedirs` docs](https://docs.python.org/3/library/os.html) — exist_ok parameter

### Secondary (MEDIUM confidence)
- [pandas 2.0.0 What's New](https://pandas.pydata.org/docs/dev/whatsnew/v2.0.0.html) — DataFrame.append removal confirmed
- [pandas 2.2.0 What's New](https://pandas.pydata.org/pandas-docs/stable/whatsnew/v2.2.0.html) — fillna FutureWarning details
- [python-dotenv PyPI](https://pypi.org/project/python-dotenv/) — load_dotenv behavior
- [pathlib official docs](https://docs.python.org/3/library/pathlib.html) — Path vs str guidance

### Tertiary (LOW confidence)
- None — all claims verified against primary or secondary sources.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in requirements.txt; versions pinned in MERGE-DECISIONS.md
- Architecture: HIGH — ABC pattern verified against Python docs; registry pattern is straightforward dict; patterns derived from existing code structure
- Pitfalls: HIGH for import/pandas issues (verified in code); MEDIUM for StorageClient backend string bug (shared/ copy has the issue but production copy status needs confirmation)

**Research date:** 2026-02-28
**Valid until:** 2026-05-28 (stable libraries; pandas 2.2.2 is pinned; no fast-moving dependencies)
