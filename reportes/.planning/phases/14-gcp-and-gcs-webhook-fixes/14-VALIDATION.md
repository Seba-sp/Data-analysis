---
phase: 14
slug: gcp-and-gcs-webhook-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini or pyproject.toml (existing) |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 1 | PDF filename fix | unit | `pytest tests/ -k "test_pdf_filename" -q` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 1 | Email extraction | unit | `pytest tests/ -k "test_extract_email" -q` | ❌ W0 | ⬜ pending |
| 14-02-01 | 02 | 1 | AssessmentMapper get_route_full | unit | `pytest tests/ -k "test_get_route_full" -q` | ❌ W0 | ⬜ pending |
| 14-02-02 | 02 | 1 | Startup summary log | unit | `pytest tests/ -k "test_startup_summary" -q` | ❌ W0 | ⬜ pending |
| 14-03-01 | 03 | 2 | BatchProcessor per-assessment grouping | unit | `pytest tests/ -k "test_batch_assessment" -q` | ❌ W0 | ⬜ pending |
| 14-03-02 | 03 | 2 | Webhook stores assessment_name | unit | `pytest tests/ -k "test_webhook_assessment_name" -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_phase14_pdf_filename.py` — stubs for PDF filename contract fix
- [ ] `tests/test_phase14_assessment_mapper.py` — stubs for get_route_full and startup log
- [ ] `tests/test_phase14_batch_processor.py` — stubs for per-assessment grouping

*Existing infrastructure (conftest.py) covers fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end email delivery | Full pipeline smoke test | Requires live Firestore + GCS + SMTP | Queue a test student, run PipelineRunner, verify email received |
| Cloud Run log startup summary | GCP log visibility | Requires deployed container | Deploy and check Cloud Run logs for "ids.xlsx startup summary" entry |
| GCS ids.xlsx sync | Data integrity | Requires GCS access | Upload updated ids.xlsx, restart service, verify startup summary matches |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
