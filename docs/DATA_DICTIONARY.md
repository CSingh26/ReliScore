# Data contracts

| Field | Meaning |
| --- | --- |
| drive_id / serial_number | Stable device identity; not a person identifier |
| day / as_of_date | UTC observation date; no future input belongs in its features |
| capacity_bytes | Raw device capacity in bytes |
| age_days | Calendar days since the device's lifetime first observation |
| SMART `<attribute>_raw` | Vendor-specific raw value; not comparable across all device models |
| temperature | Reported drive temperature; source must establish unit conventions |
| `_mean_7d`, `_mean_30d` | Mean of nonmissing values among last 7/30 observations |
| `_std_30d` | Population standard deviation among last 30 observations |
| `_delta_vs_7d` | Current value minus last-seven-observation mean; unknown current is zero-imputed |
| `_is_increasing` | One only when current and preceding observed values exist and current is larger |
| label_30d | Failure in the next 30 days; negative only with sufficient follow-up; otherwise null |
| risk_score | Model output in [0,1]; class-balanced and not proven fleet-calibrated |
| risk_bucket | Illustrative threshold bucket, always consistent with stored model output |
| top_reasons.contribution | Coefficient × transformed feature, in log-odds units for supported logistic models |
| model_version | Artifact identity; synthetic tests visibly use `synthetic-software-fixture-v1` |
| artifact_sha256 | Hash of joblib bytes for identification, not a trust signature |

PostgreSQL retains historical FeaturesDaily columns such as `labelFailWithin14d` and `smart5Slope14d` for compatibility. The versioned `featureVector` JSON is the scoring contract; those legacy names are not the current 30-day target or fitted inputs. The current schema does not hold SMART241/242; zero imputation is explicitly documented. `predictedFailures30d` is a historical API response name meaning count of HIGH flags; the UI labels it High-risk drives.
