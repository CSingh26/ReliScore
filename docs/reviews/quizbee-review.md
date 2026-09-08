# Independent QuizBee review

Reviewed commit `f6bbc0a3663463ca0917d8ee8b8650d8cc0fc734` read-only on 2026-09-08. Reviewer owns ReliScore and made no QuizBee edits.

## Actionable findings

- **P2 — Activate now retains future start.** `backend/controller/instructor/roomController.js`, `activateScheuledRoomNow`, copies scheduled `startTime` unchanged. The new authoritative `requireOpenRoom` rejects questions/submissions until that future time, contradicting the action. Set activation start to now, reject an already expired end, and cover the transition.
- **P2 — Invalid intervals can be persisted.** `createRoom` checks truthiness only. Reversed/equal intervals create unusable rooms and invalid date/type values can return 500. Validate strict date/time strings, finite timestamps and start < end before writes; test invalid input produces 400 and no persistence.

## Evidence and remaining limits

All 12 backend domain/controller/authorization/cookie tests passed in this review. Read the actual MongoDB integration test: it imports nested questions, submits a real graded attempt, protects linked modules, injects a leaderboard failure inside a real transaction and asserts the attempt count stays one. It is credible rollback coverage; this reviewer did not rerun its database setup.

Assigned-module grading, legal-option checks, request-time room checks, role gates before uploads, and atomic attempt/leaderboard writes are substantive engineering improvements. Authentication uses signed cookie role claims; cookie scope is coherent for same-site HTTPS production and HTTP local development. Typed frontend submission uses credentialed requests and sends answers rather than trusting client scores. Browser fixtures are labeled synthetic.

Room lifecycle copy/delete transitions remain non-transactional, and cross-collection room identity is not globally unique; concurrency and repeat-attempt policy remain documented limitations. Question shuffling uses a biased random sort; this affects fairness/randomization, not grading correctness. Runtime response decoding remains weaker than compile-time frontend types.

## Portfolio lens

README states a clear CS problem and connects invariants to actual test evidence within 90 seconds. Finance functionality would be artificial here. The project's value is authorization, transaction boundaries, deterministic grading and distributed-time consistency. Resolve the two timing defects before calling this release complete.
