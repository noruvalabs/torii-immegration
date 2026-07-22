# infra

Deployment shape for Torii: one host, everything behind a single nginx edge.

```
compose/docker-compose.yml   postgres · redis · api · worker · web · nginx
nginx/conf.d/torii.conf      edge routing (/ → web, /backend/* → api)
.env.example                 environment template (copy to compose/.env)
```

## Run the whole stack

```bash
cp infra/.env.example infra/compose/.env      # then edit POSTGRES_PASSWORD etc.
cd infra/compose
docker compose up -d --wait --build           # --build compiles the api/web images locally
# → http://localhost:8080         (applicant app)
# → http://localhost:8080/admin   (back office)
# → http://localhost:8080/backend/docs   (API reference)
```

`TORII_MIGRATE_ON_STARTUP=true` in `.env` means the API applies Alembic migrations on boot, so
the schema is ready without a manual step. The `worker` service runs the arq scheduler (outbox
drain + renewal reminders + change monitor) against the same Postgres and Redis.

## Networks

- **edge** — nginx ⇄ web/api. Only nginx publishes a host port.
- **data** — api/worker ⇄ postgres + redis. Not reachable from the host or from nginx.

## Notes

- Images are normally built in CI and pulled by `TAG`; `--build` is the local-iteration path.
- TLS/443 is intentionally omitted here — terminate at the host edge (caddy/certbot) or a
  load balancer in front, and add the `443` server block when real certificates exist.
