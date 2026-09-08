# ReliScore reliability delivery specification

Preserve storage-telemetry predictive failure and the existing Next.js → NestJS/PostgreSQL → FastAPI/scikit-learn architecture. No finance features or invented performance results.

## Contracts

1. Persist exactly the model probability and threshold bucket, even if every drive is low risk. Ranking must never manufacture probabilities.
2. Serve only finite bounded inputs, exact ordered feature schemas, and finite probabilities. Explicit null values use documented training-time fills. Missing artifact metadata cannot silently invent zeros or explanations.
3. For supported binary linear estimators, explain coefficient × transformed feature in log-odds units. Other estimators provide no unsupported local attribution.
4. Expose unavailable health/503 when artifacts are absent. Model information carries artifact provenance and explanation method; joblib files remain trusted local executable inputs.
5. Train and serve with the same zero-fill policy; enforce chronological holdout with a horizon purge, remove train-evaluation fallback, report baseline and holdout provenance. Synthetic training fixtures verify software only.
6. Upgrade vulnerable dependencies compatibly, lock installation, run Node lint/types/tests/build and Python model/training tests in CI.

## Milestones

- Record independent QuizBee review and this specification.
- Add failing score-preservation/input/explanation/artifact tests; implement minimal corrections and verify.
- Add chronological training fixture tests, consistent preprocessing and honest evaluation metadata.
- Patch dependencies/CI, document methodology/architecture/limits, verify UI and release evidence.

## Acceptance

Exact observed counts and CI links in PORTFOLIO_DELIVERY; independent core review by portfolio lead; push ordinary verified commits to existing main. Existing AWS/UI evidence remains historical and labeled. No full Backblaze training claimed without running it.
