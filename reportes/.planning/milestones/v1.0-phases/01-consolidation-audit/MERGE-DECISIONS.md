# Merge Decisions: Unified Report Pipeline

**Produced:** 2026-02-28
**Status:** Final — all decisions explicit before Phase 2 begins
**Source:** 01-RESEARCH.md + body diffs confirmed in Plan 01-01 Task 1

---

## 1. assessment_downloader.py — Method Matrix

Abbreviation key: **diag** = diagnosticos/ (== diagnosticos/complete_deployment/); **uim** = diagnosticos_uim/ (== diagnosticos_uim/complete_deployment/); **eg** = ensayos_generales/; **aa** = assessment-analysis-project/ (== reportes de test de diagnostico/).

Status values: **IDENTICAL** = exact same body across the listed copies; **DIVERGES** = bodies differ in at least one pair; **ABSENT** = method does not exist in that copy.

| Method | diag | uim | eg | aa/rtd | Status | Destination |
|--------|------|-----|----|--------|--------|-------------|
| `__init__` | P | P | P | P | DIVERGES | `core/` |
| `get_json_file_path` | P | P | P | P | IDENTICAL | `core/` |
| `get_csv_file_path` | P | P | P | P | IDENTICAL | `core/` |
| `get_incremental_json_file_path` | P | P | P | — | IDENTICAL (diag/uim/eg) | `core/` |
| `get_temp_csv_file_path` | — | — | P | — | ABSENT in diag/uim/aa | `core/` |
| `get_temp_analysis_file_path` | — | — | P | — | ABSENT in diag/uim/aa | `core/` |
| `get_users_csv_file_path` | — | — | — | P | ABSENT in diag/uim/eg | `core/` |
| `get_latest_timestamp_from_json` | P | P | P | P | DIVERGES (aa reads `created`; diag/eg read `submittedTimestamp`) | `core/` |
| `get_latest_user_timestamp_from_json` | — | — | P | — | ABSENT in diag/uim/aa | `core/` |
| `_download_responses_incremental` | P | P | P | P | DIVERGES (aa: no min_date logic, uses `created` timestamp; diag/eg: use `submittedTimestamp` + optional MIN_DOWNLOAD_DATE filter) | `core/` |
| `download_assessment_responses_incremental` | P | P | P | P | DIVERGES (diag/eg: has `return_df` param; aa: no `return_df`; aa also has `get_only_new_responses` replaced by `download_form_responses_incremental`) | `core/` |
| `get_only_new_responses` | P | P | P | — | ABSENT in aa | `core/` |
| `download_form_responses_incremental` | — | — | — | P | ABSENT in diag/uim/eg | `core/` |
| `_download_responses_full` | P | P | P | P | DIVERGES (aa: no MIN_DOWNLOAD_DATE filter, no `reached_min_date` loop flag) | `core/` |
| `_download_assessment_responses_full` | P | P | P | P | IDENTICAL across all | `core/` |
| `_download_form_responses_full` | — | — | P | P | IDENTICAL (eg == aa — both delegate to `_download_responses_full`) | `core/` |
| `save_responses_to_json` | P | P | P | P | IDENTICAL across all | `core/` |
| `save_incremental_responses_to_json` | P | P | P | — | IDENTICAL (diag/uim/eg) | `core/` |
| `save_temp_responses_to_csv` | — | — | P | — | ABSENT in diag/uim/aa | `core/` |
| `save_responses_to_csv` | P | P | P | P | DIVERGES (eg adds `include_usernames` param; eg also adds "No respondida" for empty answers in body) | `core/` |
| `save_form_responses_to_csv` | — | — | — | P | ABSENT in diag/uim/eg | `core/` |
| `merge_incremental_to_main_json` | P | P | P | — | IDENTICAL (diag/uim/eg) | `core/` |
| `cleanup_incremental_files` | P | P | — | — | ABSENT in eg/aa — RENAME RESOLVED: use `cleanup_temp_files` | `core/` |
| `cleanup_temp_files` | — | — | P | — | ABSENT in diag/uim/aa — same conceptual method as above | `core/` |
| `load_responses_from_json` | P | P | P | P | IDENTICAL across all | `core/` |
| `filter_responses` | P | P | P | P | DIVERGES (diag/uim/eg: Union type hint; aa: plain List; diag: `r.get('userId') or r.get('user_id')`; eg/aa: `r.get('user_id')` only) | `core/` |
| `add_answer_columns_to_csv` | P | P | P | P | DIVERGES (eg adds "No respondida" substitution for empty/NaN answers; diag/aa do not) | `core/` |
| `delete_assessment_data` | P | P | P | P | IDENTICAL across all | `core/` |
| `_download_and_process_common` | P | P | P | P | DIVERGES (diag: incremental mode keeps data in memory; eg: incremental mode writes temp CSV via `save_temp_responses_to_csv`; aa: no `incremental_mode` param at all) | `core/` |
| `download_and_process_form` | — | — | — | P | ABSENT in diag/uim/eg | `core/` |
| `download_and_process_assessment` | P | P | P | P | DIVERGES (aa: no `incremental_mode` param) | `core/` |
| `download_all_assessments` | P | P | P | P | DIVERGES (aa: no `incremental_mode` param; diag/eg: differ only in one docstring line — functionally equivalent) | `core/` |
| `get_assessment_info` | P | P | P | P | IDENTICAL across all | `core/` |
| `download_users` | — | — | P | — | ABSENT in diag/uim/aa | `core/` |
| `merge_incremental_users` | — | — | P | — | ABSENT in diag/uim/aa | `core/` |
| `load_users_from_json` | — | — | P | — | ABSENT in diag/uim/aa | `core/` |
| `get_username_by_user_id` | — | — | P | — | ABSENT in diag/uim/aa | `core/` |
| `_normalize_commune` | — | — | — | P | ABSENT in diag/uim/eg — DOMAIN-SPECIFIC | `reports/assessment_analysis/` |
| `_compare_emails` | — | — | — | P | ABSENT in diag/uim/eg — DOMAIN-SPECIFIC | `reports/assessment_analysis/` |
| `_process_email_columns` | — | — | — | P | ABSENT in diag/uim/eg — DOMAIN-SPECIFIC | `reports/assessment_analysis/` |
| `load_assessment_list_from_env` (module-level fn) | P | P* | P | P | PER-PROJECT — hardcodes project-specific assessment ID env var names | per-report module |
| `parse_arguments` (module-level fn) | P | P | P | P | PER-PROJECT CLI entry | per-report module |
| `main` (module-level fn) | P | P | P | P | PER-PROJECT entry point | per-report module |

