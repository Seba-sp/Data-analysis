# Roadmap: Unified Report Pipeline

## Milestones

- [x] **v1.0 Plugin Architecture MVP** - Phases 1-6 (shipped 2026-03-01)
- [ ] **v1.1 Dynamic Assessment Routing + 3 New Report Types** - Phases 7-13 (in execution; phases 7-9 complete)

## Phases

<details>
<summary>[x] v1.0 Plugin Architecture MVP (Phases 1-6) - SHIPPED 2026-03-01</summary>

- [x] Phase 1: Consolidation Audit (1/1 plans) - completed 2026-02-28
- [x] Phase 2: Core Package (5/5 plans) - completed 2026-03-01
- [x] Phase 3: First Plugin Migration (2/2 plans) - completed 2026-03-01
- [x] Phase 4: Unified Entry Points (2/2 plans) - completed 2026-03-01
- [x] Phase 5: GCP Deployment (4/4 plans) - completed 2026-03-01
- [x] Phase 6: Remaining Migrations (4/4 plans) - completed 2026-03-01

See `.planning/milestones/v1.0-ROADMAP.md` for full phase details.

</details>

## v1.1 Phases

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 7 | 3/3 | Completed | ROUT-01, ROUT-02, ROUT-03, ROUT-04, ROUT-05 | 4 |
| 8 | Template and Cover Foundation | Convert DOCX templates and cover images into render-ready HTML contracts for all 3 new report types | TMPL-01, TMPL-02, TMPL-03, TMPL-04 | 4 |
| 9 | Test de Eje Plugin | Deliver production-ready `test_de_eje` plugin using API + XLSX question bank + HTML templates | PLUG-01, DATA-01 | 4 |
| 10 | 5/5 | Complete   | 2026-03-08 | 5 |
| 11 | Examen de Eje Plugin | Deliver production-ready `examen_de_eje` plugin using API + XLSX question bank + HTML templates | PLUG-02, DATA-02 | 4 |
| 12 | Ensayo Plugin + Integration Hardening | Deliver `ensayo` plugin and verify one-assessment-per-email behavior with no regressions on existing types | PLUG-03, DATA-03, PLUG-04, MAIL-02 | 5 |
| 13 | Full New-Plugin GCP Deployment Validation | Deploy and validate `examen_de_eje` + `ensayo` in GCP with production mapping and Firestore state checks | DEPL-01 | 4 |

### Phase Details

**Phase 7: Dynamic ID Routing (Local First)**
Goal: Replace env-only routing for new assessments with runtime mapping from `ids.xlsx` (local now, GCS in production).
Requirements: ROUT-01, ROUT-02, ROUT-03, ROUT-04, ROUT-05
Success criteria:
1. Webhook pipeline can load and cache `ids.xlsx` from local input path for current development flow.
2. Name parser normalizes case/accent variants and maps to canonical report type + assessment subtype.
3. Unsupported group prefixes are rejected with clear logs/metrics instead of silent routing.
4. Routing layer is production-ready to switch mapping source to configured GCS object path.

**Phase 8: Template and Cover Foundation**
Goal: Build render foundation from provided DOCX templates and cover images for 3 new report types.
Requirements: TMPL-01, TMPL-02, TMPL-03, TMPL-04
Success criteria:
1. HTML templates exist for `test_de_eje`, `examen_de_eje`, and `ensayo` preserving source layout closely.
2. Each report type has a generated cover HTML page from its corresponding image and is insertable as page 1.
3. Placeholder schema is documented and implemented for computed fields and static text blocks.
4. Dynamic table insertion points are implemented and validated with sample inputs.

**Phase 9: Test de Eje Plugin**
Goal: Implement and register `test_de_eje` end-to-end report generation.
Requirements: PLUG-01, DATA-01
Success criteria:
1. `reports/test_de_eje/generator.py` implements `download -> analyze -> render` through `BaseReportGenerator`.
2. Plugin consumes API responses plus `M30M2-TEST DE EJE 1-DATA.xlsx` question-bank metadata for calculations/tables.
3. Generated PDF includes cover + body template + dynamic table content with expected placeholders filled.
4. Webhook route invoking a mapped test-de-eje assessment produces one report for one student event.

