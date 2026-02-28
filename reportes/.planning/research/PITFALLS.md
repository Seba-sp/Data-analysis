# Pitfalls Research

**Domain:** Python pipeline consolidation — duplicated scripts into a plugin-based framework with GCP Cloud Run
**Researched:** 2026-02-28
**Confidence:** HIGH (all pitfalls observed directly in the codebase, not assumed)

## Critical Pitfalls

### Pitfall 1: Choosing the Wrong Canonical Version When Methods Have Diverged

**What goes wrong:**
You pick one project's file as the canonical `core/` version, but callers in other projects expect a different interface. Silent bugs (wrong results) or crashes appear only when you run a specific project's report type after migration.

**Why it happens:**
The same file was copied across projects and then evolved independently. There is no single "latest" version — each project has unique-to-it additions. Whoever copies first wins, and the others break.

**Concrete evidence from this codebase:**
- `diagnosticos/assessment_downloader.py` has method `cleanup_incremental_files()`. `ensayos_generales/assessment_downloader.py` renamed it `cleanup_temp_files()` and added new behavior (deletes temp CSV and temp analysis files, not just incremental JSON). Any caller using `cleanup_incremental_files` will get an `AttributeError` if the ensayos_generales version is chosen as canonical.
- `save_responses_to_csv()` gained a new parameter `include_usernames: bool = True` in ensayos_generales. The diagnosticos version does not have this parameter. Both callers assume the API they know — neither will error at import time, only at runtime with wrong output.
- The user_id field lookup differs: diagnosticos uses `r.get('userId') or r.get('user_id')` while ensayos_generales uses only `r.get('user_id')`. Choosing the ensayos_generales version silently drops any records where the API returns `userId` (LearnWorlds field name inconsistency is a known API issue).
- `AssessmentAnalyzer.__init__` takes `config: Dict = None` in diagnosticos (injectable config) but takes no parameters in ensayos_generales (hardwires everything internally). These are architecturally different — you cannot swap one for the other without rewriting all callers.

**How to avoid:**
Before writing a single line of the `core/` module, perform a line-by-line diff of every shared file across all 5 projects. Produce a merge decision log: for each method that diverged, explicitly decide which behavior wins and whether the other projects need migration. The `complete_deployment/` subdirectory in diagnosticos and diagnosticos_uim is a third copy — it must be included in this diff, not assumed to match its parent folder (it does not: it uses pandas 2.2.2 while the parent folder pinned `pandas==1.*`).

**Warning signs:**
- Any method rename between two project copies (grep for `def cleanup_` across all .py files to find renames)
- Method signature differences visible in `__init__` or any method with default parameters added
- Silent wrong output instead of a crash on first post-migration test run

**Phase to address:**
Phase 1 (Consolidation Audit) — before writing any shared code. Produce the merge decision document as a deliverable of this phase, not an implicit assumption.

---

### Pitfall 2: `complete_deployment/` Subfolder Is a Separate Copy, Not a Deployment Script

**What goes wrong:**
The `complete_deployment/` subdirectory inside `diagnosticos/` and `diagnosticos_uim/` is treated as "just a GCP packaging thing" and ignored during consolidation. In reality it contains independently evolved Python files. The consolidated `core/` module ends up missing changes that only exist in `complete_deployment/` and Cloud Run deployments silently regress.

**Why it happens:**
The `complete_deployment/` pattern was created to bundle everything a Cloud Run deployment needs into a single folder (since Cloud Run copies the whole directory). Over time, hotfixes went into `complete_deployment/` without being reflected back in the parent folder, or vice versa. The result is three-way divergence: parent folder / complete_deployment / other projects.

**Concrete evidence from this codebase:**
- `diagnosticos/requirements.txt` pins `pandas==1.*` and `weasyprint==56.*`. `diagnosticos/complete_deployment/requirements.txt` pins `pandas==2.2.2`, `weasyprint==66.0`, and `reportlab==4.4.3`. These are not compatible pinning strategies — `pandas==1.*` code can silently break under pandas 2.x (DataFrame copy semantics changed). The production Cloud Run is running the `complete_deployment/` versions, meaning the parent folder is already behind.
- `diagnosticos/complete_deployment/main.py` differs from `diagnosticos/main.py` — the complete_deployment version adds `load_dotenv()` call at the top and has different service initialization error handling (per-service try/except instead of all-or-nothing).
- `diagnosticos_uim/` has both `main.py` and `main_app.py` in `complete_deployment/` — it is not clear which one is actually deployed.

