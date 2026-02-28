# Feature Research

**Domain:** Internal report pipeline framework (Python, plugin-based, GCP + local)
**Researched:** 2026-02-28
**Confidence:** HIGH — based on direct analysis of 5 existing production codebases

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that must exist or the framework is broken for its purpose. Every existing project already implements these — they are the baseline that must survive migration unchanged.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Pluggable report generator interface | Core value: new reports = new module only. Without a consistent interface, each report type requires framework-level knowledge | MEDIUM | Requires agreed protocol: `generate(student_data) -> bytes`. Exists today as ad-hoc class per project; needs standardization |
| Unified entry point accepting `--report-type` | Without this, the framework is just multiple projects in one folder. Callers (manual + GCP) need one command surface | LOW | `python main.py --report diagnosticos --download --reports` pattern already proven in existing code |
| Shared core services (`assessment_downloader`, `assessment_analyzer`, `storage`, `email_sender`, `drive_service`) | All 5 projects use all of these — they are the pipeline infrastructure, not project-specific logic | MEDIUM | Already partially in `shared/`. Problem is projects have drifted local copies. Needs canonical single-source versions |
| Template-per-report-type organization | Each report type has distinct docx/HTML templates. Without organized storage these become unmanageable | LOW | A `templates/<report_type>/` directory structure. Currently templates are scattered inside each project folder |
| Duplicate email suppression (processed_emails tracking) | Already implemented in `diagnosticos/send_emails.py` with `processed_emails.csv`. Re-sending reports to students who already received them is a real operational failure | LOW | CSV-based tracking already works. Needs to move to shared core — currently duplicated per project |
| LearnWorlds API download (`assessment_downloader`) | All GCP projects are triggered by LearnWorlds webhooks and download assessment responses. Non-negotiable for any report type in this system | HIGH | Most complex shared service. Has per-project drift with different functions. Single canonical version needed |
| Data analysis pipeline (`assessment_analyzer`) | Converts raw LearnWorlds response data into per-student analysis CSVs. Required upstream of every report generator | HIGH | Also drifted across projects. Must consolidate |
| Email delivery with PDF attachment | Reports are delivered via email. Without this the pipeline output goes nowhere | LOW | SMTP via `email.message.EmailMessage` + Gmail. Configuration from `.env`. Already works across projects |
| Environment-based configuration (`.env`) | All credentials (API keys, SMTP, GCP project ID, assessment IDs) must not be hardcoded | LOW | All projects use `python-dotenv`. Pattern is established |
| Incremental processing mode | Only process new responses since last run. Without this, every GCP run would re-process all historical data and re-send emails | MEDIUM | `--incremental` flag pattern exists in diagnosticos. Merges temp files into main JSON after processing |

### Differentiators (Competitive Advantage)