*uim variant uses `F30M_ASSESSMENT_ID`, `B30M_ASSESSMENT_ID`, `Q30M_ASSESSMENT_ID` vs diag's `CL_ASSESSMENT_ID`, `CIEN_ASSESSMENT_ID`.

---

## 2. assessment_downloader.py — Resolution Decisions

| Method | Situation | Resolution | Destination | Canonical Base | Notes |
|--------|-----------|------------|-------------|----------------|-------|
| `__init__` | diag/eg: include MIN_DOWNLOAD_DATE handling; aa: no date filter; uim: same as diag | Use diag as base. Include MIN_DOWNLOAD_DATE optional filter (feature, not bug). aa's absence of this is a regression. | `core/` | diagnosticos | `self.min_date` and `self.min_timestamp` attributes come from diag/eg; include them |
| `get_latest_timestamp_from_json` | diag/eg use `submittedTimestamp` field; aa uses `created` field | **CONFLICT on field name.** The LearnWorlds API uses `submittedTimestamp` for assessment responses and `created` for user records and form responses. Resolution: rename method to clarify scope — `get_latest_assessment_timestamp_from_json` (reads `submittedTimestamp`) and keep `get_latest_user_timestamp_from_json` (reads `created`). Alternatively, pass the field name as a param. Implement the diag version as canonical — the aa version inadvertently uses `created` for assessments, which would be wrong for assessment pagination. | `core/` | diagnosticos | The aa version is a latent bug — it reads `created` on assessment records which is the LearnWorlds account creation date, not submission date. diag is correct. |
| `_download_responses_incremental` | diag/eg: use `submittedTimestamp` + MIN_DOWNLOAD_DATE filter; aa: no date filter, uses `created` | Use diag as base. MIN_DOWNLOAD_DATE filtering is a feature. aa version lacks it and uses the wrong timestamp field (`created` instead of `submittedTimestamp`). | `core/` | diagnosticos | |
| `download_assessment_responses_incremental` | diag/eg: has `return_df: bool = False` param; aa: no `return_df`, simpler wrapper | Use diag as base (more capable). Include `return_df` param. | `core/` | diagnosticos | |
| `get_only_new_responses` | diag/eg only; aa replaced this with a different architecture (no incremental JSON) | Include from diag. aa family does not use incremental JSON pattern. | `core/` | diagnosticos | |
| `download_form_responses_incremental` | aa only; diag/eg do not process forms | Include from aa. Form download infrastructure. | `core/` | assessment-analysis-project | |
| `_download_responses_full` | diag/eg: MIN_DOWNLOAD_DATE filter stops pagination early; aa: no filter | Use diag as base. MIN_DOWNLOAD_DATE filter is a production feature. | `core/` | diagnosticos | |
| `_download_assessment_responses_full` | Identical across all | Copy verbatim from diag. | `core/` | diagnosticos | |
| `_download_form_responses_full` | eg and aa: **bodies are IDENTICAL** — both are single-line wrappers: `return self._download_responses_full(form_id, form_name, "forms")` | Copy verbatim — either source is identical. | `core/` | ensayos_generales (or aa — identical) | Q2 confirmed resolved: bodies are identical |
| `save_responses_to_csv` | eg: adds `include_usernames: bool = True` param and "No respondida" substitution for empty answers; diag: no username lookup, no empty-answer substitution; aa: same as diag | Use eg as base (most feature-complete). Include `include_usernames` param and "No respondida" substitution. | `core/` | ensayos_generales | Username lookup depends on `load_users_from_json` also being in core/ |
| `save_form_responses_to_csv` | aa only; form infrastructure | Include from aa. | `core/` | assessment-analysis-project | |
| `save_temp_responses_to_csv` | eg only; writes incremental responses to temp CSV (used in incremental mode) | Include from eg. Required by the eg version of `_download_and_process_common`. | `core/` | ensayos_generales | |
| `cleanup_temp_files` | **Naming conflict resolved:** diagnosticos has `cleanup_incremental_files`; eg has `cleanup_temp_files`. Same concept: delete intermediate files. | Use `cleanup_temp_files` as canonical name (more general — incremental files are temp files; not all temp files are incremental). Merge eg body (broader: deletes incremental JSON, temp CSV, and temp analysis files) rather than diag body (deletes incremental JSON only). | `core/` | ensayos_generales | The eg version is a strict superset of diag's scope |
| `filter_responses` | diag: `r.get('userId') or r.get('user_id')` (handles both LearnWorlds API variants); eg/aa: only `r.get('user_id')` | Use diag as base. The `userId` fallback handles the API's inconsistent field naming across endpoint versions. Union type hint from diag/eg is more permissive and correct. | `core/` | diagnosticos | |
| `add_answer_columns_to_csv` | eg: adds "No respondida" substitution for empty/NaN answers; diag/aa: no substitution | Use eg as base (correct behavior — empty answers should be explicitly labeled). | `core/` | ensayos_generales | |
| `_download_and_process_common` | diag: incremental mode stores data in memory (`csv_path = None`); eg: incremental mode writes temp CSV; aa: no `incremental_mode` param | Use eg as base. Writing temp CSV is more robust than in-memory processing (survives restarts, allows inspection). Merge: add `incremental_mode` param, use `save_temp_responses_to_csv` for incremental path. | `core/` | ensayos_generales | The diag approach (in-memory) was a design decision that eg evolved away from |
| `download_and_process_assessment` | diag/eg: has `incremental_mode` param; aa: does not | Use diag as base. Include `incremental_mode`. | `core/` | diagnosticos | |
| `download_all_assessments` | diag/eg: has `incremental_mode` param; aa: does not. diag vs eg differ only in one docstring line (cosmetic). | Use diag as base (or eg — functionally equivalent for this method). Include `incremental_mode`. | `core/` | diagnosticos | |
| `download_and_process_form` | aa only; form infrastructure | Include from aa. | `core/` | assessment-analysis-project | |
| `download_users` | eg only; user infrastructure | Include from eg. | `core/` | ensayos_generales | |
| `merge_incremental_users` | eg only | Include from eg. | `core/` | ensayos_generales | |
| `load_users_from_json` | eg only | Include from eg. | `core/` | ensayos_generales | |
| `get_username_by_user_id` | eg only | Include from eg. | `core/` | ensayos_generales | |
| `get_temp_csv_file_path` | eg only | Include from eg (needed by `save_temp_responses_to_csv`). | `core/` | ensayos_generales | |
| `get_temp_analysis_file_path` | eg only | Include from eg (needed by `cleanup_temp_files`). | `core/` | ensayos_generales | |
| `get_users_csv_file_path` | aa only | Include from aa (needed by form response CSV saving). | `core/` | assessment-analysis-project | |
| `get_latest_user_timestamp_from_json` | eg only | Include from eg (needed by `download_users` incremental mode). | `core/` | ensayos_generales | |
| `_normalize_commune` | aa only; data-normalization specific to assessment-analysis report domain | Do NOT promote. Stays in `reports/assessment_analysis/`. | `reports/assessment_analysis/` | — | |
| `_compare_emails` | aa only; domain-specific | Do NOT promote. Stays in `reports/assessment_analysis/`. | `reports/assessment_analysis/` | — | |
| `_process_email_columns` | aa only; domain-specific | Do NOT promote. Stays in `reports/assessment_analysis/`. | `reports/assessment_analysis/` | — | |
| `load_assessment_list_from_env` | All projects; each hardcodes its own assessment ID env var names | Do NOT promote to `core/`. Stays per-report module. Each report module defines its own list from its own env vars. | per-report module | — | See Q3 resolution in Section 9 |

