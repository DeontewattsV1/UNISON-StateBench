// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { analyzeHats, minimizeTelemetry } from './hats-analytics.mjs';

const epoch = Date.parse('2026-10-29T10:00:00.000Z');
const at = ms => new Date(epoch + ms).toISOString();
const policy = { maxDepth: 3, maxChildren: 3, maxAgents: 12, spawnLimit: 6, spawnWindowMs: 60_000 };
function snapshot(times = [0, 1000, 3000]) {
  return {
    policy,
    agents: [{ id: 'root', parentId: null, depth: 0, createdAt: at(0) }, ...times.map((ms, i) => ({ id: `child-${i}`, parentId: 'root', depth: 1, createdAt: at(ms) }))],
    events: times.map((ms, i) => ({ type: 'agent.spawned', time: at(ms), evidence: 'SIMULATED', data: { childId: `child-${i}`, parentId: 'root' } })),
  };
}
function span(overrides = {}) {
  return { traceId: 'a'.repeat(32), spanId: 'b'.repeat(16), parentSpanId: null, agentId: 'declared-agent_1', kind: 'tool', startedAt: at(0), endedAt: at(50), status: 'ok', ...overrides };
}
function fixture(spans = [span()]) { return { sourceClass: 'SIMULATED', coverageComplete: true, spans }; }

test('measures event intervals, rolling count, and registered graph density exactly', () => {
  const input = snapshot();
  const before = structuredClone(input);
  const analysis = analyzeHats(input);
  assert.deepEqual(input, before);
  assert.equal(analysis.features.meanSpawnIntervalMs, 1500);
  assert.equal(analysis.features.requestIntervalVarianceMs2, 250000);
  assert.equal(analysis.features.recentSpawnCount, 3);
  assert.equal(analysis.features.spawnRatePerMinute, 3);
  assert.equal(analysis.features.lineageGraphDensity, 3 / 12);
  assert.equal(analysis.features.maxDepth, 1);
  assert.equal(analysis.forecast.spawnRisk, 'HIGH'); // Recorded root has reached maxChildren.
  assert.equal(analysis.coverage.status, 'COMPLETE');
  assert.equal(analysis.authority, 'none');
  assert.equal(analysis.evidence, 'CONJECTURE');
  assert.equal(analysis.originTrusted, false);
});

test('empty or insufficient observations preserve null metrics and UNKNOWN forecast', () => {
  const missing = analyzeHats();
  assert.equal(missing.coverage.status, 'UNKNOWN');
  assert.equal(missing.forecast.spawnRisk, 'UNKNOWN');
  assert.equal(missing.features.requestIntervalVarianceMs2, null);
  assert.equal(missing.features.lineageGraphDensity, null);
  assert.equal(missing.features.spawnRatePerMinute, null);
  const single = analyzeHats(snapshot([0]));
  assert.equal(single.features.meanSpawnIntervalMs, null);
  assert.equal(single.features.requestIntervalVarianceMs2, null);
  assert.equal(single.forecast.spawnRisk, 'UNKNOWN');
  assert.equal(single.coordination.status, 'UNKNOWN');
});

test('window end follows last recorded activity and expires old spawns', () => {
  const input = snapshot([0, 1000, 61000]);
  input.events.push({ type: 'action.denied', time: at(62000), evidence: 'OBSERVED', data: {} });
  const output = analyzeHats(input);
  assert.equal(output.features.recentSpawnCount, 1);
  assert.equal(output.features.windowEndedAt, at(62000));
});

test('coincidence ratio derives from actual declared-agent timing, not a fixed swarm score', () => {
  const output = analyzeHats(snapshot([0, 10, 1000]));
  assert.equal(output.coordination.status, 'MEASURED');
  assert.equal(output.coordination.activeBuckets, 2);
  assert.equal(output.coordination.coincidentBuckets, 1);
  assert.equal(output.coordination.coincidenceRatio, 0.5);
  assert.match(output.coordination.detail, /does not establish/);
});

test('broken inventory, cycles, bad dates, and declared incomplete coverage remain UNKNOWN', () => {
  for (const alter of [
    value => { value.registryComplete = false; },
    value => { value.agents[1].parentId = 'missing'; },
    value => { value.agents[0].parentId = 'child-0'; },
    value => { value.events[0].time = '2026-02-30T00:00:00.000Z'; },
    value => { value.agents[1].depth = '3'; },
    value => { value.agents[1].depth = 2; },
    value => { value.agents[0].depth = 1; },
    value => { value.events.push(value.events[0]); },
  ]) {
    const input = snapshot();
    alter(input);
    const output = analyzeHats(input);
    assert.equal(output.coverage.status, 'UNKNOWN');
    assert.equal(output.forecast.spawnRisk, 'UNKNOWN');
  }
});

test('metadata-only schema returns a detached explicit allowlist and untrusted source declaration', () => {
  const input = fixture();
  const output = minimizeTelemetry(input);
  assert.equal(output.coverage.status, 'COMPLETE');
  assert.equal(output.originTrusted, false);
  assert.match(output.sourceAssertion, /not independently verified/);
  assert.deepEqual(output.spans, input.spans);
  input.spans[0].agentId = 'modified';
  assert.equal(output.spans[0].agentId, 'declared-agent_1');
});

