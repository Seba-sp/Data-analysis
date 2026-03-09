---
phase: 14-gcp-and-gcs-webhook-fixes
plan: "03"
subsystem: webhook-pipeline
tags:
  - per-assessment-queue
  - assessment-scoping
  - tdd
  - batch-processor
  - pipeline-runner
dependency_graph:
  requires:
    - 14-02  # AssessmentMapper.get_route_full() 3-tuple added in plan 02
  provides:
    - assessment_name flows from webhook event to generator.download() filter
    - BatchProcessor groups students by assessment_name for isolated processing
  affects:
    - webhook_service.py
    - core/batch_processor.py
    - core/runner.py
    - reports/base.py
    - reports/test_de_eje/generator.py
    - reports/examen_de_eje/generator.py
    - reports/diagnosticos/generator.py
    - reports/diagnosticos_uim/generator.py
    - reports/test_diagnostico/generator.py
    - reports/ensayos_generales/generator.py
tech_stack:
  added: []
  patterns:
    - Per-assessment scoped download via assessment_name kwarg propagation through generate()->download()
    - Student grouping in BatchProcessor with dict.setdefault() for O(n) grouping
key_files:
  created:
    - tests/test_phase14_batch_processor.py
  modified:
    - webhook_service.py
    - core/batch_processor.py
    - core/runner.py
    - reports/base.py
    - reports/test_de_eje/generator.py
    - reports/examen_de_eje/generator.py
    - reports/diagnosticos/generator.py
    - reports/diagnosticos_uim/generator.py
    - reports/test_diagnostico/generator.py
    - reports/ensayos_generales/generator.py
    - tests/webhook/test_webhook_phase7_routing.py
    - tests/webhook/test_webhook_phase9_test_de_eje_integration.py
    - tests/test_runner.py
decisions:
  - "assessment_name kwarg propagated via BaseReportGenerator.generate() -> download() to keep base lifecycle intact without duplicating logic"
  - "download() filters are applied in generator using normalized assessment_name match — empty string means no filter (all assessments, legacy behaviour)"
  - "process_report_type() signature extended with assessment_name kwarg (default empty string) for backward compatibility with existing callers"
metrics:
  duration: "~35 minutes"
  completed_date: "2026-03-08"
  tasks_completed: 2
  files_modified: 13
  files_created: 1
---

# Phase 14 Plan 03: Per-Assessment Queue Architecture Summary

Per-assessment scoping implemented: assessment_name flows from webhook -> Firestore queue -> BatchProcessor grouping -> PipelineRunner -> generator.download() filter so each webhook processes exactly the one assessment that fired.

## Tasks Completed

| # | Task | Commit | Result |
|---|------|--------|--------|
| 1 | Write failing tests (RED) | 2c74add | 2 RED, 1 GREEN — correct RED state confirmed |
| 2 | Implement per-assessment architecture (GREEN) | ee06185 | All 3 tests GREEN, no regressions |

## What Was Built

### webhook_service.py
- `handle_webhook()` now calls `get_route_full()` instead of `get_route()`, unpacking a 3-tuple `(report_type, assessment_type, assessment_name)`.
- `student_data` dict now includes `'assessment_name': assessment_name` field before queuing to Firestore.

### core/batch_processor.py
- `process_batch()` groups students from the queue by `assessment_name` using `student.get("assessment_name", "")` — legacy records with no key fall into the `""` group.
- `process_report_type()` is called once per distinct group, passing `assessment_name=` kwarg.
- `process_report_type()` signature updated: `(report_type: str, assessment_name: str = "") -> Dict[str, Any]`.

### core/runner.py
- `PipelineRunner.__init__()` accepts `assessment_name: Optional[str] = None`, stored as `self.assessment_name = assessment_name or ""`.
- `run()` passes `assessment_name=self.assessment_name` to `generator.generate()`.

### reports/base.py
- `BaseReportGenerator.generate()` accepts `assessment_name: str = ""` and passes it to `download(assessment_name=assessment_name)`.
- `download()` abstract method updated to `download(self, assessment_name: str = "") -> Any`.