---

## 3. assessment_analyzer.py — Method Matrix

Config-based family only (diagnosticos, diagnosticos_uim, assessment-analysis-project, reportes de test de diagnostico). The ensayos_generales analyzer is architecturally separate — see paragraph after table.

| Method | diag | uim | aa/rtd | Status | Destination |
|--------|------|-----|--------|--------|-------------|
| `__init__` | P | P | P | DIVERGES (diag: full per-assessment config dict; uim: minimal default — only `_default` template using percentage-based; aa: minimal default + StorageClient usage; uim has percentage-only defaults for F30M/B30M/Q30M) | `core/` |
| `_get_default_config` | P | P | P | DIVERGES SIGNIFICANTLY (diag: full config for M1/CL/CIEN/HYST with difficulty/skill/materia types; uim: minimal `_default` template, percentage-based only; aa: same structure as uim, percentage-based with different threshold values) | `core/` |
| `_format_percentage_for_excel` | P | P | P | IDENTICAL | `core/` |
| `_extract_answers_from_response` | P | P | P | IDENTICAL | `core/` |
| `analyze_assessment` | P | P | P | DIVERGES (diag/aa: raise ValueError for unknown assessment; uim: falls back to `_default` config for unknown assessments — does NOT raise) | `core/` |
| `_analyze_by_category_generic` | P | — | P | ABSENT in uim | `core/` |
| `_analyze_percentage_based_generic` | P | P | P | DIVERGES (uim version only handles percentage-based routing; diag/aa version handles all types) | `core/` |
| `_determine_level_unified` | P | P | P | DIVERGES (diag: handles all 4 types; uim: percentage-based only, 3-tier levels General/Avanzado/Excelente; aa: same structure as uim with percentage-based logic) | `core/` |
| `_analyze_by_lecture` | P | P | P | IDENTICAL | `core/` |
| `_get_internal_level` | P | P | P | DIVERGES (diag: checks M1/CL for Nivel 4 distinction; uim: always returns reported level; aa: same as uim) | `core/` |
| `analyze_assessment_from_csv` | P | P | P | DIVERGES (diag: `return_df` param, `StorageClient` for I/O, accepts DataFrame as input; uim: same as diag; aa/rtd: no `return_df`, uses `pd.read_csv`/`df.to_csv` directly, simplified output) | `core/` |

