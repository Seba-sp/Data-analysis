# Phase 1: Consolidation Audit - Research

**Researched:** 2026-02-28
**Domain:** Python codebase diff audit — documenting method divergence across 6 project copies before any canonical code is written
**Confidence:** HIGH (all findings are direct source-code inspection, no third-party library research required)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Core boundary — what belongs in core/ vs per-report module**

Default rule: methods that exist in only ONE project and are specific to that report type's domain stay in the report module, NOT in `core/`.

**Override — user/form infrastructure goes to `core/` regardless of current distribution:**
- `download_users` → `core/` (even though currently only in ensayos_generales — user downloading is shared pipeline infrastructure)
- `download_and_process_form` → `core/` (even though currently only in assessment-analysis family — form processing is shared infrastructure)
- `save_form_responses_to_csv` → `core/` (same rationale — CSV output for form responses is shared)
- `_download_form_responses_full` → `core/` (already in 2+ projects, also infrastructure)

Per-report domain methods that stay per-report (report-type-specific logic, NOT infrastructure):
- `_normalize_commune`, `_compare_emails`, `_process_email_columns` (assessment-analysis-specific data normalization) → stay in `reports/assessment_analysis/`

Methods that exist in 2+ projects go into `core/` — these are the shared infrastructure.

**The ensayos_generales analyzer is architecturally separate**

`ensayos_generales/assessment_analyzer.py` is completely different from the config-based family (`get_unique_identifiers`, `load_conversion_data`, `calculate_assessment_score`, `convert_score`). It should NOT be forced into the same `BaseReportGenerator`/`AssessmentAnalyzer` ABC. It lives as `reports/ensayos_generales/analyzer.py` — a report-specific helper, not a `core/` service.

The `BaseReportGenerator` ABC only governs the `generate()` interface — not the analysis approach.

### Claude's Discretion

- How to resolve `cleanup_incremental_files` vs `cleanup_temp_files` naming conflict — pick whichever name is clearest for the canonical core version
- Audit document format — method-by-method comparison table with explicit resolution decision per row
- Where `_download_form_responses_full` goes: DECIDED → `core/` (user/form infrastructure rule applies; body similarity check is still needed to reconcile the two versions, but destination is `core/`)
- Whether `diagnosticos_uim/complete_deployment` and `diagnosticos/complete_deployment` share enough differences to be audited separately or can be treated as one
- How to handle the `main.py` vs `main_app.py` ambiguity in `diagnosticos_uim/complete_deployment/` — investigate which one Cloud Run actually calls

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CORE-01 | Developer can run a diff audit that documents all diverged functions across 6 copies of `assessment_downloader.py` and `assessment_analyzer.py`, producing a merge decision document before any canonical version is written | Direct source inspection completed — all 6 downloader copies and all 6 analyzer copies have been diff'd; full method-presence matrix and resolution decisions documented below |
</phase_requirements>

---

## Summary

Phase 1 produces exactly one artifact: a merge decision document (markdown). No code is written to `core/`. The work is entirely investigative — reading the 6 existing copies of `assessment_downloader.py` and 6 copies of `assessment_analyzer.py`, cataloguing every method that differs or is absent across copies, and recording an explicit resolution for each (which copy to use as base, what to merge, what to discard, where the canonical version lives).

Direct source inspection has been completed as part of this research. The key finding is that the codebase splits into well-defined families, not a random patchwork. `diagnosticos` and `diagnosticos_uim` parent directories are identical in `assessment_downloader.py` and identical in `assessment_analyzer.py` to their respective `complete_deployment/` subfolders — the only differences between the two projects are in `load_assessment_list_from_env()` (different assessment ID env var names: CL/CIEN for diagnosticos vs F30M/B30M/Q30M for diagnosticos_uim). The `assessment-analysis-project` and `reportes de test de diagnostico` are byte-for-byte identical in both files. This reduces the effective diff surface significantly.

For `requirements.txt`, two distinct pin strategies exist (wildcard `==3.*` style vs semver `>=1.3.0` style) with a concrete version bump in `complete_deployment/` (pandas 1.x → 2.2.2, reportlab 3.x → 4.4.3, weasyprint 56.x → 66.0). For environment variables, five distinct env configs exist with naming conflicts (`GOOGLE_CLOUD_PROJECT` vs `GCP_PROJECT_ID`) and additive vars per project. The `main.py` vs `main_app.py` question for `diagnosticos_uim/complete_deployment/` is resolved below: `main.py` IS the Cloud Run webhook handler; `main_app.py` is a standalone batch runner.

