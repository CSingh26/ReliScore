"""Synthetic fitted models verify serving contracts, never fleet performance."""
import json
import numpy as np
import pytest
from pydantic import ValidationError
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from app.model_loader import ModelStore, LoadedModel
from app.schemas import ScoreRequest, BatchScoreRequest


def fitted_store():
    x = np.array([[10.], [20.], [30.], [40.]])
    scaler = StandardScaler().fit(x)
    model = LogisticRegression().fit(scaler.transform(x), [0, 0, 1, 1])
    store = ModelStore()
    store.loaded = LoadedModel(model, scaler, 'LogisticRegression', ['temperature'], {'temperature': 0.}, {'temperature': float(model.coef_[0, 0])}, 30, 'synthetic-test', {})
    return store


def test_reasons_use_scaled_log_odds():
    store = fitted_store()
    score, _, reasons = store.score({'temperature': 10.})
    expected = store.loaded.model.coef_[0, 0] * store.loaded.scaler.transform([[10.]])[0, 0]
    assert reasons[0].contribution == pytest.approx(expected, abs=1e-6)
    assert reasons[0].direction == 'DOWN'
    assert score < .5


def test_missing_imputation_metadata_is_rejected():
    store = fitted_store()
    store.loaded.fill_values = {}
    with pytest.raises(ValueError, match='fill'):
        store.score({'temperature': None})


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf'), True, '12'])
def test_invalid_numeric_values_rejected(value):
    with pytest.raises(ValidationError):
        ScoreRequest(drive_id='d1', day='2026-01-01', features={'temperature': value})


@pytest.mark.parametrize('size', [0, 1001])
def test_batch_is_bounded(size):
    item = dict(drive_id='d1', day='2026-01-01', features={'temperature': 1.})
    with pytest.raises(ValidationError):
        BatchScoreRequest(items=[item] * size)


def test_duplicate_or_disagreeing_artifact_schema_rejected():
    for schema in [[{'name': 'a'}, {'name': 'a'}], [{'name': 'b'}]]:
        with pytest.raises(ValueError):
            ModelStore._resolve_feature_columns({'feature_columns': ['a']}, {'ordered_features': schema})
