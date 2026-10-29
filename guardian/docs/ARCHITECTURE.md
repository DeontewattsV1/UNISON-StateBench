# Architecture and trust boundaries

```mermaid
flowchart LR
  UI[React user interface] --> API[Session API]
  API --> E[Deterministic authority engine]
  E --> G[Registered graph and rooted grants]
  E --> Q[Queued synthetic operations]
  E --> L[Hash-linked evidence]
  API --> S[Node memory or Worker SQLite checkpoint]
  API --> N[Local Node model adapter]
  N --> M[Meta Responses API]
  M --> P[Locally validated advisory proposal]
  P --> UI
```

## Independent lanes

The authority engine has no model dependency. Only explicit registered grants and current ancestor state can authorize its synthetic action. Parent scope cannot widen through delegation. Missing parents, cycles, and integrity failures deny execution. A previously authorized queue item must pass a new current-state check before it changes the synthetic action counter.

The local Node model lane receives a detached snapshot, labels that data untrusted, and returns a strict structured proposal. Only grant IDs already in the registered snapshot are accepted. No endpoint converts model text into a grant, revocation, or protected action. The API labels proposals `CONJECTURE`, `authority: none`, and records the analyzed run and revision in the response. A subsequent state transition can make an earlier proposal stale. The public Worker does not import the model adapter and always rejects model analysis with `PUBLIC_MODEL_DISABLED`.

## Registered graph verification

Revoking the primary grant invalidates all descendants. Traversal finds active operator-to-action paths in the sealed registration, including an intentionally independent service-account route in the alternate scenario. The witness path explains a failure without pretending that one revoked grant covers every other root.

PASS requires all of the following: primary grant validly revoked, no registered active route to the action, a queued attempt actually denied after revocation, internally consistent evidence, and scenario-declared inventory completeness. A known failure takes precedence; otherwise an unknown required condition preserves UNKNOWN. Even PASS is limited to registered synthetic routes in this run.

The completeness flag is a scenario declaration, not independent discovery of every real system or credential. The demo does not implement credential rotation, distributed revocation propagation, expiring capability tokens, real tool adapters, or third-party identity attestation.

## Ledger

Each event records sequence, run reference, time, type, evidence class, data, previous digest, and a SHA-256 digest of canonical JSON with lexicographically sorted object keys. Verification recomputes digests and validates contiguous sequence, unique IDs, run references, and chain links. The engine retains a tip and sealed registration outside the public snapshot. Node retains them in process memory; the Worker preserves them in a server-side SQLite checkpoint and restores them into engine-owned state on each operation.

The exported bundle contains the final snapshot, event chain, verification result, scope, and explicit trust limitations. A party with write access to an entire unanchored export can rewrite and rehash it. The standalone verifier can report internal consistency, but cannot recover external origin trust or vouch for the reported runtime result.

## Local Node service

Native Node HTTP serves the React build and a small JSON API. Per-session in-memory sandboxes prevent browsers from changing each other's demo runs. JSON bodies are bounded, cross-origin mutations are rejected, provider errors are sanitized, credentials remain server-side, and model calls have a timeout and local rate limit.

Bind the Node service to loopback by default. Its cookie is not an identity assertion or authentication mechanism. Authenticated ingress and shared quotas are required before exposing its paid model endpoint publicly. Trusted signing keys, operational policy and real protected-system adapters are outside this demonstration.

## Public Worker and persistence

`worker/index.mjs` serves an explicit allowlist of built interface assets and the deterministic API. A random 192-bit session cookie selects a `GuardianSession` Durable Object. The HTTPS cookie uses `HttpOnly`, `Secure` and `SameSite=Strict`; possession isolates one anonymous demo session and does not establish a person's identity. JSON requests are bounded to 16 KiB, and declared cross-origin mutations are rejected.

Each Durable Object stores a single checkpoint row in SQLite. Reads, restoration, engine operations and checkpoint writes run synchronously in one transaction. No model call or external action runs inside that transaction. The checkpoint preserves the registration, revoked grants, queue receipts, idempotency flags, evidence chain and result. It is internal server state, never an accepted browser upload or an evidence export.

Restoration checks the checkpoint version, shape, size, checksum, registered topology and retained-state consistency before recreating engine-owned metadata. A corrupted checkpoint fails closed. The checksum detects corruption relative to retained data; it is unkeyed and does not protect against a privileged server operator who replaces the entire checkpoint.

Worker runtime restart does not discard a valid SQLite checkpoint. Each successful operation extends the one-hour idle deadline; an alarm removes an expired row, and an expired session starts a fresh run. Reset replaces the run. A run can contain at most 200 events; an operation that would cross the limit is rejected without persisting its changes. State and evidence remain readable so the participant can export and reset.

The Worker has no model-secret binding or Meta transport and always returns HTTP 503 for `/api/analyze`. Paid model access would require a separately authenticated service with shared rate limiting. Public traffic can still consume Worker and Durable Object resources; the event bound is not an account-wide abuse or billing limit. See [DEPLOYMENT.md](DEPLOYMENT.md).

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Runtime mode and Meta availability; no secret value |
| GET | `/api/state` | Detached session snapshot |
| POST | `/api/reset` | New `queued`, `alternate`, or `unknown` sandbox |
| POST | `/api/baseline` | Authorized synthetic operation and queued work |
| POST | `/api/revoke` | Revoke the primary grant |
| POST | `/api/replay` | Recheck and attempt pending queued work |
| POST | `/api/verify` | Compute bounded deterministic results |
| GET | `/api/evidence` | Download evidence JSON |
| POST | `/api/analyze` | Local Node: non-authoritative Meta proposal; public Worker: always disabled |
