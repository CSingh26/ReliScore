# Reproducing the release checks

Install Node22, pnpm9.12.3 and Python3.12. `pnpm install --frozen-lockfile` and `pip install -r requirements-lock.txt` reproduce the checked dependency set. Generate Prisma and build shared code before API tests. `.github/workflows/quality.yml` is the complete executable recipe and runs on every push, including documentation-only release commits.

## Unit and numerical verification

- `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build` cover all three Node packages.
- `pytest services/model/tests -q` fits real classifiers on synthetic fixtures and checks serving, temporal purge and censoring.
- `ruff check services/model/app ml/training --select E9,F63,F7,F82` and `python -m compileall -q services/model/app ml/training` check Python syntax and undefined-name hazards. This is not static Python type coverage.
- `pnpm audit`, `pip-audit -r requirements-lock.txt`, and `python tests/scan_secrets.py` provide bounded dependency/secret evidence.

## Real integration and browser fixture

Use a disposable PostgreSQL database whose name contains `reliscore_portfolio_test`; the integration script refuses other names and deletes only its four prefixed synthetic drives. It does not migrate or erase an existing production database.

```sh
docker run --name reliscore-portfolio-postgres \
  -e POSTGRES_USER=reliscore -e POSTGRES_PASSWORD=reliscore \
  -e POSTGRES_DB=reliscore_portfolio_test \
  -p 127.0.0.1:5441:5432 -d postgres:16-alpine
export DATABASE_URL=postgresql://reliscore:reliscore@127.0.0.1:5441/reliscore_portfolio_test
export MODEL_ARTIFACTS_ROOT=/tmp/reliscore-integration-artifacts
export MODEL_VERSION=synthetic-software-fixture-v1
export MODEL_SERVICE_URL=http://127.0.0.1:8041
pnpm --filter @reliscore/api exec prisma db push
.venv/bin/python tests/create_model_fixture.py
.venv/bin/uvicorn app.main:app --app-dir services/model --host 127.0.0.1 --port 8041
```

In a second terminal with those same environment variables, run:

```sh
KEEP_SYNTHETIC_FIXTURE=true pnpm --filter @reliscore/api exec tsx test/persistence.integration.ts
API_PORT=4041 pnpm --filter @reliscore/api start
```

In a third terminal, run `pnpm --filter @reliscore/web exec playwright install chromium` then `pnpm --filter @reliscore/web test:e2e`. The Playwright configuration starts the built web application and tests desktop/mobile against the actual API; it does not intercept requests or substitute browser data. The screenshot is explicitly labeled synthetic in device identity and model version.

The database test exercises real feature selection, HTTP model scoring, persisted predictions, repeated-run idempotency, exclusion of stale/failed drives and latest-model deduplication in fleet/filter/detail queries. It is one integration scenario with multiple assertions, not a measured load or resilience benchmark.
