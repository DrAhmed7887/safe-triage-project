# SAFE-Triage CI/CD Action Plan

Companion to `docs/devops/google-cicd-devops-extension-reference.md`. This doc is the decision log: what (if anything) we adopt from the Gemini CLI CI/CD extension, in what order, and what the guard-rails are.

- **Date:** 2026-05-19
- **Owner:** Dr. Ahmed Zayed
- **Status:** PLAN ONLY — nothing in this document has been executed. No GCP resources created, no IAM changed, no secrets added.
- **Hard budget cap:** $950 across all GenAI App Builder + GCP infra spend, enforced by `backend/budget_guard.py`. The free-trial credit ($105) expired 2026-05-05; we are on the $1,000 GenAI App Builder credit (exp 2027-02). Any plan step that could spend money must be flagged.

---

## 1. Why we're looking at this now

Current CI/CD has known drift (documented in the reference doc, §7):

- Two Cloud Run service names: `safe-triage` (GitHub Action, `us-central1`) vs `safe-triage-api` (`cloudbuild.yaml`, `me-west1`).
- Two regions. Demos and the parity harness assume `us-central1`.
- GitHub Actions auth uses a **JSON service-account key** stored in a secret — there's already a `# TODO(post-demo): replace JSON key auth with Workload Identity Federation.` in `.github/workflows/cloud-run-deploy.yml`.
- Production deploy is **manual-dispatch only**. No staging.
- No artifact pinning — Cloud Run `--source` rebuilds the image every deploy.

The Gemini CLI CI/CD extension is interesting because it could *generate* a unified `cloudbuild.yaml` + trigger from a single prompt. It is **not** a substitute for the work above; it's a way to do that work faster *if* we keep it on a leash.

---

## 2. What we are NOT doing in this plan

Explicit non-goals so we don't drift:

- **No** installation of the extension in this pass.
- **No** `gcloud` commands run from this plan.
- **No** new Cloud Run services, Artifact Registry repos, Cloud Build triggers, or Developer Connect links created.
- **No** IAM grants, role changes, or new service accounts.
- **No** new secrets written into GitHub or Secret Manager.
- **No** changes to `cloudbuild.yaml` or `.github/workflows/*` in this PR. The reference doc + this plan land first; implementation is a separate, reviewed change.
- **No** PHI exposure risk introduced. SAFE-Triage handles no PHI, only synthetic / MIMIC-IV data, but we still write guard-rails as if it did.

---

## 3. Decision questions (answer before any implementation step)

| # | Question | Default if not decided |
|---|---|---|
| Q1 | Do we adopt the extension at all, or only borrow patterns from its output? | Borrow patterns, do not install. |
| Q2 | Which Cloud Run service name is canonical — `safe-triage` or `safe-triage-api`? | `safe-triage` (matches GitHub Action + Firebase URL). |
| Q3 | Which region is canonical — `us-central1` or `me-west1`? | `us-central1` (matches `triage-parity.yml`, demos, `FRONTEND_URL`). |
| Q4 | Do we want a `staging` environment in front of production? | Yes, but defer until after the thesis defense. |
| Q5 | Replace SA-key auth with Workload Identity Federation now or post-defense? | Post-defense. Defense is the higher-priority irreversible deadline. |
| Q6 | Should production deploy stay manual-dispatch, or auto-deploy on merge to `main`? | Manual-dispatch through defense. |

These answers anchor every subsequent step. If you disagree with any default, flip it in this table *before* moving to §4.

---

## 4. Phased plan (no execution)

