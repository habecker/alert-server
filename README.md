# Alert Server

FastAPI-based alert broadcasting service with server-sent events (SSE), Redis/Valkey pub/sub, and simple API-key authentication backed by TinyDB. It lets producers publish alerts and consumers subscribe to a real-time stream while also receiving the latest recent alert on connect.

## Features

- REST endpoints to publish and stream alerts.
- Real-time delivery via SSE with Redis/Valkey pub/sub.
- On-connect replay of the latest alert within a TTL window.
- API-key auth with salted+hashed storage (PBKDF2) in a lightweight JSON store.
- Environment-based behavior (dev enables docs; prod hides them).

## Architecture

- `FastAPI` app at `src/alert/app.py`.
- `PUT /alerts` stores and publishes alerts; `GET /alerts` streams alerts via SSE.
- `Redis/Valkey` used for pub/sub and for caching the latest alert.
- `TinyDB` stores users and API keys under `AUTH_STORE_DIR`.
- Simple auth middleware verifies a Bearer token (custom API key) on every request.

Main modules (simplified):

- `alert.app`: FastAPI app, middleware, health endpoint, uvicorn runner.
- `alert.alert.adapter`: Alert router (`/alerts` PUT/GET), SSE publisher/subscriber.
- `alert.core.domain`: API key generation/validation and user model.
- `alert.core.application`: auth use-cases (create/validate API keys).
- `alert.core.domain.repository`: TinyDB-backed user/api-key repository.
- `alert.infrastructure.redis`: Redis client (async) configured from env.
- `alert.infrastructure.environment`: Env var access and validation.
- `alert.create_api_key`: CLI to create an API key for a username.

## Requirements

- Python 3.11+
- Redis-compatible server (Valkey or Redis). A `docker compose` setup is included for Valkey.
- `uv` (recommended) or `pip`/`venv` to install dependencies.

## Environment Variables

Set these via `.env` (see `.env.example`):

- `AUTH_STORE_DIR`: Directory where the TinyDB JSON auth store lives, e.g. `./data/auth/`.
- `STAGE`: `dev` or `prod`. In `prod`, docs/OpenAPI are disabled.
- `REDIS_HOST`: Host for Redis/Valkey (e.g., `localhost`).
- `REDIS_PORT`: Port for Redis/Valkey (e.g., `6379`).

Note: Ensure `AUTH_STORE_DIR` exists before running (e.g., `mkdir -p data/auth`).

## Quickstart (Local)

1. Start Valkey (Redis-compatible) locally using Docker Compose:

```bash
docker compose up -d
```

2. Copy the example env and adjust if needed:

```bash
cp .env.example .env
mkdir -p data/auth
```

3. Install dependencies and run the server.

Using uv (recommended):

```bash
uv sync
uv run python -m alert.app
```

The API listens on `http://localhost:8080`.

## Authentication and API Keys

All endpoints require a Bearer token. Create an API key per username with the provided CLI:

```bash
uv run python -m alert.create_api_key -u alice
# or: python -m alert.create_api_key -u alice
```

This prints a secret API key. Store it securely and use it as a Bearer token:

```
Authorization: Bearer <API_KEY>
```

Implementation details:

- API keys are generated per user, then stored as salted+hashed entries (PBKDF2) under the user.
- The secret itself is never stored; only the salt and hash are persisted.
- Validation extracts the username from the key and checks the hash for a match.

## API

All requests must include `Authorization: Bearer <API_KEY>`.

- `GET /health`

  - Returns `{"status":"ok"}` for basic service health.

- `PUT /alerts`

  - Body: `{"message": "...", "level": "info|warn|error", "metadata": { ... }}`
  - Stores the latest alert with a TTL (30 minutes) and publishes to the SSE channel.
  - Response: `{"status": "alert stored", "alert": { ... }}`

- `GET /alerts`
  - SSE stream of alerts (`text/event-stream`).
  - On connect, if a recent alert exists (within TTL), it is sent immediately.
  - Each event is delivered as a line starting with `data: ` followed by JSON.

### Example Usage

Create an alert:

```bash
API_KEY=... # output from create_api_key
curl -X PUT \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message":"Deploy completed","level":"info","metadata":{"version":"1.2.3"}}' \
  http://localhost:8080/alerts
```

Subscribe to alerts (SSE):

```bash
API_KEY=...
curl -N -H "Authorization: Bearer $API_KEY" http://localhost:8080/alerts
```

Health check:

```bash
curl -H "Authorization: Bearer $API_KEY" http://localhost:8080/health
```

## Dev Notes

- Dev vs Prod: When `STAGE=dev`, Swagger UI is available at `/docs` and OpenAPI at `/openapi.json`. In `prod`, these are disabled. Endpoints still require a Bearer token in all stages (Swagger can be configured with the token via the top-right Authorize button).
- Redis/Valkey: Configured via `REDIS_HOST`/`REDIS_PORT`. The included Compose file exposes Valkey on `127.0.0.1:6379`.
- Data store: TinyDB file is created under `AUTH_STORE_DIR` as `auth.json`. Ensure the directory exists.

## Project Scripts and Entrypoints

- Run app: `python -m alert.app` (or `uv run python -m alert.app`).
- Create API key: `python -m alert.create_api_key -u <username>`.

## Production Considerations

- Set `STAGE=prod` to disable docs and OpenAPI.
- Run behind a reverse proxy and terminate TLS at the edge.
- Provide a managed Redis/Valkey and secure network access to it.
