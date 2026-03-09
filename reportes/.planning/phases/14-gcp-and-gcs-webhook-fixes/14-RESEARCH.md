# Phase 14: GCP and GCS Webhook Fixes - Research

**Researched:** 2026-03-08
**Domain:** Python webhook pipeline, Firestore queue, GCS file routing, per-assessment batching
**Confidence:** HIGH — based on direct code inspection of all affected files

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **ids.xlsx integrity logging:** Add a startup summary log listing which assessment names have no valid ID. Format: "X assessments loaded, Y rejected (list of rejected assessment names)". Currently logged silently as "invalid_assessment_id" with no summary.
- **Assessment group support:** `_ALLOWED_GROUPS` needs review — user changed the group set (was CL before). Verify all groups present in ids.xlsx are included in `_ALLOWED_GROUPS` and aliases map correctly. L30M: check whether it should be supported or intentionally excluded.
- **Queue architecture — per-assessment queues (CRITICAL):** Store `assessment_name` (e.g. `"M30M2-TEST DE EJE 1-DATA"`) in the student Firestore record at webhook time. BatchProcessor groups students by `assessment_name` and calls the pipeline once per distinct assessment_name, passing it through to the generator's `download()`. Each assessment downloads only its own data.
- **Webhook signature validation:** Direct secret comparison via `hmac.compare_digest(received_signature, WEBHOOK_SECRET)` is correct. Do NOT change this.
- **Pipeline failure root cause:** Run the test_de_eje pipeline locally with real Firestore data to identify the exact error. Likely causes: wrong assessment_name being passed to generator's download() method, or download() failing because the assessment isn't in the local ids mapping.
- **ids.xlsx GCS sync:** `gs://data-analysis-465905-t6-mapping/ids.xlsx` must be kept in sync with local `inputs/ids.xlsx`. When real IDs are added locally, upload to GCS. Add this as an explicit runbook step.

### Claude's Discretion

- How to implement `get_route_full()` vs extending `get_route()` return value.
- Whether FirestoreService namespace extends to `(report_type, assessment_name)` or assessment_name is just stored as a field in the existing per-report-type queue.
- Exact method signature for passing `assessment_name` through `BatchProcessor.process_batch()` to `PipelineRunner` to `generator.download()`.

### Deferred Ideas (OUT OF SCOPE)

- Adding real LearnWorlds IDs for F30M, H30M, L30M assessments — data entry done manually after phase 14.
- Full GCS upload runbook for ids.xlsx updates — noted for documentation only.
</user_constraints>

---

## Summary

Phase 14 fixes the broken end-to-end webhook pipeline for `test_de_eje` and `examen_de_eje`. Code inspection reveals **four distinct failure points**, at least one of which (PDF filename contract mismatch) causes a silent total failure: students are queued, the pipeline runs, PDFs are generated, but `PipelineRunner._extract_email_from_pdf()` cannot parse the filenames that the generators produce, so zero emails are sent and no error is raised.

The other three failure points are: (1) the BatchProcessor downloads ALL assessments for a report_type instead of just the specific one that fired, causing failures when most assessments have invalid IDs; (2) `AssessmentMapper` silently rejects rows with invalid IDs but produces no actionable startup summary; (3) `_ALLOWED_GROUPS` currently includes L30M which may or may not be intended, and CL is excluded even though it appeared in prior diagnosticos mapping.