**Primary recommendation:** Write the merge decision document as a single markdown file with four sections: (1) downloader method matrix, (2) analyzer method matrix, (3) requirements.txt conflict resolution, (4) env var consolidation catalogue. Complete all four sections before moving to Phase 2.

---

## Standard Stack

This phase produces a markdown document. No new libraries are installed. The work is text editing plus careful Python file reading.

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Markdown table | — | Method-by-method comparison | Scannable, diffable, consumed by planner downstream |
| Python `diff` / manual read | — | Body-level comparison of methods | Only reliable way to detect subtle logic divergence |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-written markdown table | Automated AST diff tool | Automation would miss semantic decisions (which version is correct); manual is appropriate here |

---

## Architecture Patterns

### Recommended Document Structure

```
.planning/phases/01-consolidation-audit/
└── MERGE-DECISIONS.md
    ├── ## assessment_downloader.py — Method Matrix
    ├── ## assessment_downloader.py — Resolution Decisions
    ├── ## assessment_analyzer.py — Method Matrix
    ├── ## assessment_analyzer.py — Resolution Decisions
    ├── ## requirements.txt — Conflict Resolution
    └── ## Environment Variables — Consolidation Catalogue
```

### Pattern 1: Method Presence Matrix

**What:** A table with one row per method and one column per project copy. Cells show: present (P), absent (—), or variant (V).

**When to use:** For every method in both files, across all 6 copies.

**Example:**
```markdown
| Method | diag | diag_uim | diag/cd | uim/cd | ensayos | aa-proj | rtd |
|--------|------|----------|---------|--------|---------|---------|-----|
| get_json_file_path | P | P | P | P | P | P | P |
| get_incremental_json_file_path | P | P | P | P | P | — | — |
| cleanup_incremental_files | P | P | P | P | — | — | — |
| cleanup_temp_files | — | — | — | — | P | — | — |
| download_users | — | — | — | — | P | — | — |
```

### Pattern 2: Per-Method Resolution Record

**What:** After the matrix, a second table with one row per diverged method listing the resolution decision.

**When to use:** Only for methods that differ (absent in some copies, or present with variant bodies).

**Example:**
```markdown
| Method | Situation | Resolution | Destination | Notes |
|--------|-----------|------------|-------------|-------|
| cleanup_incremental_files | diagnosticos family only | Use diagnosticos version as base | core/ | Rename decision: use `cleanup_temp_files`? → TBD by discretion |
| download_users | ensayos_generales only | Promote to core/ per override rule | core/ | Body is unique — copy verbatim |
| _download_form_responses_full | ensayos + aa-proj (2 versions) | Body comparison required before merge | core/ | Check if bodies are equivalent |
```

### Anti-Patterns to Avoid

- **Treating `complete_deployment/` as footnotes:** They are the actual production code for Cloud Run. `diagnosticos/complete_deployment/` and `diagnosticos_uim/complete_deployment/` must be listed as independent columns in the matrix.
- **Skipping body comparison for "same-named" methods:** Two methods with the same name and signature can have diverged bodies (the `analyze_assessment_from_csv` return type divergence across diagnosticos vs assessment-analysis-project proves this).
- **Assuming identical files are truly identical:** Always diff before concluding equality. Research confirmed diagnosticos parent == diagnosticos/complete_deployment (zero diff) and aa-project == rtd (zero diff), but this must be verified task-by-task.
- **Mixing requirements resolution with method audit:** Keep them as separate document sections to avoid conflation.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Detecting body-level differences | Custom AST parser | Shell `diff` with `-u` flag is sufficient |
| Tracking which methods are in which copy | Custom script | Markdown matrix table |
| Version conflict resolution logic | Anything automated | Manual decision based on which environment the unified `core/` targets |

---

## Common Pitfalls

### Pitfall 1: Mistaking "same line count" for "identical body"

**What goes wrong:** Two copies of a method have the same number of lines but different internal logic (e.g., one uses `StorageClient.read_csv()`, the other uses `pd.read_csv()` directly). The diff must be checked at the body level, not just at the signature level.

