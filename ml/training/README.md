# Training Pipeline

This package trains the failure-risk model from Backblaze telemetry and writes versioned artifacts to:
`services/model/artifacts/<model_version>/`.

## Workflow

1. Install Python deps:
   `pip install -r ml/training/requirements.txt`
2. Download Backblaze data with caching:
   `python -m src.download_backblaze --quarter 2020_Q2`
3. Prepare model dataset:
   `python -m src.prepare_dataset --input-dir ml/training/data/cache/2020_Q2`
4. Train + emit artifacts:
   `python -m src.train --prepared ml/training/data/processed/training_dataset.csv`

Or run the full pipeline:
`python -m src.pipeline --quarter 2020_Q2`

## Output Artifacts

- `model.joblib`
- `metrics.json` (includes PR-AUC, recall@top_k, calibration curve)
- `model_card.md`
- `version.json`
- `feature_schema.json`
