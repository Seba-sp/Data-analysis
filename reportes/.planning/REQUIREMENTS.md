# Requirements: Unified Report Pipeline

**Defined:** 2026-03-06
**Core Value:** Adding a new report type requires only a new `reports/<type>/generator.py` module and templates, while shared infrastructure remains reusable.

## v1.1 Requirements

### Routing

- [x] **ROUT-01**: System can load `ids.xlsx` from local project inputs in non-production environments, with GCS bucket support for production.
- [x] **ROUT-02**: System can parse assessment names matching `[GROUP]-[TYPE N]-DATA` for TYPE in `TEST DE EJE`, `EXAMEN DE EJE`, `ENSAYO`.
- [x] **ROUT-03**: Name parsing accepts lowercase and accent variants while normalizing to canonical report types.
- [x] **ROUT-04**: Routing rejects rows with unsupported group prefixes (allowed: `M1`, `M2`, `H30M`, `Q30M`, `F30M`, `B30M`, `CL`) and logs validation errors.
- [x] **ROUT-05**: Webhook path resolves `assessment_id` to exactly one target report plugin using GCS-provided mappings.

### Plugins

- [x] **PLUG-01**: A dedicated `test_de_eje` plugin exists and is registered in `reports.REGISTRY`.
- [x] **PLUG-02**: A dedicated `examen_de_eje` plugin exists and is registered in `reports.REGISTRY`.
- [ ] **PLUG-03**: A dedicated `ensayo` plugin exists and is registered in `reports.REGISTRY`.
- [ ] **PLUG-04**: Each new plugin can run full lifecycle (`download -> analyze -> render`) through `PipelineRunner`.

### Templates and Covers

- [x] **TMPL-01**: DOCX templates for each new report type are converted to HTML preserving layout as closely as possible.
- [x] **TMPL-02**: Each report type includes a dedicated cover page generated from its image converted to HTML and inserted as page 1.
- [x] **TMPL-03**: Generator logic fills template placeholders with computed values from API results and XLSX metadata.
- [x] **TMPL-04**: Generator logic inserts per-report dynamic tables defined by the template requirements.

### Scoring and Inputs

- [x] **DATA-01**: `M30M2-TEST DE EJE 1-DATA.xlsx` structure is consumed as question bank/metadata to compute test de eje outputs.
- [x] **DATA-02**: `M30M2-EXAMEN DE EJE 1-DATA.xlsx` structure is consumed as question bank/metadata to compute examen de eje outputs.
- [ ] **DATA-03**: `M30M2-ENSAYO 1-DATA.xlsx` structure is consumed as question bank/metadata to compute ensayo outputs, including pilot-question handling.

### Delivery Behavior

- [x] **MAIL-01**: When a student completes one supported assessment, the pipeline sends one email containing only that assessment's report.
- [ ] **MAIL-02**: Existing report types continue to function without behavior regression.

### Deployment

- [ ] **DEPL-01**: The three new plugins (`test_de_eje`, `examen_de_eje`, `ensayo`) are deployed to GCP Cloud Run and verified with webhook-triggered execution.
- [x] **DEPL-02**: Production Firestore queue/counter/batch-state behavior is verified for webhook events routed to the currently scoped plugin(s), starting with `test_de_eje`.

## v1.2 Requirements (Deferred)

### Routing Operations

- **ROPS-01**: Admin tooling to edit and validate `ids.xlsx` mapping automatically before deployment.
- **ROPS-02**: Automated sync/versioning workflow for mapping and question banks across environments.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-assessment report aggregation per email | v1.1 explicitly requires one assessment per email |
| Unlimited custom group prefixes | v1.1 scope is restricted to known groups only |
| Re-architecture of webhook batching and Cloud Tasks | Not required to deliver v1.1 business value |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ROUT-01 | Phase 7 | Complete |
| ROUT-02 | Phase 7 | Complete |
| ROUT-03 | Phase 7 | Complete |
| ROUT-04 | Phase 7 | Complete |
| ROUT-05 | Phase 7 | Complete |
| TMPL-01 | Phase 8 | Complete |
| TMPL-02 | Phase 8 | Complete |
| TMPL-03 | Phase 8 | Complete |
| TMPL-04 | Phase 8 | Complete |
| PLUG-01 | Phase 9 | Complete |
| DATA-01 | Phase 9 | Complete |
| MAIL-01 | Phase 10 | Complete |
| DEPL-02 | Phase 10 | Complete |
| PLUG-02 | Phase 11 | Complete |
| DATA-02 | Phase 11 | Complete |
| PLUG-03 | Phase 12 | Pending |
| DATA-03 | Phase 12 | Pending |
| PLUG-04 | Phase 12 | Pending |
| MAIL-02 | Phase 12 | Pending |
| DEPL-01 | Phase 13 | Pending |

**Coverage:**
- v1.1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0

---
*Requirements defined: 2026-03-06*
*Last updated: 2026-03-08 after phase-order replan for test_de_eje production hardening*