**Phase 10: Test de Eje Email + GCP Production Validation**
Goal: Stabilize one-assessment-per-email behavior for `test_de_eje` and validate production webhook processing in GCP before implementing additional new plugins.
Requirements: MAIL-01, DEPL-02
Plans: 5 plans
Plans:
- [ ] 10-01-PLAN.md — Harden one-event/one-email contract in runner and sender (MAIL-01)
- [ ] 10-02-PLAN.md — Firestore queue/counter/batch observability and webhook correlation (DEPL-02)
- [ ] 10-03-PLAN.md — Production runbook, validation script, and phase verification matrix
- [ ] 10-04-PLAN.md — Per-report-type email subject/body templates (test_de_eje template + extensible mechanism)
- [ ] 10-05-PLAN.md — GCP deployment, GCS ids.xlsx upload, env-key fix, and production evidence collection
Success criteria:
1. One `test_de_eje` webhook completion event produces exactly one email containing only that student's report PDF.
2. Production mapping source (`ids.xlsx` in GCS) resolves `test_de_eje` assessment IDs correctly at runtime.
3. Firestore queue, counters, and batch state update correctly during webhook-triggered processing for `test_de_eje`.
4. At least one full production webhook run succeeds end-to-end (`route -> queue -> process -> email`) for `test_de_eje`.
5. Failure paths are observable with actionable logs and do not silently mark the phase complete.

**Phase 11: Examen de Eje Plugin**
Goal: Implement and register `examen_de_eje` end-to-end report generation.
Requirements: PLUG-02, DATA-02
Plans: 3 plans
Plans:
- [ ] 11-01-PLAN.md — Failing test scaffolding (TDD RED state) for PDU% logic, data contract, REGISTRY, render contract
- [ ] 11-02-PLAN.md — Implement ExamenDeEjeGenerator + email template + REGISTRY registration (tests GREEN)
- [ ] 11-03-PLAN.md — Smoke test with real bank file + human visual verification of generated PDF
Success criteria:
1. `reports/examen_de_eje/generator.py` implements `download -> analyze -> render` through `BaseReportGenerator`.
2. Plugin consumes API responses plus `M30M2-EXAMEN DE EJE 1-DATA.xlsx` metadata for state/recommendation outputs.
3. Generated PDF includes cover + report narrative + unit status/recommendation table.
4. Webhook route invoking a mapped examen-de-eje assessment produces one report for one student event.

**Phase 12: Ensayo Plugin + Integration Hardening**
Goal: Implement `ensayo` plugin and complete cross-plugin integration guarantees.
Requirements: PLUG-03, DATA-03, PLUG-04, MAIL-02
Success criteria:
1. `reports/ensayo/generator.py` is registered and executes full lifecycle through `PipelineRunner`.
2. Plugin uses `M30M2-ENSAYO 1-DATA.xlsx` metadata including pilot-question handling in score logic.
3. Generated PDF includes cover + scoring summary + rapid report table output.
4. Regression checks confirm existing report types still route and run without behavior breakage.
5. Existing and newly added plugin paths keep one-assessment-per-email behavior with no mixed-report attachments.

**Phase 13: Full New-Plugin GCP Deployment Validation**
Goal: Deploy and validate `examen_de_eje` and `ensayo` in GCP after plugin implementation.
Requirements: DEPL-01
Success criteria:
1. Cloud Run deployment contains `test_de_eje`, `examen_de_eje`, and `ensayo` in registry/runtime image.
2. Production assessment mapping source (`ids.xlsx` in GCS) resolves IDs correctly for `examen_de_eje` and `ensayo`.
3. Firestore queue/counter/batch-state behavior is validated for webhook-triggered processing of `examen_de_eje` and `ensayo`.
4. Webhook-triggered execution succeeds in GCP for one assessment each of `examen_de_eje` and `ensayo`.

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Consolidation Audit | v1.0 | 1/1 | Complete | 2026-02-28 |
| 2. Core Package | v1.0 | 5/5 | Complete | 2026-03-01 |
| 3. First Plugin Migration | v1.0 | 2/2 | Complete | 2026-03-01 |
| 4. Unified Entry Points | v1.0 | 2/2 | Complete | 2026-03-01 |
| 5. GCP Deployment | v1.0 | 4/4 | Complete | 2026-03-01 |
| 6. Remaining Migrations | v1.0 | 4/4 | Complete | 2026-03-01 |
| 7. Dynamic ID Routing from GCS | v1.1 | 3/3 | Complete | 2026-03-06 |
| 8. Template and Cover Foundation | v1.1 | 5/5 | Complete | 2026-03-07 |
| 9. Test de Eje Plugin | v1.1 | 1/1 | Complete | 2026-03-08 |
| 10. Test de Eje Email + GCP Production Validation | v1.1 | 2/5 | In execution | - |
| 11. Examen de Eje Plugin | v1.1 | 0/3 | Pending | - |
| 12. Ensayo Plugin + Integration Hardening | v1.1 | 0/0 | Pending | - |
| 13. Full New-Plugin GCP Deployment Validation | v1.1 | 0/0 | Pending | - |
