# Meta Global AI Developer Hackathon — form answers

[Submission form](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit) · [Event page](https://cerebralvalley.ai/e/meta-ai-developer-hackathon)

Copy-paste answers. The Meta answer preserves the repository's current disclosure that successful live inference remains pending.

**Team Name**
```text
UNISON
```

**Team Members**
```text
Deonte Watts — Deontewattsv1
```

**Project title, if requested**
```text
UNISON: Verifiable Evidence and Authority for AI Agents
```

**Track**
```text
Indie Developer
```

**Problem statement**
```text
Push the Frontier
```

**Project Description**
```text
UNISON helps developers trace what supports an AI claim and whether a delegated action is currently authorized. It makes evidence, uncertainty, and permission transitions visible through two runnable workflows.

The new browser traceability playground starts a synthetic claim as UNKNOWN, attaches hashed evidence, and runs explicit evidence-window, governance, and state-transition checks. Its 12-stage trace labels implemented mechanisms, advisory output, and illustrative concepts. Implemented blocking checks determine whether the demonstration receipt remains UNKNOWN or reaches locally_supported. Editing a recorded stage output makes hash-chain verification report BROKEN.

Guardian tests the execution boundary. Run an authorized action, queue another, revoke its ancestor grant, and replay the queued action. Guardian rechecks current authority and denies stale execution while its synthetic action counter stays at one. A surviving independent route produces FAIL; incomplete inventory produces UNKNOWN.

The HATS lab extends this with a Macro/Meso/Micro/Nano hierarchy, inherited scopes, depth and spawning limits, and descendant checks after ancestor revocation. Guardian also includes a Muse Wonder adapter for structured advisory analysis of registered authority paths.

Hackathon contributions include Guardian, HATS, the new browser integration and ports, an evidence-record JSON Schema, a claims register, and unified provenance documentation. Eight source repositories are consolidated with their origins recorded. Existing StateBench and imported implementations are credited as earlier source material.

The demonstrations use synthetic actions and local checks. Hash consistency, local support, scientific truth, and independent reproduction remain distinct.
```

**Public GitHub Repository**
```text
https://github.com/DeontewattsV1/UNISON-StateBench
```

**Live product, if requested**
```text
https://unison-guardian.info-ccehospitalitygroup.workers.dev
```

**3-Minute Demo Video**
```text
https://github.com/DeontewattsV1/UNISON-StateBench/releases/download/hackathon-demo-2026-11-04/UNISON-Guardian-demo.mp4
```
> Video notes: see below.

**Describe your use of Meta products to build the submitted project**
```text
UNISON Guardian includes a server-side Muse Wonder integration using muse-wonder-1.0 through Meta’s Responses API. The Ask Muse panel requests an explanation of the registered authority graph, suggested grant IDs to inspect, and explicit uncertainty.

The adapter requests high reasoning effort and strict JSON-schema output. Local validation checks the returned structure and requires suggested grant IDs to exist in the supplied graph. Proposals are bound to the analyzed run and revision, and credentials remain on the server. Deterministic execution checks govern authority decisions; model analysis is advisory.

The upgraded traceability playground runs locally in the browser and makes no model calls. It separately demonstrates evidence and promotion boundaries.

Current repository evidence establishes the implemented adapter and mocked transport tests. A successful real Meta request remains pending, and the public Guardian sandbox disables model requests. This submission describes implemented integration without claiming verified live inference or use of additional Meta products.
```

**Why are Meta’s models important to your solution?**
```text
Muse Wonder’s intended contribution is to help developers interpret delegated authority: explain how a protected action remains reachable, identify registered grants worth inspecting, and communicate uncertainty in a structured proposal.

This requires reasoning across delegation paths and changing state. Structured output lets UNISON validate proposed identifiers and associate the explanation with a specific run. The deterministic verifier and inspectable evidence let developers assess that interpretation against registered authority state.

Meta supplies the proposed reasoning layer in Guardian. The new browser playground demonstrates the evidence discipline around such outputs, including explicit checks before promoting a claim. A completed real Meta request is still needed to demonstrate that model contribution; the repository currently supports no comparative performance claim.
```

**Biggest obstacle — use if this matches your experience**
```text
Keeping authority and evidence boundaries explicit across a growing system. Queued work had to be checked against current permissions, and a local check could not silently become a stronger claim. The implementation addresses this with action-time ancestry checks, PASS/FAIL/UNKNOWN scenarios, explicit promotion blockers, and a claims register separating implemented mechanisms from concepts and unmeasured hypotheses.
```

**Comparison with other models**
```text
The submitted repository contains no controlled cross-model evaluation or retained successful Meta inference, so it does not support a comparative performance claim. Current verification covers deterministic workflows and adapter behavior under mocked responses.
```

## Demo video notes
- Video: https://github.com/DeontewattsV1/UNISON-StateBench/releases/download/hackathon-demo-2026-11-04/UNISON-Guardian-demo.mp4
- Release page: https://github.com/DeontewattsV1/UNISON-StateBench/releases/tag/hackathon-demo-2026-11-04
- Duration ~97 seconds (under 3 minutes); silent screen capture of the public Worker.
- Branch B: Ask Muse showed live analysis disabled; no live Meta inference claimed.
- Demo observed: Queued delegation PASS, Alternate path FAIL, Incomplete inventory UNKNOWN, HATS lab Pass 11/11 including ANCESTOR_REVOKED on stale Nano — so the live Worker does include HATS for this recording.

---

Leave optional **partner feedback** and the **X post link** blank unless applicable. Choose your own experience ratings and review the publication-consent checkbox personally.

The supplied guide lists **November 4, 2026, at 9 PM ET** as the deadline; whether the portal still accepts submissions has not been confirmed.
