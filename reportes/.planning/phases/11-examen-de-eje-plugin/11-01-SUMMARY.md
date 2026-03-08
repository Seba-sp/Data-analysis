---
phase: 11-examen-de-eje-plugin
plan: 01
subsystem: testing
tags: [tdd, pytest, examen_de_eje, pdu-threshold, data-contract, render-contract]

# Dependency graph
requires:
  - phase: 09-test-de-eje-plugin
    provides: "TestDeEjeGenerator pattern, TDD test structure, _FakeHTML pattern"
  - phase: 10-test-de-eje-email-gcp-production-validation
    provides: "Plugin email template pattern, importlib plugin loading"
provides:
  - "20 failing TDD tests (RED) for ExamenDeEjeGenerator behavioral contract"
  - "PDU% threshold boundary tests at 0, 49.9, 50, 79.9, 80, 100"
  - "UnitStats dataclass tests (zero-total safety, percent calculation)"
  - "ExamenPlan unit_order preservation test"
  - "REGISTRY key test for examen_de_eje"
  - "Bank column validation tests (required set, missing column, extra columns)"
  - "Mapping load tests (valid rows, TDE skipped, junk raises)"
  - "render() filename, HTML injection, output_dir, empty-plan tests"
affects:
  - "11-02-PLAN.md (implements ExamenDeEjeGenerator to turn these RED tests GREEN)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD RED: test files import from non-existent module to confirm ImportError"
    - "_FakeHTML monkeypatch pattern for weasyprint isolation"
    - "_workdir helper using .tmp_testdata/{prefix}_{uuid4().hex} for isolated test dirs"
    - "MappingRow inline import in monkeypatch lambdas (avoids circular import at collection)"

key-files:
  created:
    - tests/test_examen_de_eje_phase11_logic.py
    - tests/test_examen_de_eje_phase11_data_contract.py
    - tests/test_examen_de_eje_phase11_render_contract.py
  modified: []

key-decisions:
  - "PDU% thresholds locked at 50 (Riesgo→En desarrollo) and 80 (En desarrollo→Solido) per CONTEXT.md"
  - "UnitStats (not UnitProgress) is the examen_de_eje dataclass — no lesson-level breakdown"
  - "ExamenPlan carries unit_order list to preserve bank row insertion order"
  - "Bank required columns are {pregunta, alternativa, unidad} — no leccion needed for examen_de_eje"
  - "REGISTRY key is 'examen_de_eje', class name is 'ExamenDeEjeGenerator'"
  - "PDF filename pattern follows test_de_eje convention: {assessment_label}__{email}.pdf"
  - "render() must skip plans with empty units without raising (graceful no-op)"

patterns-established:
  - "ExamenPlan.unit_order: explicit list preserving bank row sequence for render injection"
  - "MappingRow imported via __import__ inside monkeypatch lambda to avoid import-time failures"

requirements-completed: [PLUG-02, DATA-02]

# Metrics
duration: 3min
completed: 2026-03-08
---

# Phase 11 Plan 01: Examen de Eje TDD Scaffolding Summary

**20 failing TDD tests (RED) establishing the full behavioral contract for ExamenDeEjeGenerator — PDU% thresholds, bank column validation, REGISTRY registration, and render output**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-08T19:01:33Z
- **Completed:** 2026-03-08T19:04:40Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- 9 logic tests covering PDU% boundary values (0, 49.9, 50.0, 79.9, 80.0, 100.0), UnitStats.percent (zero-total safety + normal), and ExamenPlan.unit_order preservation
- 7 data contract tests covering REGISTRY key, bank column validation (valid, missing, extra), and mapping load (valid rows, TDE rows skipped, junk raises)
- 4 render contract tests covering PDF filename, HTML injection of unit rows, output_dir identity, and empty-plan graceful skip
- All 20 tests confirmed in RED state: `ModuleNotFoundError: No module named 'reports.examen_de_eje'`

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing PDU% logic tests** - `54b3cd8` (test)
2. **Task 2: Write failing data contract and REGISTRY tests** - `0200b7e` (test)
3. **Task 3: Write failing render contract tests** - `848daa1` (test)

## Files Created/Modified

- `tests/test_examen_de_eje_phase11_logic.py` - 9 tests: PDU% thresholds, UnitStats.percent, ExamenPlan.unit_order
- `tests/test_examen_de_eje_phase11_data_contract.py` - 7 tests: REGISTRY, bank columns, mapping load
- `tests/test_examen_de_eje_phase11_render_contract.py` - 4 tests: PDF filename, HTML content, output_dir, empty plan

## Decisions Made

- Used `UnitStats` (not `UnitProgress`) as the examen_de_eje dataclass since there is no lesson-level tracking — only unit-level PDU% is needed.
- `ExamenPlan.unit_order` carries a separate list (in addition to `units` dict) to preserve bank row insertion order independently of dict ordering guarantees.
- MappingRow is imported via `__import__` inside monkeypatch lambda bodies to avoid test-time import failure (since the module doesn't exist yet). This is a valid TDD workaround.
- render() empty-plan test asserts no PDFs are created — the directory may or may not exist; `glob("*.pdf")` on a non-existent dir returns empty list gracefully.

## Deviations from Plan

None - plan executed exactly as written. The plan specified 19 tests; 20 were written (the logic file has 9 tests vs the plan's 8 because `test_pdu_threshold_riesgo` was split into two boundary tests at 0.0 and 49.9 rather than combined in one function — this improves boundary visibility with no scope change).

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 20 tests in RED state — Plan 02 (implementation) can proceed immediately
- RED state confirmed output snippet:
  ```
  ModuleNotFoundError: No module named 'reports.examen_de_eje'
  3 errors in collection (one per test file)
  ```
- Plan 02 must implement: `ExamenDeEjeGenerator`, `ExamenPlan`, `UnitStats`, `_assign_estado_recomendacion`, `MappingRow`, `IDS_LOCAL_PATH`, `BANKS_DIR`, `_load_examen_de_eje_mapping()`, `analyze()`, `render()` — plus register `"examen_de_eje"` in `reports/__init__.py` REGISTRY.

---
*Phase: 11-examen-de-eje-plugin*
*Completed: 2026-03-08*