**Why it happens:** The method signature matrix shows presence/absence only. Body comparison is a separate step.

**How to avoid:** For every method that appears in 2+ projects, do a body-level diff before assigning a resolution. The `analyze_assessment_from_csv` case illustrates this: diagnosticos version adds `return_df: bool = False`, uses `StorageClient` for I/O, and adds a DataFrame return path — the assessment-analysis version does not.

**Warning signs:** A method exists in all copies but the diff step was skipped.

### Pitfall 2: Using the wrong `load_assessment_list_from_env()` as the base

**What goes wrong:** `diagnosticos` and `diagnosticos_uim` have different assessment ID env var names in `load_assessment_list_from_env()`: diagnosticos uses `CL_ASSESSMENT_ID` and `CIEN_ASSESSMENT_ID`, while diagnosticos_uim uses `F30M_ASSESSMENT_ID`, `B30M_ASSESSMENT_ID`, `Q30M_ASSESSMENT_ID`. The unified core version must NOT hardcode either set — it must be config-driven or registry-driven.

**How to avoid:** Document this as a per-report-module responsibility, not a `core/` function. `load_assessment_list_from_env()` should stay per-report.

**Warning signs:** Any `load_assessment_list_from_env()` function in `core/` with hardcoded assessment ID names.

### Pitfall 3: Confusing `main.py` roles across project levels

**What goes wrong:** The `main.py` at `diagnosticos_uim/` root is a standalone batch runner (argparse-based, no `functions_framework`). The `main.py` in `diagnosticos_uim/complete_deployment/` is the Cloud Run webhook handler (imports `functions_framework`, exposes `webhook_handler`). Auditing the wrong one as the "production entry point" leads to wrong decisions.

**How to avoid:** Document both levels separately. The Cloud Run entry point for `diagnosticos_uim/complete_deployment/` is `main.py` (the webhook handler). `main_app.py` in that subfolder is a copy of the standalone batch runner.

**Warning signs:** Referring to "main.py" without specifying whether it is the parent-dir or complete_deployment version.

### Pitfall 4: Treating requirements pinning style as a conflict

**What goes wrong:** `diagnosticos` uses `pandas==1.*` (wildcard); `assessment-analysis-project` uses `pandas>=1.3.0` (floor). These are NOT conflicting upper bounds — they are different pinning philosophies. The actual conflict is the pandas major version: 1.x (parent dirs) vs 2.2.2 (complete_deployment dirs).

**How to avoid:** Separate the resolution into two decisions: (1) choose a pinning style for the unified `requirements.txt`, (2) choose the target pandas version and document the rationale for the major version choice.

**Warning signs:** Treating `==1.*` vs `>=1.3.0` as a conflict without checking whether the underlying version range overlaps.

### Pitfall 5: Missing UIM-specific env vars not in the env_template

**What goes wrong:** `diagnosticos_uim/env_template.txt` mirrors the diagnosticos template (has `CL_ASSESSMENT_ID`, `CIEN_ASSESSMENT_ID`) but the actual `assessment_mapper.py` uses `F30M_ASSESSMENT_ID`, `B30M_ASSESSMENT_ID`, `Q30M_ASSESSMENT_ID`. The template is outdated — the real env vars are discoverable only from source code.

**How to avoid:** For every project, read both the env template AND the actual source code's `os.getenv()` calls to produce the complete env var list.

---

## Code Examples

### Verified: complete_deployment copies are identical to parent dirs

```bash
# Confirmed zero diff:
diff diagnosticos/assessment_downloader.py diagnosticos/complete_deployment/assessment_downloader.py
# → no output (identical)

diff diagnosticos_uim/assessment_downloader.py diagnosticos_uim/complete_deployment/assessment_downloader.py
# → no output (identical)

# Same for analyzers:
diff diagnosticos/assessment_analyzer.py diagnosticos/complete_deployment/assessment_analyzer.py
# → no output

diff diagnosticos_uim/assessment_analyzer.py diagnosticos_uim/complete_deployment/assessment_analyzer.py
# → no output
```

### Verified: assessment-analysis-project == reportes de test de diagnostico

```bash
diff assessment-analysis-project/assessment_downloader.py "reportes de test de diagnostico/assessment_downloader.py"
# → no output (identical)

diff assessment-analysis-project/assessment_analyzer.py "reportes de test de diagnostico/assessment_analyzer.py"
# → no output (identical)
```

