# Google CI/CD DevOps Extension — Local Reference

Local mirror / study notes for the Google Cloud blog post:

- **Source:** https://cloud.google.com/blog/topics/developers-practitioners/ship-code-within-minutes-with-the-gemini-cli-devops-extension
- **Fetched:** 2026-05-19
- **Status:** Reference only. Not installed in this repo. No GCP resources, IAM, or secrets have been created in connection with this document.

This file is a faithful condensation of the article plus the supporting GitHub repo (`gemini-cli-extensions/cicd`) so we can reason about the extension without round-tripping the browser. A SAFE-Triage-specific action plan lives in `docs/devops/safe-triage-cicd-action-plan.md` — keep that doc as the place where we decide what (if anything) to actually adopt.

---

## 1. What it is

The **Gemini CLI Extension for CI/CD** is an AI-agent extension that bridges the *inner loop* (local code edit → deploy) and the *outer loop* (full CI/CD pipeline generation) on Google Cloud. It is delivered as a set of "skills" plus a background **MCP server** (Model Context Protocol) that exposes strongly-typed tools the agent can call against Google Cloud.

Conceptually three tiers:

1. **Skills** — `google-cicd-deploy` (inner loop) and `google-cicd-pipeline-design` (outer loop). These steer the agent's reasoning and error-recovery.
2. **CI/CD MCP server** — a Go process running locally that exposes typed tools (`create_artifact_repository`, `create_build_trigger`, scan secrets, provision Cloud Run, etc.) to whichever agent is driving (Gemini CLI, Claude Code, Antigravity, …).
3. **Local knowledge base** — a pre-indexed RAG store of "verified architecture patterns" used to ground design decisions.

The extension does **not** invent permissions. It operates strictly within whatever your local **Application Default Credentials (ADC)** can already do.

---

## 2. Google Cloud services it touches

| Service | Used for |
|---|---|
| Cloud Run | Deploy dynamic services (source-based, Buildpacks) |
| Google Cloud Storage | Static site hosting |
| Cloud Build | Run pipelines, tests, image builds |
| Artifact Registry | Container image storage |
| Google Cloud Buildpacks | Automatic containerization (no Dockerfile required) |
| Developer Connect | Connect GitHub repos to Cloud Build |
| Cloud Build Triggers | Run pipelines on push / PR events |
| Application Default Credentials (ADC) | Auth boundary for everything above |

---

## 3. Install commands (verbatim from the article)

> **Do not run any of these against the SAFE-Triage GCP project until the action plan explicitly approves it.**

**Gemini CLI:**

```bash
gemini extensions install https://github.com/gemini-cli-extensions/cicd
```

**Claude Code:**

```bash
# 1. Add the Marketplace
claude plugin marketplace add https://github.com/gemini-cli-extensions/cicd.git

# 2. Install the Plugin
claude plugin install cicd
```

**Antigravity / agents that support `npx skills`:**

```bash
npx skills add https://github.com/gemini-cli-extensions/cicd --global --all --agent antigravity
```

Prerequisites in all cases:

- `gcloud` CLI installed
- `gcloud auth application-default login` already run
- An existing Google Cloud project the ADC user has rights in

---

## 4. The two flows

### 4.1 Inner loop — "deploy this thing"

The user gives the agent a single natural-language prompt. The agent:

1. Detects language / framework (e.g. `package.json` → Node.js, `go.mod` → Go).
2. Runs a **pre-deployment secret scan** locally. Refuses to deploy if it finds Stripe keys, DB passwords, etc.
3. For monorepos with a JS frontend + Node backend, generates a root `package.json` with a build script that builds the frontend and lets the backend serve it statically (so it fits the single-entry-point Buildpack model).
4. Pauses and asks the user three deployment parameters:
   - **Region** (e.g. `us-central1`, `europe-west1`)
   - **Public vs private** (`--allow-unauthenticated` or not)
   - **Service name** (proposes one, asks for confirmation)
5. Deploys to Cloud Run from source using Buildpacks.
6. Returns the public Cloud Run URL.

Example prompt:

```bash
gemini "Deploy this application to Google Cloud using the google-cicd-deploy skill"
```

```bash
claude -p "Deploy this application to Google Cloud using the google-cicd-deploy skill"
```

Example clarification prompt the agent emits (quoted verbatim from the article):

> "I have completed the analysis and prepared the application for a unified deployment to Cloud Run. Since the Node.js buildpack requires a single entry point, I created a root `package.json` with a custom build script that builds the React frontend and allows the Express backend to serve it statically.
>
> Additionally, the secret scan completed successfully, and no sensitive credentials were found.
>
> Before we deploy using the Cloud Run source deployment option (buildpacks), I need to clarify a few deployment parameters:
>
> 1. Region/Location: …
> 2. Access: Should this application be publicly accessible or private?
> 3. Service Name: I propose naming the service `cosmic-guestbook`. Does that sound good to you?"

### 4.2 Outer loop — "design a CI/CD pipeline"

Prompt:

```bash
gemini "Design a CI/CD pipeline using the google-cicd-pipeline-design skill"
# or
claude -p "Design a CI/CD pipeline using the google-cicd-pipeline-design skill"
```

The agent then:

1. Inspects the repo and asks clarifying questions (branch model, prod vs staging, etc.).
2. Calls MCP tools to provision/declare the infrastructure pieces — Artifact Registry repo, Cloud Build triggers, Developer Connect link to GitHub.
3. Generates a `cloudbuild.yaml` and any supporting config.
4. Hands back: a working pipeline + a URL to the trigger.

