# Metadata-only telemetry boundary

Guardian currently runs a synthetic authority and lineage sandbox. It does not install eBPF programs, attach to a container runtime, inspect live traffic, scan memory or classify real people. The HATS analytic lane uses recorded metadata; its outputs cannot grant authority. This document describes a separate operator-controlled integration boundary and a small input contract for evaluating metadata. It is not a record of a deployed cluster sensor.

## Accepted metadata

The metadata minimizer accepts an explicit allowlist. Unknown properties are rejected, including unknown nested span properties. Rejected raw values must not be echoed to an error response or written to a log.

| Field | Meaning |
| --- | --- |
| `sourceClass` | `SIMULATED` or `OBSERVED`, declared by the producer; it is not independently authenticated by this field |
| `coverageComplete` | Producer declaration about this batch, not a discovery guarantee over the cluster |
| `spans` | At most 128 bounded metadata records |
| `traceId` | 32 hexadecimal characters |
| `spanId`, `parentSpanId` | 16 hexadecimal characters; the parent may be null |
| `agentId` | Bounded opaque identifier; do not put a username, address, secret or payload in it |
| `kind` | `spawn`, `tool` or `message` |
| `startedAt`, `endedAt` | Valid timestamps defining the observed interval |
| `status` | `ok`, `error` or `unknown` |

Trace and span IDs support correlation; they are not authenticated agent identities. Missing ancestry or incomplete coverage remains `UNKNOWN`. A claimed `OBSERVED` source must be distinguished from a trusted sensor attestation. A permitted span does not become an authorization receipt.

The default contract excludes raw prompts, generated responses, token streams, request/response bodies, credentials, authorization headers, private headers, literal IP addresses, full URLs, mouse trajectories and process-memory contents. Nano-level instrumentation can report bounded task/span metadata; it does not require token interception. Behavioral features must not be described as a calibrated human/AI likelihood without a separately evaluated dataset and methodology.

Run the included synthetic metadata example locally from `guardian/`:

```bash
node scripts/analyze-telemetry.mjs examples/telemetry/synthetic-spans.json
```

The CLI bounds input to 64 KiB, validates and minimizes the batch, then reports actual span counts, duration statistics and timestamp coincidences. It makes no network request and has no action authority. Complete metadata coverage within a batch does not establish complete authority-path coverage; that remains `UNKNOWN` for this standalone analysis.

## Collector placement and source trust

Deploy collectors only in an explicitly selected operator-controlled sandbox. A practical path is application instrumentation → authenticated local collector → authenticated ingestion gateway → separate analytic store. Attach trusted workload/deployment identity at the ingestion boundary after authenticating the source. Keep a producer-declared agent ID separate from a signed build/deployment attestation, and keep both separate from legal ownership.

Use a pinned OpenTelemetry Collector build, bounded queues and batches, memory limits and measured CPU/network budgets. Strip disallowed attributes before export. Configure tail sampling with trace-parent retention; if sampling, dropped spans, restart or queue loss makes ancestry incomplete, retain that fact rather than inventing a complete trace. Do not put full payloads into span names, errors, attributes or collector debug logs.

Application instrumentation cannot independently observe a compromised or uninstrumented process. Kernel and runtime signals can strengthen an observation record only within their actual coverage. A cryptographic digest supplied by an untrusted producer is still an untrusted digest.

## Network flow rules

Keep telemetry transport separate from authority traffic. Start with default-deny ingress and egress for the observed namespace. Permit only required application dependencies and authenticated telemetry export. Do not grant a monitored agent access to the authority policy store, sensor control API or signing keys.

The following Kubernetes policies illustrate the telemetry portion. They are **not applied by Guardian** and must be adapted to the cluster's namespace labels, CNI, DNS and required application dependencies. NetworkPolicy limits connectivity; mTLS, source authentication, tenant authorization and rate limits must also be enforced by the collector/gateway.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: guardian-default-deny
  namespace: guardian-observed
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: guardian-metadata-egress
  namespace: guardian-observed
spec:
  podSelector:
    matchLabels:
      guardian-telemetry: enabled
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: guardian-sensors
          podSelector:
            matchLabels:
              app: otel-collector
      ports:
        - protocol: TCP
          port: 4317
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
```

Add corresponding collector ingress rules that accept only the selected instrumented workloads. Limit collector egress to its authenticated ingestion gateway and required DNS. Avoid broad internet egress or payload mirror destinations. Resolve deployment-specific addresses in the operator's infrastructure; the exported analytic record should contain opaque endpoint/service identifiers rather than literal IP addresses.

## Optional eBPF and runtime adapters

An eBPF adapter would be a separately reviewed deployment, typically a node-level component with only the kernel capabilities its selected probes require. Do not make every application sidecar privileged. Pin and audit the probe program, kernel support, container image and deployment manifest; measure overhead under the intended workload and define a rollback path before enabling it.

Useful default events are process creation/exit references, container lifecycle references and aggregated connection metadata mapped to opaque service IDs. Filter and minimize at the collection boundary. No packet payload, environment-variable dump, command argument payload, credential/header capture or periodic memory scan is required for this demonstration. Treat failed probe attachment, lost events, unsupported kernels and unobserved nodes as incomplete coverage.

| Layer | Bounded observation | Explicit limit |
| --- | --- | --- |
| Macro | Process lifetime and declared API-session references | A process is not proof of an agent's vendor or legal owner |
| Meso | Container/task-queue and parent-span references | A missing worker or queue adapter leaves a coverage gap |
| Micro | Function invocation interval and tool span outcome | A short invocation can be missed by sampling |
| Nano | Bounded subtask/span references | No raw token stream or embedded reasoning capture |
| Multi-agent topology | Registered edges and timestamp overlap | Density or synchronized timestamps do not prove consensus or coordination |

The collector's export interval should follow a measured resource budget. The proposed 100 ms flow updates and 30-second memory scans in the original concept are not implemented or validated requirements. Raw memory scanning is outside the default privacy boundary.

## Authority remains independent

The analytic store may propose a risk assessment or a grant to inspect. The protected-action gateway must use current authenticated policy, validate the full delegation lineage, reject missing or cyclic evidence and enforce its own depth, scope and resource limits. It must not convert a model score, producer source label or collector connection into permission. The runnable HATS lab demonstrates this separation with synthetic records and a counter; production containment needs a real protected-system adapter and its own verification.