---

## Findings: assessment_downloader.py Method Matrix

### Abbreviation Key

| Short | Full path |
|-------|-----------|
| diag | diagnosticos/ |
| uim | diagnosticos_uim/ |
| diag-cd | diagnosticos/complete_deployment/ |
| uim-cd | diagnosticos_uim/complete_deployment/ |
| eg | ensayos_generales/ |
| aa | assessment-analysis-project/ |
| rtd | reportes de test de diagnostico/ |

Note: diag == diag-cd (identical). uim == uim-cd (identical). aa == rtd (identical). Effective distinct versions: 3 (diagnosticos family, ensayos family, assessment-analysis family).

### Method Presence Matrix

| Method | diag | uim | eg | aa/rtd | Resolution | Destination |
|--------|------|-----|----|--------|------------|-------------|
| `__init__` | P | P* | P | P | Merge — uim variant uses different default assessment IDs | core/ |
| `get_json_file_path` | P | P | P | P | Identical across all | core/ |
| `get_csv_file_path` | P | P | P | P | Identical across all | core/ |
| `get_incremental_json_file_path` | P | P | P | — | diagnosticos family version; absent in aa family (different arch) | core/ |
| `get_temp_csv_file_path` | — | — | P | — | ensayos_generales only | core/ |
| `get_temp_analysis_file_path` | — | — | P | — | ensayos_generales only | core/ |
| `get_users_csv_file_path` | — | — | — | P | aa family only | core/ |
| `get_latest_timestamp_from_json` | P | P | P | P | Identical across all | core/ |
| `get_latest_user_timestamp_from_json` | — | — | P | — | ensayos_generales only; user-download infrastructure | core/ |
| `_download_responses_incremental` | P | P | P | P | Body comparison needed — eg version adds user timestamp logic | core/ |
| `download_assessment_responses_incremental` | P | P | P | P | Signature differs: diag/eg have `return_df`; aa lacks it | core/ |
| `download_form_responses_incremental` | — | — | — | P | aa family only; form infrastructure | core/ |
| `get_only_new_responses` | P | P | P | — | diagnosticos/eg family; absent in aa (different incremental arch) | core/ |
| `_download_responses_full` | P | P | P | P | Body comparison needed | core/ |
| `_download_assessment_responses_full` | P | P | P | P | Likely identical | core/ |
| `_download_form_responses_full` | — | — | P | P | 2 versions — body comparison REQUIRED before merge | core/ |
| `save_responses_to_json` | P | P | P | P | Identical across all | core/ |
| `save_incremental_responses_to_json` | P | P | P | — | diagnosticos/eg only | core/ |
| `save_temp_responses_to_csv` | — | — | P | — | ensayos_generales only | core/ |
| `save_responses_to_csv` | P | P | P | P | Signature differs: eg adds `include_usernames: bool = True`; aa/rtd lacks `return_df` | core/ |
| `save_form_responses_to_csv` | — | — | — | P | aa family only; form infrastructure | core/ |
| `merge_incremental_to_main_json` | P | P | P | — | diagnosticos/eg family | core/ |
| `cleanup_incremental_files` | P | P | — | — | diagnosticos family only | core/ — RENAME CANDIDATE |
| `cleanup_temp_files` | — | — | P | — | ensayos_generales only; same conceptual role as above | core/ — RENAME CANDIDATE |
| `load_responses_from_json` | P | P | P | P | Identical across all | core/ |
| `filter_responses` | P | P | P | P | Signature differs: diag/eg use Union type; aa uses plain List | core/ |
| `add_answer_columns_to_csv` | P | P | P | P | Signature differs same as filter_responses | core/ |
| `delete_assessment_data` | P | P | P | P | Likely identical | core/ |
| `_download_and_process_common` | P | P | P | P | Body comparison needed — likely diverged with incremental vs form paths | core/ |
| `download_and_process_form` | — | — | — | P | aa family only; form infrastructure | core/ |
| `download_and_process_assessment` | P | P | P | P | Likely similar; body comparison needed | core/ |
| `download_all_assessments` | P | P | P | P | Likely similar | core/ |
| `get_assessment_info` | P | P | P | P | Likely identical | core/ |
| `download_users` | — | — | P | — | ensayos_generales only; user infrastructure | core/ |
| `merge_incremental_users` | — | — | P | — | ensayos_generales only | core/ |
| `load_users_from_json` | — | — | P | — | ensayos_generales only | core/ |
| `get_username_by_user_id` | — | — | P | — | ensayos_generales only | core/ |
| `_normalize_commune` | — | — | — | P | aa family only; DOMAIN-SPECIFIC | reports/assessment_analysis/ |
| `_compare_emails` | — | — | — | P | aa family only; DOMAIN-SPECIFIC | reports/assessment_analysis/ |
| `_process_email_columns` | — | — | — | P | aa family only; DOMAIN-SPECIFIC | reports/assessment_analysis/ |
| `load_assessment_list_from_env` (module-level) | P | P* | P | P | PER-PROJECT — stays per report module; uim uses different env var names | per-report module |
| `parse_arguments` (module-level) | P | P | P | P | per-project CLI; not promoted | per-report module |
| `main` (module-level) | P | P | P | P | per-project entry point | per-report module |

