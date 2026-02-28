---
phase: 01-consolidation-audit
plan: 01
subsystem: infra
tags: [python, assessment-downloader, assessment-analyzer, diff-audit, merge-decisions]

requires: []
provides:
  - "MERGE-DECISIONS.md: complete method-level merge decision document for all 6 copies of assessment_downloader.py and assessment_analyzer.py"
  - "Body diffs confirmed for all 11 flagged methods across 3 downloader families"
  - "Canonical base version documented for every diverged method"
  - "Unified requirements.txt with exact production pins (pandas 2.2.2 stack)"
  - "Canonical .env.example with all variables grouped by scope"
  - "Cloud Run vs local entry point ambiguity resolved"
affects:
  - "02-core-implementation: reads MERGE-DECISIONS.md before writing any core/ code"
  - "03-report-modules: reads per-report destination decisions"
  - "05-packaging: reads requirements.txt decisions"

tech-stack:
  added: []
  patterns:
    - "Diff-first audit: run shell diffs before documenting any method decision"
    - "Three-family downloader model: diagnosticos, ensayos_generales, assessment-analysis families are the effective distinct versions"
    - "Incremental-mode architecture: ensayos_generales writes temp CSV (preferred over diag in-memory approach)"

key-files:
  created:
    - ".planning/phases/01-consolidation-audit/MERGE-DECISIONS.md"
  modified: []

key-decisions:
  - "Use cleanup_temp_files as canonical name (replaces cleanup_incremental_files — more general)"
  - "Use GCP_PROJECT_ID as canonical project ID var (avoids collision with GCP runtime GOOGLE_CLOUD_PROJECT)"
  - "Use diagnosticos as canonical base for most diverged methods (most feature-complete)"
  - "Use ensayos_generales as base for save_responses_to_csv and cleanup_temp_files (superset features: include_usernames, No respondida substitution)"
  - "Adopt pandas==2.2.2 + numpy==1.26.4 (matches production complete_deployment environment)"
  - "Adopt weasyprint==66.0, reportlab==4.4.3 (matches production)"
  - "_analyze_by_category_generic: include in core/ — uim omitted intentionally but core must support M1/CL/CIEN"
  - "_download_form_responses_full bodies confirmed IDENTICAL across eg and aa (single-line wrapper)"
  - "load_assessment_list_from_env stays per-report permanently — hardcodes project-specific env var names"
  - "get_latest_timestamp_from_json: aa version has latent bug (reads created instead of submittedTimestamp for assessments) — use diag version"

patterns-established:
  - "Body diff before decision: never assign canonical base without running the diff"
  - "Three-tier variable scoping: core shared / Cloud Run deployment / per-report assessment IDs"

requirements-completed:
  - CORE-01

duration: 45min
completed: 2026-02-28
---

# Phase 1 Plan 1: Consolidation Audit — Merge Decisions Summary

**Complete method-level merge decision document covering all 6 copies of assessment_downloader.py (3 effective families) and assessment_analyzer.py (config-based family + separate ensayos analyzer), with confirmed body diffs, explicit canonical base versions, resolved requirements.txt pinning, and canonical env var catalogue**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-02-28T23:10:18Z
- **Completed:** 2026-02-28T23:55:00Z
- **Tasks:** 2 (Task 1: body diffs + open questions; Task 2: write MERGE-DECISIONS.md)
- **Files created:** 1 (MERGE-DECISIONS.md — 441 lines, 39,739 chars)

## Accomplishments

- Ran body diffs across all 11 flagged methods — 8 confirmed diverged, 3 confirmed identical
- Resolved all 3 open questions from 01-RESEARCH.md (Q1: uim omission intentional; Q2: form responses bodies identical; Q3: load_assessment_list_from_env stays per-report)
- Produced complete 9-section MERGE-DECISIONS.md that passes automated verification (all sections present, zero TBD entries)
- Discovered and documented a latent bug in aa's `get_latest_timestamp_from_json` (reads `created` instead of `submittedTimestamp` for assessment records)
- Produced pasteable unified requirements.txt and .env.example

## Task Commits

Each task was committed atomically:

1. **Tasks 1+2: Body diffs + write MERGE-DECISIONS.md** - `a38bf1e` (feat)

**Plan metadata:** (see final commit below)

## Files Created/Modified

