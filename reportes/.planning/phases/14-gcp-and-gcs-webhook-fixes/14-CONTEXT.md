# Phase 14: GCP and GCS Webhook Fixes - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the end-to-end webhook pipeline for `test_de_eje` and `examen_de_eje` report types.
Both webhooks receive events but students are not being processed correctly.
Scope: assessment mapper correctness, ids.xlsx validation logging, queue-per-assessment
architecture change, and pipeline failure debugging for these two report types.

</domain>

<decisions>
## Implementation Decisions

### ids.xlsx integrity
- Many assessments (F30M 1-4, H30M 1, L30M 1-3, etc.) have no real LearnWorlds IDs yet — placeholder text was deleted, leaving invalid strings.
- The mapper correctly rejects non-hex IDs, but should log a **clear WARNING** listing which assessment names have no valid ID (currently logged silently as "invalid_assessment_id" with no summary).
- Add a startup summary log: "X assessments loaded, Y rejected (list of rejected assessment names)" so missing IDs are immediately visible in Cloud Run logs.

### Assessment group support
- `_ALLOWED_GROUPS` needs review — user changed the group set (was CL before). Verify all groups present in ids.xlsx are included in `_ALLOWED_GROUPS` and aliases map correctly.
- L30M: check whether it should be supported or intentionally excluded (user noted the group changed).

### Queue architecture change — per-assessment queues (CRITICAL)
- **Current (broken)**: Webhook stores `report_type + assessment_type` in queue. BatchProcessor downloads ALL assessments for the report_type, ignoring which specific assessment triggered the webhook. Extremely inefficient (downloads 4 assessments when only 1 fired) and fails when most assessments have no real IDs yet.
- **New design**: Store `assessment_name` (e.g. `"M30M2-TEST DE EJE 1-DATA"`) in the student Firestore record when queuing. This name comes from ids.xlsx lookup at webhook time — the mapper already knows it. BatchProcessor passes `assessment_name` to the pipeline, which downloads ONLY that specific assessment.
- Queue key should include `assessment_name` so students who took different assessments in the same interval are grouped correctly and each assessment is downloaded only once.
- This scales to 40 concurrent webhooks: each assessment gets its own queue slot, and only assessments with actual queued students are downloaded.

### Webhook signature validation
- Direct secret comparison (`hmac.compare_digest(received_signature, WEBHOOK_SECRET)`) is correct. LearnWorlds sends the raw secret as the signature. Do NOT change this.

### Pipeline failure root cause
- Student gets queued but pipeline fails. The failure is in the PipelineRunner execution.
- Phase must include end-to-end tracing: run the test_de_eje pipeline locally with real Firestore data to identify the exact error.
- Likely causes: wrong assessment_name being passed to the generator's download() method, or download() failing because the assessment isn't in the local ids mapping.

### ids.xlsx GCS sync
- The GCS copy at `gs://data-analysis-465905-t6-mapping/ids.xlsx` must be kept in sync with local `inputs/ids.xlsx`.
- When real IDs are added to local ids.xlsx, they must be uploaded to GCS. Add this as an explicit step/runbook.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AssessmentMapper._parse_assessment_name()` — already extracts group, report_type, assessment_type from name string. Can be extended to also return the full canonical assessment_name.
- `AssessmentMapper._load_ids_xlsx_rows()` — already returns (row_index, assessment_id, assessment_name) tuples. The assessment_name is available at webhook time.
- `FirestoreService.queue_student(student_data)` — already accepts arbitrary dict. Add `assessment_name` key to student_data in `handle_webhook()`.

### Established Patterns
- Firestore namespace per report_type: `FirestoreService(report_type)`. May need to extend to namespace per (report_type, assessment_name) for separate queues per assessment.
- `BatchProcessor.process_report_type(report_type)` → `PipelineRunner.run()` — needs to accept and pass through `assessment_name`.

### Integration Points
- `webhook_service.py` `handle_webhook()`: add `assessment_name` to `student_data` dict (line ~210). `_am.get_route()` returns `(report_type, assessment_type)` — mapper also has the name available, needs a new method or the dict lookup can return it.
- `AssessmentMapper.get_route()`: currently returns `(report_type, assessment_type)`. Consider adding `get_route_full()` returning `(report_type, assessment_type, assessment_name)`.
- `BatchProcessor.process_batch()` → needs to group students by `assessment_name` and process each group separately.

</code_context>

<specifics>
## Specific Ideas

- "With the assessment_id from the webhook, cross with ids.xlsx → know exact assessment → put in specific queue. When 40 webhooks arrive in the interval, download only the assessments that actually have students queued — not all of them."
- Startup log summary: list which assessment names in ids.xlsx have invalid IDs so it's immediately visible what needs to be filled in.

</specifics>

<deferred>
## Deferred Ideas

- Adding real LearnWorlds IDs for F30M, H30M, L30M assessments — this is data entry, not code. Done manually after phase 14.
- Full GCS upload runbook for ids.xlsx updates — simple operational procedure, noted for documentation.

</deferred>

---

*Phase: 14-gcp-and-gcs-webhook-fixes*
*Context gathered: 2026-03-08*