**ensayos_generales analyzer — architecturally separate:**

`ensayos_generales/assessment_analyzer.py` has zero method overlap with the config-based family above. Its methods are: `get_unique_identifiers`, `load_conversion_data`, `calculate_assessment_score`, `convert_score`, `analyze_all_assessments`. These implement a score-conversion table approach (XLSX-based conversion tables, raw → scaled score mapping) that is fundamentally incompatible with the config-driven category/percentage analysis of the other three projects. This file lives as `reports/ensayos_generales/analyzer.py` — a report-specific helper module. Zero methods are promoted to `core/`. The `BaseReportGenerator` ABC governs only the `generate()` interface, not the analysis approach.

---

## 4. assessment_analyzer.py — Resolution Decisions

| Method | Situation | Resolution | Destination | Canonical Base | Notes |
|--------|-----------|------------|-------------|----------------|-------|
| `__init__` | diag: full typed config; uim: minimal percentage-only defaults; aa: minimal with StorageClient | Use diag as base. The full config dict is the correct default — it supports all assessment types. Pass `config=None` to use defaults; callers can override with their own config. | `core/` | diagnosticos | |
| `_get_default_config` | diag: rich per-assessment config for M1, CL, CIEN, HYST; uim: only `_default` percentage template with 3-tier levels; aa: same as uim | Use diag as base. The diag config contains the complete, correct assessment definitions. uim's simplified config was intentional for its percentage-only assessment types (F30M/B30M/Q30M), but core/ must support all types. uim plugin can pass its own config to `__init__` at instantiation without relying on the default. | `core/` | diagnosticos | The uim `_default` template with F30M/B30M/Q30M configs should be defined in the uim report module, NOT in core/ defaults |
| `analyze_assessment` | diag/aa: raise `ValueError` for unknown assessment type; uim: fall back to `_default` config | Use diag as base (raise on unknown). The `_default` fallback in uim is a feature for dynamic assessment types, but it can silently mask misconfiguration. Core/ behavior: raise `ValueError` for unknown assessment names. uim plugin can subclass or pass its own config that includes the `_default` key. | `core/` | diagnosticos | uim's `_default` fallback was intentional — uim must pass its own config dict that includes the `_default` template |
| `_analyze_by_category_generic` | ABSENT in uim; PRESENT in diag and aa/rtd | Include in core/ using diag version (which is identical to aa version). uim intentionally omitted this because uim's assessment types (F30M/B30M/Q30M) are all percentage-based and never call category analysis. The core/ version must include this method so diagnosticos and aa-project reports can use it. uim's report module simply never invokes it. | `core/` | diagnosticos | Q1 resolved: uim omitted intentionally — its assessment types never need category analysis. Including in core/ is correct and harmless for uim. |
| `_analyze_percentage_based_generic` | uim version only handles percentage routing; diag version handles all types (but percentage method body is the same) | Use diag version as base — it is the superset. The percentage-based logic body is identical between diag and uim. | `core/` | diagnosticos | |
| `_determine_level_unified` | diag: handles all 4 assessment types; uim: handles percentage-based only, uses 3-tier (General/Avanzado/Excelente) | Use diag version as base. The per-assessment-type level determination in diag is complete and correct. The uim levels (General/Avanzado/Excelente) are driven by the config thresholds, not by hard-coded logic — so the diag method body already handles them if the uim config is passed. | `core/` | diagnosticos | |
| `_get_internal_level` | diag: M1/CL have Nivel 4 internal distinction; uim/aa: always return reported level | Use diag version as base. The Nivel 4 internal tracking is a feature of the M1 and CL assessments in diagnosticos. uim/aa assessments have no Nivel 4, so the uim/aa code path (return reported_level for unknown assessments) is already included in the diag method's `else` branch. | `core/` | diagnosticos | |
| `analyze_assessment_from_csv` | diag: `return_df: bool = False`, accepts DataFrame input, uses `StorageClient`; uim: same as diag; aa: no `return_df`, uses `pd.read_csv` directly | Use diag as base (most capable). Include `return_df` param and DataFrame input support. Use `StorageClient` for I/O — allows GCS/local backend switching. aa version's use of `pd.read_csv` directly is a regression (no GCS support). | `core/` | diagnosticos | The `return_df` path is used by the incremental processing pipeline where data flows through memory without intermediate files |
| `_format_percentage_for_excel` | Identical across all | Copy verbatim from diag. | `core/` | diagnosticos | |
| `_extract_answers_from_response` | Identical across all | Copy verbatim from diag. | `core/` | diagnosticos | |
| `_analyze_by_lecture` | Identical across all | Copy verbatim from diag. | `core/` | diagnosticos | |

---

## 5. requirements.txt — Conflict Resolution

### Version conflict matrix

