from pathlib import Path
import sys

MODEL_ROOT = Path(__file__).resolve().parents[1]
if str(MODEL_ROOT) not in sys.path:
    sys.path.insert(0, str(MODEL_ROOT))

# Fitted synthetic classifier is test infrastructure, never a production artifact.
import json
import os
import tempfile
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

_fixture_root = tempfile.TemporaryDirectory(prefix='reliscore-synthetic-tests-')
os.environ['MODEL_ARTIFACTS_ROOT'] = _fixture_root.name
os.environ['MODEL_VERSION'] = 'synthetic-test-v1'
_fixture = Path(_fixture_root.name) / 'synthetic-test-v1'
_fixture.mkdir()
_model = LogisticRegression().fit(np.array([[0.], [1.], [2.], [3.]]), [0, 0, 1, 1])
joblib.dump({'model': _model, 'model_type': 'LogisticRegression', 'feature_columns': ['temperature'], 'fill_values': {'temperature': 0.}, 'horizon_days': 30}, _fixture / 'model.joblib')
for name, payload in {
    'feature_schema.json': {'ordered_features': [{'name': 'temperature'}]},
    'version.json': {'model_version': 'synthetic-test-v1', 'horizon_days': 30, 'data_source': 'SYNTHETIC TEST FIXTURE'},
    'metrics.json': {'evaluation_scope': 'synthetic software fixture; no fleet evaluation'},
}.items():
    (_fixture / name).write_text(json.dumps(payload))