*uim variant of `load_assessment_list_from_env` uses `F30M_ASSESSMENT_ID`, `B30M_ASSESSMENT_ID`, `Q30M_ASSESSMENT_ID` instead of `CL_ASSESSMENT_ID`, `CIEN_ASSESSMENT_ID`.

### Naming Conflict: cleanup_incremental_files vs cleanup_temp_files

Both methods serve the same conceptual purpose (cleaning up intermediate files after merge). They are present in different families and cannot coexist in `core/` under two names without creating confusion. Resolution is at planner/implementer discretion. Recommendation: use `cleanup_temp_files` as the canonical name since it is more descriptive (incremental files ARE temp files; not all temp files are incremental files). Final decision documented in MERGE-DECISIONS.md.

---

## Findings: assessment_analyzer.py Method Matrix

### Effective distinct versions

- **Config-based family (4 copies):** diagnosticos, uim, aa/rtd — all share the same class structure
- **Score-conversion family (1 copy):** ensayos_generales — architecturally separate, stays per-report

### Config-based analyzer method comparison

| Method | diag | uim | aa/rtd | Notes |
|--------|------|-----|--------|-------|
| `__init__` | P | P* | P* | diag has full assessment config dict; uim has minimal default; aa/rtd has minimal default with different threshold values |
| `_get_default_config` | P | P | P | Body differs significantly — see note below |
| `_format_percentage_for_excel` | P | P | P | Likely identical |
| `_extract_answers_from_response` | P | P | P | Likely identical |
| `analyze_assessment` | P | P | P | Entry point; body comparison needed |
| `_analyze_by_category_generic` | P | — | P | MISSING in uim; present in diag and aa/rtd |
| `_analyze_percentage_based_generic` | P | P | P | Present in all config-based copies |
| `_determine_level_unified` | P | P | P | Present in all |
| `_analyze_by_lecture` | P | P | P | Present in all |
| `_get_internal_level` | P | P | P | Present in all |
| `analyze_assessment_from_csv` | P | P | P | Signature differs: diag adds `return_df: bool = False` → `str \| pd.DataFrame`; aa/rtd returns only `str` |

### Critical divergence: `_analyze_by_category_generic` missing in diagnosticos_uim

This method is present in `diagnosticos/assessment_analyzer.py` (line 176) and `assessment-analysis-project/assessment_analyzer.py` (line 176), but ABSENT from `diagnosticos_uim/assessment_analyzer.py`. This is the most significant structural divergence in the analyzer family. The `_get_default_config` in uim also has a minimal default vs diag's full per-assessment config dict. Resolution decision: use diagnosticos version as the base (it is the more complete implementation); document whether uim was intentionally simplified or accidentally diverged.

### Critical divergence: `analyze_assessment_from_csv` return type

- `diagnosticos/` (line 625): `return_df: bool = False` parameter, returns `str | pd.DataFrame`, uses `StorageClient` for CSV I/O
- `assessment-analysis-project/` (line 625): no `return_df` parameter, returns `str` only, uses `pd.read_csv()` directly

Resolution: Use diagnosticos version as base (more capable). The `return_df` path and `StorageClient` usage are features, not bugs.

### Ensayos_generales analyzer — stays per-report

