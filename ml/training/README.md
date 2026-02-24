# Backblaze H=30 Training

This directory contains the full-dataset Backblaze training pipeline for a
30-day failure horizon (`label_30d`).

## Disk And Runtime Warning

Backblaze ZIPs are large and the full historical ingest requires significant
disk and time. Plan for tens of GB locally when running the full pipeline.

## Quick Smoke Test

Runs a minimal end-to-end validation with one ZIP and limited partitions:

```bash
make train-smoke
```

This executes:
1. Build dataset manifest.
2. Download one ZIP.
3. Build parquet warehouse (limited CSV files).
4. Build H=30 features (limited rows).
5. Train streaming model and export artifacts.

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

`services/model/artifacts/backblaze_h30_all_<YYYYMMDDHHMM>/`

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
