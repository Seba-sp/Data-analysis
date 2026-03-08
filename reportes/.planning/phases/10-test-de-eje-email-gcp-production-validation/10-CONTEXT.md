# Phase 10: Test de Eje Email + GCP Production Validation - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Reorder the next execution phase to focus only on `test_de_eje` hardening: fix email-delivery behavior for one assessment event -> one email, then validate GCP production execution (mapping, queueing, batch lifecycle, and successful delivery evidence). `examen_de_eje` and `ensayo` implementation remain out of this phase.

</domain>

<decisions>
## Implementation Decisions

### Email Trigger and Recipient Policy
- Email behavior remains one assessment completion event -> one email containing only that assessment report PDF.
- Recipient in production validation is the student email from webhook payload (no production recipient override as default behavior).
- All emails in this phase must keep PDF attachment behavior unchanged.

### Email Failure Semantics and Proof
- Email send failures must be recorded and processing must continue (no full batch abort on first email failure).
- Phase sign-off requires webhook end-to-end evidence: one webhook event, one generated PDF, one outbound email, and matching operational logs/counters.

### GCP Runtime Scope and Exit Criteria
- GCP deployment/validation scope for this phase is `test_de_eje` only.
- Validation must use production mapping source (`ids.xlsx` from configured GCS path), not local-only mapping.
- Firestore verification is required for queue ingestion, per-type counters, and batch state lifecycle.
- If production webhook execution fails for `test_de_eje`, phase remains incomplete.

### Claude's Discretion
- Exact logging shape and assertion helper format for production evidence collection.
- Test harness structure for replaying webhook payloads in controlled validation runs.

</decisions>

<specifics>
## Specific Ideas

- Keep phase tightly scoped to `test_de_eje` to unblock reliable production behavior before starting `examen_de_eje` and `ensayo` plugin implementation.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/runner.py`: central generation -> email -> Drive loop already enforces per-PDF send flow and captures `emails_sent`/`errors` counts.
- `core/email_sender.py`: shared SMTP sender used by runner; current static subject/body behavior is the starting point for email fixes.
- `webhook_service.py`: production webhook entrypoint with routing, queueing, and task scheduling paths.
- `core/firestore_service.py`: queue/counter/batch-state methods needed for production validation checks.

### Established Patterns
- Plugin generation is isolated from side effects; email and Drive happen in `PipelineRunner` after PDF creation.
- Webhook processing is route-first (`AssessmentMapper`) then Firestore queue + Cloud Tasks orchestration.
- Per-report-type namespacing in Firestore is already established and should remain unchanged.

### Integration Points
- `webhook_service.handle_webhook()` for route resolution + student queue entry.
- `core.batch_processor` and `core.runner.PipelineRunner` for report execution and outbound email side effects.
- `reports/test_de_eje/generator.py` output contract consumed by runner for attachment sending.

</code_context>

<decisions_update>
## Gap-Closure Decisions (added 2026-03-08)

### Per-Report-Type Email Content (UNDEFERRED — now required in Phase 10)
- Each report type MUST send emails with a distinct subject and distinct body text.
- `email_sender.py` and `runner.py` must accept and use a report-type-specific email template (subject + body) when composing outbound messages.
- For this phase, at minimum `test_de_eje` must have its own subject and body; the mechanism must be extensible so other plugins can define their own templates without modifying shared runner code.
- The PDF attachment behavior remains unchanged.

### GCP Deployment and GCS Files (required in Phase 10)
- Phase 10 must include deploying the current codebase (with `test_de_eje` plugin and all Phase 10 fixes) to GCP Cloud Run.
- Production `ids.xlsx` mapping file must be uploaded to the configured GCS bucket path (`IDS_XLSX_GCS_PATH`) and verified as the mapping source during webhook execution.
- Any data files required by `test_de_eje` at runtime (question bank, templates) must be confirmed reachable in the GCP environment (either bundled in the container image or accessible via GCS).
- Fix the `ids_path` / `IDS_XLSX_GCS_PATH` env-key mismatch in `webhook_service.py` diagnostics (VERIFICATION.md code gap).

</decisions_update>

<deferred>
## Deferred Ideas

- None — per-report-type email templates have been promoted to required in this phase.

</deferred>

---

*Phase: 10-test-de-eje-email-gcp-production-validation*
*Context gathered: 2026-03-08*
