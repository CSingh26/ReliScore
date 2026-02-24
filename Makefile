SHELL := /bin/sh

.PHONY: dev up down stop logs test test-api test-model lint train seed backblaze-all train-h30-all train-smoke backfill-fleet

dev:
	docker compose up --build

up:
	docker compose up -d --build

down:
	docker compose down -v

stop:
	@if [ -f docker-compose.yml ]; then docker compose down --remove-orphans; fi
	@ids=$$(docker ps -aq --filter name=reliscore); \
	if [ -n "$$ids" ]; then docker stop $$ids; fi
	@ids=$$(docker ps -aq --filter label=com.docker.compose.project=reliscore); \
	if [ -n "$$ids" ]; then docker stop $$ids; fi
	@docker ps

logs:
	docker compose logs -f --tail=200

seed:
	docker compose exec api pnpm prisma:seed

train:
	python3 -m pip install -r ml/training/requirements.txt
	$(MAKE) train-h30-all

backblaze-all:
	python3 -m pip install -r ml/training/requirements.txt
	python3 ml/training/backblaze_manifest.py --out data/backblaze/manifest.json
	python3 ml/training/download_backblaze.py --manifest data/backblaze/manifest.json --dest data/backblaze/zips
	python3 ml/training/build_warehouse.py --zips data/backblaze/zips --out data/backblaze/warehouse --clean
	python3 ml/training/build_features.py --warehouse data/backblaze/warehouse --out data/backblaze/features_h30 --horizon-days 30 --clean

train-h30-all:
	$(MAKE) backblaze-all
	python3 ml/training/train_streaming.py --features data/backblaze/features_h30 --horizon-days 30

train-smoke:
	python3 -m pip install -r ml/training/requirements.txt
	python3 ml/training/backblaze_manifest.py --out data/backblaze/manifest.json --include_year_from 2023
	python3 ml/training/download_backblaze.py --manifest data/backblaze/manifest.json --dest data/backblaze/zips --max_files 1
	python3 ml/training/build_warehouse.py --zips data/backblaze/zips --out data/backblaze/warehouse --max_csv_files 2 --clean
	python3 ml/training/build_features.py --warehouse data/backblaze/warehouse --out data/backblaze/features_h30 --horizon-days 30 --row-limit 200000 --clean
	python3 ml/training/train_streaming.py --features data/backblaze/features_h30 --horizon-days 30 --batch-size 50000 --test-months 6 --max-train-batches 6 --max-test-batches 2

backfill-fleet:
	docker run --rm --network reliscore_default \
		-v "$$(pwd):/workspace" -w /workspace \
		python:3.12-slim sh -lc "python -m pip install -r ml/training/requirements.txt && python ml/training/backfill_app_db.py \
		--warehouse data/backblaze/warehouse \
		--database-url '$${BACKFILL_DATABASE_URL:-postgresql://reliscore:reliscore@postgres:5432/reliscore}' \
		--lookback-days '$${BACKFILL_LOOKBACK_DAYS:-45}' \
		--max-drives '$${BACKFILL_MAX_DRIVES:-5000}' \
		--min-history-days '$${BACKFILL_MIN_HISTORY_DAYS:-14}' \
		--score-url '$${BACKFILL_SCORE_URL:-http://api:4000/api/v1/score/run}'"

test:
	pnpm test
	pytest services/model/tests

test-api:
	pnpm --filter @reliscore/api test

test-model:
	pytest services/model/tests

lint:
	pnpm lint
