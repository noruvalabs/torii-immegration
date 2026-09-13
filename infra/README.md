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

## Host sizing

The staging host is a GCE **e2-micro**: 964 MB of RAM and — the number that actually bites — a
**0.25 vCPU sustained baseline** that only bursts to 2. Several values in
`compose/docker-compose.yml` are tuned to that box specifically. **Read this before resizing
the VM**, or the stack will keep behaving as if it still has 1 GB.

Measured on 2026-09-12, this host saturates at roughly **8–10 concurrent requests**. That is
not 8–10 users: with normal think-time, 50 people using the app generate about 3–8 concurrent
requests, and most of those are now served from the nginx cache without waking Node.

### What does NOT change with host size

These are correctness fixes rather than tuning, and they get *more* valuable under load, not
less. Leave them alone:

- The healthcheck probes. `import httpx` + one GET cost **3.5 s** per probe in the api image;
  at the old 15 s interval the api and ai liveness checks together burned ~46% of a core in a
  continuous loop. They use stdlib `urllib` at 30 s instead. The web probe uses busybox `wget`
  against `127.0.0.1` rather than booting a second Node runtime (~2 s, and it overran its own
  5 s timeout under load, flapping the container to `unhealthy` while it served traffic fine).
- nginx static-asset caching, HTML/RSC caching, gzip on API responses, upstream keepalive.
  Next.js already compresses its own output, so the gzip win is confined to the FastAPI
  responses — `openapi.json` drops from 149 KB to 19 KB.
- Log rotation, and the HTML cache purge in `deploy.sh`.

### What DOES change with host size

| Setting | e2-micro (1 GB, now) | e2-small (2 GB) | e2-medium (4 GB) |
| --- | --- | --- | --- |
| `shared_buffers` | 96MB | 256MB | 512MB |
| `effective_cache_size` | 256MB | 768MB | 2GB |
| `max_connections` | 40 | 60 | 100 |
| `work_mem` | 4MB | 8MB | 16MB |
| `max_parallel_workers_per_gather` | 0 | 0 | 2 |
| postgres `mem_limit` | 256m | 512m | 1g |
| api / ai / web `mem_limit` | 224m / 256m / 224m | 384m each | 768m each |
| `NODE_OPTIONS` heap (`WEB_NODE_OPTIONS`) | 160 | 320 | 640 |
| uvicorn `--workers` (api, ai) | 1 | 1 | 2 |

Also re-enable the Google Cloud Ops agents once there is RAM to spare —
`scripts/tune-host.sh --trim-agents` stops them to reclaim ~115 MB, which is 13% of an
e2-micro but noise on anything larger. Reverse with
`systemctl enable --now google-cloud-ops-agent`.

**`--workers` is the only one of these that raises the user ceiling.** The rest stop the box
falling over; workers add throughput. Set it to the sustained vCPU count, and raise
`max_connections` alongside it — each worker carries its own pool of 10 + 5 (see
`apps/api/src/torii_api/db/engine.py`, overridable via `TORII_DB_POOL_SIZE`).

### One assumption the HTML cache depends on

nginx caches prerendered HTML and RSC payloads. That is safe **only** because the web app
authenticates from `localStorage` with no Next.js middleware, so the server cannot tell who is
asking and returns a byte-identical shell to everyone; per-user data arrives afterwards over
`/backend/`, which is never cached.

**If the app ever gains cookie-based auth, a `middleware.ts`, or server-rendered per-user
content, the `torii_html` zone in `nginx/conf.d/torii.conf` must be removed** — otherwise one
user's page can be served to another. Every other change here is a performance trade; this one
is a correctness boundary.

### When vertical scaling runs out

Resizing carries this shape to roughly 150–300 active users. Past that the binding constraint
is Postgres sharing a host with everything else, and the fix is architectural rather than a
tuning value: move the database to Cloud SQL, then run multiple api containers behind nginx.
The compose file does not need rewriting for that — `TORII_DATABASE_URL` simply points
elsewhere and the `data` network loses its postgres service.

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

Generate it with **`base64 -w0`** — unwrapped, single line. `deploy.sh` decodes it to a scratch
file, checks that it is valid base64, non-empty, and actually contains `TORII_DATABASE_URL`,
`TORII_JWT_SECRET_KEY` and the `POSTGRES_*` keys, and only then swaps it into place. A bad
secret now fails the deploy loudly and leaves the existing `.env` untouched. Before that guard
existed, a malformed value truncated `.env` to zero bytes and exited before the rollback trap
was armed: the running containers carried on serving from the environment they already held,
so nothing looked broken until the next `docker compose up` recreated them with no
configuration — at which point the api would have fallen back to its `sqlite:///./torii.db`
default and stopped reading Postgres entirely.

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
