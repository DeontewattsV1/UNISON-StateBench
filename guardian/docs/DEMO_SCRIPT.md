# Three-minute demo storyboard

**Total running time: 3:00 exactly.** The intervals below are consecutive and sum to 180 seconds. Use newly generated synthetic runs. Keep browser controls and evidence labels visible, and record only features present in the submitted build.

Before recording, check the three revocation scenarios and run the HATS demo once. Reset them for the recording. Match the source/deployment revision to the release record. Keep API keys, browser credentials and private research inputs out of the video. Prepare the actual model status; choose the truthful branch at 2:10.

| Time | On screen | Narration |
| --- | --- | --- |
| **0:00–0:15** | Open Guardian. Show the registered authority graph and synthetic-sandbox notice. | “UNISON Guardian makes delegated authority testable. The model proposes; deterministic checks decide. This sandbox uses synthetic identities and actions, without moving funds or controlling external agents.” |
| **0:15–0:55** | Select **Queued delegation**. Click **Run baseline**, inspect counter one and the pending job, then **Revoke authority** and **Replay queued action**. Show PASS and its checks. | “The baseline executes once and queues another action. I revoke its ancestor grant. At execution, the gateway checks current authority again. The stale queued operation is denied and the counter stays at one. PASS is bounded to this registered graph and tested boundary.” |
| **0:55–1:15** | Select **Alternate authority path** and repeat baseline, revoke and replay. Show FAIL and the surviving service-account witness path. | “A second root survives this revocation. Guardian reports FAIL and shows its witness path. Removing one permission does not close an independent route.” |
| **1:15–1:30** | Select **Incomplete inventory**, repeat the workflow and show UNKNOWN. | “Known paths are disconnected here, but coverage is incomplete. The result stays UNKNOWN rather than claiming global closure.” |
| **1:30–2:10** | Open **HATS lab** and run the fresh HATS demo. Show Macro → Meso → Micro → Nano, denied depth/scope/quota steps, ancestor revocation and the denied descendant action. Inspect the analytic and authority lanes. | “HATS binds each child record to its run, parent, identity and inherited scope, then recomputes the lineage. Hard depth, scope and spawning limits reject these attempts. Revoking the ancestor also blocks the descendant's next action; the counter stays at one. Timing and topology features are advisory heuristics. They cannot override current authority, and they do not prove real-world identity or a swarm.” |
| **2:10–2:35** | Return to **Authority graph** and open **Ask Muse**. Use exactly one model branch below. | Use the matching narration below. |
| **2:35–3:00** | Show a recomputed ledger receipt, export revocation evidence, then open the HATS lab and export its separate evidence. End with contribution disclosure and repository link visible. | “The exports preserve synthetic records and checks actually performed by the harness. Hashes support consistency inspection; they do not authenticate an external origin or make history immutable. Guardian's graph, HATS lab, verifier, interface and adapter are new work. Existing StateBench is disclosed as prior work. These are bounded results you can reproduce.” |

## The model segment: choose the truthful branch

### Branch A — a real request succeeds during the recording

At 2:10, click **Analyze this sandbox** in the local Node app configured with a server-held key. Show the actual structured Meta response and a non-secret response identifier when supplied. Only call it a live request if it completed during this recording. The public Worker disables model requests.

Narration: “Muse Wonder analyzes this registered graph through the Meta Model API. Its structured response proposes grants to inspect and states uncertainty. It cannot issue authority, spawn an agent or change a verification outcome. The current deterministic result stays separate.”

If the request does not complete inside the segment, retake it or label a previously completed response **recorded real API response**. Do not substitute a fixture or claim a timeout completed successfully. Recheck the final running time.

### Branch B — no successful real request is available

Show the actual unconfigured, disabled, pending or error state. Do not display a mock proposal as Meta-generated output.

Narration: “The Muse Wonder adapter is implemented, but a successful real Meta request is still pending. Public paid requests are disabled. Deterministic scenarios and HATS remain runnable; this recording does not yet establish live Meta model usage.”

## Recording notes

- Scenario and HATS resets create separate runs. Do not imply one continuous ledger across them.
- Run the HATS demo only in a fresh lab. Its exact expected outcomes must match the resulting records; do not narrate an unchecked step as passed.
- A permitted HATS action increments a synthetic counter; the lab does not launch a real process or recursive agent swarm.
- Use the actual published revision and verified test results. HATS must be deployed before claiming it works at the public URL.
- Keep the 25-second model segment for either branch so the storyboard remains exactly three minutes.
- This is a recording plan, not evidence that a video was recorded, uploaded or submitted.