**How to avoid:**
Treat `complete_deployment/` as a fourth project during the audit phase. Diff it against both its parent folder and against the other projects. The unified framework must capture the `complete_deployment/` version of any file where it differs from the parent, since that is what production runs.

**Warning signs:**
- Any requirements.txt in `complete_deployment/` with different pinned versions than the parent folder
- Files present in `complete_deployment/` that have no counterpart in the parent folder
- `load_dotenv()` appearing or not appearing at module level inconsistently

**Phase to address:**
Phase 1 (Consolidation Audit). Explicitly list `complete_deployment/` contents in the file inventory alongside the parent project files.

---

### Pitfall 3: Dependency Version Conflicts Break the Unified Install

**What goes wrong:**
Each project has its own `requirements.txt` with different pinning strategies. When a single `requirements.txt` for the unified framework is assembled, conflicting pins cause either an unresolvable dependency tree or silent version selection that breaks one project's behavior.

**Why it happens:**
Projects diverged over time and were pinned at different points. No one maintained cross-project compatibility because there was no shared dependency file.

**Concrete evidence from this codebase:**
- `ensayos_generales/requirements.txt` pins `pandas==1.*`. `diagnosticos/complete_deployment/requirements.txt` pins `pandas==2.2.2`. These are major versions with breaking changes (notably DataFrame `__setitem__` copy-on-write behavior changed in pandas 2.0).
- `weasyprint` spans `56.*` (diagnosticos parent), `66.0` (diagnosticos complete_deployment), and `>=54.0` (assessment-analysis-project). weasyprint 60+ changed its Pango/Cairo dependency requirements and HTML rendering behavior — a template that renders correctly under 56.* may not render identically under 66.0.
- `reportlab` spans `3.*` and `4.4.3` across projects.
- `assessment-analysis-project/requirements.txt` uses `>=` floor-only pinning (e.g., `pandas>=1.3.0`) while others use `==X.*`. When combined, pip resolves to the newest version, which may be higher than any individual project tested against.
- `ensayos_generales/requirements.txt` has no `google-auth`, `google-api-python-client`, or `google-cloud-*` entries — it does not use Drive or GCS in its dependencies, meaning those local projects may not have those packages installed locally at all.

**How to avoid:**
Run each project's full pipeline once with its own requirements before consolidation to establish a working baseline. Then resolve versions top-down: start with the highest pinned version of each package and run all pipelines against it. If a pipeline fails, that is a behavioral regression to fix, not a dependency to downgrade. For weasyprint specifically, test all HTML templates against the target version before committing.

**Warning signs:**
- Any `requirements.txt` that uses `==1.*` for a package that has a `2.*` available with breaking changes
- A package appearing in some projects' requirements but absent from others
- `pip install` warnings about conflicting requirements when assembling the unified `requirements.txt`

**Phase to address:**
Phase 1 (Consolidation Audit) must produce a resolved unified `requirements.txt` as an explicit output. Do not defer this to "when it breaks."

---

### Pitfall 4: Relative Imports Break When Files Move to `core/`

**What goes wrong:**
All existing files use bare module imports (`from storage import StorageClient`, `from assessment_downloader import AssessmentDownloader`). When these files are moved to `core/`, these imports either break immediately (ImportError) or silently resolve to a stale per-project copy that happens to still be on `sys.path`.

**Why it happens:**
Python resolves bare module imports from `sys.path`. When files lived together in the same directory, this worked. After reorganization into `core/`, the importing file is no longer in the same directory as the imported module, and unless `sys.path` is explicitly managed or proper package structure is used, imports fail or find the wrong file.

**Concrete evidence from this codebase:**
- Every `main.py` across all projects uses `from storage import StorageClient` (bare import). After consolidation to `core/storage.py`, this must become `from core.storage import StorageClient` — or an `__init__.py` must re-export it. Neither is automatically handled.
- `webhook_service.py` uses `from firestore_service import firestore_service as fs` — also bare import. This is called lazily inside a function, so it will not error at import time; it will error silently when the first webhook arrives in production.
- `batch_processor.py` uses `from firestore_service import firestore_service` — same bare import pattern at module top level.
- The `complete_deployment/` folder works precisely because everything is in a flat directory and Cloud Run runs from there. The unified framework breaks this assumption.

**How to avoid:**
Establish the `core/` package with a proper `__init__.py` that exports all public classes. Update imports project-by-project during migration, not all at once. Run each migrated project's full pipeline immediately after updating its imports. Do not do a mass search-and-replace — change one project at a time and verify.

