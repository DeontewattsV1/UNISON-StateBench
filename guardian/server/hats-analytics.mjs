// SPDX-License-Identifier: Apache-2.0
// Metadata measurements are advisory. This module has no execution or policy API.
const SOURCE_CLASSES = new Set(['SIMULATED', 'OBSERVED']);
const KINDS = new Set(['spawn', 'tool', 'message']);
const STATUSES = new Set(['ok', 'error', 'unknown']);
const ID = /^[a-zA-Z0-9_-]{1,80}$/;
const HEX32 = /^[a-f0-9]{32}$/;
const HEX16 = /^[a-f0-9]{16}$/;
const ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/;
const DAY = 86_400_000;

function record(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function badTelemetry() {
  const error = new Error('Telemetry must match the bounded metadata-only schema. Payload text, headers, addresses, and unknown fields are rejected.');
  error.code = 'INVALID_TELEMETRY';
  error.status = 400;
  return error;
}

function exact(value, keys) {
  if (!record(value) || Object.keys(value).length !== keys.length || keys.some(key => !Object.hasOwn(value, key))) throw badTelemetry();
}

function time(value) {
  if (typeof value !== 'string' || !ISO.test(value)) return null;
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed) || parsed < Date.UTC(2000, 0, 1) || parsed >= Date.UTC(2100, 0, 1)) return null;
  // Date.parse normalizes impossible dates such as February 30. Reject those.
  if (new Date(parsed).toISOString() !== (value.includes('.') ? value : value.replace('Z', '.000Z'))) return null;
  return parsed;
}

/**
 * Validate an operator-supplied metadata fixture without retaining its envelope.
 * Source labels are declarations, never authenticated ingestion attestations.
 * Missing parents preserve UNKNOWN; duplicate identifiers and cycles are invalid.
 */
export function minimizeTelemetry(input) {
  exact(input, ['sourceClass', 'coverageComplete', 'spans']);
  if (!SOURCE_CLASSES.has(input.sourceClass) || typeof input.coverageComplete !== 'boolean'
    || !Array.isArray(input.spans) || input.spans.length > 128) throw badTelemetry();

  const spans = [];
  const byId = new Map();
  let first = Infinity;
  let last = -Infinity;
  for (const item of input.spans) {
    exact(item, ['traceId', 'spanId', 'parentSpanId', 'agentId', 'kind', 'startedAt', 'endedAt', 'status']);
    const started = time(item.startedAt);
    const ended = time(item.endedAt);
    if (typeof item.traceId !== 'string' || !HEX32.test(item.traceId)
      || typeof item.spanId !== 'string' || !HEX16.test(item.spanId)
      || (item.parentSpanId !== null && (typeof item.parentSpanId !== 'string' || !HEX16.test(item.parentSpanId)))
      || typeof item.agentId !== 'string' || !ID.test(item.agentId)
      || !KINDS.has(item.kind) || !STATUSES.has(item.status)
      || started === null || ended === null || ended < started || ended - started > DAY
      || byId.has(item.spanId)) throw badTelemetry();
    // Reconstruct each field explicitly: never copy arbitrary input attributes.
    const span = {
      traceId: item.traceId, spanId: item.spanId, parentSpanId: item.parentSpanId,
      agentId: item.agentId, kind: item.kind, startedAt: item.startedAt,
      endedAt: item.endedAt, status: item.status,
    };
    spans.push(span);
    byId.set(span.spanId, span);
    first = Math.min(first, started);
    last = Math.max(last, ended);
  }
  if (spans.length && last - first > DAY) throw badTelemetry();

  const reasons = [];
  if (!input.coverageComplete) reasons.push('The supplied inventory is explicitly incomplete.');
  if (!spans.length) reasons.push('No span metadata was supplied.');
  for (const span of spans) {
    let current = span;
    const visited = new Set();
    while (current) {
      if (visited.has(current.spanId)) throw badTelemetry();
      visited.add(current.spanId);
      if (current.parentSpanId === null) break;
      const parent = byId.get(current.parentSpanId);
      if (!parent || parent.traceId !== current.traceId) {
        reasons.push('At least one span parent is missing from its trace.');
        break;
      }
      current = parent;
    }
  }
  return {
    sourceClass: input.sourceClass,
    coverageComplete: input.coverageComplete,
    spans,
    coverage: { status: reasons.length ? 'UNKNOWN' : 'COMPLETE', reasons: [...new Set(reasons)] },
    originTrusted: false,
    sourceAssertion: 'Caller-declared; not independently verified.',
  };
}