test('private payloads and all unknown fields are rejected without echoing contents', () => {
  for (const field of ['prompt', 'text', 'headers', 'token', 'ip', 'url', 'rawMouseTrajectory', 'response']) {
    for (const where of ['envelope', 'span']) {
      const input = fixture();
      (where === 'envelope' ? input : input.spans[0])[field] = 'PRIVATE-CONTENT';
      assert.throws(() => minimizeTelemetry(input), error => error.code === 'INVALID_TELEMETRY'
        && error.status === 400 && !error.message.includes('PRIVATE-CONTENT'));
    }
  }
});

test('strict identifiers, bounded duration, timestamps, and source labels prevent unconstrained metadata', () => {
  for (const change of [
    { traceId: 'https://example.test' }, { spanId: 'not-hex' }, { spanId: 1111111111111111 }, { parentSpanId: 1111111111111111 }, { parentSpanId: 'bad' },
    { agentId: '127.0.0.1' }, { agentId: 'name@example.test' }, { agentId: 'a'.repeat(81) },
    { kind: 'prompt' }, { status: 'secret' }, { startedAt: at(100), endedAt: at(0) },
    { endedAt: at(86_400_001) }, { startedAt: '2026-02-30T00:00:00Z' },
    { startedAt: '2026-10-29' },
  ]) assert.throws(() => minimizeTelemetry(fixture([span(change)])), { code: 'INVALID_TELEMETRY' });
  assert.throws(() => minimizeTelemetry({ ...fixture(), sourceClass: 'TRUSTED' }), { code: 'INVALID_TELEMETRY' });
  assert.throws(() => minimizeTelemetry({ ...fixture(), coverageComplete: 'true' }), { code: 'INVALID_TELEMETRY' });
  assert.throws(() => minimizeTelemetry(fixture(Array.from({ length: 129 }, () => span()))), { code: 'INVALID_TELEMETRY' });
});

test('missing span parents stay UNKNOWN while duplicate IDs and cycles are invalid', () => {
  assert.equal(minimizeTelemetry(fixture([span({ parentSpanId: 'c'.repeat(16) })])).coverage.status, 'UNKNOWN');
  assert.equal(minimizeTelemetry({ ...fixture(), coverageComplete: false }).coverage.status, 'UNKNOWN');
  assert.equal(minimizeTelemetry(fixture([])).coverage.status, 'UNKNOWN');
  assert.throws(() => minimizeTelemetry(fixture([span(), span()])), { code: 'INVALID_TELEMETRY' });
  assert.throws(() => minimizeTelemetry(fixture([span({ parentSpanId: 'b'.repeat(16) })])), { code: 'INVALID_TELEMETRY' });
  assert.throws(() => minimizeTelemetry(fixture([
    span({ parentSpanId: 'c'.repeat(16) }), span({ spanId: 'c'.repeat(16), parentSpanId: 'b'.repeat(16) }),
  ])), { code: 'INVALID_TELEMETRY' });
});

test('optional telemetry is revalidated and never silently upgrades unknown coverage', () => {
  const input = snapshot();
  input.telemetry = { ...minimizeTelemetry(fixture()), coverage: { status: 'COMPLETE' } };
  input.telemetry.spans[0].parentSpanId = 'c'.repeat(16);
  const output = analyzeHats(input);
  assert.equal(output.coverage.status, 'UNKNOWN');
  assert.equal(output.forecast.spawnRisk, 'UNKNOWN');
  input.telemetry.spans[0].text = 'PRIVATE-CONTENT';
  assert.equal(analyzeHats(input).coverage.status, 'UNKNOWN');
});

test('local CLI measures the fixture, preserves unknown authority, and rejects private or oversized files without echoes', () => {
  const cli = fileURLToPath(new URL('../scripts/analyze-telemetry.mjs', import.meta.url));
  const supplied = fileURLToPath(new URL('../examples/telemetry/synthetic-spans.json', import.meta.url));
  const run = filename => spawnSync(process.execPath, [cli, filename], { encoding: 'utf8', timeout: 5000, maxBuffer: 65_536 });
  const valid = run(supplied);
  assert.equal(valid.status, 0, valid.stderr);
  const result = JSON.parse(valid.stdout);
  assert.equal(result.features.spanCount, 4);
  assert.equal(result.features.durationMs.mean, 55);
  assert.equal(result.metadataCoverage.status, 'COMPLETE');
  assert.equal(result.registeredAuthorityCoverage.status, 'UNKNOWN');
  assert.equal(result.authority, 'none');
  assert.equal(result.originTrusted, false);
  const directory = mkdtempSync(join(tmpdir(), 'guardian-metadata-'));
  try {
    const privateFile = join(directory, 'private.json');
    writeFileSync(privateFile, JSON.stringify({ ...fixture(), prompt: 'PRIVATE-CONTENT' }));
    const rejected = run(privateFile);
    assert.equal(rejected.status, 1);
    assert.equal(rejected.stdout, '');
    assert.doesNotMatch(rejected.stderr, /PRIVATE-CONTENT/);
    const oversized = join(directory, 'oversized.json');
    writeFileSync(oversized, ' '.repeat(65_537));
    assert.equal(run(oversized).status, 1);
  } finally { rmSync(directory, { recursive: true, force: true }); }
});
