# Phase 4: Unified Entry Points - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

A single `main.py` routes to any registered report type, runs the full pipeline through `PipelineRunner`, and supports dry-run and test-email modes with a structured result on every exit. No GCP deployment work (Phase 5). No additional report type migrations (Phase 6).

</domain>

<decisions>
## Implementation Decisions

### Failure handling
- Continue on individual email failures — never abort the run for one student's error
- Dedup tracking via `processed_emails.csv` (already at `self.processed_emails_path` in `BaseReportGenerator`) — re-runs skip already-successfully-emailed students
- `success: bool` = did the run complete without crashing (not "did every email land") — partial sends are normal and expected
- `errors: list` collects individual per-student failures for visibility
- Records processed and emails sent are counted even in partial-success runs

### Dry-run scope
- `--dry-run` still hits the LearnWorlds API to download fresh data
- Dry-run skips email sending and Drive upload only — no output side effects
- All three generator lifecycle steps (download → analyze → render) run normally
- Structured result is still returned on dry-run exit

### Test-email behavior
- `--test-email dev@example.com` redirects ALL student emails to that single address
- Full volume: if 50 students have reports, 50 emails land at the dev address
- Drive upload is suppressed in test-email mode (same as dry-run for Drive)
- The test-email address replaces every recipient — no student addresses receive mail

### CLI output / progress
- Per-student log lines for every email sent or failed (e.g. `[diagnosticos] Sent: student@example.com (M1)`)
- Primary reason: these lines become GCP Cloud Run logs — the main debugging mechanism in production
- Final summary at end of run: records processed, emails sent, error count
- Logging through Python `logging` module (not print) so Cloud Run captures them correctly

### Claude's Discretion
- Exact `PipelineRunner` class location (in `core/` or at root level or `runner/`)
- How `records_processed` is counted (by student? by report? by assessment type?)
- Log format details beyond the per-student line pattern
- How `processed_emails.csv` interacts with test-email mode (likely: still writes to dedup file even in test mode, so re-runs in test mode also skip already-processed students)

</decisions>

<specifics>
## Specific Ideas

- Per-student log lines are intentionally structured for GCP Cloud Run log viewer — they are the primary production debugging tool
- The dedup mechanism already exists in `BaseReportGenerator.processed_emails_path` — `PipelineRunner` should use it, not bypass it

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `reports/base.py`: `BaseReportGenerator` with `generate()` orchestrating download → analyze → render. Already has `self.processed_emails_path` for dedup tracking.
- `reports/__init__.py`: `REGISTRY` dict + `get_generator(report_type)` — already wired up for `"diagnosticos"`
- `reports/diagnosticos/generator.py`: `DiagnosticosGenerator` — `render()` returns a *directory path* (not a single file) containing per-student PDFs
- `core/email_sender.py`: `EmailSender.send_comprehensive_report_email()` — sends one email per call, takes `recipient_email` as first arg (this is where test-email override goes)
- `core/storage.py`, `core/drive_service.py`: services available for Drive upload step

### Established Patterns
- Generator lifecycle is `download() → analyze() → render()` — `PipelineRunner` calls `generator.generate()` then handles email + Drive separately
- Base class docstring explicitly states: "Email sending is NOT part of the generator — PipelineRunner (Phase 4) handles it"
- Per-report namespaced data dirs (`data/<report_type>/raw/`, `processed/`, `analysis/`) already set up by `BaseReportGenerator.__init__`

### Integration Points
- `main.py` at repo root → `PipelineRunner` → `get_generator(report_type)()` → `generator.generate()` → email loop → Drive upload
- `--dry-run` flag disables email + Drive legs of PipelineRunner
- `--test-email` flag overrides recipient in `EmailSender` call (or wraps it)
- Structured result `{success, records_processed, emails_sent, errors}` returned from `PipelineRunner.run()` and printed/logged by `main.py`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-unified-entry-points*
*Context gathered: 2026-03-01*