Features that go beyond the baseline. These improve developer experience, reduce operational risk, or make the framework more maintainable. Not all are needed for MVP.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Report plugin registry / autodiscovery | Instead of hardcoding report type names in main.py, discover available plugins from `reports/` directory automatically. New report = drop a module in, zero changes to core | MEDIUM | LOW priority for v1 — explicit registration (a simple dict or list) is simpler and equally extensible for small N of report types. Autodiscovery adds complexity with minimal benefit until there are 10+ types |
| Single `Dockerfile` / `cloudbuild.yaml` for all report types | Today each GCP project has its own `complete_deployment/` subfolder duplicating the entire codebase. A single deployment artifact reduces drift and deployment errors | MEDIUM | This is a strong differentiator — eliminates the `complete_deployment/` copy problem. GCP Cloud Run can accept a `--report-type` env var at deploy time |
| Structured per-run result dict (consistent return schema) | Currently each project returns ad-hoc dicts from operations. A consistent `{success, records_processed, emails_sent, errors[]}` schema across all operations enables monitoring | LOW | Low effort, high value. Already partially present — just needs standardization across all operations |
| Health/status endpoint for GCP deployments | `diagnosticos/webhook_service.py` already has a `/status` endpoint. Making this available in all GCP-deployed report types adds observability without per-project work | LOW | Reuse existing pattern. Route: `GET /status` returns queue depth, batch state, assessment mapping info |
| Dry-run mode | `assessment-analysis-project/main.py` already has `--dry-run`. Useful for validation without side effects. Should be a first-class option in the unified entry point | LOW | Prevents accidental re-processing or email storms during development |
| Test mode (redirect emails to TEST_EMAIL) | `diagnosticos/send_emails.py` already has `--test-email`. Redirects all outgoing emails to a single address. Critical for safe development iteration | LOW | Already works. Just needs to be part of shared email_sender interface consistently |
| Slack error notifications | `shared/slack_service.py` exists but is inconsistently used across projects. Centralizing error notification routing via shared core would give operational visibility | LOW | Existing code is already there. Wire it into the shared pipeline error handler |
| Per-report-type question bank / data files organized under `data/<report_type>/` | Currently data files (question banks, analysis CSVs, processed CSVs) are flat inside each project. In a unified framework these would collide without namespacing | MEDIUM | Needed for correctness — without this, `data/analysis/M1.csv` from one report type would be overwritten by another. Not glamorous, but essential for multi-type coexistence |
| Google Drive upload per-delivery | `diagnosticos/send_emails.py` saves reports to Google Drive on send. Good for audit trail. Already implemented in `drive_service.py` | LOW | Optional flag `--no-drive` to skip for speed. Keep as default behavior |

### Anti-Features (Deliberately NOT Build)

Features that seem helpful but would add complexity without matching value for this internal tool.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Config-file-driven report definition (YAML/JSON config per report type) | "More flexible, no code for new reports" | This domain has custom Python logic per report type (different template rendering, different score interpretation). A config-driven system would need to become Turing-complete to cover all cases, or fall short and require Python anyway. Explicit is better than implicit here | New report type = new Python module. One file to write, no config DSL to learn |
| Database-backed processed_emails tracking (replacing CSV) | "More robust than a flat file" | The CSV approach works fine at this scale (hundreds of students, not millions). A database introduces a service dependency (PostgreSQL, SQLite, etc.), complicates local development, and requires migrations. The existing CSV approach is already safe against race conditions because the pipeline is single-process | Keep `processed_emails.csv` in shared core with atomic read-then-write using pandas. Optionally migrate to Firestore only if GCP parallel processing proves the CSV approach insufficient |
| Web UI / dashboard for report status | "Nice to see what's been sent" | This is an internal operational tool run by a small team. A UI adds frontend code, auth, and hosting. Operational visibility needs are fully met by logging + the existing `/status` GCP endpoint | Use GCP Cloud Logging for operational visibility. The `/status` endpoint covers ad-hoc checks |
| Multi-tenancy (different customers with different configs) | "Could be used by other clients" | Introduces auth, data isolation, and config complexity. Current scope is one organization (M30M). Pre-building multi-tenancy for a framework that serves one client is YAGNI | Build for single-tenant first. If multi-tenancy is genuinely needed later, the plugin architecture already supports per-tenant report modules |
| Retry queue with exponential backoff | "What if email fails?" | LearnWorlds-triggered pipelines run in batch windows. A failed email is logged, the operator can re-run with `--force` flag. Implementing a retry queue (Redis, Celery) adds significant infrastructure for a failure mode that is already operationally manageable | Structured error output with list of failed emails + `--resend-failed` flag |
| Report versioning / archival system | "Keep history of sent reports" | Google Drive already serves as the archival layer. The processed_emails.csv already records what was sent and when. Building a separate versioning system would duplicate this | Google Drive upload (already implemented) is the archive |
| Per-student webhook trigger (immediate report on completion) | "Student gets report instantly" | The existing batch model (15-minute collection window) exists for good reason: it prevents API rate-limit hammering and amortizes the overhead of downloading all assessment data. Immediate per-student processing would require a fundamentally different architecture | Keep batch model. The 15-minute window is fast enough for educational use case |