**Warning signs:**
- Any `from X import Y` where X is a filename without a package prefix
- `sys.path.append()` calls in any file (indicates someone already hit this and worked around it)
- ImportError in Cloud Run logs after deployment but not locally (different working directory)

**Phase to address:**
Phase 2 (Core Package Creation). The import refactor is part of this phase, not an afterthought.

---

### Pitfall 5: Cloud Run Assumes Flat Directory; Package Structure Breaks Deployment

**What goes wrong:**
Cloud Run (via `functions_framework`) expects a flat directory where `main.py` (or the entry point) and all its imports are co-located. When the unified framework uses a `core/` package, the `Dockerfile` or deployment command must be updated accordingly. Without this, Cloud Run deploys successfully (no build error) but fails at the first request with an ImportError.

**Why it happens:**
The `complete_deployment/` pattern exists precisely because Cloud Run deployments needed everything in one flat directory. The whole problem this consolidation solves is also the reason Cloud Run deployment is fragile to package reorganization.

**Concrete evidence from this codebase:**
- `diagnosticos/webhook_service.py` uses `import functions_framework` at module top level. If this file is moved and its working directory changes, the import path for sibling modules (`from assessment_mapper import ...`) breaks silently on the first real request.
- There is no `Dockerfile` anywhere in the repo — deployments presumably use `gcloud functions deploy` or `gcloud run deploy` with a source directory. The source directory for Cloud Run must be the flat folder that contains all needed files. After consolidation, that flat folder no longer exists; the entry point is `main.py` at the root of the unified project with `core/` as a subdirectory.
- `diagnosticos_uim/complete_deployment/` has both `main.py` and `main_app.py` — it is not documented which is the actual deployed entry point. This ambiguity must be resolved before migration.

**How to avoid:**
Before decommissioning `complete_deployment/`, verify the exact deploy command used for each Cloud Run service and what entry point file it references. Then write a single `Dockerfile` for the unified framework that copies the full project (including `core/`) and sets the correct working directory. Test the Docker build locally before deploying. Do not rely on `gcloud run deploy --source .` without first verifying that all relative imports work from the project root.

**Warning signs:**
- No `Dockerfile` in the project (relying on Cloud Run source deploy auto-detection)
- Cloud Run deploy succeeds but first request returns 500
- `functions_framework` not in the shared `requirements.txt` (it is only needed for Cloud Run, not local)

**Phase to address:**
Phase 3 (GCP Deployment Consolidation). This is a dedicated phase, not a footnote of Phase 2.

---

### Pitfall 6: Hardcoded Assessment Type Lists Spread Across Every Class

**What goes wrong:**
Every class that iterates over assessment types has its own hardcoded list. When a new assessment type is added, it must be updated in 5+ places. During consolidation, these lists are discovered to differ between projects — creating ambiguity about which list is "correct" for the shared framework.

**Why it happens:**
No single source of truth for assessment configuration was established when projects were originally copied. Each project added its own assessment types as needed.

**Concrete evidence from this codebase:**
- `diagnosticos/main.py`: `self.assessment_types = ["M1", "CL", "CIEN", "HYST"]`
- `ensayos_generales/main.py`: `self.assessment_types = ["M1", "M2", "CL", "CIENB", "CIENF", "CIENQ", "CIENT", "HYST"]`
- `ensayos_generales/assessment_analyzer.py`: `self.assessment_types = ["M1", "M2", "CL", "CIENB", "CIENF", "CIENQ", "CIENT", "HYST"]` (same, repeated)
- `diagnosticos/assessment_mapper.py` derives types from environment variables (`M1_ASSESSMENT_ID`, `CL_ASSESSMENT_ID`, etc.) — a different approach that avoids hardcoding but is not used in other projects
- `diagnosticos/batch_processor.py`: `self.assessment_types = ['M1', 'CL', 'CIEN', 'HYST']` (hardcoded, ignoring env vars)

**How to avoid:**
The `core/` package should have a single config module (e.g., `core/config.py`) that reads assessment type configuration from environment variables, with no hardcoded lists in any business-logic class. Each report plugin declares its own assessment types. The consolidation phase should not silently pick one list and call it done — both lists are valid for different report types.

**Warning signs:**
- `self.assessment_types = [` appearing in any class other than a configuration/registry class
- The same assessment type string appearing in 3+ files
- Different lists in `main.py` vs `assessment_analyzer.py` within the same project