Each phase has a **Trigger** (when it's safe to start), **Steps** (what would be done), and **Exit criteria** (what proves it worked). Nothing here is a command to run today.

### Phase 0 — Land the docs (this PR)

- Write `docs/devops/google-cicd-devops-extension-reference.md` and this file.
- No code or config changes.

**Exit criteria:** Both files merged. No other files modified.

### Phase 1 — Reconcile current CI without the extension

(*Highest leverage, lowest risk. Do this whether or not we ever adopt the extension.*)

1. Pick canonical service name + region (Q2, Q3).
2. Update `cloudbuild.yaml` and `.github/workflows/cloud-run-deploy.yml` to agree on:
   - Service name
   - Region
   - Memory / CPU / instance bounds (the GH Action sets `--cpu 2 --memory 1Gi --min-instances 1 --max-instances 3`; `cloudbuild.yaml` currently sets neither CPU nor min/max).
   - Port (currently 8080 in both, keep).
3. Confirm both paths still build and deploy the same image conceptually.
4. Add a short `docs/devops/deployment-runbook.md` describing: who deploys, which path is canonical, how to roll back.

**Exit criteria:** Manual-dispatch deploy succeeds via the chosen canonical path. Old name/region is documented as deprecated. **No** Cloud Build trigger created automatically — deploys remain manual.

**Cost flag:** None new. Same Cloud Run footprint.

### Phase 2 — Pin Artifact Registry

1. Decide AR repo name + location (proposal: `safe-triage` repo in `us-central1`).
2. Update `cloudbuild.yaml` to `docker build` + `docker push` to AR, then `gcloud run deploy --image …` instead of `--source .`.
3. Image tag = git short SHA, with a moving `:latest` tag for convenience.

**Exit criteria:** Production deploy uses a pinned, inspectable image. Rollback = redeploy a previous SHA. **Do not** introduce an automated trigger yet.

**Cost flag:** Artifact Registry storage cost (cents/month for our image sizes). Cloud Build per-minute cost is unchanged because we already run Cloud Build.

### Phase 3 — (Optional) Try the Gemini CLI CI/CD extension on a sandbox project

Only after Phases 1–2 are merged and stable, and only if there is appetite.

1. Create a **separate** GCP project for the experiment (e.g. `safe-triage-cicd-sandbox`) — **not** the production `safe-triage-ai` project.
2. Run `gcloud auth application-default login` as a user with limited rights in that sandbox project only. (Do **not** authenticate as an owner of `safe-triage-ai`.)
3. Install the extension per §3 of the reference doc.
4. Run only the `google-cicd-pipeline-design` flow, in read/dry-run mode if available, and capture the generated `cloudbuild.yaml` for inspection.
5. Diff the generated YAML against ours. Lift only the bits we like.
6. Tear down the sandbox project.

**Exit criteria:** A written diff in `docs/devops/extension-evaluation.md` saying what we kept, what we rejected, and why.

**Cost flag:** Anything in the sandbox project. Track via `python budget_guard.py --status`. Hard cap stays $950.

### Phase 4 — Workload Identity Federation (post-defense)

Replace the JSON service-account key in `FIREBASE_SERVICE_ACCOUNT_SAFE_TRIAGE_AI` with WIF. This deletes the standing TODO in `cloud-run-deploy.yml`.

Steps to plan (do **not** execute now):

1. Create a WIF pool + provider for GitHub OIDC.
2. Bind the SAFE-Triage deploy SA to that provider, scoped to this repo.
3. Update the GH Action to use `google-github-actions/auth@v2` with `workload_identity_provider` instead of `credentials_json`.
4. Rotate / delete the existing JSON key only after the WIF path is confirmed.
5. Remove the JSON-key secret from the repo settings.

**Exit criteria:** No JSON key in any GitHub secret. Deploy still works via manual dispatch.

**Cost flag:** None.

### Phase 5 — Staging environment (post-defense, optional)

Add a `safe-triage-staging` Cloud Run service that auto-deploys on every merge to `main`; promote to `safe-triage` only on manual dispatch.

**Exit criteria:** Production deploys still gated by a human. Staging URL listed in the runbook.

**Cost flag:** A second always-on Cloud Run service. Set `--min-instances 0` to keep cost negligible.

---

## 5. Guard-rails (apply to every phase)

These are the rules even if the agent or extension wants to do otherwise.

1. **Budget guard first.** Before any `gcloud` command that creates a resource, run `python budget_guard.py --status` and confirm we're well under $950.
2. **One change at a time.** No mega-PRs that touch CI, IAM, and code in one go.
3. **No `--no-verify`, no force-push to `main`.** The agent must not bypass pre-commit hooks or branch protection. If a hook fails, fix the underlying issue.
4. **No secrets in commits.** Pre-deployment secret scan is good; `git diff --cached` + a grep for `API_KEY` / `PRIVATE_KEY` is better.
5. **No PHI / no MIMIC-IV data in any artifact.** Buildpacks copy the working tree. Confirm `mimic-iv-ed-2.2/` is `.gcloudignore`'d before any `--source` deploy. (Check current state of `.gcloudignore` / `.dockerignore` in Phase 1.)
6. **All resources tagged** with `app=safe-triage`, `env=prod|staging|sandbox`, `owner=ahmedzayed` so the budget guard's clean-up sweep can find them.
7. **Reversibility:** prefer Cloud Build trigger creation via `gcloud builds triggers import <file>.yaml` (declarative, in-repo) over CLI flags so we can re-apply or delete cleanly.
8. **No org-wide changes.** Everything stays scoped to the `safe-triage-ai` project unless Phase 3's sandbox project is in play.

---

## 6. What I'd recommend if you asked me today

(*This is a recommendation, not a decision.*)

- **Do** land the docs (Phase 0) — that's this PR.
- **Do** Phase 1 (reconcile service name + region) before the thesis defense. It's the bug most likely to bite during the live demo.
- **Defer** Phase 2 (Artifact Registry pinning) until after defense unless you want rollback insurance for the demo.
- **Skip** Phase 3 entirely before defense. The Gemini CLI CI/CD extension is interesting, but trying a new agent-driven tool on the production project two months before the thesis is exactly the kind of move that has burned us before (Cloud Run cost incident). Revisit in summer.
- **Plan** Phases 4–5 for after the defense and before the RWTH start in fall 2026.

---

## 7. What this plan deliberately leaves to a human

- Final answers to Q1–Q6 in §3.
- Whether `safe-triage` or `safe-triage-api` "owns" the canonical name in production.
- Whether the existing `me-west1` service is in use by anyone (it must be confirmed dead before being deleted; that delete is **not** part of any phase here).
- The actual click in GCP Console / `gcloud` that creates anything.

---

## 8. Stop condition

Per the original instruction: **stop after writing the docs and this plan.** Nothing in `backend/`, `frontend/`, `cloudbuild.yaml`, `.github/`, or any GCP project changes as part of this work.

Next time we touch this, start from §3 (decision questions) and walk forward.
