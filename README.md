# ReliScore

Storage Telemetry -> Predictive Failure platform built as a monorepo.

## Architecture

```text
┌─────────────────────────────┐
│ Next.js Dashboard (apps/web)│
│ - Fleet overview             │
│ - Drive filters + details    │
└───────────────┬──────────────┘
                │ HTTP (REST)
                ▼
┌─────────────────────────────┐
│ Node Platform API           │
│ services/api (NestJS + TS)  │
│ - Fleet/drives endpoints    │
│ - Feature job + scoring job │
│ - Prisma + Postgres         │
└───────────────┬──────────────┘
                │ HTTP (service-to-service)
                ▼
┌─────────────────────────────┐
│ FastAPI Model Service       │
│ services/model (Python)     │
│ - /score /score_batch       │
│ - /model/info /health       │
│ - Loads versioned artifacts │
└───────────────┬──────────────┘
                │
                ▼
┌─────────────────────────────┐
│ Artifacts + Data            │
│ - services/model/artifacts  │
│ - Postgres (docker compose) │
└─────────────────────────────┘
```

## Repository Layout

```text
.
├── apps/web
├── services/api
├── services/model
├── ml/training
├── infra/local
├── packages/shared
├── .github/workflows
├── .env.example
├── docker-compose.yml
├── Makefile
└── README.md
```

## Local Setup

### Prerequisites
- Node.js 20+
- pnpm 9+
- Python 3.11+
- Docker + Docker Compose

### One-command startup

```bash
docker compose up --build
```

This starts:
- `postgres` on `localhost:5432`
- `model` on `localhost:8000`
- `api` on `localhost:4000`
- `web` on `localhost:3000`

API startup automatically:
1. Applies Prisma schema (`prisma db push`)
2. Seeds demo fleet + telemetry
3. Generates features
4. Runs one scoring batch

Dashboard is immediately populated with meaningful demo data.

### Make targets

```bash
make dev        # docker compose up --build
make up         # detached mode
make down       # stop + remove volumes
make stop       # safe stop for reliscore compose + containers
make logs       # tail logs
make seed       # rerun seed in API container
make backblaze-all  # manifest + download + warehouse + H30 features
make train-h30-all  # full pipeline + streaming train
make train-smoke    # fast end-to-end smoke run
make test       # pnpm test + pytest
```

## Environment Variables

### Root (`.env.example`)
- `DATABASE_URL`
- `API_PORT`
- `MODEL_SERVICE_URL`
- `MODEL_SERVICE_TOKEN`
- `NEXT_PUBLIC_API_BASE_URL`
- `API_INTERNAL_URL`
- `MODEL_ARTIFACTS_ROOT`
- `MODEL_VERSION`

### Service-specific examples
- `apps/web/.env.example`
- `services/api/.env.example`
- `services/model/.env.example`

## API Docs

- FastAPI docs: `http://localhost:8000/docs`
- FastAPI ReDoc: `http://localhost:8000/redoc`
- Node API Swagger UI: `http://localhost:4000/api/docs`
- Node OpenAPI JSON: generated to `services/api/openapi.json` on startup

## Training a Model

Training code is in `ml/training`.

```bash
python3 -m pip install -r ml/training/requirements.txt
make train-smoke
```

For full all-period Backblaze training:

```bash
make train-h30-all
```

Artifacts are written to:

```text
services/model/artifacts/<model_version>/
  ├── model.joblib
  ├── metrics.json
  ├── model_card.md
  ├── version.json
  └── feature_schema.json
```

`services/model/artifacts/ACTIVE_MODEL` is updated automatically to the latest trained version.

## Running Scoring Manually

### Trigger from Node API

```bash
curl -X POST http://localhost:4000/api/v1/score/run \
  -H "Content-Type: application/json" \
  -d '{"day":"2026-02-23"}'
```

### Direct model scoring

Feature keys must exactly match `/model/info` -> `features`.

```bash
python3 - <<'PY'
import requests

base = "http://localhost:8000"
info = requests.get(f"{base}/model/info", timeout=30).json()
features = {name: 0.0 for name in info["features"]}
payload = {"drive_id": "DRV-0001", "day": "2026-02-23", "features": features}
response = requests.post(f"{base}/score", json=payload, timeout=30)
print(response.status_code)
print(response.json())
PY
```

## Testing

```bash
# Python model tests
pytest services/model/tests

# Monorepo JS tests (requires dependencies installed)
pnpm test
```

GitHub Actions workflows:
- `.github/workflows/ci-web.yml`
- `.github/workflows/ci-api.yml`
- `.github/workflows/ci-model.yml`

All workflows run lint/test/build only (no deployment steps).

## Screenshots and Demo Video Placeholders

- Fleet Overview Screenshot: `docs/demo-assets/fleet-overview.png`
- Drives List Screenshot: `docs/demo-assets/drives-list.png`
- Drive Detail Screenshot: `docs/demo-assets/drive-detail.png`
- Demo Video Placeholder: `docs/demo-assets/demo-video-link.txt`

## Future Work

- AWS deployment (ECS + RDS + ALB + Vercel) from CI
- S3-backed artifact store with active-model pointer in DB
- Drift monitoring:
  - data drift (feature distribution)
  - calibration drift
  - operational drift (score volume, latency, error rates)
- Alerting + acknowledgment workflows and export APIs
- Offline backfill jobs for large historical date ranges
