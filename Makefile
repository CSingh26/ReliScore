SHELL := /bin/sh

.PHONY: dev up down logs test test-api test-model lint train seed

dev:
	docker compose up --build

up:
	docker compose up -d --build

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=200

seed:
	docker compose exec api pnpm prisma:seed

train:
	python3 -m pip install -r ml/training/requirements.txt
	cd ml/training && python3 -m src.pipeline --quarter 2020_Q2

test:
	pnpm test
	pytest services/model/tests

test-api:
	pnpm --filter @reliscore/api test

test-model:
	pytest services/model/tests

lint:
	pnpm lint