---

## Feature Dependencies

```
[Shared core services (storage, downloader, analyzer, email_sender)]
    └──required by──> [Pluggable report generator interface]
                          └──required by──> [Unified entry point]
                                                └──required by──> [GCP webhook routing]
                                                └──required by──> [Incremental processing]

[Duplicate email suppression]
    └──requires──> [Shared core email_sender]
    └──requires──> [Processed emails tracking (shared)]

[Per-report data namespacing (data/<report_type>/)]
    └──required by──> [Any second report type coexisting in unified framework]
    └──required by──> [Incremental processing] (temp files must not collide between types)

[GCP webhook routing]
    └──requires──> [Assessment mapper (ID -> report type)]
    └──requires──> [Firestore queue service]
    └──requires──> [Cloud Tasks batch scheduler]

[Single Dockerfile / cloudbuild.yaml]
    └──requires──> [Unified entry point] (needs --report-type to work)
    └──requires──> [Per-report data namespacing] (no collisions in container)

[Dry-run mode] ──enhances──> [Unified entry point]
[Test mode (TEST_EMAIL)] ──enhances──> [Email delivery]
[Health/status endpoint] ──enhances──> [GCP webhook routing]
[Slack error notifications] ──enhances──> [Shared core error handling]
```

### Dependency Notes

- **Shared core services must come before the plugin interface:** The generator modules depend on the shared services being importable from a stable location (`from core.email_sender import EmailSender`). If shared services aren't consolidated first, the plugin interface is built on a moving foundation.
- **Per-report data namespacing is required before migrating a second report type:** Running diagnosticos and ensayos_generales in the same container without namespaced data directories will cause file collisions on `data/analysis/*.csv` and `data/processed/*.csv`.
- **Incremental processing depends on data namespacing:** Temp files (`temp_M1.csv`) would collide across report types without the namespace prefix.
- **GCP webhook routing is independent of local CLI:** The webhook layer (webhook_service.py, firestore_service.py, task_service.py, batch_processor.py) can be built and deployed separately from local report generation. They share the same entry point but the webhook infrastructure is an add-on concern.
- **Duplicate email suppression conflicts with force-resend:** A `--force` flag intentionally bypasses the processed_emails check. These are not incompatible — suppression is the default, `--force` is the escape hatch.

---

## MVP Definition

### Launch With (v1)

Minimum viable: consolidate existing projects into one framework without breaking anything.

- [ ] Shared `core/` package with canonical single versions of: `storage.py`, `email_sender.py`, `drive_service.py`, `assessment_downloader.py`, `assessment_analyzer.py` — eliminates drift
- [ ] Plugin interface: each report type implements `generate(analysis_data) -> bytes` in `reports/<report_type>/generator.py`
- [ ] Per-report template storage: `templates/<report_type>/` directory structure
- [ ] Per-report data namespacing: `data/<report_type>/analysis/`, `data/<report_type>/processed/`, `data/<report_type>/raw/`
- [ ] Unified `main.py` accepting `--report-type diagnosticos` (and other types) — routes to correct generator
- [ ] Shared `processed_emails.csv` tracking (or per-report-type: `data/<report_type>/processed_emails.csv`) — duplicate suppression
- [ ] All 5 existing report types migrated and producing identical output to current standalone versions

### Add After Validation (v1.x)

Add once migration is confirmed working and all 5 types are generating correctly.

- [ ] Single `Dockerfile` covering all report types (controlled by `REPORT_TYPE` env var) — eliminates `complete_deployment/` duplicates
- [ ] Single `cloudbuild.yaml` for unified GCP deployment
- [ ] Dry-run mode in unified entry point
- [ ] Test mode (`--test-email`) standardized across all report types via shared email_sender
- [ ] Structured result schema standardized across all operations

