# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

---

## Milestone: v1.0 — Plugin Architecture MVP

**Shipped:** 2026-03-01
**Phases:** 6 | **Plans:** 18 | **Commits:** ~28

### What Was Built

- Method-level merge decisions for 6 diverged pipeline copies
- `core/` package: canonical AssessmentDownloader (38 methods), AssessmentAnalyzer, storage, email, drive, firestore, task, batch services
- `BaseReportGenerator` ABC + plugin `REGISTRY` pattern
- 4 report type plugins: `diagnosticos`, `diagnosticos_uim`, `ensayos_generales`, `test_diagnostico`
- `PipelineRunner` with dry-run, test-email, structured `PipelineResult`
- `main.py` CLI routing to any registered generator
- Single `webhook_service.py` + `Dockerfile` for all report types on Cloud Run
- Eliminated all 4 `complete_deployment/` subfolders and 4 standalone source directories

### What Worked

- **Wave-based parallel execution** — Plans 06-01/02/03 ran simultaneously, completing in ~11 min wall time vs ~30 min sequential
- **Phase 1 audit-first** — Producing MERGE-DECISIONS.md before writing any code meant zero ambiguity during Phase 2 implementation; no rework
- **Plugin interface proved early** — Validating the full plugin lifecycle on `diagnosticos` alone (Phase 3) before migrating 3 more types caught interface issues before they multiplied
- **Fail-fast `download()` pattern** — Manual-prep plugins (ensayos_generales, test_diagnostico) raise `FileNotFoundError` before generating, not silently skipping — easy to debug in production
- **Checkpoint-gated registry wiring** — Plan 06-04's human-verify checkpoint ensured all 3 new plugins were spot-checked before being declared complete

### What Was Inefficient

- **STATE.md stacking** — Multiple gsd-tools state update attempts left duplicate frontmatter blocks in STATE.md; needed manual cleanup at milestone close
- **Continuation agent Bash denial** — 06-04 continuation agent had Bash denied mid-execution; orchestrator had to manually run state update commands, breaking the autonomous flow
- **CORE-01 traceability gap** — Requirement was `[x]` in requirements list but traceability table showed "Pending"; simple sync gap but required manual fix at milestone close

### Patterns Established

- `data/<report_type>/` namespacing — each plugin owns its own data subdirectory, no cross-plugin data pollution
- `templates/<report_type>/` namespacing — same pattern for templates
- Manual-prep plugin pattern: `download()` raises `FileNotFoundError` with clear message when input file missing
- API-download plugin pattern: `download()` reads env vars for assessment IDs, returns 0 records gracefully when unset
- Force-add pattern for static config assets: `git add -f` for `.xlsx` files that are template assets (not data)
- Two-step Cloud Run deploy: initial deploy → retrieve URL → update `PROCESS_BATCH_URL` env var (chicken-and-egg resolution)

### Key Lessons

1. **Audit before coding** — The Phase 1 MERGE-DECISIONS.md approach should be the default for any consolidation project; it front-loads all ambiguity
2. **One plugin proves the interface** — Don't migrate all N report types at once; prove the plugin interface with one, then parallelize the rest
3. **Parallel waves need clean separation** — Wave 1 plans (06-01/02/03) worked because each plugin was fully independent; ensure future parallel plans have no shared write targets
4. **Checkpoint placement matters** — Placing the human-verify checkpoint in the last plan of the phase (not scattered across plans) concentrated human attention at the right moment

### Cost Observations

- Model mix: 100% sonnet (all plans executed on sonnet profile)
- Sessions: ~6 context windows across the milestone
- Notable: Wave 1 parallel execution was the single biggest efficiency gain — 3 plans in ~11 min wall time

---

## Cross-Milestone Trends

| Milestone | Phases | Plans | Avg Plans/Phase | Parallel Waves |
|-----------|--------|-------|-----------------|----------------|
| v1.0 MVP | 6 | 18 | 3.0 | 1 (Wave 1, Phase 6) |
