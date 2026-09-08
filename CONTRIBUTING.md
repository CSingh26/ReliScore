# Contributing

Use Node22, pnpm9.12.3 and Python3.12. Install the checked-in pnpm lock and requirements-lock.txt. Run the complete Quality workflow locally before proposing changes; preserve pure numeric contracts, exact feature order and truthful unavailable states.

Changes to preprocessing must test both training and serving semantics. Model comparisons require chronological evidence and documented cohort/label assumptions. Synthetic fixtures prove software behavior only. Never commit populated environment files, credentials, raw private data or untrusted model artifacts. See docs/METHODOLOGY.md and docs/LIMITATIONS.md before interpreting results.
