# Phase 14: GCP and GCS Webhook Fixes - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the end-to-end webhook pipeline for `test_de_eje` and `examen_de_eje` report types.
Both webhooks receive events but students are not being processed correctly.
Scope: assessment mapper correctness, ids.xlsx validation logging, queue-per-assessment
architecture change, pipeline failure debugging for these two report types, and
email-side delivery contracts (filename + dedupe ledger).

</domain>

<decisions>
## Implementation Decisions

### ids.xlsx integrity
- Many assessments (F30M 1-4, H30M 1, L30M 1-3, etc.) have no real LearnWorlds IDs yet; placeholder text was deleted, leaving invalid strings.
- The mapper correctly rejects non-hex IDs, but should log a clear WARNING listing which assessment names have no valid ID (currently logged as invalid_assessment_id with weak summary).
- Add a startup summary log: "X assessments loaded, Y rejected (list of rejected assessment names)" so missing IDs are immediately visible in Cloud Run logs.

### Assessment group support
- `_ALLOWED_GROUPS` needs review; user changed the group set (was CL before). Verify all groups present in ids.xlsx are included in `_ALLOWED_GROUPS` and aliases map correctly.
- L30M: check whether it should be supported or intentionally excluded.

### Queue architecture change - per-assessment queues (critical)
- Current (broken): Webhook stores `report_type + assessment_type` in queue. BatchProcessor downloads all assessments for the report_type, ignoring which specific assessment triggered the webhook. This is inefficient and fails when most assessments have no real IDs yet.
- New design: Store `assessment_name` (for example, `M30M2-TEST DE EJE 1-DATA`) in the student Firestore record when queuing. This name comes from ids.xlsx lookup at webhook time. BatchProcessor passes `assessment_name` to the pipeline, which downloads only that specific assessment.
- Queue key should include `assessment_name` so students who took different assessments in the same interval are grouped correctly and each assessment is downloaded only once.
- This scales to high-concurrency webhook bursts: each assessment gets its own queue slot, and only assessments with queued students are downloaded.

### Webhook signature validation
- Direct secret comparison (`hmac.compare_digest(received_signature, WEBHOOK_SECRET)`) is correct. LearnWorlds sends the raw secret as the signature. Do not change this.

### Pipeline failure root cause
- Student gets queued but pipeline fails. The failure is in PipelineRunner execution.
- Phase must include end-to-end tracing: run the test_de_eje pipeline locally with real Firestore data to identify the exact error.
- Likely causes: wrong assessment_name passed to generator download(), or download() failing because the assessment is not in the local ids mapping.

### ids.xlsx GCS sync
- The GCS copy at `gs://data-analysis-465905-t6-mapping/ids.xlsx` must be kept in sync with local `inputs/ids.xlsx`.
- When real IDs are added to local ids.xlsx, they must be uploaded to GCS. Add this as an explicit step/runbook.

### Email attachment filename contract (new)
- Attachment/PDF filename format is locked to:
  - `informe_{report_type}_{assessment_name}_{email}.pdf`
- Rationale: deterministic uniqueness per report + assessment + student, and explicit assessment traceability in outbound emails.
- This replaces the older parser assumption of `informe_{email}_{assessment_type}.pdf`.

### Sent-email dedupe key (new)
- Dedupe identity is locked to:
  - `(report_type, assessment_name, email)`
- Behavior:
  - Skip only if the exact triple was already sent successfully.
  - Do not block different assessments for the same student.

### Processed-emails ledger output (new)
- Persist successful sends to per-report Excel ledger:
  - `data/{report_type}/processed_emails.xlsx`
- Write timing:
  - Append row immediately after successful SMTP send for each student.
- Minimum columns:
  - `report_type`, `assessment_name`, `email`, `attachment_filename`, `sent_at_utc`, `event_key`
- Existing CSV tracking may remain for backward compatibility, but XLSX is required output.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AssessmentMapper._parse_assessment_name()` already extracts group, report_type, and assessment_type from name string. It can be extended to also return the full canonical assessment_name.
- `AssessmentMapper._load_ids_xlsx_rows()` already returns row tuples containing assessment_name, so the value is available at webhook time.
- `FirestoreService.queue_student(student_data)` already accepts arbitrary dict payloads; `assessment_name` can be added without schema migration.

### Established Patterns
- Firestore namespace is per report_type via `FirestoreService(report_type)`.
- `BatchProcessor.process_report_type(report_type, assessment_name)` already supports assessment_name pass-through.
- `PipelineRunner` currently parses email from filename stem and builds event_key from filename semantics.

### Integration Points
- `webhook_service.py` `handle_webhook()`:
  - include `assessment_name` in queued student record.
  - prefer mapper API returning full route metadata in one call.
- `AssessmentMapper.get_route()`:
  - add/keep `get_route_full()` style return for `(report_type, assessment_type, assessment_name)`.
- `BatchProcessor.process_batch()`:
  - group queued records by `assessment_name` and process each group independently.
- `core/runner.py`:
  - `_extract_email_from_pdf()` and `_event_key_for_pdf()` must parse the new filename contract.
  - send loop must check dedupe ledger before sending and append successful sends after sending.
- `reports/test_de_eje/generator.py` and `reports/examen_de_eje/generator.py`:
  - output filename generation must include `report_type` + `assessment_name` + `email` in that order.
- `reports/base.py`:
  - current `processed_emails_path` CSV can stay, but XLSX ledger path must be added and used by runner.

</code_context>

<specifics>
## Specific Ideas

- "With assessment_id from webhook, cross with ids.xlsx, get exact assessment, queue by assessment, and only download assessments that actually have queued students."
- Startup warning summary should list rejected assessment names so missing IDs are immediately visible.
- Email dedupe must prevent resending the same assessment PDF to the same student while allowing future different assessments.

</specifics>

<deferred>
## Deferred Ideas

- Adding real LearnWorlds IDs for F30M, H30M, L30M assessments (data entry task, not code).
- Full GCS upload runbook for ids.xlsx updates (operational docs).
- Global cross-report dedupe ledger (single file for all report types); deferred, keep per-report ledger in this phase.

</deferred>

---

*Phase: 14-gcp-and-gcs-webhook-fixes*
*Context gathered: 2026-03-09*
