# Three-minute demo storyboard

**Total running time: 3:00 exactly.** The intervals below are consecutive and sum to 180 seconds. Use newly generated synthetic runs. Keep browser controls and the evidence labels visible. Match the final recording to the actual submitted commit.

Before recording, start the app and verify all three scenarios. Do not expose API keys, environment files, browser credentials or private research material. Prepare the actual model status; choose the matching branch at 2:15.

| Time | On screen | Narration |
| --- | --- | --- |
| **0:00–0:20** | Open UNISON Guardian. Show the graph and synthetic-sandbox notice. | “An agent can lose its main permission while a delegated or queued action remains possible. UNISON Guardian makes that boundary testable. This is a controlled synthetic sandbox: no real funds, credentials or external jobs are affected.” |
| **0:20–0:45** | Select the `queued` scenario. Point to Operator, Planner, Delegate, Queued worker, Tool gateway and Protected action. Briefly inspect an identity field. | “The registered graph shows which grants connect an operator to a protected action. Delegated grants inherit their ancestor's authority. A run identifier, a task, a configured model and an owner are different claims. The demo does not authenticate an external owner.” |
| **0:45–1:25** | Click **Run baseline**. Show the baseline counter and queued job. Click **Revoke authority**, then **Replay queued action**. Inspect the PASS result and its checks; click **Run verification** if needed. | “The baseline executes once and queues another operation. Now I revoke the planner's root grant. The queued operation still carries its earlier permission, but execution checks the current ancestor chain again. It is blocked before changing the counter. PASS means the registered routes are disconnected and this queued replay was denied in this sandbox.” |
| **1:25–1:55** | Switch to the `alternate` scenario, resetting the run. Repeat **Run baseline**, **Revoke authority**, **Replay queued action**. Show FAIL and the surviving service-account path. | “This case has another independent grant. Revoking the planner blocks its descendants but leaves that route active. Guardian reports FAIL and names the surviving path. A successful revocation of one grant is not complete closure.” |
| **1:55–2:15** | Switch to `unknown`. Repeat the workflow. Show UNKNOWN and the incomplete-coverage check. | “Here the inventory is declared incomplete. Known routes can be disconnected and the queued action blocked, yet Guardian still returns UNKNOWN. Missing coverage is not proof that every possible route is gone.” |
| **2:15–2:40** | Expand **Ask Muse**. Use exactly one of the two branches below. | Use the matching narration below. |
| **2:40–3:00** | Open **Evidence ledger**, inspect a receipt and download the evidence JSON. End on the graph/result with the repository's contribution disclosure available. | “Every run preserves labeled events and recomputable local digests. Those hashes do not prove identity or immutable history. The graph, verifier, scenarios, interface and Meta adapter were built for this entry. Guardian's claim is bounded and reproducible: inspect authority, test revocation and keep unsupported claims visible.” |

## The model segment: choose the truthful branch

### Branch A — a real request succeeds during the recording

At 2:15, click **Analyze this sandbox**. Show the successful structured response from the actual Meta request and a non-secret response identifier when the provider supplies one. Keep the same run visible. Only describe this as a live call if the request really completed during this recording.

Narration: “Muse Wonder is analyzing this registered graph through the Meta Model API. Its structured response suggests grants to inspect and states uncertainty. It cannot issue authority or change the verifier. The deterministic result remains separate from the model's explanation.”

If the request does not complete inside the allotted segment, do not invent output or silently substitute a fixture. Retake the segment, or label a previously completed response **recorded real API response**, not live. Recheck the final running time.

### Branch B — no successful real request is available

Show the actual unconfigured, pending or error state. Do not show a mock proposal as model output.

Narration: “The Muse Wonder adapter is implemented, but a successful real Meta request is still pending for this recording. Deterministic checks work locally. This is not yet evidence of live Meta model usage; that submission requirement still needs a real response.”

## Recording notes

- Scenario resets create new runs; do not imply the ledger is one continuous execution across all three scenarios.
- The PASS, FAIL and UNKNOWN labels describe the synthetic test scope, not a universal safety assessment.
- Keep the 25-second model segment in both branches so the final storyboard remains exactly three minutes.
- This file is a recording plan. It does not establish that a video has been recorded, uploaded or submitted.