### Future Consideration (v2+)

Defer until the framework has been stable for at least one full usage cycle.

- [ ] Plugin autodiscovery (automatic detection of modules in `reports/`) — only valuable when N > 8 report types
- [ ] Slack error notification integration via shared error handler — nice to have, not blocking
- [ ] Health/status endpoint for all GCP-deployed report types — currently only diagnosticos has it

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Shared core services (single source of truth) | HIGH | MEDIUM | P1 |
| Plugin generator interface | HIGH | MEDIUM | P1 |
| Per-report data namespacing | HIGH | LOW | P1 |
| Unified entry point (--report-type) | HIGH | LOW | P1 |
| Duplicate email suppression (shared) | HIGH | LOW | P1 |
| Template-per-report-type organization | HIGH | LOW | P1 |
| Migrate all 5 existing report types | HIGH | HIGH | P1 |
| Single Dockerfile / cloudbuild.yaml | MEDIUM | MEDIUM | P2 |
| Structured result schema | MEDIUM | LOW | P2 |
| Dry-run mode | MEDIUM | LOW | P2 |
| Test mode (TEST_EMAIL) standardized | MEDIUM | LOW | P2 |
| Health/status endpoint for all GCP types | LOW | LOW | P2 |
| Plugin autodiscovery | LOW | MEDIUM | P3 |
| Slack error notification integration | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for launch (migration is broken without these)
- P2: Should have, add when possible (reduce operational risk and developer friction)
- P3: Nice to have, defer to v2+

---

## Competitor Feature Analysis

This is an internal tool with no direct commercial competitors. Reference points are the existing 5 standalone projects, which represent the "status quo" the framework must improve upon.

| Feature | Current (5 standalone projects) | Target (unified framework) |
|---------|----------------------------------|---------------------------|
| Add new report type | Copy entire project folder, manually update 6+ files | Create one Python module + template folder |
| Fix a bug in assessment_downloader | Fix in one project, manually propagate to others (often missed) | Fix once in `core/`, all report types benefit |
| Deploy to GCP | Maintain 2 `complete_deployment/` subfolders (diagnosticos + diagnosticos_uim) each with full codebase copy | One Dockerfile, deploy with `REPORT_TYPE=diagnosticos` env var |
| Duplicate email protection | CSV-based tracking exists in diagnosticos; unclear if all projects have it | Shared implementation in `core/`, consistent across all types |
| Run locally for testing | Each project has its own venv, requirements.txt, .env | One repo, one venv, `--report-type` flag selects target |
| Template management | Templates scattered inside each project directory | Organized under `templates/<report_type>/` |

---

## Sources

- Direct code analysis: `diagnosticos/main.py` (871 lines) — pipeline operation pattern, incremental mode, skip-existing-reports logic
- Direct code analysis: `diagnosticos/send_emails.py` — processed_emails.csv duplicate suppression implementation
- Direct code analysis: `diagnosticos/webhook_service.py` — GCP webhook handler, signature validation, Firestore queue integration, batch window logic (15-minute delay, 400-student early-trigger)
- Direct code analysis: `diagnosticos/firestore_service.py` — queue management, batch state, atomic counters
- Direct code analysis: `diagnosticos/batch_processor.py` — subprocess invocation of main.py per assessment type, cleanup after batch
- Direct code analysis: `assessment-analysis-project/main.py` — dry-run pattern, segment/student-type filtering
- Direct code analysis: `shared/email_sender.py` — SMTP delivery, error notification pattern
- Direct code analysis: `shared/` directory listing — confirmed: storage.py, email_sender.py, drive_service.py, slack_service.py (not used by all projects)
- Project structure analysis: all 5 projects have local copies of core files, confirming the drift problem
- PROJECT.md: confirmed out-of-scope items (config-file-driven reports, non-Python, rewriting logic)

---

*Feature research for: internal Python report pipeline framework*
*Researched: 2026-02-28*
