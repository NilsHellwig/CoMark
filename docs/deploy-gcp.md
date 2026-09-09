# Deploy to Google Cloud Run

One multi-container Cloud Run service (Caddy → FastAPI + Next.js, plus an
ephemeral Redis), Postgres on **Neon**, deployed by GitHub Actions on every green
push to `main`. Scales to zero — **~$0/month** for hobby traffic.

New to Google Cloud? [google-cloud-explained.md](google-cloud-explained.md) walks
through every term, every permission, and every command in plain language.

```
push main → CI (backend · frontend · e2e) green → deploy job
          → build 3 images → Artifact Registry
          → alembic upgrade head → Neon
          → gcloud run services replace → https://comark-<hash>.<region>.run.app
```

## 1. Neon database

1. Create a project at <https://neon.tech> (free tier).
2. Copy the **connection string** (`postgres://…?sslmode=require`). The app strips
   `sslmode` and adds TLS itself.

## 2. One-time GCP setup

```bash
PROJECT_ID=<PROJEKT-ID> REGION=europe-west1 GITHUB_REPO=NilsHellwig/CoMark \
  ./infra/bootstrap.sh
```

It enables APIs, creates the Artifact Registry repo, mirrors `redis:8-alpine`,
sets up **Workload Identity Federation** (keyless GitHub → GCP auth) and a
`comark-deployer` service account, and creates the Secret Manager secrets
(`comark-secret-key`, `comark-database-url`, `comark-google-client-id`,
`comark-google-client-secret`). It prints the exact GitHub config to set.

## 3. GitHub repo config

**Settings → Secrets and variables → Actions**

| Variables | Value |
|---|---|
| `GCP_PROJECT_ID` | `<PROJEKT-ID>` |
| `GCP_REGION` | `europe-west1` |
| `GCP_WIF_PROVIDER` | printed by `bootstrap.sh` |
| `GCP_DEPLOYER_SA` | `comark-deployer@…iam.gserviceaccount.com` |
| `GOOGLE_ENABLED` | `true` / `false` (shows the Google button) |
| `PUBLIC_URL` | leave unset for the first deploy |

| Secrets | Value |
|---|---|
| `NEON_DATABASE_URL` | the Neon connection string (migrations step only) |

## 4. First deploy

Push to `main` (or run the **CI** workflow manually). The `deploy` job ends with
`::notice:: Set repo variable PUBLIC_URL=https://comark-<hash>.<region>.run.app`.
Set that variable so later deploys skip an extra revision.

Smoke test:

```bash
curl https://comark-<hash>.<region>.run.app/api/v1/health
```

## 5. Google sign-in (optional)

After the first deploy, add the redirect URI to your OAuth client
(<https://console.cloud.google.com/auth/clients>):

```
https://comark-<hash>.<region>.run.app/api/v1/auth/google/callback
```

Then store real credentials and set `GOOGLE_ENABLED=true`:

```bash
printf '%s' "<client-id>"     | gcloud secrets versions add comark-google-client-id --data-file=-
printf '%s' "<client-secret>" | gcloud secrets versions add comark-google-client-secret --data-file=-
```

Re-run the workflow.

## Notes

- **One instance.** Yjs rooms live in the FastAPI process. Going past one instance
  needs the Redis room bridge (`backend/app/collab/pubsub.py`, currently a stub).
- **Cold start** ~2–4 s after idle; open editors reconnect and rooms rehydrate
  from the `yjs_updates` table — no data loss.
- **Cost driver:** long-lived WebSocket tabs count as active instance time. The
  Cloud Run free tier covers ~50 h/month; beyond that ~$0.06/h.
- **Rollback:** `gcloud run services update-traffic comark --to-revisions <rev>=100 --region <region>`.
- **Logs:** `gcloud run services logs read comark --region <region>`.
- If `gcloud run services replace` rejects the summed CPU (`1000m`), bump each
  container's `cpu:` so the total is `2`.