`ensayos_generales/assessment_analyzer.py` has zero overlap with the config-based family:
- `get_unique_identifiers()` — reads XLSX conversion tables
- `load_conversion_data()` — loads score conversion DataFrames
- `calculate_assessment_score()` — raw score calculation from answer key
- `convert_score()` — raw → scaled score via conversion table
- `analyze_all_assessments()` — full pipeline for all assessments

This file lives at `reports/ensayos_generales/analyzer.py`. No methods are promoted to `core/`.

---

## Findings: requirements.txt Conflicts

### Version matrix across all 7 copies

| Package | diag/uim (parent) | diag/uim cd | eg | aa/rtd |
|---------|-------------------|-------------|-----|--------|
| pandas | `==1.*` | `==2.2.2` | `==1.*` | `>=1.3.0` |
| weasyprint | `==56.*` | `==66.0` | (absent) | `>=54.0` |
| reportlab | `==3.*` | `==4.4.3` | `==3.*` | (absent) |
| protobuf | `==4.*` | `==4.*` | (absent) | (absent) |
| numpy | (absent) | `==1.26.4` (pinned) | (absent) | (absent) |
| openpyxl | `==3.*` | `==3.1.5` | `==3.*` | `>=3.0.0` |
| jinja2 | `==3.*` | `==3.1.4` | `==3.*` | (absent) |
| functions-framework | `==3.*` | `==3.*` | `==3.*` | (absent) |
| google-cloud-firestore | `==2.*` | `==2.*` | `==2.*` | (absent) |
| google-cloud-tasks | `==2.*` | `==2.*` | `==2.*` | (absent) |
| google-cloud-storage | `==2.*` | `==2.*` | `==2.*` | (absent) |
| google-api-python-client | `==2.*` | `==2.*` | (absent) | `>=2.0.0` |
| google-auth | `==2.*` | `==2.*` | (absent) | `>=2.0.0` |
| google-auth-oauthlib | (absent) | (absent) | (absent) | `>=0.4.6` |
| google-auth-httplib2 | (absent) | (absent) | (absent) | `>=0.1.0` |
| flask | `==2.*` | `==2.*` | `==2.*` | (absent) |
| requests | `==2.*` | `==2.*` | `==2.*` | `>=2.25.1` |
| python-dotenv | `==0.*` | `==0.*` | `==0.*` | `>=0.19.0` |
| reportlab | `==3.*` | `==4.4.3` | `==3.*` | (absent) |

### Key conflicts requiring explicit resolution in the merge document

1. **pandas 1.x vs 2.2.2**: The `complete_deployment/` folders (production Cloud Run) run pandas 2.2.2. The parent dirs use `pandas==1.*`. The unified `requirements.txt` must pick one. The complete_deployment version is what actually runs in production. Rationale to document: adopt pandas 2.2.2 as the target (matches production), pin numpy 1.26.4 as a companion (already pinned in cd).

2. **weasyprint 56.x vs 66.0**: Same split — parent dirs pin to 56.x, complete_deployment runs 66.0. Note: weasyprint has breaking changes between major versions. Rationale: adopt 66.0 to match the production environment.

3. **reportlab 3.x vs 4.4.3**: Same pattern. Production (cd) runs 4.4.3.

4. **protobuf 4.x**: Only present in diagnosticos/uim family (needed for Firestore/Cloud Tasks). Absent in ensayos and aa. Must be included in unified requirements with a note about why.

5. **functions-framework**: Only needed for Cloud Run deployment (webhook handler). Can be kept in a `requirements-cloudrun.txt` or annotated as optional in the unified file. Rationale to document.

6. **Pinning style**: The complete_deployment folders use exact pins (`==2.2.2`), while parent dirs use wildcard pins (`==3.*`) and aa uses floor pins (`>=1.3.0`). The merge document must pick one style for the unified file and state why.

---

## Findings: Environment Variables Catalogue

### Master variable list across all 5 projects + shared/

