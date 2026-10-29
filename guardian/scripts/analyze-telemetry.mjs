// SPDX-License-Identifier: Apache-2.0
import { open } from 'node:fs/promises';
import { analyzeHats, minimizeTelemetry } from '../server/hats-analytics.mjs';

const MAX_BYTES = 65_536;

async function readBounded(filename) {
  const handle = await open(filename, 'r');
  try {
    if (!(await handle.stat()).isFile()) throw new Error('INPUT_INVALID');
    const buffer = Buffer.alloc(MAX_BYTES + 1);
    let length = 0;
    while (length < buffer.length) {
      const { bytesRead } = await handle.read(buffer, length, buffer.length - length, null);
      if (!bytesRead) break;
      length += bytesRead;
    }
    if (length > MAX_BYTES) throw new Error('INPUT_TOO_LARGE');
    return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(buffer.subarray(0, length)));
  } finally { await handle.close(); }
}

if (process.argv.length !== 3) {
  console.error('Usage: node scripts/analyze-telemetry.mjs path/to/metadata.json');
  process.exitCode = 1;
} else {
  try {
    const telemetry = minimizeTelemetry(await readBounded(process.argv[2]));
    const measurements = analyzeHats({ agents: [], events: [], telemetry });
    const durations = telemetry.spans.map(span => Date.parse(span.endedAt) - Date.parse(span.startedAt));
    const output = {
      product: 'UNISON Guardian metadata inspector',
      evidence: 'CONJECTURE', measurementEvidence: 'OBSERVED',
      sourceClass: telemetry.sourceClass,
      sourceAssertion: telemetry.sourceAssertion,
      originTrusted: false, signaturesVerified: false, authority: 'none',
      metadataCoverage: telemetry.coverage,
      registeredAuthorityCoverage: {
        status: 'UNKNOWN',
        reason: 'This file supplies span metadata only. No registered authority graph, agent lineage, or execution boundary was verified.',
      },
      features: {
        spanCount: telemetry.spans.length,
        declaredAgentCount: new Set(telemetry.spans.map(span => span.agentId)).size,
        traceCount: new Set(telemetry.spans.map(span => span.traceId)).size,
        durationMs: {
          mean: durations.length ? durations.reduce((sum, value) => sum + value, 0) / durations.length : null,
          min: durations.length ? Math.min(...durations) : null,
          max: durations.length ? Math.max(...durations) : null,
        },
      },
      timingCoincidence: measurements.coordination,
      limitations: [
        'Span parentage is not delegated authority or a verified agent lineage.',
        'Source class, timestamps, and identifiers are caller declarations; OBSERVED labels do not authenticate the producer.',
        'Timing coincidence does not classify human behavior, detect consensus, or establish an agent swarm.',
        'This local command makes no network requests and cannot authorize execution.',
      ],
    };
    console.log(JSON.stringify(output, null, 2));
  } catch {
    // Do not echo file contents, filenames, parser excerpts, or private fields.
    console.error('Metadata rejected: provide a UTF-8 JSON file of at most 64 KiB matching the metadata-only schema. No payload text, headers, addresses, or unknown fields are accepted.');
    process.exitCode = 1;
  }
}