**Phase to address:**
Phase 2 (Core Package Creation). Assessment type configuration must be centralized as part of establishing the plugin interface.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Copy `complete_deployment/` as the Cloud Run entrypoint instead of building a Dockerfile | No deployment change needed immediately | Third copy of every file; fixes never propagate | Never — this is what created the problem |
| Keep per-project `.env` files with different variable names | Each project works independently | Unified framework cannot have a single env config; GCP Secret Manager migration is blocked | Only acceptable during the audit phase while projects still run independently |
| Flatten `core/` back into the root directory to avoid import path changes | Avoids import refactor | Defeats the entire purpose; next report type will copy files again | Never |
| Pick one project's version of a diverged file without diffing the others | Fast to start | Silent regressions in the projects whose version was not chosen | Never for critical pipeline files |
| Use `sys.path.append()` to fix broken imports after restructuring | Fixes the immediate ImportError | Masks the structural problem; breaks again in Cloud Run | Never |
| Defer resolving the `complete_deployment/` vs parent-folder version conflict | Faster to start core work | Both will be partially merged; `complete_deployment/` will be redeployed over the unified version | Never |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| LearnWorlds API | `user_id` vs `userId` field name inconsistency — diagnosticos handles both via `r.get('userId') or r.get('user_id')`, ensayos_generales only handles `user_id` | The canonical downloader must handle both field names; test with actual API responses from both project environments before choosing |
| GCP Cloud Storage | Passing Windows-style backslash paths to `_gcs_path()` — the `replace('\\', '/')` fix is present but only in storage.py versions that inherit from the diagnosticos branch; ensayos_generales storage.py also has it | Verify the unified storage.py explicitly tests path normalization; do not assume all copies have this fix |
| GCP Firestore | `from google.cloud import firestore` will raise ImportError in local development if `google-cloud-firestore` is not installed, even for local projects that never use Firestore | The unified framework must make Firestore an optional import; `firestore_service.py` must not be imported at module level by any code that runs in non-GCP mode |
| GCP Cloud Tasks | `from protobuf import timestamp_pb2` — this import path may fail depending on protobuf version; `google-cloud-tasks` bundles its own protobuf but the import style differs between protobuf 3.x and 4.x | Pin protobuf version explicitly and test the import in both local and Cloud Run environments |
| LearnWorlds Webhook | Webhook signature validation uses HMAC; `LEARNWORLDS_WEBHOOK_SECRET` must be exactly the same secret configured in LearnWorlds dashboard | After migrating to unified Cloud Run URL, the webhook endpoint URL changes — update LearnWorlds webhook configuration before cutting over |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading all user JSON into memory to resolve usernames in `save_responses_to_csv` | Slow report generation; Cloud Run memory limit exceeded | Batch the user lookup or cache the user dictionary once per pipeline run, not once per response row | When cohort size exceeds ~5,000 users in users.json |
| `for _, row in df.iterrows()` for per-user processing | Slow analysis step that scales linearly with student count | Use vectorized pandas operations or `df.apply()` with a prebuilt lookup dict | When cohort > 1,000 students |
| Cloud Run generating all PDF reports in a single request before responding | Cloud Run 60-minute timeout exceeded; memory exhaustion | The existing batch + Cloud Tasks queue pattern is the right approach — do not simplify it away during consolidation | When a batch has > 200 students |
| weasyprint loading HTML templates from disk on every call | Slow cold start on Cloud Run | Cache parsed templates in the `ReportGenerator` instance; load once in `__init__`, reuse per call | Noticeable above ~50 reports per batch |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Per-project `.env` files committed to the repo (8 `.env` files currently present in the directory tree) | API tokens, GCP credentials, and LearnWorlds secrets exposed in git history | Verify `.gitignore` covers all `.env` files before the unified framework is committed; audit git log for any `.env` accidentally committed in the past |
| `ACCESS_TOKEN` stored as a plain env variable with no rotation mechanism | If token leaks, all LearnWorlds data is accessible until manually rotated | Use GCP Secret Manager for Cloud Run deployments; document the rotation procedure |
| Webhook handler validates HMAC signature but logs `WEBHOOK_SECRET not set` as a warning rather than refusing to start | Webhooks accepted without validation if secret is missing from env | Change to a startup error (raise, not warn) in the unified webhook service |
| Student PII (email, username) in CSV files written to `data/processed/` with no cleanup | PII accumulates on local developer machines or GCS without retention policy | The existing `cleanup_temp_files()` pattern is correct — ensure it runs at end of every pipeline, including on error paths |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Core package created:** Verify `from core.assessment_downloader import AssessmentDownloader` works from the project root, not just from within the `core/` directory itself
- [ ] **Cloud Run deployment migrated:** Verify the deployed function actually uses the new unified code path — not a stale `complete_deployment/` source that gcloud cached
- [ ] **All 5 projects migrated:** `ensayos_generales` has no `assessment_mapper.py` and no `firestore_service.py` — verify it works through the plugin system without those dependencies being imported
- [ ] **Backwards compatibility verified:** Run the actual full pipeline for each of the 5 report types end-to-end and check that output files match pre-migration output (not just "no crash")
- [ ] **Webhook routing tested:** After unifying Cloud Run, verify the webhook routes the correct `assessment_id` to the correct report plugin — not just that it receives the webhook without error
- [ ] **Env var consolidation complete:** Verify there is one documented `.env.example` at the project root and that per-project `.env` files are no longer needed
- [ ] **`complete_deployment/` decommissioned:** Both `diagnosticos/complete_deployment/` and `diagnosticos_uim/complete_deployment/` must be removed from the repo after the unified Cloud Run deployment is confirmed working — otherwise the old copies will be rediscovered and reused

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Wrong canonical version chosen; one project's reports produce wrong output | MEDIUM | Diff the broken project's old file against the canonical; identify the missing method or behavior; add it to the canonical with a test |
| Cloud Run deployment uses wrong source after restructuring | LOW | Re-deploy from the correct source directory; verify with a test webhook request |
| Dependency version conflict causes weasyprint rendering regression | HIGH | Pin the exact previous weasyprint version for the affected template; refactor the template to be compatible with the target version before upgrading |
| Bare imports break after moving to `core/` package | LOW | Fix the import path; if it is in many files, use a `core/__init__.py` re-export to minimize callers that must change |
| Firestore import crashes non-GCP local pipeline | LOW | Wrap in `try/except ImportError` with a clear error message; add `google-cloud-firestore` as an optional dependency |
| Student PII CSV cleanup missed on error path | MEDIUM | Add `try/finally` around the pipeline run to ensure cleanup runs; add a manual cleanup script that can be run to clear any stale processed files |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Wrong canonical version chosen | Phase 1: Consolidation Audit | Merge decision document lists every diverged method with explicit choice |
| `complete_deployment/` missed in audit | Phase 1: Consolidation Audit | File inventory explicitly lists all `complete_deployment/` files alongside parent files |
| Dependency version conflicts | Phase 1: Consolidation Audit | Single `requirements.txt` produced; `pip install` succeeds cleanly |
| Bare imports break after restructuring | Phase 2: Core Package Creation | All 5 projects' `main.py` run successfully with `from core.X import Y` style imports |
| Hardcoded assessment type lists | Phase 2: Core Package Creation | No `self.assessment_types = [` in any file outside `core/config.py` |
| Cloud Run flat directory assumption | Phase 3: GCP Deployment Consolidation | `Dockerfile` present; `docker build && docker run` succeeds locally before deploying |
| Webhook routing after URL change | Phase 3: GCP Deployment Consolidation | LearnWorlds dashboard updated; test webhook received and routed correctly |
| PII cleanup on error paths | Phase 2: Core Package Creation | Pipeline uses `try/finally` for cleanup; verified by introducing an artificial error mid-run |

## Sources

- Direct code diff: `diagnosticos/assessment_downloader.py` vs `ensayos_generales/assessment_downloader.py` (observed method rename `cleanup_incremental_files` -> `cleanup_temp_files`, signature change in `save_responses_to_csv`, user_id field handling difference)
- Direct inspection: `diagnosticos/requirements.txt` vs `diagnosticos/complete_deployment/requirements.txt` (pandas 1.* vs 2.2.2, weasyprint 56.* vs 66.0)
- Direct inspection: `diagnosticos/assessment_analyzer.py` vs `ensayos_generales/assessment_analyzer.py` (constructor signature difference, different assessment type lists)
- Direct inspection: `diagnosticos/webhook_service.py` and `batch_processor.py` (bare imports of `firestore_service` and `task_service`)
- Direct inspection: all 5 project directories and their `complete_deployment/` subfolders (file inventory, three-way divergence confirmed)
- PROJECT.md: confirmed stated constraints (no rewrite, GCP Cloud Run must continue to work, backwards compatibility required)

---
*Pitfalls research for: Python pipeline consolidation — 5 projects into plugin-based unified framework*
*Researched: 2026-02-28*
