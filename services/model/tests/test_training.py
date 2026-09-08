"""Real fitted training on synthetic parquet; results are not Backblaze evidence."""
import sys
from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'ml' / 'training'))
from train_streaming import train_streaming
from build_features import build_features, SMART_FEATURE_COLUMNS


def test_training_uses_purged_holdout_and_same_fill_at_inference(tmp_path):
    features = tmp_path / 'features'; features.mkdir()
    pd.DataFrame({'as_of_date': pd.date_range('2025-01-01', periods=180), 'serial_number': ['SYNTHETIC'] * 180, 'signal': [np.nan if i % 5 == 0 else float(i % 7) for i in range(180)], 'label_30d': [i % 2 for i in range(180)]}).to_parquet(features / 'fixture.parquet')
    manifest = tmp_path / 'manifest.json'; manifest.write_text('{"source":"SYNTHETIC TEST FIXTURE"}')
    artifact = train_streaming(features, tmp_path / 'artifacts', 30, 32, 1, manifest, None, None)
    bundle = joblib.load(artifact / 'model.joblib')
    meta = json.loads((artifact / 'version.json').read_text())
    metrics = json.loads((artifact / 'metrics.json').read_text())
    assert bundle['fill_values']['signal'] == 0.
    assert (pd.Timestamp(meta['test_range']['start']) - pd.Timestamp(meta['train_range']['end'])).days > 30
    assert metrics['evaluation_scope'] == 'chronological_holdout'
    assert 0 <= metrics['baseline_brier_score'] <= 1
    assert meta['dataset_manifest_hash'] != 'manifest_missing'


def test_empty_holdout_never_reuses_training_rows(tmp_path):
    features = tmp_path / 'features'; features.mkdir()
    pd.DataFrame({'as_of_date': [pd.Timestamp('2025-01-01')] * 4, 'signal': [0.,1.,2.,3.], 'label_30d': [0,1,0,1]}).to_parquet(features / 'fixture.parquet')
    with pytest.raises(RuntimeError, match='training|holdout'):
        train_streaming(features, tmp_path / 'artifacts', 30, 32, 1, tmp_path/'missing.json', None, None)


def test_feature_labels_exclude_failure_day_and_censor_unknown_future(tmp_path):
    warehouse = tmp_path / 'warehouse'; warehouse.mkdir()
    rows = []
    for serial in ['failed', 'surviving']:
        for i, day in enumerate(pd.date_range('2025-01-01', periods=45)):
            if serial == 'failed' and i > 35: continue
            rows.append({'date': day, 'serial_number': serial, 'model': 'SYNTHETIC', 'failure': int(serial == 'failed' and i == 35), 'capacity_bytes': 1000, **{c: 1. for c in SMART_FEATURE_COLUMNS}})
    pd.DataFrame(rows).to_parquet(warehouse / 'fixture.parquet')
    out = tmp_path / 'features'; build_features(warehouse, out, 30, None)
    frame = pd.read_parquet(out)
    failed = frame[frame.serial_number == 'failed']
    assert failed.as_of_date.max() < pd.Timestamp('2025-02-05').date()
    surviving = frame[frame.serial_number == 'surviving']
    assert surviving[surviving.as_of_date > pd.Timestamp('2025-01-15').date()].label_30d.isna().all()