**Primary recommendation:** Fix the PDF filename contract first (it's a two-line change that unblocks email delivery for every already-queued student). Then implement per-assessment queuing. Then add the startup summary log. All three are independent and can be planned as separate tasks.

---

## Critical Bug: PDF Filename Contract Mismatch (CONFIRMED)

This is a **confirmed silent failure** found by direct code inspection.

### What Each Side Expects

**`PipelineRunner._extract_email_from_pdf()` expects** (core/runner.py:69-73):
```
informe_{email}_{atype}.pdf
```
- `parts[0]` must equal `"informe"`
- Returns `None` (and skips the student) if this pattern does not match.

**`TestDeEjeGenerator.render()` and `ExamenDeEjeGenerator.render()` produce** (generator.py:533-535 and examen_de_eje/generator.py:376-378):
```
{assessment_label}__{email}.pdf
```
- Double underscore separator, no "informe" prefix, email is in position 2 not position 1-N.

### Impact

`_extract_email_from_pdf()` returns `None` for every PDF. The runner logs a warning and appends to `errors[]` but continues the loop. Zero emails are sent. `PipelineResult.success` is still `True` (success=False only when generate() raises). The pipeline appears to succeed but delivers nothing.

### Fix Options

Two approaches, both correct:

**Option A — Fix the generators** (recommended): Change both generators to produce `informe_{email}_{assessment_type}.pdf` matching the runner contract. The `assessment_type` part comes from `plan.assessment_type` (already available in the render loop).

**Option B — Fix the runner**: Extend `_extract_email_from_pdf()` to handle the generator's actual filename pattern.

Option A is safer because the runner's contract (`informe_{email}_{atype}.pdf`) is documented in the Phase 9 decision log and is the intended format. The generators diverged from this contract silently.

---

## Architecture Patterns

### Current Queue Architecture (Broken for Multi-Assessment)

```
webhook -> AssessmentMapper.get_route() -> (report_type, assessment_type)
        -> FirestoreService(report_type).queue_student({..., assessment_type})
        -> BatchProcessor.process_batch(report_type)
        -> PipelineRunner(report_type).run()
        -> generator.download()  # downloads ALL valid assessments for report_type
```

**Problem:** `download()` in `TestDeEjeGenerator` calls `_load_test_de_eje_mapping()` which iterates ALL rows in ids.xlsx with valid hex IDs and downloads all of them. When M30M2-TEST DE EJE 1-DATA has a valid ID but F30M-TEST DE EJE 1-DATA has an invalid placeholder, the generator skips the F30M row but still downloads M30M2. This is wasteful but not catastrophic for the currently-working rows. The real failure is the PDF filename contract above.

However, when **multiple assessments** share a report_type and only some have valid IDs, and a webhook fires for one of the invalid-ID ones, the generator downloads the valid ones, produces PDFs for students of those assessments, and emails wrong students. Per-assessment queuing prevents this.

### New Queue Architecture (Per-Assessment)

```
webhook -> AssessmentMapper.get_route_full()
        -> (report_type, assessment_type, assessment_name)
        -> FirestoreService(report_type).queue_student({..., assessment_name})
        -> BatchProcessor.process_batch(report_type)
        -> group students by assessment_name
        -> for each assessment_name group:
             PipelineRunner(report_type, assessment_name=name).run()
             -> generator.download(assessment_name=name)  # only ONE assessment
```

### Implementation Touch Points

| File | Current State | Change Required |
|------|--------------|-----------------|
| `core/assessment_mapper.py` | `get_route()` returns `(report_type, assessment_type)` | Add `get_route_full()` returning `(report_type, assessment_type, assessment_name)` |
| `core/assessment_mapper.py` | `_register_route()` stores route but not name | `_routes` dict value should include `assessment_name` or separate `_names` dict |
| `core/assessment_mapper.py` | `_load_ids_routes()` logs accepted/rejected counts | Add startup summary listing rejected assessment names |
| `webhook_service.py` | Uses `get_route()`, builds `student_data` without `assessment_name` | Switch to `get_route_full()`, add `assessment_name` to `student_data` |
| `core/batch_processor.py` | `process_batch()` calls `process_report_type(report_type)` once | Group queued students by `assessment_name`, call `process_report_type()` per group |
| `core/runner.py` | `PipelineRunner(report_type)`, no assessment filter | `PipelineRunner(report_type, assessment_name=None)` |
| `reports/test_de_eje/generator.py` | `download()` loads all valid rows from ids.xlsx | Accept `assessment_name` param and filter to that row only |
| `reports/examen_de_eje/generator.py` | Same as above | Same fix |
| `reports/test_de_eje/generator.py` | Produces `{label}__{email}.pdf` | Produce `informe_{email}_{assessment_type}.pdf` |
| `reports/examen_de_eje/generator.py` | Same filename issue | Same fix |

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Grouping students by field | Custom dict-building loop | `itertools.groupby` or dict comprehension on `assessment_name` | Stdlib is clear and tested |
| Startup summary log | Custom logging framework | Python `logging.warning()` with structured extra dict | Already the project pattern |
| GCS file existence check | Custom retry/polling | `blob.exists()` — already used in `TestDeEjeGenerator._bank_exists()` | Pattern is established |
| Filename safety | Custom sanitizer | `_safe_filename_component()` — already in both generators | Reuse existing utility |

---

## Common Pitfalls

### Pitfall 1: `_routes` dict stores `(report_type, assessment_type)` only — no assessment_name

**What goes wrong:** To implement `get_route_full()`, the mapper must also store the `assessment_name` at register time. Currently `_register_route()` only stores `(report_type, assessment_type)` keyed by `assessment_id`. If you add `assessment_name` to the stored value, existing tests that assert on the return type of `get_route()` must not break.

**How to avoid:** Add a parallel `_names: Dict[str, str]` dict (`assessment_id -> assessment_name`) in `AssessmentMapper.__init__`. `get_route_full()` does a two-dict lookup. `get_route()` stays unchanged.

### Pitfall 2: BatchProcessor receives ALL students for report_type, not just one assessment

**What goes wrong:** `get_queued_students()` returns all queued students for the entire `report_type` namespace. After grouping by `assessment_name`, the batch loop must ensure it passes only the relevant student subset to each pipeline invocation — but the current generator's `download()` ignores queued students entirely and re-fetches from LearnWorlds API directly. Filtering students in Firestore is not sufficient; the generator must also be told which assessment to download.

**How to avoid:** Pass `assessment_name` as a parameter all the way through: `process_batch` -> `process_report_type` -> `PipelineRunner` -> `generator.download(assessment_name)`.

### Pitfall 3: Generator's `_load_test_de_eje_mapping()` instantiates a fresh `AssessmentMapper()` on every call

**What goes wrong:** `TestDeEjeGenerator._gcs_bank_blob()` and `_bank_exists()` each call `AssessmentMapper()` directly (lines 321, 328), constructing a new instance and re-loading ids.xlsx from GCS each time. In production (GCS source), this adds a GCS round-trip per call.

**How to avoid:** Pass the existing mapper instance or cache the mapper at generator `__init__` time. Not a Phase 14 blocker but worth noting.

### Pitfall 4: PDF filename contract — generators and runner are out of sync

**What goes wrong:** Described in detail above. Silent failure — pipeline returns `success=True` with `emails_sent=0`.

**Warning signs:** `records_processed > 0` but `emails_sent == 0` in batch result. Log entries like "Could not extract email from ..." for every PDF.

**How to avoid:** Fix generators to produce `informe_{email}_{assessment_type}.pdf`. Verify by checking runner `_extract_email_from_pdf()` with a sample filename after fix.

### Pitfall 5: `_ALLOWED_GROUPS` currently includes L30M — may reject CL rows

**Current state** (`assessment_mapper.py` line 36):
```python
_ALLOWED_GROUPS = {"M1", "M2", "H30M", "Q30M", "F30M", "B30M", "L30M"}
```
`CL` is NOT in `_ALLOWED_GROUPS`. The diagnosticos mapping uses `CL_ASSESSMENT_ID` env var directly (line 21), bypassing the ids.xlsx group validation. Any CL rows in ids.xlsx would be rejected.

**What the user reported:** Group set changed (was CL before). L30M may or may not be intentional.

**How to avoid:** Clarify with user before modifying. If L30M is excluded, remove from `_ALLOWED_GROUPS`. If CL should be supported via ids.xlsx, add it to `_ALLOWED_GROUPS`.

### Pitfall 6: Startup summary log must be produced even when ids.xlsx has zero valid rows

**What goes wrong:** If all rows are rejected (all placeholder IDs), the log reads "0 assessments loaded, X rejected" which is useful. But if the log is only emitted inside `_load_ids_routes()` when `len(rows) > 0`, a completely empty file produces no summary at all.

**How to avoid:** Always emit the startup summary, even when `rows == []` or `accepted_new == 0`.

---

## Code Examples

### Current `_register_route()` — does not store assessment_name

```python
# core/assessment_mapper.py:297-331
def _register_route(self, assessment_id, report_type, assessment_type,
                    row_index=None, assessment_name=None) -> bool:
    ...
    if existing is None:
        self._routes[normalized_id] = candidate  # candidate = (report_type, assessment_type)
    self.validation_counters["accepted"] += 1
    return True
```

To support `get_route_full()`, store name in a parallel dict:
```python
# Proposed addition
if existing is None:
    self._routes[normalized_id] = candidate
    if assessment_name:
        self._names[normalized_id] = assessment_name
```

### Current `_load_ids_routes()` — no startup summary

```python
# core/assessment_mapper.py:213-221
logger.info(
    "Loaded ids.xlsx routes",
    extra={
        "rows_total": len(rows),
        "accepted_new": ...,
        "rejected_new": ...,
    },
)
```

Startup summary should add rejected names:
```python
rejected_names = [name for id_, name in self._names_rejected]  # new tracking list
logger.warning(
    "ids.xlsx startup summary",
    extra={
        "accepted": accepted_new,
        "rejected": rejected_new,
        "rejected_names": rejected_names,
    },
)
```

### Current generator filename (BROKEN vs runner contract)

```python
# reports/test_de_eje/generator.py:532-536 — produces wrong format
assessment_label = _strip_data_suffix(plan.assessment_name or plan.assessment_type)
pdf_path = output_dir / (
    f"{_safe_filename_component(assessment_label)}__"
    f"{_safe_filename_component(email)}.pdf"
)

# runner expects: informe_{email}_{assessment_type}.pdf
# Fix:
pdf_path = output_dir / (
    f"informe_{_safe_filename_component(email)}"
    f"_{_safe_filename_component(plan.assessment_type)}.pdf"
)
```

### BatchProcessor grouping pattern (proposed)

```python
# core/batch_processor.py — proposed process_batch change
from itertools import groupby

students = fs.get_queued_students()
# Group by assessment_name field stored at webhook time
by_assessment = {}
for student in students:
    name = student.get("assessment_name", "")
    by_assessment.setdefault(name, []).append(student)

for assessment_name, group in by_assessment.items():
    pipeline_result = self.process_report_type(report_type, assessment_name=assessment_name)
```

---

## State of the Art

| Old Approach | Current Approach | Issue |
|--------------|------------------|-------|
| Download ALL assessments for report_type | Download ALL valid rows in ids.xlsx | Wastes API calls, downloads wrong assessments |
| Silent rejection of invalid IDs | Warning logged per row but no startup summary | Non-actionable in Cloud Run log stream |
| No assessment_name in queue record | assessment_type only | Cannot distinguish which of N assessments for same type triggered |

---

## Open Questions

1. **Should L30M remain in `_ALLOWED_GROUPS`?**
   - What we know: L30M is currently listed as allowed. CONTEXT.md says "the group changed" and to check whether L30M should be supported or intentionally excluded.
   - What's unclear: Whether any active ids.xlsx rows use L30M prefix.
   - Recommendation: Check ids.xlsx content. If no L30M rows exist and CL was the prior group, remove L30M and add nothing (CL rows go through env vars, not ids.xlsx).

2. **Does `FirestoreService` need a new namespace for per-assessment queues, or is `assessment_name` just a field?**
   - What we know: CONTEXT.md says "queue key should include `assessment_name` so students who took different assessments in the same interval are grouped correctly."
   - What's unclear: Whether this means a new Firestore collection path (`report_types/{type}/{assessment_name}/queue`) or just a field in the existing collection.
   - Recommendation: Keep the existing per-report-type namespace. Use `assessment_name` as a filter field in `get_queued_students()`. This avoids breaking `clear_queue()` and `clear_batch_state()` which operate on the whole namespace.

3. **What is the exact pipeline failure when running locally?**
   - What we know: CONTEXT.md says to run locally with real Firestore data to identify the exact error. Based on code inspection, the PDF filename contract mismatch is the confirmed failure.
   - Recommendation: Confirm by running `PipelineRunner("test_de_eje").run()` locally with a test student in Firestore and checking whether `emails_sent == 0` with the filename mismatch warning in logs.

---

## Validation Architecture

> Skipped — `workflow.nyquist_validation` is not present in `.planning/config.json` (only `research`, `plan_check`, `verifier` keys exist). Treating as disabled.

---

## Sources

### Primary (HIGH confidence)

- Direct inspection of `core/assessment_mapper.py` — full file read, all method signatures confirmed
- Direct inspection of `core/batch_processor.py` — full file read
- Direct inspection of `core/firestore_service.py` — full file read
- Direct inspection of `core/runner.py` — full file read, `_extract_email_from_pdf()` contract confirmed
- Direct inspection of `reports/test_de_eje/generator.py` — full file read, filename mismatch confirmed at lines 532-536
- Direct inspection of `reports/examen_de_eje/generator.py` — filename mismatch confirmed at lines 375-379
- Direct inspection of `webhook_service.py` — full file read, `handle_webhook()` logic confirmed
- `.planning/phases/14-gcp-and-gcs-webhook-fixes/14-CONTEXT.md` — all locked decisions

### Secondary (MEDIUM confidence)

- `.planning/REQUIREMENTS.md` — requirement traceability (MAIL-01, DEPL-01, DEPL-02)
- `.planning/STATE.md` — accumulated project decisions and context

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries needed; all changes are in existing Python files
- Architecture: HIGH — failure points confirmed by direct code inspection, not inference
- Pitfalls: HIGH — PDF filename mismatch and group validation are verified facts; others inferred from code structure
- Queue redesign: MEDIUM — design is clear from CONTEXT.md but implementation details (Firestore schema) require a decision on namespace vs field approach

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (code changes in this repo are the only thing that would invalidate findings)
