# Backblaze H=30 Training

This directory contains the full-dataset Backblaze training pipeline for a
30-day failure horizon (`label_30d`).

## Disk And Runtime Warning

Backblaze ZIPs are large and the full historical ingest requires significant
disk and time. Plan for tens of GB locally when running the full pipeline.

## Quick Smoke Test

`make train-smoke` runs the real training and feature-building code on explicitly synthetic temporary parquet fixtures. It checks the temporal purge, zero-fill parity, censoring and rejection of empty evaluation windows. No Backblaze download or production artifact is produced. Tiny two-day public-data samples cannot support a 30-day target plus holdout, so they are no longer mislabeled as evaluation.

## Full Training (All Available Backblaze Periods)

```bash
make train-h30-all
```

This executes:
1. `backblaze_manifest.py` to collect all annual + quarterly datasets.
2. `download_backblaze.py` to cache ZIPs under `data/backblaze/zips/`.
3. `build_warehouse.py` to convert ZIP CSVs into parquet partitions.
4. `build_features.py` to create `label_30d` + rolling features.
5. `train_streaming.py` to train incrementally across all rows.

## Manual Commands

```bash
python3 ml/training/backblaze_manifest.py --out data/backblaze/manifest.json
python3 ml/training/download_backblaze.py --manifest data/backblaze/manifest.json --dest data/backblaze/zips
python3 ml/training/build_warehouse.py --zips data/backblaze/zips --out data/backblaze/warehouse --clean
python3 ml/training/build_features.py --warehouse data/backblaze/warehouse --out data/backblaze/features_h30 --horizon-days 30 --clean
python3 ml/training/train_streaming.py --features data/backblaze/features_h30 --horizon-days 30
```

## Artifact Output

Artifacts are written to:

`services/model/artifacts/telemetry_h30_<timestamp>/`

Required files:
- `model.joblib`
- `feature_schema.json`
- `metrics.json`
- `version.json`
- `model_card.md`

## Backfill App Database

To populate the API/Postgres tables from parquet warehouse for dashboard use:

```bash
make backfill-fleet
```

This imports real Backblaze drives/telemetry (no synthetic scores) and triggers
`POST /api/v1/score/run` for the latest warehouse day.
