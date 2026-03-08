---
phase: 11
slug: examen-de-eje-plugin
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pytest.ini` or `pyproject.toml` (existing) |
| **Quick run command** | `pytest tests/test_examen_de_eje_*.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_examen_de_eje_*.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-W0 | 01 | 0 | PLUG-02 | unit stub | `pytest tests/test_examen_de_eje_contract.py -q` | ❌ W0 | ⬜ pending |
| 11-01-01 | 01 | 1 | PLUG-02 | unit | `pytest tests/test_examen_de_eje_contract.py::test_generator_registered -q` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | DATA-02 | unit | `pytest tests/test_examen_de_eje_contract.py::test_analyze_pdu_thresholds -q` | ❌ W0 | ⬜ pending |
| 11-01-03 | 01 | 1 | PLUG-02 | unit | `pytest tests/test_examen_de_eje_contract.py::test_render_produces_pdf -q` | ❌ W0 | ⬜ pending |
| 11-01-04 | 01 | 2 | PLUG-02 | integration | `pytest tests/test_examen_de_eje_contract.py::test_webhook_one_report_one_email -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_examen_de_eje_contract.py` — stubs for PLUG-02 and DATA-02 (PDU% thresholds, generator registration, render output, one-report-per-email)
- [ ] Existing `tests/conftest.py` — shared fixtures (already exists)

*Existing test infrastructure covers pytest. Wave 0 adds only the new test file.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Webhook end-to-end in GCP | PLUG-02 (SC4) | Requires live LearnWorlds webhook trigger + GCP Cloud Run | Deferred to Phase 13 GCP validation |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