| Package | diag/uim (parent) | diag/uim complete_deployment | eg | aa/rtd | Resolution | Rationale |
|---------|-------------------|------------------------------|----|--------|------------|-----------|
| pandas | `==1.*` | `==2.2.2` | `==1.*` | `>=1.3.0` | `==2.2.2` | complete_deployment is production; pin to exact production version |
| numpy | (absent) | `==1.26.4` | (absent) | (absent) | `==1.26.4` | companion pin required by pandas 2.2.2 for stable ABI |
| weasyprint | `==56.*` | `==66.0` | (absent) | `>=54.0` | `==66.0` | production version; has breaking changes from 56.x — adopt production |
| reportlab | `==3.*` | `==4.4.3` | `==3.*` | (absent) | `==4.4.3` | production version; has breaking changes from 3.x — adopt production |
| openpyxl | `==3.*` | `==3.1.5` | `==3.*` | `>=3.0.0` | `==3.1.5` | exact production pin |
| jinja2 | `==3.*` | `==3.1.4` | `==3.*` | (absent) | `==3.1.4` | exact production pin |
| protobuf | `==4.*` | `==4.*` | (absent) | (absent) | `==4.*` | required by Firestore/Cloud Tasks (diag/uim only); keep wildcard minor pin (Cloud protobuf client manages minor version) |
| functions-framework | `==3.*` | `==3.*` | `==3.*` | (absent) | `==3.*` | Cloud Run webhook handler only; see note below |
| google-cloud-firestore | `==2.*` | `==2.*` | `==2.*` | (absent) | `==2.*` | all projects using Cloud infra need this |
| google-cloud-tasks | `==2.*` | `==2.*` | `==2.*` | (absent) | `==2.*` | diag/uim only but include for unified requirements |
| google-cloud-storage | `==2.*` | `==2.*` | `==2.*` | (absent) | `==2.*` | shared infrastructure |
| google-api-python-client | `==2.*` | `==2.*` | (absent) | `>=2.0.0` | `==2.*` | uniform wildcard minor |
| google-auth | `==2.*` | `==2.*` | (absent) | `>=2.0.0` | `==2.*` | uniform wildcard minor |
| google-auth-oauthlib | (absent) | (absent) | (absent) | `>=0.4.6` | `>=0.4.6` | from aa family; OAuth flow for Drive access |
| google-auth-httplib2 | (absent) | (absent) | (absent) | `>=0.1.0` | `>=0.1.0` | from aa family; HTTP adapter for google-auth |
| flask | `==2.*` | `==2.*` | `==2.*` | (absent) | `==2.*` | Cloud Run webhook handler |
| requests | `==2.*` | `==2.*` | `==2.*` | `>=2.25.1` | `==2.*` | uniform wildcard minor |
| python-dotenv | `==0.*` | `==0.*` | `==0.*` | `>=0.19.0` | `==0.*` | uniform wildcard minor |

**Pinning style decision:** Use **exact pins (`==X.Y.Z`)** for packages with version conflicts and **wildcard minor pins (`==X.*`)** for stable packages. Rationale: the `complete_deployment/` folders (actual production Cloud Run environment) already use exact pins for the conflicted packages. Following production is the correct strategy.

**pandas 2.x breaking change acknowledgment:** pandas 2.x drops `df.append()`, changes default dtype inference, and changes some GroupBy behavior. All existing code in the projects must be validated against pandas 2.2.2 before Phase 2 implementation. This is a Phase 2 concern — Phase 1 only documents the version decision.

**functions-framework note:** Required for Cloud Run webhook deployment only. Not needed for local batch runs. A future split into `requirements.txt` (core) and `requirements-cloudrun.txt` (Cloud Run extras) is a Phase 5 packaging concern. For now, include in the unified requirements.

### Proposed unified requirements.txt

```
# ============================================================
# Unified requirements.txt — Report Pipeline
# Produced: 2026-02-28
# Target environment: Cloud Run (pandas 2.2.2 production stack)
# ============================================================

# ---- Data processing ----
pandas==2.2.2
numpy==1.26.4
openpyxl==3.1.5

# ---- Web requests / LearnWorlds API ----
requests==2.*

# ---- Report generation ----
weasyprint==66.0
reportlab==4.4.3
jinja2==3.1.4

# ---- Environment ----
python-dotenv==0.*

# ---- Google Cloud infrastructure ----
google-cloud-storage==2.*
google-cloud-firestore==2.*
google-cloud-tasks==2.*
google-api-python-client==2.*
google-auth==2.*
google-auth-oauthlib>=0.4.6
google-auth-httplib2>=0.1.0
protobuf==4.*

# ---- Cloud Run webhook handler ----
# Not needed for local batch runs
functions-framework==3.*
flask==2.*
```

---

## 6. Environment Variables — Consolidation Catalogue

### Master variable table