- `.planning/phases/01-consolidation-audit/MERGE-DECISIONS.md` — Complete merge decision document: 9 sections, method matrices, resolution tables, proposed requirements.txt, proposed .env.example, entry point documentation, core boundary rules, open question resolutions

## Decisions Made

- **cleanup_temp_files as canonical name:** `cleanup_incremental_files` (diagnosticos) vs `cleanup_temp_files` (ensayos_generales) resolved by using `cleanup_temp_files` — more general; the ensayos body is a strict superset (deletes incremental JSON, temp CSV, and temp analysis files vs diagnosticos deleting incremental JSON only)
- **GCP_PROJECT_ID as canonical env var:** `GOOGLE_CLOUD_PROJECT` (used by diag/uim) vs `GCP_PROJECT_ID` (used by eg/aa/shared) — `GCP_PROJECT_ID` avoids collision with Cloud Run runtime's auto-set `GOOGLE_CLOUD_PROJECT` variable
- **diagnosticos as default canonical base:** The diagnosticos version is the most feature-complete for most methods (includes MIN_DOWNLOAD_DATE filter, `return_df` param, `userId` or `user_id` fallback in filter_responses)
- **ensayos_generales base for save_responses_to_csv:** eg version adds `include_usernames` param and "No respondida" empty-answer substitution — both are improvements over diag version
- **ensayos_generales base for _download_and_process_common:** eg version writes temp CSV during incremental mode instead of diag's in-memory approach — more robust
- **pandas 2.2.2 + exact pins:** Production `complete_deployment/` folders already run 2.2.2 — adopt production to avoid drift. pandas 2.x breaking changes must be validated in Phase 2
- **_analyze_by_category_generic in core/:** uim intentionally omitted (its assessments are percentage-only), but core/ must include it for M1/CL/CIEN reports. uim never calls it — harmless inclusion
- **load_assessment_list_from_env per-report permanently:** A config-driven core/ version would just move the env var name list one layer up — same problem. Per-report is the correct scope

## Deviations from Plan

**1. [Rule 1 - Bug discovered] Latent bug in aa's get_latest_timestamp_from_json**
- **Found during:** Task 1 (body diff of `_download_responses_incremental`)
- **Issue:** The `assessment-analysis-project` version of `get_latest_timestamp_from_json` reads `created` field from records. For assessment records the correct field is `submittedTimestamp`. The `created` field is the LearnWorlds account creation date — using it for incremental pagination would cause all assessments to appear "new" on every run after the first record's account creation date.
- **Fix:** Not fixed in source (Phase 1 is audit-only). Documented in MERGE-DECISIONS.md Section 2 — canonical base is diagnosticos which reads `submittedTimestamp` correctly.
- **Impact:** Zero code written in Phase 1. Phase 2 must use diagnosticos version for this method.

---

**Total deviations:** 1 bug discovered (documented, not fixed — Phase 1 is audit-only)
**Impact on plan:** Bug discovery confirms the research finding that body diffs are essential before assigning canonical bases. Plan executed correctly.

## Issues Encountered

- `python3` not found on Windows shell — switched to `python` (Python 3.x available as `python` on this system). No impact on outcomes.

## User Setup Required

None — no external service configuration required. Phase 1 is audit-only (no code written).

## Next Phase Readiness

- MERGE-DECISIONS.md is complete and self-contained — Phase 2 implementer can begin writing `core/` without re-reading source files
- Every method has an explicit destination (`core/` or `reports/<type>/`) and canonical base version
- No `TBD`, `unclear`, or `decide later` entries remain in the document
- Proposed `requirements.txt` and `.env.example` are complete and pasteable
- Phase 2 must validate existing code against pandas 2.2.2 breaking changes before implementing core/ methods that use pandas

## Self-Check: PASSED

- FOUND: `.planning/phases/01-consolidation-audit/MERGE-DECISIONS.md` (441 lines, 9 sections, 0 TBDs)
- FOUND: `.planning/phases/01-consolidation-audit/01-01-SUMMARY.md`
- FOUND: commit `a38bf1e` (feat task commit)
- FOUND: commit `be110b2` (docs metadata commit)
- STATE.md updated with position, decisions, blockers
- ROADMAP.md updated: Phase 1 complete 1/1 plans
- REQUIREMENTS.md: CORE-01 checked off

---
*Phase: 01-consolidation-audit*
*Completed: 2026-02-28*
