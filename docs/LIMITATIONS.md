# Limits and honest interpretation

- No full Backblaze training, measured fleet performance, production load benchmark or maintenance benefit is claimed in this delivery. Tests fit small synthetic data for software verification.
- Class-balanced logistic scores require calibration and independently chosen thresholds before probability or replacement-cost interpretation. High-risk counts are not expected failures.
- The training split is chronological with a 30-day purge, but devices can recur across periods. Hardware cohorts, temporal drift, censoring, class imbalance and selection effects remain research concerns.
- Current PostgreSQL telemetry omits SMART241/242, and zero imputation can create train/serve distribution shift. Vendor-specific SMART semantics need cohort evaluation.
- Rolling `7d/30d` feature names retain historical compatibility but represent 7/30 observations, not calendar durations. Irregular histories are allowed; very short histories yield weaker evidence.
- Artifact signatures, authenticated APIs, rate limiting, drift alerts, durable job orchestration and large-fleet performance work remain future requirements. Joblib inputs must be trusted.
- Feature generation and score persistence are separate phases. Repeated runs use an idempotent drive/day/model key; concurrent telemetry edits are not snapshot-isolated across model calls.
- Existing screenshots under docs/media/ui and docs/media/aws are historical UI/deployment material, not proof of this release's deployment or model quality.
