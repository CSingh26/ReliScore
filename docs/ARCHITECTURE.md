# Architecture and trust boundaries

Next.js server-rendered views read a typed NestJS API. Prisma stores drive identity, raw telemetry, daily feature vectors, versioned predictions and audit entries in PostgreSQL. FastAPI loads local scikit-learn artifacts. DuckDB converts historical parquet into causal rolling features, then Python trains with bounded batches.

```text
Backblaze/public or user telemetry → parquet warehouse → labeled features
                                               ↓
                              purged temporal train/test → artifact bundle
                                               ↓
PostgreSQL telemetry → observation windows → NestJS → FastAPI model
                                               ↓          ↓
                                     versioned prediction ← validated score
                                               ↓
                                  Next.js fleet and drive views
```

The model boundary accepts 1–1000 observations, each with an exact feature-key set of at most 256 finite numeric/null values. The API chunks larger fleets sequentially. Every returned item must match requested drive, day, order, count and the inspected model version before persistence. Prediction writes are one database transaction; feature generation and the later audit log are separate transactions, so operational retries remain necessary.

Artifact loading checks ordered feature agreement, unique names, finite complete fills and metadata version. `/model/info` adds SHA-256 and training provenance. Pickled/joblib artifacts execute Python while loading: accept only locally controlled artifacts, never untrusted uploads. A checksum identifies an artifact; it does not authenticate its author.

Missing model artifacts leave `/health` inspectable with `model_loaded=false`; scoring and information endpoints return 503. Invalid requests produce 422. No model is invented. The model is loaded at startup; installing a new artifact requires a service restart. Pin MODEL_VERSION for reproducible deployment; `latest` otherwise selects filesystem modification time.

The API and model are local/internal research services without an implemented authentication perimeter or rate limits. Bind locally or place behind an authenticated gateway; the optional client token alone does not establish server-side authorization. Credentials use ignored environment files and checked-in examples only.
