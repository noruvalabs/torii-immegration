# infra

Deployment shape for Torii: GitHub Actions builds the images, GHCR stores them, and one host
pulls them behind a single nginx edge. **The host never builds.**

```
compose/docker-compose.yml   postgres · redis · api · worker · ai · web · nginx
nginx/conf.d/torii.conf      edge routing (/ → web, /backend/* → api, /assistant/* → ai)
scripts/deploy.sh            runs ON the host: pull → up → smoke test → rollback on failure
scripts/bootstrap-host.sh    one-time host preparation
.env.example                 environment template (copy to compose/.env)
```

## The pipeline

```
push to staging ─┐
push to main ────┴─► Deploy ──► gates (reuses CI) ──► build 3 images ──► push to GHCR
                                                                              │
                       host: docker compose pull → up --wait → smoke test ◄────┘
                                               └─ on failure: roll back to the last good tag
```

| Workflow | Trigger | What it does |
| --- | --- | --- |
| [ci.yml](../.github/workflows/ci.yml) | PRs to `main`/`staging`/`develop`, pushes to `develop` | Ruff + pyright + pytest for `apps/api` and `apps/ai`, lint + typecheck for `apps/web`, a no-push build of all three images, and a compose/nginx/shellcheck config pass |
| [deploy.yml](../.github/workflows/deploy.yml) | push to `staging` or `main`, or manual | Runs CI as its gate, builds and pushes `ghcr.io/<owner>/torii-{api,ai,web}`, then deploys over SSH |

`main` and `staging` are deliberately absent from CI's own `push:` trigger — Deploy calls CI as
a reusable workflow, so the gates run once per release, not twice.

## Environments

| Branch | Environment | Deploys to |
| --- | --- | --- |
| `staging` | `staging` | The staging host |
| `main` | `production` | The production host |

Anything else that reaches the workflow resolves to `staging`, so no stray branch can land in
production by accident. A manual run picks its target from the **environment** input.

Both environments use the **same secret names** — GitHub resolves each to the environment the
job selects, so there are no `STAGING_`/`PROD_` prefixes anywhere. Create them under
**Settings → Environments**, add the secrets from the table below to each, and add a required
reviewer on `production` if you want a human gate before a release reaches the live host.

To run both stacks on one box, give staging all three of these — otherwise the two collide on
paths, container names, volumes, and the host port:

- the environment *variable* `TORII_APP_ROOT`, e.g. `/opt/torii-staging`
- `COMPOSE_PROJECT_NAME=torii-staging` in its env file (this also namespaces the volumes, so
  staging gets its own database rather than sharing production's)
- a distinct `NGINX_HTTP_PORT`, e.g. `8081`

### Image tags

Every release is pushed as `sha-<7-char commit>` plus `latest`. **The rollout only ever uses
the sha tag** — it is immutable, so what the host runs is exactly what CI built, and the last
tag that passed its smoke test is recorded on the host for rollback. `latest` exists for humans
reading `docker images`.

### Rolling back

`scripts/deploy.sh` rolls back on its own when the smoke test fails. To go back further, run
the Deploy workflow manually and put a known tag in the **tag** input — that path skips the
build and the gates and re-deploys an image already in GHCR.

## First-time host setup

```bash
scp infra/scripts/bootstrap-host.sh root@HOST:/tmp/
ssh root@HOST 'bash /tmp/bootstrap-host.sh deploy'
```

Then add the deploy key to `/home/deploy/.ssh/authorized_keys`, and terminate TLS in front of
the published nginx port (`NGINX_HTTP_PORT`, default `8080`) with caddy, certbot, or a load
balancer. The compose stack deliberately does not own certificates.

## Repository secrets

Set these under **Settings → Secrets and variables → Actions**. The `deploy` job also targets
the `production` GitHub environment, so add a required reviewer there if you want a manual
approval gate before anything reaches the host.

| Secret | Required | Purpose |
| --- | --- | --- |
| `DEPLOY_SSH_HOST` | yes | Deploy target hostname or IP |
| `DEPLOY_SSH_USER` | yes | SSH user (the `deploy` user from `bootstrap-host.sh`) |
| `DEPLOY_SSH_KEY` | yes | Private half of the deploy key, PEM, whole file including headers |
| `DEPLOY_ENV_FILE_B64` | yes | `base64 -w0` of the production compose `.env` (start from `.env.example`) |
| `DEPLOY_SSH_PORT` | no | SSH port; defaults to `22` |
| `DEPLOY_SSH_KNOWN_HOSTS` | no | Host key line (`ssh-keyscan HOST`). Without it the workflow falls back to trust-on-first-use and logs a warning |
| `GHCR_PULL_TOKEN` | no | Long-lived `read:packages` PAT for the host's registry login. Without it the job's own `GITHUB_TOKEN` is used — it pulls fine during the deploy, but the credentials it leaves in the host's `~/.docker/config.json` expire when the job ends, so a later manual `docker compose pull` on the host will need a fresh login |
| `DEPLOY_WEBHOOK_URL` | no | Discord webhook for deploy notifications; the step is skipped when unset |

`DEPLOY_ENV_FILE_B64` holds every runtime secret (database password, JWT key, SMTP, LLM and
search provider keys). Nothing in it is ever decoded on the runner — it is passed through the
SSH session and written to `/opt/torii/compose/.env` at `0600`.

## Run the whole stack locally

```bash
cp infra/.env.example infra/compose/.env      # then edit POSTGRES_PASSWORD etc.
cd infra/compose
docker compose up -d --wait --build           # --build compiles the images locally
# → http://localhost:8080              (applicant app)
# → http://localhost:8080/admin        (back office)
# → http://localhost:8080/backend/docs (API reference)
# → http://localhost:8080/assistant/health (AI service)
```

`--build` is the local-iteration path only; the production host always pulls. Note that the
**web image builds from the repo root**, not `apps/web` — its Dockerfile needs the workspace
pnpm lockfile, and a lockfile-less install would resolve fresh dependency versions on every
build. The compose `build:` section already sets that context.

`TORII_MIGRATE_ON_STARTUP=true` in `.env` means the API applies Alembic migrations on boot, so
the schema is ready without a manual step. The `worker` service runs the arq scheduler (outbox
drain + renewal reminders + change monitor) against the same Postgres and Redis.

## Networks

- **edge** — nginx ⇄ web/api/ai. Only nginx publishes a host port.
- **data** — api/worker ⇄ postgres + redis. Not reachable from the host or from nginx.

## Health

Every service carries its own `HEALTHCHECK`, and `docker compose up --wait` blocks until they
all pass. `deploy.sh` then adds an end-to-end check through the published edge:

| Path | Reaches |
| --- | --- |
| `/healthz` | nginx itself |
| `/backend/health` | api |
| `/assistant/health` | ai |
| `/` | web |
