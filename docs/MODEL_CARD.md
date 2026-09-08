# Model transparency

No production model is bundled. The versioned training output is a class-balanced, incrementally fitted binary logistic classifier for a 30-day observed-failure target. Inputs and preprocessing are defined in METHODOLOGY.md. Deployment requires trusted model.joblib, feature_schema.json, metrics.json and version.json files in one version directory.

Current validation is synthetic software testing. It verifies actual fitting, split purge, censoring, fill parity, scaled explanations, unavailable state and request contracts. Its results cannot estimate deployment quality. A deployable model needs chronological cohort evaluation, calibration at natural prevalence, a maintenance-policy baseline, false-positive analysis and independent acceptance criteria.

The service exposes model type, version, horizon, feature order, available metrics, artifact hash, training provenance and explanation method. Review these with every model replacement. Older artifacts lacking complete valid fill/schema metadata must be regenerated. Existing numerical predictions produced by the removed rank fallback should be treated as historical operational scores and rescored before comparison with current probabilities.