| Variable | diag | uim | eg | aa/rtd | shared | Canonical Name | Notes |
|----------|------|-----|----|--------|--------|----------------|-------|
| `CLIENT_ID` | P | P | P | P | P | `CLIENT_ID` | Uniform — LearnWorlds client ID |
| `SCHOOL_DOMAIN` | P | P | P | P | P | `SCHOOL_DOMAIN` | Uniform — e.g., `company.mylearnworlds.com` |
| `ACCESS_TOKEN` | P | P | P | P | P | `ACCESS_TOKEN` | Uniform — LearnWorlds API bearer token |
| `GOOGLE_CLOUD_PROJECT` | P | P | — | — | — | **`GCP_PROJECT_ID`** | NAMING CONFLICT — see resolution below |
| `GCP_PROJECT_ID` | — | — | P | P | P | **`GCP_PROJECT_ID`** | NAMING CONFLICT — canonical name |
| `GCP_BUCKET_NAME` | — | — | P | P | P | `GCP_BUCKET_NAME` | GCS bucket for storage backend |
| `TASK_LOCATION` | P | P | — | — | — | `TASK_LOCATION` | Cloud Tasks location (diag/uim Cloud Run only) |
| `TASK_QUEUE_ID` | P | P | — | — | — | `TASK_QUEUE_ID` | Cloud Tasks queue ID (diag/uim Cloud Run only) |
| `LEARNWORLDS_WEBHOOK_SECRET` | P | P | — | — | P | `LEARNWORLDS_WEBHOOK_SECRET` | Webhook HMAC secret |
| `BATCH_INTERVAL_MINUTES` | P | P | — | — | — | `BATCH_INTERVAL_MINUTES` | Batch processor interval |
| `PROCESS_BATCH_URL` | P | P | — | — | — | `PROCESS_BATCH_URL` | Cloud Functions trigger URL (diag/uim only) |
| `MIN_DOWNLOAD_DATE` | P | P | P | — | — | `MIN_DOWNLOAD_DATE` | Optional date filter for incremental downloads (YYYY-MM-DD) |
| `EMAIL_FROM` | P | P | P | — | P | `EMAIL_FROM` | Sender email address |
| `EMAIL_PASS` | P | P | P | — | P | `EMAIL_PASS` | Sender email password/app password |
| `SMTP_SERVER` | — | — | P | — | P | `SMTP_SERVER` | SMTP server hostname |
| `SMTP_PORT` | — | — | P | — | P | `SMTP_PORT` | SMTP server port |
| `TEST_EMAIL` | — | — | P | — | — | `TEST_EMAIL` | Development testing email (eg only) |
| `STORAGE_BACKEND` | — | — | P | P | — | `STORAGE_BACKEND` | `local` or `gcs` (eg/aa only) |
| `REGION` | — | — | P | P | — | `REGION` | GCP region for Cloud Run |
| `GOOGLE_SHARED_DRIVE_ID` | — | — | P | P | — | `GOOGLE_SHARED_DRIVE_ID` | Google Shared Drive ID |
| `GOOGLE_DRIVE_FOLDER_ID` | — | — | P | P | P | `GOOGLE_DRIVE_FOLDER_ID` | Google Drive folder ID for output |
| `GOOGLE_SERVICE_ACCOUNT_KEY` | — | — | P | P | P | `GOOGLE_SERVICE_ACCOUNT_KEY` | Path or JSON for service account key |
| `GOOGLE_APPLICATION_CREDENTIALS` | — | — | P | P | — | `GOOGLE_APPLICATION_CREDENTIALS` | ADC credentials path (eg/aa only) |
| `IGNORED_USERS` | — | — | P | P | P | `IGNORED_USERS` | Comma-separated user IDs to exclude from reports |
| `GRADE_ZERO_THRESHOLD` | — | — | P | P | — | `GRADE_ZERO_THRESHOLD` | Minimum score to include in report |
| `TIME_MAX_THRESHOLD_MINUTES` | — | — | P | P | — | `TIME_MAX_THRESHOLD_MINUTES` | Max time threshold for valid response |
| `REPORT_TOP_PERCENT` | — | — | P | P | — | `REPORT_TOP_PERCENT` | Top percentile threshold for report classification |
| `USERS` | — | — | — | P | — | `USERS` | JSON string of user list (aa/rtd only) |
| `SLACK_BOT_TOKEN` | — | — | — | — | P | `SLACK_BOT_TOKEN` | Slack notification bot token (shared only) |
| `SLACK_CHANNEL` | — | — | — | — | P | `SLACK_CHANNEL` | Slack channel for notifications (shared only) |
| `ADMIN_EMAIL` | — | — | — | — | P | `ADMIN_EMAIL` | Admin email for system notifications (shared only) |
| `M1_ASSESSMENT_ID` | P | P | P | P | — | `M1_ASSESSMENT_ID` | Assessment ID — shared across most projects |
| `CL_ASSESSMENT_ID` | P | — | P | P | — | `CL_ASSESSMENT_ID` | Assessment ID — diag/eg/aa (NOT in uim) |
| `CIEN_ASSESSMENT_ID` | P | — | — | P | — | `CIEN_ASSESSMENT_ID` | Assessment ID — diag/aa only |
| `HYST_ASSESSMENT_ID` | P | P | P | P | — | `HYST_ASSESSMENT_ID` | Assessment ID — uniform |
| `F30M_ASSESSMENT_ID` | — | P | — | — | — | `F30M_ASSESSMENT_ID` | Assessment ID — uim only |
| `B30M_ASSESSMENT_ID` | — | P | — | — | — | `B30M_ASSESSMENT_ID` | Assessment ID — uim only |
| `Q30M_ASSESSMENT_ID` | — | P | — | — | — | `Q30M_ASSESSMENT_ID` | Assessment ID — uim only |
| `M2_ASSESSMENT_ID` | — | — | P | — | — | `M2_ASSESSMENT_ID` | Assessment ID — eg only |
| `CIENB_ASSESSMENT_ID` | — | — | P | — | — | `CIENB_ASSESSMENT_ID` | Assessment ID — eg only |
| `CIENF_ASSESSMENT_ID` | — | — | P | — | — | `CIENF_ASSESSMENT_ID` | Assessment ID — eg only |
| `CIENQ_ASSESSMENT_ID` | — | — | P | — | — | `CIENQ_ASSESSMENT_ID` | Assessment ID — eg only |
| `CIENT_ASSESSMENT_ID` | — | — | P | — | — | `CIENT_ASSESSMENT_ID` | Assessment ID — eg only |

