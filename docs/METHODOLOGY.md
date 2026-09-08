# Predictive-failure methodology

## Question and target

ReliScore investigates whether historical drive telemetry can rank disks for investigation before a recorded failure. This is an imbalanced event prediction problem, not proof a disk will fail. The supported target is failure strictly after an as-of day and within the following 30 days. Failure-day and later observations are excluded. A negative requires the drive to remain observed at least 30 more days; otherwise the target is unknown and excluded from training/evaluation. Disappearance is not assumed to be failure.

SMART attributes are vendor-specific. Raw counts, temperature, capacity and age are model inputs, not interchangeable physical units. Features use the last 7 or 30 **observations**, including the current day, with mean, population standard deviation, delta from the seven-observation mean and increase indicator. Legacy names ending in `d` mean observations; irregular sampling can span more calendar days. Drive age uses lifetime first-seen date. Online scoring requires a target-day observation and rejects drives already recorded failed.

## Preprocessing and fitting

Nonfinite training values become missing, then zero before standardization. The identical zero fills are exported in the bundle. Zero is a pragmatic baseline, not a claim that an unavailable SMART attribute is physically zero. The API cannot currently ingest SMART 241/242; these inputs are zero-imputed and this distribution mismatch requires validation before real deployment.

`StandardScaler.partial_fit` learns location and scale from the training period only. A second pass fits deterministic-seed `SGDClassifier(loss="log_loss")` with inverse-frequency class weights. Batches iterate chronologically. The last requested months form holdout; training stops 30 days before the split so its labels do not use holdout events. Both classes must be investigated when interpreting metrics; the same device may appear in train and test, so this is temporal, not unseen-device, generalization.

## Evaluation and provenance

The pipeline refuses to substitute training observations when holdout is empty. Artifacts include eligible train/test ranges (batch caps can consume shorter ranges), purge length, requested batch limits, imputation policy and manifest SHA-256 (or explicit unavailable marker). Metrics include average precision (`pr_auc` historical API name), Brier score, calibration bins and recall among the top 1%/5%, compared with a constant training-prevalence baseline. Top-fraction recall uses at least one observation. These metrics are not claimed for Backblaze in this delivery: the executable experiment uses an explicitly synthetic fixture to test plumbing and mathematics.

Class balancing changes the learning objective and raw probabilities may be poorly calibrated for fleet prevalence. LOW < .40, MED [.40,.75), HIGH >= .75 are illustrative fixed thresholds, not optimized maintenance policies. The API preserves actual model output even if all disks remain LOW; it never resizes the distribution to manufacture urgent work.

## Explanations

For supported binary logistic estimators, each displayed term is `coefficient[j] × transformed_feature[j]` in **log-odds units**. The intercept plus all terms forms the decision function; the UI shows only the five largest absolute terms. A zero term has no effect. These are not SHAP values, causal effects, raw-unit sensitivities, or probability deltas. Unsupported estimator types return an empty explanation list and `explanation_method="unavailable"`.

## Primary references

- [Backblaze Drive Stats data and definitions](https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data).
- [scikit-learn SGDClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.SGDClassifier.html).
- [scikit-learn probability calibration](https://scikit-learn.org/stable/modules/calibration.html).
- [scikit-learn StandardScaler](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html).
