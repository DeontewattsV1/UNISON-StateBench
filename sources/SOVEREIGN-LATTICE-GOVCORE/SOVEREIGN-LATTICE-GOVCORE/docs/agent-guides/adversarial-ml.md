# Adversarial ML Defense Reference

Based on NIST Adversarial Machine Learning (AML) taxonomy.

## Five Primary Risk Categories

### 1. Training Data Poisoning
Attacker injects malicious samples into training data.
Defense: signed data pipelines, source scoring, provenance validation on ingestion.

### 2. Privacy Attacks Against Model Parameters
Membership inference, model inversion, attribute inference.
Defense: differential privacy in training, output scrubbing, rate limiting on repeated queries.

### 3. Direct Prompt Injection
Malicious instructions injected directly into user input.
Defense: VanguardProbe-style intent scanning, policy-gated tool calls.

### 4. Indirect Prompt Injection (via Retrieved Content)
Malicious instructions embedded in documents, web pages, or data sources that the model retrieves.
Defense: retrieval isolation, content sanitization before injection into context, source trust scoring.

### 5. Model Extraction
Adversary queries model repeatedly to reconstruct parameters or decision boundaries.
Defense: rate limiting, query pattern monitoring, output perturbation for sensitive queries.

## Integration with GovCore Agents
The `AdversarialMLMonitor` agent in `sovereign_govcore/agents/` watches for:
- Prompt injection patterns in inputs and retrieved content
- Model extraction behavior signatures (high-volume systematic queries)
- Data poisoning indicators in ingestion pipelines
- Indirect injection via threat intelligence feeds or SBOM data
