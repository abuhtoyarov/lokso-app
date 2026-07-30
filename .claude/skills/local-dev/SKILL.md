---
name: local-dev
description: Use when starting work for the day, when the app won't come up locally, or when the user asks to check, start, or troubleshoot the local Lokso environment — verifies prerequisites, infrastructure containers, API health and frontend build state, then reports exactly what is missing and how to fix it.
user_invocable: true
---

# Local Dev Environment

Check and bring up the local Lokso development environment. The full human-facing guide is `ЛОКАЛЬНАЯ-РАЗРАБОТКА.md`; this skill is the fast programmatic path.

## Layout

Infrastructure runs in Docker, the frontend runs natively for hot reload. The backend can run either way — in Docker for a quick look, natively when you need to debug it.

| Service      | Where                    | Port                                  |
| ------------ | ------------------------ | ------------------------------------- |
| PostgreSQL   | Docker (`plane-db`)      | 5432                                  |
| Valkey/Redis | Docker (`plane-redis`)   | 6379                                  |
| RabbitMQ     | Docker (`plane-mq`)      | not published to host (internal only) |
| MinIO        | Docker (`plane-minio`)   | 9000, console 9090                    |
| Django API   | Docker (`api`) or native | 8000                                  |
| web          | native                   | 3000                                  |
| admin        | native                   | 3001                                  |

## Diagnose

Run all of these and read the results together before changing anything:

```bash
node -v && pnpm -v && python3 --version && docker --version
docker info >/dev/null 2>&1 && echo "docker daemon: OK" || echo "docker daemon: DOWN"
ls apps/*/.env 2>/dev/null | wc -l
docker compose -f docker-compose-local.yml ps
curl -s -m 5 http://localhost:8000/
curl -s -m 3 -o /dev/null -w "%{http_code}\n" http://localhost:3000/
find packages -maxdepth 3 -type d -name dist | head
```

Read the output against this table:

| Symptom                                                                        | Cause                                                                                                                  | Fix                                                                             |
| ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Node below 22.18 or pnpm not 11.x                                              | Wrong toolchain                                                                                                        | `nvm install 22 && npm install -g pnpm@11`                                      |
| `docker daemon: DOWN`                                                          | Docker Desktop not running                                                                                             | Start Docker Desktop, wait for the whale icon                                   |
| Fewer than 5 `.env` files                                                      | Env files never generated                                                                                              | `./setup.sh`                                                                    |
| Containers missing from `ps`                                                   | Infrastructure not up                                                                                                  | See "Bring up infrastructure"                                                   |
| `curl :8000` returns nothing                                                   | API not running                                                                                                        | See "Run the backend"                                                           |
| `api` container `Up` but `curl :8000` never responds, logs stuck on migrations | Started `api` (Option A) without `migrator` on a fresh DB — the entrypoint waits for migrations but never applies them | `docker compose -f docker-compose-local.yml up -d migrator`, then restart `api` |
| `curl :3000` returns `000`                                                     | Frontend not running                                                                                                   | See "Run the frontend"                                                          |
| No `dist` directories under `packages`                                         | Internal packages not built                                                                                            | `pnpm turbo run build --filter='web^...'`                                       |
| File upload fails, or an uploaded attachment/cover/avatar won't open           | `MINIO_PUBLIC_ENDPOINT_URL` not set in `apps/api/.env`                                                                 | Set `MINIO_PUBLIC_ENDPOINT_URL="http://localhost:9000"`                         |

## Bring up infrastructure

```bash
docker compose -f docker-compose-local.yml up -d plane-db plane-redis plane-mq plane-minio
docker compose -f docker-compose-local.yml ps
```

All four must show `Up`. To run the backend in Docker as well, add `migrator api worker beat-worker` to the `up` command — `migrator` applies migrations once and exits; `api`'s entrypoint only waits for migrations to exist, it never applies them, so omitting `migrator` hangs the API forever on a fresh database.

## Run the backend

The backend as shipped **does not work natively at all**: `apps/api/.env` points every dependency at a Docker-internal hostname — `POSTGRES_HOST="plane-db"`, `REDIS_HOST="plane-redis"`, `RABBITMQ_HOST="plane-mq"`, `AWS_S3_ENDPOINT_URL="http://plane-minio:9000"` (active, `USE_MINIO=1`) — and none of these hostnames resolve from the host. `python manage.py migrate`, the very first command, fails immediately on DNS resolution of `plane-db`, before RabbitMQ ever enters the picture. `plane-mq` also has no `ports:` mapping in `docker-compose-local.yml` (container-internal only, see Layout table), so even after fixing hostnames, the broker is still unreachable until that's added too. Two options:

**Option A — Docker (recommended when background tasks matter).** Add `migrator api worker beat-worker` to the "Bring up infrastructure" `up` command. Works out of the box, no config changes — but `migrator` must be included on a fresh database, or `api` hangs waiting for migrations that never get applied (see Diagnose table).

**Option B — Native**, for hot reload and a debugger. Requires deliberately overriding every dependency's address — do not make these changes automatically:

- In `apps/api/.env`, set `POSTGRES_HOST`, `REDIS_HOST`, `RABBITMQ_HOST` to `localhost`, and `AWS_S3_ENDPOINT_URL` to `http://localhost:9000`
- Add a `ports:` mapping for `plane-mq` in `docker-compose-local.yml` (e.g. `5672:5672`) — Postgres, Redis, and MinIO already publish theirs

Django does not read `.env` on its own, so it has to be sourced:

```bash
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements/local.txt
set -a && source .env && set +a
python manage.py migrate
python manage.py runserver 8000
```

Verify: `curl http://localhost:8000/` returns `{"status": "OK"}`. This only proves Django itself is up — it passes even when RabbitMQ is unreachable, so it does not prove background tasks work.

Background tasks, in another tab with the same venv and the same `source .env` (requires Option B's full hostname override including RabbitMQ, or use Option A instead):

```bash
celery -A plane worker -l info
```

## Run the frontend

Internal packages must be built before the dev server starts:

```bash
pnpm install
pnpm turbo run build --filter='web^...'
pnpm --filter web dev
```

Open `http://localhost:3000`. The admin panel is `pnpm --filter admin dev`, the public pages are `pnpm --filter space dev`.

## Before committing

```bash
pnpm check:types
pnpm check:lint
```

Backend tests run in their own Docker stack:

```bash
docker compose -f docker-compose-test.yml run --rm api-tests pytest -m unit
```

## Common Mistakes

- Running `manage.py` without `set -a && source .env && set +a` — Django does not load `.env` itself, and the failure looks like a database connection error
- Starting `pnpm --filter web dev` before building internal packages — fails with `Failed to resolve entry for "@plane/..."`
- Assuming `docker compose ps` listing a container means the service is healthy — check the API with `curl` as well
- Running the API both in Docker and natively — both bind port 8000 and the second one fails
- Reaching for `docker compose -f docker-compose-local.yml up -d` with no service names when only infrastructure is wanted — that starts the backend containers too
- Running the backend natively without overriding `apps/api/.env` first — `migrate` fails immediately on DNS resolution of `plane-db`; RabbitMQ is not the only blocker, all four hostnames (`plane-db`, `plane-redis`, `plane-mq`, `plane-minio`) need to become `localhost`
- Running the backend natively, seeing `curl http://localhost:8000/` return `{"status": "OK"}`, and concluding the environment is fully working — that check passes even when RabbitMQ is unreachable; Celery and any task-dispatching request will still fail
