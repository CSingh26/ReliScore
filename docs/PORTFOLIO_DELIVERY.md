# ReliScore portfolio delivery evidence

Repository: https://github.com/CSingh26/ReliScore (existing main; visibility preserved). Baseline: `dd3d7e4ae1d76ff9353e794556f2ad5a0783b6fe`, 42 commits. Verified full-stack milestone: `6d33e15cb8c0b73125d8a63f35b53e2780b86223`, 49 commits. Final application change: `36166c2` (complete static chart rendering, web rebuild and all four browser tests rerun); 50 commits before this final report. This report is the 51st meaningful commit. No history padding or force push.

## Scope delivered

Preserved predictive storage failure as CS/ML infrastructure. Removed fabricated operational probabilities; aligned training and inference transformations, lifetime age and observation windows; made unavailable models explicit; bounded/validated scoring and batch provenance; purged temporal labels, censored unknown outcomes and removed training-evaluation fallback; fixed stale retry inputs and latest-version fleet/filter/detail reads. Added model provenance, calibrated-interpretation limits, actual DB/model/browser tests, audited dependency patches and full latest-commit Quality CI.

## Observed local checks (2026-09-08)

| Command / evidence | Observed result |
| --- | --- |
| `npx pnpm@9.12.3 install --frozen-lockfile` | Success |
| `pnpm lint` | All packages pass; existing ESLint/Next lint deprecation notices |
| `pnpm typecheck` | Shared, API and web pass |
| `pnpm test` | 13 pass: shared2, API10, web1 |
| `pnpm build` | Shared/API builds and Next15.5.25 optimized build pass |
| `.venv/bin/pytest services/model/tests -q` | 19 pass; two upstream Starlette test-client deprecation warnings |
| Real PostgreSQL + HTTP model integration | One scenario passes, including actual score persistence and latest-version semantics |
| `pnpm --filter @reliscore/web test:e2e` | 4 pass, desktop/mobile; actual API and synthetic fitted artifact |
| `ruff check services/model/app ml/training --select E9,F63,F7,F82`, `python -m compileall -q services/model/app ml/training` | Pass |
| `docker compose config --quiet && docker compose build` | API, web and model images build successfully |
| Container with no artifacts | Health says unavailable and model info returns503 |
| `pnpm audit` | No known vulnerabilities after js-yaml4.3.2 patch |
| `pip-audit -r requirements-lock.txt` | No known vulnerabilities |
| `python tests/scan_secrets.py` | No common secret-pattern match in tracked text; not proof of absence |

37 passing unit/integration/browser cases in total; the integration scenario contains multiple assertions but is counted once. See TESTING.md for exact environment and fixture commands. No test coverage percentage or model performance metric is claimed.

## Review and visual evidence

Independent portfolio reviewer reproduced online/offline age/missing-delta mismatches and stale-feature retry behavior; all findings were closed after code corrections and independent reruns (19 Python, 10 API tests). Review evidence lives in the separate PortfolioPilot repository `docs/reviews/reliscore.md`. ReliScore's independent review of QuizBee is recorded in `docs/reviews/quizbee-review.md`.

`docs/media/current/synthetic-drive.png` is the current working application reading an isolated database and a real fitted synthetic model. Historical AWS/UI assets are preserved as historical material only. README and methodology, architecture, dictionary, model card and limitations explain the CS story and empirical limits.

## Release verification

Quality runs every push/PR and covers the whole stack, locked installs, lint/types/tests/build, dependency audits, real PostgreSQL/model integration and browser journeys. Observed successful complete run for `6d33e15`: https://github.com/CSingh26/ReliScore/actions/runs/34285227243. The final application change (`36166c2`) changes chart animation only; its web build and four browser tests passed locally. The report commit triggers the same full Quality gate; final containing-commit SHA and latest-run result are verified in the portfolio orchestrator’s release report after push (a document cannot embed its own Git hash). [Latest main Quality run](https://github.com/CSingh26/ReliScore/actions/workflows/quality.yml?query=branch%3Amain).

## Remaining limits

No full Backblaze training, current cloud deployment, production load validation, authenticated service perimeter, calibrated fleet probabilities or maintenance outcomes are claimed. SMART241/242 are not present in online telemetry; zero imputation requires cohort validation. The same drive may appear on both sides of the temporal split. Batch-limited artifact ranges are eligible bounds, not necessarily consumed bounds. Prisma distinct/filter paths need large-fleet performance work; artifacts must be trusted and their hashes are identification, not signatures.
