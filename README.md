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
make logs       # tail logs
make seed       # rerun seed in API container
make train      # run ML training pipeline locally
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
cd ml/training
python3 -m src.pipeline --quarter 2020_Q2 --max-drives 500 --horizon-days 14
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

```bash
curl -X POST http://localhost:8000/score_batch \
  -H "Content-Type: application/json" \
  -d '{"items":[{"drive_id":"DRV-0001","day":"2026-02-23","features":{"age_days":120,"smart_5_mean_7d":6,"smart_5_slope_14d":0.3,"smart_197_max_30d":12,"smart_197_mean_7d":5,"smart_198_delta_7d":2,"smart_199_volatility_30d":1.8,"temperature_mean_7d":35,"read_latency_mean_7d":4.4,"write_latency_mean_7d":5.1,"missing_smart_197_30d":0}}]}'
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