Example MCP calls (from the article):

```json
{
  "name": "create_artifact_repository",
  "arguments": {
    "repository_id": "demo-app-repo",
    "location": "us-central1",
    "format": "DOCKER"
  }
}
```

```json
{
  "name": "create_build_trigger",
  "arguments": {
    "trigger_name": "main-branch-deploy",
    "filename": "cloudbuild.yaml",
    "branch_pattern": "^main$"
  }
}
```

Example generated `cloudbuild.yaml` fragment:

```yaml
steps:
  # Step 1: Install tools (like the linter) and clean the cache.
  - name: 'golang:1.24'
    id: 'Install Tools'
    entrypoint: 'sh'
    args:
      - '-c'
      - |
        set -e
        export PATH=/workspace/bin:$$PATH
        echo "Installing golangci-lint..."
        go install github.com/golangci/golangci-lint/cmd/golangci-lint@v1.64.8
        echo "Cleaning module cache..."
        go clean -modcache
    env:
      - 'GOPATH=/workspace'
    dir: 'devops-mcp-server'
```

---

## 5. Security model (read this before recommending it for SAFE-Triage)

- **Permissions** = whatever your ADC user already has. No privilege escalation. No new service accounts implicitly. If your local user has `roles/owner`, the agent has `roles/owner`. **This is the single most important thing to internalise — the blast radius is your `gcloud` blast radius.**
- **Pre-deploy secret scan** runs locally before any code leaves the machine.
- **MCP tools** are strongly typed, so the agent cannot improvise gcloud commands the server doesn't expose.
- The article explicitly recommends **principle of least privilege** for ADC and for any service accounts the generated pipelines use.

What it does **not** do (article does not claim these):

- Workload Identity Federation setup
- Secret Manager bootstrap
- Org-policy review
- VPC-SC / private-IP Cloud Run configuration
- Approval gates / manual-approval steps in the generated pipeline
- Dataset / BigQuery / patient-data compliance posture (HIPAA-style controls)

For a clinical-AI product like SAFE-Triage that's a non-trivial gap — the extension is a productivity tool, not a compliance tool.

---

## 6. Supported stacks (as evidenced in the article)

- **Backend:** Node.js (Express), Go.
- **Frontend:** React + Vite.
- **Detection:** `package.json`, `go.mod`.
- **Containerization:** Buildpacks; no manual Dockerfile required.
- **Not shown but presumably supported via Buildpacks:** Python, Java, .NET, Ruby — Google Buildpacks supports these upstream, but the article does not demonstrate them.

SAFE-Triage is **Python + FastAPI backend** and **React + Vite frontend**. Backend deployment would rely on the Python Buildpack (which exists but the article doesn't exercise it). Our existing `cloudbuild.yaml` already deploys via `gcloud run deploy --source .`, which is the same Buildpacks path — so this should "just work" for the backend.

---

## 7. How this maps to where SAFE-Triage already is

Already in the repo:

- `cloudbuild.yaml` at repo root — deploys `safe-triage-api` to Cloud Run `me-west1`, then builds and Firebase-deploys the frontend.
- `.github/workflows/cloud-run-deploy.yml` — manual-dispatch GitHub Action that deploys `safe-triage` to Cloud Run `us-central1` via JSON service-account key (TODO marker for WIF migration is already in the file).
- `.github/workflows/firebase-hosting-merge.yml`, `firebase-hosting-pull-request.yml` — Firebase Hosting on PR + merge.
- `.github/workflows/triage-parity.yml` — Python parity tests.

Inconsistencies the extension would not magically fix (see action plan):

- Two different Cloud Run service names (`safe-triage` vs `safe-triage-api`).
- Two different regions (`us-central1` vs `me-west1`).
- Service-account JSON key auth instead of Workload Identity Federation.
- No Artifact Registry pinning (Cloud Run `--source` builds and stores images in a default GCR/AR location).
- No staging environment in front of production.

The action plan picks up from here.

---

## 8. Open questions to resolve before adopting

1. Does the Python Buildpack handle FastAPI cold-start times acceptably for the demo? (Current cloudbuild flow already uses it, so probably yes.)
2. Does the extension's generated trigger respect our existing `cloudbuild.yaml`, or does it want to replace it?
3. Can the extension generate **WIF**-based GitHub Actions auth, or does it only know Cloud Build? (Article only shows Cloud Build.)
4. Does the local MCP server require any always-on background process, and is that acceptable on this machine?
5. Pricing implications of Cloud Build minutes if a generated trigger fires on every push to `main` (we are on the $105 free trial that expires **2026-05-05** — already past). Default to **manual-dispatch** until we have answers.

---

## 9. Citations

- **Primary:** Google Cloud blog post linked at top.
- **Repo:** https://github.com/gemini-cli-extensions/cicd
- **Buildpacks:** https://cloud.google.com/docs/buildpacks/overview
- **Cloud Run source deploys:** https://cloud.google.com/run/docs/deploying-source-code
- **Cloud Build Triggers:** https://cloud.google.com/build/docs/triggers
- **Developer Connect:** https://cloud.google.com/developer-connect/docs
- **MCP:** https://modelcontextprotocol.io/

Anything beyond the cited blog post is annotation by Dr. Ahmed / Claude on 2026-05-19 and should be re-checked before acting on it.