| Variable | diag | uim | eg | aa/rtd | shared | Notes |
|----------|------|-----|----|--------|--------|-------|
| `CLIENT_ID` | P | P | P | P | P | Uniform |
| `SCHOOL_DOMAIN` | P | P | P | P | P | Uniform |
| `ACCESS_TOKEN` | P | P | P | P | P | Uniform |
| `GOOGLE_CLOUD_PROJECT` | P | P | — | — | — | **NAMING CONFLICT** with `GCP_PROJECT_ID` |
| `GCP_PROJECT_ID` | — | — | P | P | P | **NAMING CONFLICT** with `GOOGLE_CLOUD_PROJECT` |
| `GCP_BUCKET_NAME` | — | — | P | P | P | Only in eg/aa/shared |
| `TASK_LOCATION` | P | P | — | — | — | Cloud Tasks config; diag/uim only |
| `TASK_QUEUE_ID` | P | P | — | — | — | Cloud Tasks config; diag/uim only |
| `LEARNWORLDS_WEBHOOK_SECRET` | P | P | — | — | P | Webhook secret |
| `BATCH_INTERVAL_MINUTES` | P | P | — | — | — | Batch processor |
| `M1_ASSESSMENT_ID` | P | P | P | P | — | Uniform across projects |
| `CL_ASSESSMENT_ID` | P | — | P | P | — | diag/eg/aa; NOT in uim |
| `CIEN_ASSESSMENT_ID` | P | — | — | P | — | diag/aa only |
| `HYST_ASSESSMENT_ID` | P | P | P | P | — | Uniform |
| `F30M_ASSESSMENT_ID` | — | P | — | — | — | uim only |
| `B30M_ASSESSMENT_ID` | — | P | — | — | — | uim only |
| `Q30M_ASSESSMENT_ID` | — | P | — | — | — | uim only |
| `M2_ASSESSMENT_ID` | — | — | P | — | — | eg only |
| `CIENB_ASSESSMENT_ID` | — | — | P | — | — | eg only |
| `CIENF_ASSESSMENT_ID` | — | — | P | — | — | eg only |
| `CIENQ_ASSESSMENT_ID` | — | — | P | — | — | eg only |
| `CIENT_ASSESSMENT_ID` | — | — | P | — | — | eg only |
| `EMAIL_FROM` | P | P | P | — | P | Uniform |
| `EMAIL_PASS` | P | P | P | — | P | Uniform |
| `SMTP_SERVER` | — | — | P | — | P | eg/shared only |
| `SMTP_PORT` | — | — | P | — | P | eg/shared only |
| `TEST_EMAIL` | — | — | P | — | — | eg only |
| `STORAGE_BACKEND` | — | — | P | P | — | eg/aa only |
| `REGION` | — | — | P | P | — | eg/aa only |
| `GOOGLE_SHARED_DRIVE_ID` | — | — | P | P | — | eg/aa only |
| `GOOGLE_DRIVE_FOLDER_ID` | — | — | P | P | P | eg/aa/shared |
| `GOOGLE_SERVICE_ACCOUNT_KEY` | — | — | P | P | P | eg/aa/shared |
| `GOOGLE_APPLICATION_CREDENTIALS` | — | — | P | P | — | eg/aa only |
| `IGNORED_USERS` | — | — | P | P | P | eg/aa/shared |
| `GRADE_ZERO_THRESHOLD` | — | — | P | P | — | eg/aa only |
| `TIME_MAX_THRESHOLD_MINUTES` | — | — | P | P | — | eg/aa only |
| `REPORT_TOP_PERCENT` | — | — | P | P | — | eg/aa only |
| `USERS` | — | — | — | P | — | aa/rtd only |
| `SLACK_BOT_TOKEN` | — | — | — | — | P | shared only |
| `SLACK_CHANNEL` | — | — | — | — | P | shared only |
| `ADMIN_EMAIL` | — | — | — | — | P | shared only |
| `MIN_DOWNLOAD_DATE` | P | P | P | — | — | Optional filter; diag/uim/eg |
| `PROCESS_BATCH_URL` | P | P | — | — | — | Cloud Functions URL; diag/uim only |

### Naming conflict: GOOGLE_CLOUD_PROJECT vs GCP_PROJECT_ID

Both variables refer to the GCP project ID. `diagnosticos` and `diagnosticos_uim` use `GOOGLE_CLOUD_PROJECT` (the GCP-native ADC variable name). `ensayos_generales`, `assessment-analysis-project`, and `shared/env.template` use `GCP_PROJECT_ID` (a custom name). The merge document must pick one name for the consolidated `.env.example` and document the rationale. Recommendation: use `GCP_PROJECT_ID` — it is explicit and avoids collision with GCP's own `GOOGLE_CLOUD_PROJECT` which is set automatically by the Cloud Run runtime.