### reports/test_de_eje/generator.py
- `download(assessment_name="")` filters `_load_test_de_eje_mapping()` rows to only the matching `assessment_name` when non-empty (normalized before comparison). Empty string = all rows.

### reports/examen_de_eje/generator.py
- Same assessment_name filter applied in `download()` as test_de_eje.

### Other generators (auto-fix)
- `diagnosticos`, `diagnosticos_uim`, `test_diagnostico`, `ensayos_generales` — `download()` signature updated to `download(self, assessment_name: str = "")` for base class compatibility. They ignore the kwarg (no scoping needed — they use env-var IDs, not ids.xlsx rows).

## Test Results

```
tests/test_phase14_batch_processor.py::test_webhook_stores_assessment_name    PASSED
tests/test_phase14_batch_processor.py::test_batch_groups_by_assessment_name   PASSED
tests/test_phase14_batch_processor.py::test_legacy_student_no_assessment_name PASSED
tests/test_phase14_assessment_mapper.py  — 9 tests PASSED (plan 02, no regressions)
tests/test_phase14_pdf_filename.py       — 3 tests PASSED (plan 01, no regressions)

Total: 179 passed, 9 pre-existing failures (all confirmed pre-existing before this plan)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Other generators missing assessment_name kwarg**
- **Found during:** Task 2 implementation
- **Issue:** `BaseReportGenerator.generate()` now calls `download(assessment_name=...)`, but 4 other generators (`diagnosticos`, `diagnosticos_uim`, `test_diagnostico`, `ensayos_generales`) had `def download(self)` with no kwarg — would crash with `TypeError` at runtime.
- **Fix:** Added `assessment_name: str = ""` to all 4 `download()` signatures. They silently ignore the kwarg since their download logic is not ids.xlsx-based.
- **Files modified:** `reports/diagnosticos/generator.py`, `reports/diagnosticos_uim/generator.py`, `reports/test_diagnostico/generator.py`, `reports/ensayos_generales/generator.py`
- **Commit:** ee06185

**2. [Rule 1 - Bug] Webhook fake mappers missing get_route_full()**
- **Found during:** Task 2 verification
- **Issue:** Existing webhook test fakes (`_FakeMapper` in phase 7 and phase 9 tests) only implemented `get_route()`. After our change to call `get_route_full()`, they would crash with `AttributeError`.
- **Fix:** Added `get_route_full()` to both fake mappers; also added override to `_UnknownRouteMapper` returning `None`.
- **Files modified:** `tests/webhook/test_webhook_phase7_routing.py`, `tests/webhook/test_webhook_phase9_test_de_eje_integration.py`
- **Commit:** ee06185

**3. [Rule 1 - Bug] Error message format assertion in test_runner.py**
- **Found during:** Task 2 verification
- **Issue:** `test_batch_result_is_unsuccessful_when_pipeline_reports_errors` asserted `"Pipeline failed for test_de_eje" in result["errors"]` (exact string match). New code appends `"Pipeline failed for test_de_eje assessment=''"` which contains the substring but fails exact list membership check.
- **Fix:** Changed assert to `any("Pipeline failed for test_de_eje" in e for e in result["errors"])`.
- **Files modified:** `tests/test_runner.py`
- **Commit:** ee06185

## Self-Check

Files confirmed:
- `tests/test_phase14_batch_processor.py` — created, 249 lines
- `webhook_service.py` — uses `get_route_full()`, `assessment_name` in student_data
- `core/batch_processor.py` — groups by assessment_name, passes kwarg through
- `core/runner.py` — accepts and stores assessment_name
- `reports/base.py` — generate()/download() accept assessment_name
- `reports/test_de_eje/generator.py` — filters by assessment_name in download()
- `reports/examen_de_eje/generator.py` — filters by assessment_name in download()

Commits confirmed: 2c74add (RED), ee06185 (GREEN)
