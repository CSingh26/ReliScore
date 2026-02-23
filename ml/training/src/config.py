from pathlib import Path

HORIZON_DAYS_DEFAULT = 14
FEATURE_COLUMNS = [
    "age_days",
    "smart_5_mean_7d",
    "smart_5_slope_14d",
    "smart_197_max_30d",
    "smart_197_mean_7d",
    "smart_198_delta_7d",
    "smart_199_volatility_30d",
    "temperature_mean_7d",
    "read_latency_mean_7d",
    "write_latency_mean_7d",
    "missing_smart_197_30d",
]

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS_ROOT = REPO_ROOT / "services" / "model" / "artifacts"
CACHE_ROOT = REPO_ROOT / "ml" / "training" / "data" / "cache"
PROCESSED_ROOT = REPO_ROOT / "ml" / "training" / "data" / "processed"
