# Phase 15: GCP Setup and Installation Tutorial Document for Non-Technical Users - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Create a single Markdown setup guide that a non-technical person can follow to install and deploy this project. The guide covers: local Python environment setup, Google Cloud CLI installation, pip dependencies, GCP project creation, Cloud Storage bucket, Cloud Run/Cloud Function deployment, environment variables, local verification, and a troubleshooting section.

Audience: corporate employees with no technical background, using Windows and a corporate Gmail (Google Workspace) account.

Out of scope: Git setup (recipients already have the repo connected and follow a separate tutorial to pull updates).

</domain>

<decisions>
## Implementation Decisions

### Target platform
- Windows only — all commands, paths, and installer links are Windows-specific
- Audience uses corporate Gmail (Google Workspace) — tutorial assumes the account already exists and is active (no activation steps)
- Recipients create a new GCP project from scratch — tutorial covers full setup: project creation, API enablement, bucket, function/Cloud Run, env vars, deploy

### Format & structure
- Single MD file at the root of the repo: `SETUP_GUIDE.md`
- Includes a Table of Contents at the top with anchor links to each section
- Each step follows the pattern: one-sentence context → numbered actions → ✅ expected output (what the user sees when the step succeeded)
- Sections: Prerequisites, GCP Concepts Overview, Local Setup, GCP Project Setup, Cloud Storage Bucket, Deployment, Environment Variables, Local Test Run, Verification, Troubleshooting

### Explanation depth
- Brief context + step pattern: one sentence explaining what each tool/step does before the actions
- GCP concepts intro/glossary section at the top — plain-language explanation of the 4-5 services this project uses (Cloud Run, Cloud Storage/GCS, Firestore, Pub/Sub, IAM) so the user understands the overall picture before starting
- Troubleshooting section included: 5-8 most common errors with plain-language fixes (e.g., permission denied, gcloud not found, wrong project selected, missing env var)

### Local setup scope
- **Covered:** Python installation (Windows), Google Cloud CLI (gcloud) installation, pip dependencies via `requirements.txt`
- **Not covered:** Git / repo cloning (users already have the repo; separate tutorial handles updates)
- **Environment variables:** Both a reference table (variable name, what it's for, where to find the value) AND a `.env.example` template file in the repo that users copy and fill in
- **Local test run:** Tutorial includes a "verify it works locally" checkpoint before GCP deployment — catches setup issues early

### Claude's Discretion
- Exact section headings and subsection order within the overall structure above
- Specific formatting of code blocks, callout boxes, and warning notes
- Which exact errors to include in the troubleshooting section (based on known failure modes in this project)
- Whether to use a `.env` file or shell environment variables for local dev (whichever matches the project's current pattern)

</decisions>

<specifics>
## Specific Ideas

- Step pattern confirmed: `## Step N: [Action]\n\n[One sentence what/why]\n\n1. Do X\n2. Do Y\n\n✅ You should see: [expected output]`
- The `.env.example` template file needs to be created as part of this phase (it may not exist yet)
- GCP glossary should explain: Cloud Run (where the code runs), Cloud Storage / GCS (where files are stored), Firestore (database for tracking), Pub/Sub (message queue), IAM (permissions)
- Troubleshooting section must cover: gcloud not recognized in terminal, wrong GCP project active, permission denied errors, missing or incorrect env vars, deployment failures

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Dockerfile` — already exists; tutorial will reference it for the Cloud Run deployment step
- `requirements.txt` — already exists; tutorial covers `pip install -r requirements.txt`
- `.planning/phases/10-*/10-PRODUCTION-RUNBOOK.md` — existing production runbook may contain env var names and GCP commands to reference when authoring the guide

### Established Patterns
- Project deploys to GCP Cloud Run (not Cloud Functions) — tutorial must use Cloud Run terminology and `gcloud run deploy` commands
- GCS bucket `gs://data-analysis-465905-t6-mapping/` is used for `ids.xlsx` mapping — bucket creation step must cover this
- Environment variables follow the project's existing naming (e.g., `IDS_XLSX_GCS_PATH`, `WEBHOOK_SECRET`, etc.) — pull exact names from codebase

### Integration Points
- The `.env.example` file created by this phase will live at the repo root alongside `SETUP_GUIDE.md`
- Tutorial is a standalone document — it does not modify any code

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 15-gcp-setup-and-installation-tutorial-document-for-non-technical-users*
*Context gathered: 2026-03-09*