**NAMING CONFLICT RESOLUTION: `GOOGLE_CLOUD_PROJECT` vs `GCP_PROJECT_ID`**

Canonical name: **`GCP_PROJECT_ID`**

Rationale: `GOOGLE_CLOUD_PROJECT` is set automatically by the Cloud Run runtime to the current GCP project ID. Using the same name for an application env var creates a silent collision — the application var is overwritten by the runtime on Cloud Run. `GCP_PROJECT_ID` is explicit, custom, and avoids this collision. All existing code in diagnosticos/uim that reads `GOOGLE_CLOUD_PROJECT` must be updated to read `GCP_PROJECT_ID` in Phase 2.

**Variable scoping for Phase 2:**

- **Core shared vars** (go in `.env` loaded by core/): `CLIENT_ID`, `SCHOOL_DOMAIN`, `ACCESS_TOKEN`, `GCP_PROJECT_ID`, `GCP_BUCKET_NAME`, `EMAIL_FROM`, `EMAIL_PASS`, `SMTP_SERVER`, `SMTP_PORT`, `STORAGE_BACKEND`, `REGION`, `GOOGLE_DRIVE_FOLDER_ID`, `GOOGLE_SERVICE_ACCOUNT_KEY`, `GOOGLE_APPLICATION_CREDENTIALS`, `IGNORED_USERS`, `MIN_DOWNLOAD_DATE`
- **Cloud Run deployment vars** (only needed in `complete_deployment/` environment): `TASK_LOCATION`, `TASK_QUEUE_ID`, `LEARNWORLDS_WEBHOOK_SECRET`, `BATCH_INTERVAL_MINUTES`, `PROCESS_BATCH_URL`, `GOOGLE_SHARED_DRIVE_ID`
- **Per-report assessment ID vars** (set per-project in report module `.env`): All `*_ASSESSMENT_ID` vars
- **Shared admin vars** (from shared/ only): `SLACK_BOT_TOKEN`, `SLACK_CHANNEL`, `ADMIN_EMAIL`

### Proposed .env.example

```bash
# ============================================================
# .env.example — Unified Report Pipeline
# Copy to .env and fill in your values.
# ============================================================

# ---- LearnWorlds API (required for all reports) ----
CLIENT_ID=your_learnworlds_client_id
SCHOOL_DOMAIN=yourschool.mylearnworlds.com
ACCESS_TOKEN=your_learnworlds_api_token

# ---- Google Cloud Platform (required for GCS/Cloud Run) ----
GCP_PROJECT_ID=your-gcp-project-id
GCP_BUCKET_NAME=your-gcs-bucket-name
REGION=us-central1
GOOGLE_SERVICE_ACCOUNT_KEY=/path/to/service-account-key.json
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
GOOGLE_DRIVE_FOLDER_ID=your_google_drive_folder_id
GOOGLE_SHARED_DRIVE_ID=your_google_shared_drive_id

# ---- Storage backend ----
# Options: "local" (default for dev) | "gcs" (for Cloud Run production)
STORAGE_BACKEND=local

# ---- Email (required for report sending) ----
EMAIL_FROM=sender@example.com
EMAIL_PASS=your_email_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# ---- Download filters (optional) ----
# If set, only download responses submitted on or after this date (YYYY-MM-DD)
MIN_DOWNLOAD_DATE=

# ---- Report output filters (optional) ----
# Comma-separated LearnWorlds user IDs to exclude from all reports
IGNORED_USERS=
GRADE_ZERO_THRESHOLD=
TIME_MAX_THRESHOLD_MINUTES=
REPORT_TOP_PERCENT=

# ---- Cloud Run webhook handler (only for complete_deployment/ Cloud Run deployments) ----
LEARNWORLDS_WEBHOOK_SECRET=your_webhook_hmac_secret
TASK_LOCATION=us-central1
TASK_QUEUE_ID=your-cloud-tasks-queue-id
BATCH_INTERVAL_MINUTES=60
PROCESS_BATCH_URL=https://your-cloud-function-url/process_batch

# ---- Slack notifications (shared/ admin features only) ----
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL=#reports-notifications
ADMIN_EMAIL=admin@example.com

# ---- Test/development ----
TEST_EMAIL=test@example.com

# ============================================================
# Per-report assessment IDs — set only the IDs your report uses
# ============================================================

# diagnosticos report assessments
M1_ASSESSMENT_ID=
CL_ASSESSMENT_ID=
CIEN_ASSESSMENT_ID=
HYST_ASSESSMENT_ID=

# diagnosticos_uim report assessments
F30M_ASSESSMENT_ID=
B30M_ASSESSMENT_ID=
Q30M_ASSESSMENT_ID=

# ensayos_generales report assessments
M2_ASSESSMENT_ID=
CIENB_ASSESSMENT_ID=
CIENF_ASSESSMENT_ID=
CIENQ_ASSESSMENT_ID=
CIENT_ASSESSMENT_ID=
```

---

## 7. Entry Points — Cloud Run vs Local