function average(values) { return values.reduce((sum, value) => sum + value, 0) / values.length; }
function unique(values) { return [...new Set(values)]; }
function positive(value, fallback) { return Number.isSafeInteger(value) && value > 0 ? value : fallback; }

/**
 * Compute falsifiable features from recorded synthetic activity and optional
 * validated spans. Rates refer to the latest recorded time, not a live clock.
 * No score is a probability, identity finding, or an authorization decision.
 */
export function analyzeHats(snapshot = {}) {
  const agents = Array.isArray(snapshot.agents) ? snapshot.agents : [];
  const events = Array.isArray(snapshot.events) ? snapshot.events : [];
  const policy = record(snapshot.policy) ? snapshot.policy : {};
  const spawnWindowMs = positive(policy.spawnWindowMs, 60_000);
  const reasons = [];
  if (!Array.isArray(snapshot.agents) || !agents.length) reasons.push('No registered agent inventory is available.');
  if (!Array.isArray(snapshot.events)) reasons.push('No event inventory is available.');
  if (snapshot.registryComplete === false) reasons.push('The registered inventory is explicitly incomplete.');

  const byId = new Map();
  for (const agent of agents) {
    if (!record(agent) || typeof agent.id !== 'string' || byId.has(agent.id)) {
      reasons.push('The agent inventory contains malformed or repeated identifiers.');
      continue;
    }
    byId.set(agent.id, agent);
  }
  const edges = [];
  for (const agent of byId.values()) {
    if (agent.parentId !== null) {
      if (!byId.has(agent.parentId)) reasons.push('At least one registered parent is missing.');
      else {
        edges.push([agent.parentId, agent.id]);
        if (agent.depth !== byId.get(agent.parentId).depth + 1) reasons.push('A registered depth does not match its parent.');
      }
    } else if (agent.depth !== 0) reasons.push('A registered root has an inconsistent depth.');
    const visited = new Set();
    let current = agent;
    while (current) {
      if (visited.has(current.id)) { reasons.push('The registered parent graph contains a cycle.'); break; }
      visited.add(current.id);
      if (current.parentId === null) break;
      current = byId.get(current.parentId);
    }
    if (!Number.isSafeInteger(agent.depth) || agent.depth < 0) reasons.push('At least one registered depth is missing or malformed.');
  }

  const activations = [];
  const allTimes = [];
  const spawnedIds = new Set();
  for (const event of events) {
    const at = time(event?.time);
    if (at === null) { reasons.push('At least one event timestamp is missing or malformed.'); continue; }
    allTimes.push(at);
    if (event.type === 'agent.spawned') {
      const agentId = event.data?.childId ?? event.data?.agentId;
      if (typeof agentId !== 'string' || !byId.has(agentId)) reasons.push('A spawn event does not reference a registered child.');
      else {
        if (spawnedIds.has(agentId)) reasons.push('Multiple spawn events refer to the same registered child.');
        spawnedIds.add(agentId);
        activations.push({ at, agentId });
      }
    }
  }
  // Creation timestamps provide the reference clock, but do not invent events.
  for (const agent of byId.values()) {
    const at = time(agent.createdAt);
    if (at !== null) allTimes.push(at);
    else reasons.push('At least one agent creation timestamp is missing or malformed.');
  }

  let telemetry = null;
  if (snapshot.telemetry !== null && snapshot.telemetry !== undefined) {
    try {
      // Revalidate retained data; do not trust a supplied `coverage` result.
      telemetry = minimizeTelemetry({
        sourceClass: snapshot.telemetry.sourceClass,
        coverageComplete: snapshot.telemetry.coverageComplete,
        spans: snapshot.telemetry.spans,
      });
      reasons.push(...telemetry.coverage.reasons);
    } catch {
      reasons.push('The optional telemetry failed the metadata-only schema.');
    }
  }

  const spawnTimes = activations.map(item => item.at).sort((a, b) => a - b);
  const intervals = spawnTimes.slice(1).map((at, index) => at - spawnTimes[index]);
  const meanInterval = intervals.length ? average(intervals) : null;
  const intervalVariance = intervals.length >= 2 ? average(intervals.map(value => (value - meanInterval) ** 2)) : null;
  const latest = allTimes.length ? Math.max(...allTimes) : null;
  const recent = latest === null ? null : spawnTimes.filter(at => at > latest - spawnWindowMs && at <= latest).length;
  const validDepths = agents.map(agent => agent?.depth).filter(value => Number.isSafeInteger(value) && value >= 0);

  const timingItems = telemetry
    ? telemetry.spans.map(span => ({ at: time(span.startedAt), agentId: span.agentId }))
    : activations;
  const buckets = new Map();
  for (const item of timingItems) {
    const bucket = Math.floor(item.at / 100);
    if (!buckets.has(bucket)) buckets.set(bucket, new Set());
    buckets.get(bucket).add(item.agentId);
  }
  const activeAgents = unique(timingItems.map(item => item.agentId)).length;
  const enoughTiming = timingItems.length >= 2 && activeAgents >= 2;
  const coincidentBuckets = [...buckets.values()].filter(set => set.size > 1).length;
  const featureCoverage = unique(reasons);
  const maxDepth = validDepths.length === agents.length && agents.length ? Math.max(...validDepths) : null;
  const features = {
    registeredAgents: agents.length,
    parentChildEdges: edges.length,
    maxDepth,
    spawnEvents: spawnTimes.length,
    recentSpawnCount: recent,
    spawnRatePerMinute: recent === null ? null : recent * 60_000 / spawnWindowMs,
    meanSpawnIntervalMs: meanInterval,
    requestIntervalVarianceMs2: intervalVariance,
    lineageGraphDensity: agents.length >= 2 ? edges.length / (agents.length * (agents.length - 1)) : null,
    spawnWindowMs,
    windowEndedAt: latest === null ? null : new Date(latest).toISOString(),
  };
  const policyKnown = ['maxDepth', 'maxChildren', 'maxAgents', 'spawnLimit', 'spawnWindowMs'].every(key => Number.isSafeInteger(policy[key]) && policy[key] > 0);
  let spawnRisk = 'UNKNOWN';
  let reason = 'More recorded activity and complete policy metadata are needed for a spawn forecast.';
  if (featureCoverage.length === 0 && policyKnown && spawnTimes.length >= 2) {
    const children = new Map();
    for (const [parent] of edges) children.set(parent, (children.get(parent) || 0) + 1);
    const largestFamily = children.size ? Math.max(...children.values()) : 0;
    if (recent >= policy.spawnLimit || agents.length >= policy.maxAgents || largestFamily >= policy.maxChildren) {
      spawnRisk = 'HIGH';
      reason = 'Recorded activity has reached a deterministic spawn quota; this advisory heuristic does not decide execution.';
    } else if (maxDepth >= policy.maxDepth || recent >= Math.ceil(policy.spawnLimit * 0.75)) {
      spawnRisk = 'ELEVATED';
      reason = 'Recorded depth or spawn activity is near a configured boundary. Each proposed spawn still needs its own deterministic check.';
    } else {
      spawnRisk = 'LOW';
      reason = 'Recorded activity is below the configured spawn boundaries. Future requests can still be denied by the authority lane.';
    }
  }

  return {
    evidence: 'CONJECTURE', measurementEvidence: 'OBSERVED', authority: 'none',
    method: 'Deterministic heuristic, uncalibrated.', originTrusted: false,
    sourceClasses: unique([...events.map(event => event?.evidence).filter(value => SOURCE_CLASSES.has(value)), ...(telemetry ? [telemetry.sourceClass] : [])]),
    features,
    forecast: { spawnRisk, reason },
    coordination: {
      status: enoughTiming ? 'MEASURED' : 'UNKNOWN', bucketMs: 100,
      activeAgents, activeBuckets: buckets.size,
      coincidentBuckets: enoughTiming ? coincidentBuckets : null,
      coincidenceRatio: enoughTiming ? coincidentBuckets / buckets.size : null,
      detail: enoughTiming
        ? 'Fraction of nonempty 100 ms buckets containing multiple declared agents. Timing coincidence does not establish coordination, consensus, or an agent swarm.'
        : 'At least two timed activities from different declared agents are needed. No coordination conclusion is available.',
    },
    coverage: { status: featureCoverage.length ? 'UNKNOWN' : 'COMPLETE', reasons: featureCoverage },
    limitations: [
      'Features describe only the supplied registered graph and timestamp metadata.',
      'Source labels and agent identifiers are declarations; no signature, real-world identity, or independent origin is verified.',
      'The spawn forecast is an uncalibrated heuristic, not a probability or proof that recursion will occur.',
      'Interval variance is not a human-versus-agent classifier. Lineage density is not a communication or consensus measurement.',
      'Rates use the latest recorded activity as the window end; they do not claim continuous live monitoring.',
      'The analytic lane cannot grant authority, modify policy, or override a deterministic denial.',
    ],
  };
}
