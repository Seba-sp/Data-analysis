---
phase: 14-gcp-and-gcs-webhook-fixes
plan: 01
subsystem: pipeline
tags: [pdf, filename, weasyprint, runner, generator, tdd]

requires:
  - phase: 09-test-de-eje-plugin
    provides: TestDeEjeGenerator.render() and PipelineRunner._extract_email_from_pdf() contract
  - phase: 11-examen-de-eje-plugin
    provides: ExamenDeEjeGenerator.render() producing PDF output

provides:
  - Both generators produce informe_{email}_{assessment_type}.pdf matching runner contract
  - Automated regression test file (test_phase14_pdf_filename.py) locking filename contract
  - Fixed phase9 and phase11 render contract tests updated to expect correct filename format

affects:
  - core/runner.py — _extract_email_from_pdf() now correctly parses all generator output
  - reports/test_de_eje/generator.py — filename format changed
  - reports/examen_de_eje/generator.py — filename format changed

tech-stack:
  added: []
  patterns:
    - "PDF filename contract: informe_{email}_{assessment_type}.pdf for all generators"
    - "TDD RED/GREEN: test simulates broken path, GREEN updates test to fixed path"

key-files:
  created:
    - tests/test_phase14_pdf_filename.py
  modified:
    - reports/test_de_eje/generator.py
    - reports/examen_de_eje/generator.py
    - tests/test_test_de_eje_phase9_render_contract.py
    - tests/test_examen_de_eje_phase11_render_contract.py

key-decisions:
  - "PDF filename contract uses informe_{email}_{assessment_type}.pdf — assessment_type from plan.assessment_type (e.g. M30M2), not from assessment_name via _strip_data_suffix"
  - "Removed _strip_data_suffix(plan.assessment_name or plan.assessment_type) from both generators — label variable no longer needed"
  - "Phase9 and phase11 render contract tests updated as part of generator fix (Rule 1 auto-fix)"

patterns-established:
  - "Generator filename pattern: f'informe_{_safe_filename_component(email)}_{_safe_filename_component(plan.assessment_type)}.pdf'"

requirements-completed: [MAIL-01, PLUG-01, PLUG-02]

duration: 5min
completed: 2026-03-09
---

# Phase 14 Plan 01: PDF Filename Contract Fix Summary

**Silent delivery failure eliminated: both generators now produce `informe_{email}_{assessment_type}.pdf` that PipelineRunner can parse, unblocking email delivery for all queued students.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-09T00:40:11Z
- **Completed:** 2026-03-09T00:44:43Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 5

## Accomplishments

- Fixed confirmed silent failure: every PDF was silently skipped and zero emails sent
- Both `test_de_eje` and `examen_de_eje` generators now produce `informe_{email}_{assessment_type}.pdf`
- `PipelineRunner._extract_email_from_pdf()` now successfully parses all generator output
- Three automated regression tests committed in `tests/test_phase14_pdf_filename.py`
- Updated phase 9 and phase 11 render contract tests to match new filename format (Rule 1 auto-fix)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing tests (RED)** - `42348bb` (test)
2. **Task 2: Fix generators + update tests (GREEN)** - `d3ea878` (feat)

**Plan metadata:** (docs commit follows)

_Note: TDD tasks have RED commit (failing tests) and GREEN commit (fix + updated tests)._

## Files Created/Modified

- `tests/test_phase14_pdf_filename.py` - Regression guard: 3 tests asserting filename contract
- `reports/test_de_eje/generator.py` - render() now produces `informe_{email}_{assessment_type}.pdf`
- `reports/examen_de_eje/generator.py` - render() now produces `informe_{email}_{assessment_type}.pdf`
- `tests/test_test_de_eje_phase9_render_contract.py` - Updated expected filename to new format
- `tests/test_examen_de_eje_phase11_render_contract.py` - Updated expected filename and docstring

## Decisions Made

- Used `plan.assessment_type` directly (e.g., `"M30M2"`) as the suffix segment instead of `_strip_data_suffix(plan.assessment_name or plan.assessment_type)`. The assessment_type is already normalized and is exactly what the runner needs as the final `_` segment.
- Removed the `assessment_label` variable entirely from both generators — it was the wrong format (`{label}__` instead of `informe_`) and the only place it was used.
- Applied `_safe_filename_component()` to both email and assessment_type to preserve safety guarantees already in both generators.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated phase 9 render contract tests to expect new filename format**
- **Found during:** Task 2 (Fix generators)
- **Issue:** `tests/test_test_de_eje_phase9_render_contract.py` asserted the old broken filename format (`M30M-TEST DE EJE 1__student@example.com.pdf`) — became failing after generator was fixed
- **Fix:** Updated two assertions to expect `informe_student@example.com_M30M2.pdf` and `informe_single@example.com_M30M2.pdf`
- **Files modified:** `tests/test_test_de_eje_phase9_render_contract.py`
- **Verification:** Both tests pass (GREEN)
- **Committed in:** `d3ea878` (Task 2 commit)

**2. [Rule 1 - Bug] Updated phase 11 examen_de_eje render contract test to expect new filename**
- **Found during:** Task 2 (Fix generators)
- **Issue:** `tests/test_examen_de_eje_phase11_render_contract.py::test_render_writes_pdf_with_correct_filename` asserted `M30M2-EXAMEN DE EJE 1__student@example.com.pdf` — became failing after generator was fixed
- **Fix:** Updated assertion to expect `informe_student@example.com_M30M2.pdf` and updated docstring
- **Files modified:** `tests/test_examen_de_eje_phase11_render_contract.py`
- **Verification:** Test passes (GREEN)
- **Committed in:** `d3ea878` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs introduced by generator fix)
**Impact on plan:** Both auto-fixes necessary for test suite correctness. No scope creep — updating tests to match the corrected generator behavior is the intended outcome.

## Issues Encountered

- `test_test_de_eje_phase9_render_contract.py` was previously untracked (showed as `??` in git status) — it was added to git tracking as part of the Task 2 commit, which caused it to appear as "created" in the commit summary. The file pre-existed and was only modified.
- 9 pre-existing test failures remain in the suite (assessment_mapper group aliases, phase8 CSS contracts, webhook integration) — these are out-of-scope for this plan and documented in 14-02 and 14-03 plans.

## Next Phase Readiness

- Email delivery for already-queued students is now unblocked (filename contract enforced)
- Phase 14-02 addresses per-assessment queuing architecture and `get_route_full()` implementation
- 3 regression tests in `test_phase14_pdf_filename.py` guard against filename contract regressions

## Self-Check: PASSED

- FOUND: tests/test_phase14_pdf_filename.py
- FOUND: reports/test_de_eje/generator.py (modified)
- FOUND: reports/examen_de_eje/generator.py (modified)
- FOUND: .planning/phases/14-gcp-and-gcs-webhook-fixes/14-01-SUMMARY.md
- FOUND: commit 42348bb (RED state — test(14-01))
- FOUND: commit d3ea878 (GREEN state — feat(14-01))

---
*Phase: 14-gcp-and-gcs-webhook-fixes*
*Completed: 2026-03-09*