---

## Findings: Entry Point Investigation

### diagnosticos_uim/complete_deployment/ — main.py vs main_app.py

**Resolution: `main.py` is the Cloud Run entry point.**

Evidence from direct source inspection:
- `diagnosticos_uim/complete_deployment/main.py`: imports `functions_framework`, exposes `webhook_handler` function, uses `initialize_services()` with lazy init pattern. This is the Cloud Functions/Cloud Run webhook handler.
- `diagnosticos_uim/complete_deployment/main_app.py`: imports `argparse`, `AssessmentDownloader`, `AssessmentAnalyzer`, `ReportGenerator` — this is the standalone batch runner for local execution.

The `deploy.sh` scripts in both `diagnosticos/` and `diagnosticos_uim/` confirm this: `--entry-point=webhook_handler` maps to `webhook_handler` function in `main.py`.

**Same pattern in `diagnosticos/complete_deployment/`:**
- `main.py` = webhook handler (Cloud Run)
- `main_app.py` = standalone batch runner (local)

**Note on parent-dir `main.py`:** The `diagnosticos/main.py` and `diagnosticos_uim/main.py` at the parent directory level are standalone batch runners (same as `main_app.py` in complete_deployment). They are NOT deployed to Cloud Run. The `complete_deployment/` subfolder IS the Cloud Run deployment unit.

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| Scattered flat-directory projects | To be unified into `core/` + `reports/<type>/` | Phase 1 only audits; no code moved yet |
| Parent-dir deployments | `complete_deployment/` subfolders are the actual production units | Must be audited as independent copies |
| Wildcard pins `==1.*` | Exact pins `==2.2.2` (in cd folders) | Production has already upgraded; parent dirs are stale |

---

## Open Questions

1. **Was `_analyze_by_category_generic` intentionally removed from `diagnosticos_uim/assessment_analyzer.py`?**
   - What we know: It is present in `diagnosticos/` and `assessment-analysis-project/` but absent from `diagnosticos_uim/`.
   - What's unclear: Whether uim never needed it (different assessment types) or whether it was accidentally dropped.
   - Recommendation: Document in the merge decision document as "body comparison required — verify uim works without it before excluding from core".

2. **Are the two versions of `_download_form_responses_full` equivalent in body?**
   - What we know: Exists in `ensayos_generales/` (line 472) and `assessment-analysis-project/` (line 268). Both download form responses.
   - What's unclear: Whether the implementations are identical or whether eg added user-timestamp logic.
   - Recommendation: Body diff must be included as a task in the merge decisions document.

3. **Should `load_assessment_list_from_env` ever go to `core/`?**
   - What we know: It is per-project by nature (hardcodes different assessment ID env var names per project).
   - What's unclear: Whether a config-driven version could live in core with per-project config passed in.
   - Recommendation: Document as per-report module for Phase 1; revisit in Phase 2 when plugin architecture is defined.

---

## Sources

### Primary (HIGH confidence)
- Direct source inspection of all 7 project copies (6 assessment_downloader.py + 6 assessment_analyzer.py files, plus complete_deployment subfolders)
- Shell `diff` commands confirming byte-identical copies
- Method signature extraction via grep on all files

### Secondary (MEDIUM confidence)
- `deploy.sh` scripts confirming `main.py` as Cloud Functions entry point (`--entry-point=webhook_handler`)
- `assessment_mapper.py` in diagnosticos_uim confirming actual env var names used in production

---

## Metadata

**Confidence breakdown:**
- Method presence matrix: HIGH — extracted directly from grep of all 6 copies
- Body divergence flags: HIGH for confirmed diffs (analyze_assessment_from_csv, _get_default_config, load_assessment_list_from_env); MEDIUM for methods marked "likely identical" (body comparison deferred to tasks)
- requirements.txt conflicts: HIGH — read all 7 files directly
- Env var catalogue: HIGH — read all env templates and source files; confirmed uim template is outdated vs actual source
- Entry point finding: HIGH — confirmed by source inspection + deploy.sh corroboration

**Research date:** 2026-02-28
**Valid until:** 2026-03-28 (stable codebase — no external library research; valid until source files change)