| File | Role | Deployment |
|------|------|------------|
| `diagnosticos/complete_deployment/main.py` | Cloud Run webhook handler — imports `functions_framework`, exposes `webhook_handler(request)` | Deployed via `deploy.sh --entry-point=webhook_handler` |
| `diagnosticos/complete_deployment/main_app.py` | Standalone batch runner — imports `argparse`, `AssessmentDownloader`, `AssessmentAnalyzer`, `ReportGenerator` | Local execution only |
| `diagnosticos_uim/complete_deployment/main.py` | Cloud Run webhook handler — same pattern as diagnosticos | Deployed via `deploy.sh --entry-point=webhook_handler` |
| `diagnosticos_uim/complete_deployment/main_app.py` | Standalone batch runner — same as diagnosticos pattern | Local execution only |
| `diagnosticos/main.py` | Standalone batch runner (parent dir level) | Local execution only — NOT deployed to Cloud Run |
| `diagnosticos_uim/main.py` | Standalone batch runner (parent dir level) | Local execution only — NOT deployed to Cloud Run |

**Confirmation:** `deploy.sh` scripts in both `diagnosticos/` and `diagnosticos_uim/` use `--entry-point=webhook_handler`, confirming `main.py` in `complete_deployment/` is the Cloud Run entry point. The `main_app.py` in `complete_deployment/` is a convenience copy of the batch runner for local testing within the Cloud Run environment directory.

**Phase 2 implication:** The unified pipeline will produce two entry-point patterns per report type:
1. `reports/<type>/main.py` — batch runner (always present)
2. `reports/<type>/cloud_run_handler.py` (or equivalent) — Cloud Run webhook handler (only for deployed reports)

---

## 8. Core Boundary Rules (Summary)

These rules are locked before Phase 2 begins. Phase 2 implementer must not deviate from these without creating a new plan.

| Rule | Applies To | Decision |
|------|-----------|----------|
| Default: single-project + domain-specific | Methods only in one project AND specific to that report's data domain | Stay in `reports/<type>/` module — NOT promoted to `core/` |
| Override: user/form infrastructure | `download_users`, `download_and_process_form`, `save_form_responses_to_csv`, `_download_form_responses_full`, `download_form_responses_incremental`, `get_users_csv_file_path` | Promote to `core/` regardless of how many projects currently have them |
| Override: methods in 2+ projects | Any method present in 2 or more distinct project families | Promote to `core/` |

**Explicitly confirmed `core/` destinations:**

All methods in the method matrix with `Destination = core/` are confirmed. Key infrastructure methods that are in core/ even if currently single-project: `download_users`, `download_and_process_form`, `save_form_responses_to_csv`, `download_form_responses_incremental`, `_download_form_responses_full`, `get_users_csv_file_path`, `get_temp_csv_file_path`, `get_temp_analysis_file_path`, `get_latest_user_timestamp_from_json`, `merge_incremental_users`, `load_users_from_json`, `get_username_by_user_id`.

**Explicitly confirmed per-report destinations (do NOT put in `core/`):**

| Method | Report Module |
|--------|---------------|
| `_normalize_commune` | `reports/assessment_analysis/` |
| `_compare_emails` | `reports/assessment_analysis/` |
| `_process_email_columns` | `reports/assessment_analysis/` |
| `load_assessment_list_from_env` | each report's own module |
| `parse_arguments` | each report's own module |
| `main` | each report's own module |

---

## 9. Open Questions — Resolved

**Q1: Was `_analyze_by_category_generic` intentionally removed from `diagnosticos_uim/assessment_analyzer.py`?**

**Resolution:** YES — intentionally omitted. Confirmed by source inspection: `diagnosticos_uim/assessment_analyzer.py` has no `_analyze_by_category_generic` method. The `analyze_assessment` method in uim routes ALL assessment types through `_analyze_percentage_based_generic` only (it only handles `percentage_based` type; other types raise `ValueError`). The uim assessments (F30M, B30M, Q30M) are all percentage-based — they never need category analysis (no difficulty, skill, or materia breakdown). The uim `_get_default_config` defines only a `_default` percentage template.

**Canonical core/ decision:** Include `_analyze_by_category_generic` in `core/` using the diagnosticos version. The method is required for M1 (difficulty-based), CL (skill-based), and CIEN (materia-based) analysis. The uim report module simply never calls this method — its absence in uim was correct for uim's domain, but the canonical core/ must include it for the other report types.

---

**Q2: Are the two versions of `_download_form_responses_full` equivalent in body?**

**Resolution:** YES — confirmed IDENTICAL. Body diff shows both versions (ensayos_generales and assessment-analysis-project) are single-line wrappers:

```python
def _download_form_responses_full(self, form_id: str, form_name: str) -> List[Dict[str, Any]]:
    """
    Download all form responses (full download)
    """
    return self._download_responses_full(form_id, form_name, "forms")
```

No divergence. Copy either version verbatim. Destination confirmed as `core/`.

---

**Q3: Should `load_assessment_list_from_env` ever go to `core/`?**

**Resolution:** NO — stays per-report module permanently.

Rationale: `load_assessment_list_from_env` hardcodes assessment ID env var names that are specific to each project. diagnosticos uses `CL_ASSESSMENT_ID` and `CIEN_ASSESSMENT_ID`. diagnosticos_uim uses `F30M_ASSESSMENT_ID`, `B30M_ASSESSMENT_ID`, `Q30M_ASSESSMENT_ID`. ensayos_generales uses a different set. A "config-driven" version of this function would just be an env var loader with a list of env var names — equivalent to moving the hardcoding one layer up. The correct pattern is: each report module defines its own `load_assessment_list_from_env()` function that reads its own env vars and returns its own assessment list. Phase 2 should not attempt to unify this function. The per-report module holds this function alongside `main()` and `parse_arguments()`.
