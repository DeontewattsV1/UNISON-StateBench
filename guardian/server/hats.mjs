import { createHash, randomUUID } from 'node:crypto';
import { verifyLedger } from './engine.mjs';

// Synthetic policy engine. No receipt emitted here is a bearer credential or a
// signature; no identity, deployment attestation, or external tool is verified.
const TYPES = ['Macro', 'Meso', 'Micro', 'Nano'];
const CAPABILITIES = ['invoke:synthetic', 'spawn:agent'];
const SPECIALIZATIONS = ['orchestrator', 'workflow', 'retrieval', 'bounded-task', 'analysis', 'general'];
const DEFAULT_SPECIALIZATION = ['orchestrator', 'workflow', 'retrieval', 'bounded-task'];
const POLICY = Object.freeze({ maxDepth: 3, maxChildren: 3, maxAgents: 12, spawnLimit: 6, spawnWindowMs: 60_000 });
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const HASH = /^[0-9a-f]{64}$/;
const ZERO = '0'.repeat(64);
const MAX_EVENTS = 200;
const MAX_CHECKPOINT_BYTES = 1_048_576;
const owned = new WeakMap();

function canonical(value) {
  if (value === null || typeof value === 'boolean' || typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  throw new TypeError('Evidence must contain JSON values only.');
}
function hash(value) { return createHash('sha256').update(canonical(value)).digest('hex'); }
function copy(value) { return structuredClone(value); }
function record(value) { return value !== null && typeof value === 'object' && !Array.isArray(value); }
function fail(code, message, status = 400) { const error = new Error(message); error.code = code; error.status = status; throw error; }
function exact(value, keys, label) {
  if (!record(value) || Object.keys(value).some(key => !keys.includes(key))) fail('INVALID_HATS_INPUT', `${label} has unsupported members.`);
}
function nowFor(state) {
  const clock = owned.get(state)?.now;
  if (!clock) fail('HATS_STATE_INTEGRITY', 'Use createHats() to create an engine-owned registry.', 409);
  const now = clock();
  if (!Number.isFinite(now) || now < 0) fail('HATS_CLOCK_INVALID', 'The sandbox clock is unavailable.', 503);
  const lastEvent = Array.isArray(state.events) ? state.events.at(-1) : null;
  const previous = Date.parse(lastEvent?.time ?? state.createdAt);
  return Number.isFinite(previous) ? Math.max(now, previous) : now;
}
function seal(state) { owned.get(state).seal = hash(state); }
function intact(state) {
  try { return owned.has(state) && hash(state) === owned.get(state).seal; } catch { return false; }
}
function assertState(state, reserve = 1) {
  if (!intact(state)) fail('HATS_STATE_INTEGRITY', 'HATS state differs from the retained engine state; execution is denied.', 409);
  if (state.events.length + reserve > MAX_EVENTS) fail('EVENT_LIMIT', 'Export HATS evidence and reset the lab to start a new run.', 429);
}
function append(state, type, evidence, message, data) {
  const event = {
    seq: state.events.length + 1, id: randomUUID(), runId: state.runId,
    time: ['hats.created', 'agent.spawned'].includes(type) ? data.agent.createdAt : new Date(nowFor(state)).toISOString(), type, evidence, message,
    data: copy(data), previousHash: state.events.at(-1)?.hash ?? ZERO,
  };
  event.hash = hash(event);
  state.events.push(event);
  state.revision = state.events.length;
}

function immutable(agent) { const { revoked, ...identity } = agent; return identity; }
function lineagePayload(runId, agent, parentHash) {
  return { domain: 'unison-hats-lineage-v1', runId, ...immutable(agent), lineageHash: undefined, parentHash };
}
function lineageHash(runId, agent, parentHash) {
  const body = lineagePayload(runId, agent, parentHash);
  delete body.lineageHash;
  return hash(body);
}

/** Recompute supplied lineage records. This checks consistency, never origin. */
export function inspectHatsLineage(agents, runId) {
  const checks = [];
  if (!Array.isArray(agents) || !agents.length || typeof runId !== 'string') return { status: 'UNKNOWN', checks: [], detail: 'Lineage records are missing.', originTrusted: false };
  if (agents.length > POLICY.maxAgents) return { status: 'FAIL', checks: [], detail: 'The supplied registry exceeds the supported agent bound.', originTrusted: false };
  const byId = new Map();
  for (const agent of agents) {
    if (!record(agent) || typeof agent.id !== 'string' || byId.has(agent.id)) return { status: 'FAIL', checks: [], detail: 'Agent identifiers are missing or repeated.', originTrusted: false };
    if (!UUID.test(agent.id) || !UUID.test(agent.nonce) || typeof agent.lineageHash !== 'string' || !HASH.test(agent.lineageHash)
      || !Array.isArray(agent.capabilities) || agent.capabilities.some(item => !CAPABILITIES.includes(item))
      || new Set(agent.capabilities).size !== agent.capabilities.length || !record(agent.genome)
      || !Array.isArray(agent.genome.inheritanceMask) || canonical(agent.genome.inheritanceMask) !== canonical(agent.capabilities)) {
      return { status: 'FAIL', checks: [], detail: 'An agent identity, capability scope, or inherited mask is malformed.', originTrusted: false };
    }
    byId.set(agent.id, agent);
  }
  const cache = new Map();
  function visit(agent, path) {
    if (path.has(agent.id)) return { status: 'FAIL', detail: 'A lineage cycle has no registered genesis.' };
    if (cache.has(agent.id)) return cache.get(agent.id);
    let result;
    const depth = TYPES.indexOf(agent.type);
    const parent = agent.parentId === null ? null : byId.get(agent.parentId);
    if (agent.parentId !== null && !parent) result = { status: 'UNKNOWN', detail: 'A declared parent record is missing.' };
    else if (depth < 0 || agent.depth !== depth || (parent ? agent.depth !== parent.depth + 1 : agent.depth !== 0)) result = { status: 'FAIL', detail: 'The declared type or generational depth does not match its parent.' };
    else if (parent) {
      const ancestry = visit(parent, new Set([...path, agent.id]));
      if (ancestry.status !== 'PASS') result = ancestry;
      else if (!Array.isArray(agent.capabilities) || agent.capabilities.some(capability => !parent.capabilities.includes(capability))) result = { status: 'FAIL', detail: 'Child capabilities exceed the parent scope.' };
    }
    if (!result) {
      try {
        result = lineageHash(runId, agent, parent?.lineageHash ?? 'GENESIS') === agent.lineageHash
          ? { status: 'PASS', detail: 'Identity, scope, genome, and parent digest recomputed.' }
          : { status: 'FAIL', detail: 'A recomputed lineage digest does not match.' };
      } catch { result = { status: 'FAIL', detail: 'The lineage record is malformed.' }; }
    }
    cache.set(agent.id, result);
    return result;
  }
  for (const agent of agents) checks.push({ agentId: agent.id, ...visit(agent, new Set()) });
  const status = checks.some(check => check.status === 'FAIL') ? 'FAIL' : checks.some(check => check.status === 'UNKNOWN') ? 'UNKNOWN' : 'PASS';
  return { status, checks, detail: `${checks.filter(check => check.status === 'PASS').length}/${agents.length} registered lineage records recomputed. No signature or external origin is verified.`, originTrusted: false };
}

export function verifyHatsLineage(value) {
  return inspectHatsLineage(value?.agents, value?.runId);
}

function authority(state, agentId, capability) {
  const byId = new Map(state.agents.map(agent => [agent.id, agent]));
  const agent = byId.get(agentId);
  if (!agent) return { status: 'UNKNOWN', allowed: false, code: 'AGENT_UNKNOWN', reason: 'The requested agent is not registered.', lineage: [] };
  const inspection = inspectHatsLineage(state.agents, state.runId);
  const matching = inspection.checks.find(check => check.agentId === agentId);
  if (!matching || matching.status !== 'PASS') return { status: matching?.status === 'UNKNOWN' ? 'UNKNOWN' : 'DENIED', allowed: false, code: 'LINEAGE_INVALID', reason: matching?.detail ?? 'Lineage evidence is missing.', lineage: [] };
  const lineage = [];
  let current = agent;
  while (current) {
    if (lineage.includes(current.id)) return { status: 'DENIED', allowed: false, code: 'LINEAGE_CYCLE', reason: 'Delegation ancestry contains a cycle.', lineage };
    lineage.push(current.id);
    if (current.revoked) return { status: 'DENIED', allowed: false, code: 'ANCESTOR_REVOKED', reason: `Current ${current.type} ancestor authority is revoked.`, lineage };
    if (!current.capabilities.includes(capability)) return { status: 'DENIED', allowed: false, code: 'CAPABILITY_DENIED', reason: 'The requested capability is outside current inherited scope.', lineage };
    if (current.parentId === null) return { status: 'AUTHORIZED', allowed: true, code: 'CURRENT_AUTHORITY_VALID', reason: 'Current lineage, active ancestors, and capability scope passed deterministic checks.', lineage };
    current = byId.get(current.parentId);
    if (!current) return { status: 'UNKNOWN', allowed: false, code: 'ANCESTRY_MISSING', reason: 'A delegation ancestor is missing.', lineage };
  }
  return { status: 'UNKNOWN', allowed: false, code: 'GENESIS_MISSING', reason: 'No registered genesis was found.', lineage };
}

function decision(state, result, agentId, action) {
  const body = {
    ...result, agentId, action, evaluatedRevision: state.revision,
    receipt: null,
  };
  if (body.allowed) body.receipt = hash({ domain: 'unison-hats-transition-v1', runId: state.runId, revision: state.revision, agentId, action, lineage: body.lineage ?? [], ledgerTip: state.events.at(-1)?.hash ?? ZERO });
  state.lastDecision = body;
  state.verification = null;
  return body;
}
function refusal(state, result, agentId, action) {
  const evaluated = decision(state, { allowed: false, status: 'DENIED', ...result }, agentId, action);
  append(state, action === 'spawn:agent' ? `spawn.${evaluated.status === 'UNKNOWN' ? 'unknown' : 'denied'}` : 'action.denied', 'OBSERVED', evaluated.reason, { decision: evaluated });
  seal(state);
  return hatsSnapshot(state);
}
function validId(value, label) {
  if (typeof value !== 'string' || !UUID.test(value)) fail('INVALID_HATS_INPUT', `${label} must be a UUID.`);
}
function capabilitiesInput(value) {
  if (!Array.isArray(value) || value.length > 8 || value.some(item => typeof item !== 'string' || !/^[a-z][a-z0-9-]{0,25}:[a-z][a-z0-9-]{0,25}$/.test(item)) || new Set(value).size !== value.length) fail('INVALID_HATS_INPUT', 'Capabilities must be a unique, bounded list of capability identifiers.');
  return [...value].sort();
}
function newAgent(state, parent, type, capabilities, specialization) {
  const agent = {
    id: randomUUID(), type, parentId: parent?.id ?? null, depth: TYPES.indexOf(type),
    capabilities: [...capabilities].sort(), specialization, nonce: randomUUID(),
    createdAt: parent ? new Date(nowFor(state)).toISOString() : state.createdAt,
    genome: {
      parentStateHash: parent ? hash({ parent: immutable(parent), revoked: parent.revoked, revision: state.revision, ledgerTip: state.events.at(-1)?.hash ?? ZERO }) : null,
      inheritanceMask: [...capabilities].sort(),
    },
    revoked: false,
  };
  agent.lineageHash = lineageHash(state.runId, agent, parent?.lineageHash ?? 'GENESIS');
  return agent;
}

export function createHats({ now = Date.now, deployment = 'Local synthetic HATS sandbox' } = {}) {
  if (typeof now !== 'function' || typeof deployment !== 'string' || !deployment.trim() || deployment.length > 120) fail('INVALID_HATS_CONFIG', 'A clock function and bounded deployment label are required.');
  const timestamp = now();
  if (!Number.isFinite(timestamp) || timestamp < 0) fail('INVALID_HATS_CONFIG', 'A finite clock value is required.');
  const state = { schemaVersion: 1, runId: randomUUID(), revision: 0, deployment, sourceClass: 'SIMULATED', createdAt: new Date(timestamp).toISOString(), agents: [], events: [], policy: { ...POLICY }, syntheticActions: 0, lastDecision: null, verification: null, demo: null };
  owned.set(state, { now, seal: null });
  const root = newAgent(state, null, 'Macro', CAPABILITIES, 'orchestrator');
  state.agents.push(root);
  append(state, 'hats.created', 'SIMULATED', 'Registered one synthetic Macro genesis with bounded capabilities.', { agentId: root.id, agent: root, policy: state.policy });
  seal(state);
  return state;
}

export function hatsSnapshot(state) {
  if (!owned.has(state)) fail('HATS_STATE_INTEGRITY', 'Use an engine-owned HATS registry.', 409);
  return { ...copy(state), ledgerVerification: verifyLedger(state.events) };
}

export function spawnAgent(state, input = {}) {
  assertState(state);
  exact(input, ['parentId', 'type', 'capabilities', 'specialization'], 'Spawn request');
  const parentId = input.parentId ?? state.agents[0].id;
  validId(parentId, 'Parent ID');
  const parent = state.agents.find(agent => agent.id === parentId);
  const type = input.type ?? TYPES[(parent?.depth ?? 0) + 1];
  if (input.type !== undefined && !TYPES.includes(input.type)) fail('INVALID_HATS_INPUT', 'Type must be Macro, Meso, Micro, or Nano.');
  if (input.specialization !== undefined && !SPECIALIZATIONS.includes(input.specialization)) fail('INVALID_HATS_INPUT', 'Choose a registered specialization.');
  const capabilities = input.capabilities === undefined ? [...(parent?.capabilities ?? CAPABILITIES)] : capabilitiesInput(input.capabilities);
  const authorization = authority(state, parentId, 'spawn:agent');
  if (!authorization.allowed) return refusal(state, authorization, parentId, 'spawn:agent');
  if (parent.depth >= POLICY.maxDepth) return refusal(state, { code: 'DEPTH_LIMIT', reason: 'The maximum registered generation depth is 3; Nano agents cannot spawn descendants.' }, parentId, 'spawn:agent');
  if (type !== TYPES[parent.depth + 1]) return refusal(state, { code: 'GENERATION_MISMATCH', reason: 'A child must have the next registered generational type.' }, parentId, 'spawn:agent');
  if (capabilities.some(capability => !parent.capabilities.includes(capability))) return refusal(state, { code: 'SCOPE_WIDENING', reason: 'A child cannot inherit a capability absent from its parent.' }, parentId, 'spawn:agent');
  if (state.agents.filter(agent => agent.parentId === parentId).length >= POLICY.maxChildren) return refusal(state, { code: 'CHILD_LIMIT', reason: 'This parent has reached its deterministic child limit.' }, parentId, 'spawn:agent');
  if (state.agents.length >= POLICY.maxAgents) return refusal(state, { code: 'AGENT_LIMIT', reason: 'This registry has reached its deterministic agent limit.' }, parentId, 'spawn:agent');
  const time = nowFor(state);
  if (state.events.filter(event => event.type === 'agent.spawned' && time - Date.parse(event.time) < POLICY.spawnWindowMs).length >= POLICY.spawnLimit) return refusal(state, { code: 'SPAWN_RATE_LIMIT', reason: 'The registered spawn budget for this 60-second window is exhausted.' }, parentId, 'spawn:agent');
  const child = newAgent(state, parent, type, capabilities, input.specialization ?? DEFAULT_SPECIALIZATION[parent.depth + 1]);
  const evaluated = decision(state, { ...authorization, code: 'SPAWN_AUTHORIZED', reason: 'Current inherited scope, lineage, generation, and hard spawn budgets passed.' }, parentId, 'spawn:agent');
  state.agents.push(child);
  append(state, 'agent.spawned', 'SIMULATED', `Spawned a bounded synthetic ${child.type} child.`, { agentId: child.id, childId: child.id, parentId, agent: child, decision: evaluated });
  seal(state);
  return hatsSnapshot(state);
}

export function revokeAgent(state, input = {}) {
  assertState(state);
  exact(input, ['agentId'], 'Revocation request');
  const agentId = input.agentId ?? state.agents[0].id;
  validId(agentId, 'Agent ID');
  const agent = state.agents.find(item => item.id === agentId);
  if (!agent) return refusal(state, { status: 'UNKNOWN', code: 'AGENT_UNKNOWN', reason: 'No registered agent exists for this revocation.' }, agentId, 'revoke:authority');
  if (agent.revoked) return hatsSnapshot(state);
  agent.revoked = true;
  const evaluated = decision(state, { status: 'AUTHORIZED', allowed: true, code: 'AUTHORITY_REVOKED', reason: 'The operator revoked this registered authority. Descendant execution must recheck its current ancestry.', lineage: [agentId] }, agentId, 'revoke:authority');
  append(state, 'authority.revoked', 'SIMULATED', 'Recorded an operator revocation in the synthetic registry.', { agentId, decision: evaluated });
  seal(state);
  return hatsSnapshot(state);
}

export function adjudicateAgent(state, input = {}) {
  assertState(state);
  exact(input, ['agentId', 'action'], 'Adjudication request');
  const agentId = input.agentId ?? state.agents[0].id;
  validId(agentId, 'Agent ID');
  const action = input.action ?? 'invoke:synthetic';
  if (typeof action !== 'string' || !/^[a-z][a-z0-9-]{0,25}:[a-z][a-z0-9-]{0,25}$/.test(action)) fail('INVALID_HATS_INPUT', 'Action must be a bounded capability identifier.');
  const authorization = authority(state, agentId, action);
  if (!authorization.allowed) return refusal(state, authorization, agentId, action);
  if (action !== 'invoke:synthetic') return refusal(state, { code: 'ACTION_NOT_EXECUTABLE', reason: 'Only the registered synthetic counter action is executable at this boundary.' }, agentId, action);
  const evaluated = decision(state, authorization, agentId, action);
  state.syntheticActions += 1;
  append(state, 'action.executed', 'SIMULATED', 'Current deterministic authority permitted one synthetic counter increment.', { agentId, action, counter: state.syntheticActions, decision: evaluated });
  seal(state);
  return hatsSnapshot(state);
}

function verification(state) {
  const lineage = inspectHatsLineage(state.agents, state.runId);
  const ledger = verifyLedger(state.events);
  const sound = intact(state);
  const agents = Array.isArray(state.agents) ? state.agents : [];
  const bounds = Array.isArray(state.agents) && agents.length > 0 && agents.length <= POLICY.maxAgents && agents.every(agent => record(agent) && agent.depth <= POLICY.maxDepth && agents.filter(child => child?.parentId === agent.id).length <= POLICY.maxChildren);
  const checks = [
    { id: 'lineage', label: 'Registered lineage recomputed', status: lineage.status, detail: lineage.detail },
    { id: 'ledger', label: 'Event hash links recomputed', status: ledger.status, detail: ledger.detail },
    { id: 'retained-state', label: 'Engine-retained state matches', status: sound ? 'PASS' : 'FAIL', detail: sound ? 'Registry, decisions, counters, and event tip match the retained engine seal.' : 'State was changed outside an engine transition; authority is denied.' },
    { id: 'hard-bounds', label: 'Registered resource bounds hold', status: bounds ? 'PASS' : 'FAIL', detail: 'Depth, per-parent children, and total registered agent counts are bounded independently of analytics.' },
  ];
  if (state.demo) {
    const steps = Array.isArray(state.demo.steps) ? state.demo.steps : [];
    checks.push({ id: 'demo', label: 'Demonstration assertions', status: steps.length && ['PASS', 'FAIL'].includes(state.demo.verdict) ? state.demo.verdict : 'FAIL', detail: `${steps.filter(step => step?.passed).length}/${steps.length} recorded demonstration expectations passed.` });
  }
  return { verdict: checks.some(check => check.status === 'FAIL') ? 'FAIL' : checks.some(check => check.status === 'UNKNOWN') ? 'UNKNOWN' : 'PASS', checks, scope: 'Registered synthetic HATS identities, capabilities, and tested execution boundary only. No external identity or origin is established.', generatedAt: new Date(nowFor(state)).toISOString(), originTrusted: false, signaturesVerified: false };
}

export function verifyHats(state) {
  if (!intact(state)) return { ...hatsSnapshot(state), verification: verification(state) };
  assertState(state);
  state.verification = verification(state);
  append(state, 'verification.completed', 'OBSERVED', `Deterministic HATS verification: ${state.verification.verdict}.`, { verdict: state.verification.verdict, checks: state.verification.checks.map(({ id, status }) => ({ id, status })) });
  seal(state);
  return hatsSnapshot(state);
}

export function runHatsDemo(state) {
  if (intact(state) && state.demo?.completed) return hatsSnapshot(state);
  assertState(state, 20);
  if (state.events.length !== 1 || state.agents.length !== 1) return refusal(state, { code: 'DEMO_REQUIRES_RESET', reason: 'Reset the HATS lab before running the guided demonstration.' }, state.agents[0].id, 'demo:run');
  const steps = [];
  const capture = (label, expected) => {
    const result = state.lastDecision;
    steps.push({ label, status: result.status, code: result.code, expected, passed: result.status === expected, eventSeq: state.events.length });
  };
  const root = state.agents[0];
  spawnAgent(state, { parentId: root.id }); capture('Macro delegates to Meso', 'AUTHORIZED');
  const meso = state.agents.at(-1);
  spawnAgent(state, { parentId: meso.id }); capture('Meso delegates to Micro', 'AUTHORIZED');
  const micro = state.agents.at(-1);
  spawnAgent(state, { parentId: micro.id }); capture('Micro delegates to Nano', 'AUTHORIZED');
  const nano = state.agents.at(-1);
  adjudicateAgent(state, { agentId: nano.id }); capture('Nano executes while authorized', 'AUTHORIZED');
  spawnAgent(state, { parentId: nano.id }); capture('Hard depth budget blocks recursive descendants', 'DENIED');
  spawnAgent(state, { parentId: meso.id, capabilities: ['invoke:external'] }); capture('Scope widening is denied', 'DENIED');
  spawnAgent(state, { parentId: root.id }); capture('Second bounded Meso child', 'AUTHORIZED');
  spawnAgent(state, { parentId: root.id }); capture('Third bounded Meso child', 'AUTHORIZED');
  spawnAgent(state, { parentId: root.id }); capture('Hard child budget blocks further fanout', 'DENIED');
  revokeAgent(state, { agentId: root.id }); capture('Operator revokes Macro authority', 'AUTHORIZED');
  adjudicateAgent(state, { agentId: nano.id }); capture('Current ancestor check denies stale Nano execution', 'DENIED');
  state.demo = { completed: true, steps, verdict: steps.every(step => step.passed) && state.syntheticActions === 1 ? 'PASS' : 'FAIL', counterBeforeRevocation: 1, counterAfterRevocation: state.syntheticActions };
  append(state, 'demo.completed', 'OBSERVED', 'Finished the bounded HATS demonstration with inspectable decisions.', { verdict: state.demo.verdict, assertions: steps.length, syntheticActions: state.syntheticActions });
  seal(state);
  return verifyHats(state);
}

export function exportHatsEvidence(state) {
  return { schemaVersion: 1, product: 'UNISON Guardian', component: 'HATS', exportedAt: new Date(nowFor(state)).toISOString(), evidenceClass: 'SIMULATED', origin: { trusted: false, signaturesVerified: false, externalAnchor: null }, limitations: [
    'All agent identities, capabilities, behaviors, and actions are synthetic.',
    'Lineage and event digest consistency does not authenticate origin, ownership, or a deployment.',
    'Transition receipts are unkeyed consistency digests, not signatures, bearer credentials, or external authorizations.',
    'An unanchored export can be rewritten and rehashed. No independently trusted root is supplied.',
    'Hard limits bound registered spawning; they do not predict or contain arbitrary external agents.',
    'No external model invocation, kernel probe, container inspection, or scientific detection claim is attested.',
  ], state: hatsSnapshot(state) };
}

function checkpointError(message) { fail('INVALID_HATS_CHECKPOINT', `Invalid trusted HATS checkpoint: ${message}`, 409); }
function requireCheck(condition, message) { if (!condition) checkpointError(message); }
function exactShape(value, keys, label) { requireCheck(record(value) && Object.keys(value).sort().join('|') === [...keys].sort().join('|'), `${label} shape is unsupported.`); }
function boundedJson(value) {
  const seen = new Set();
  let budget = 0;
  function visit(item, depth) {
    requireCheck(depth <= 28, 'Nesting is too deep.');
    if (item === null || typeof item === 'boolean') return;
    if (typeof item === 'number') return requireCheck(Number.isFinite(item), 'Numbers must be finite.');
    if (typeof item === 'string') { budget += item.length; requireCheck(budget <= MAX_CHECKPOINT_BYTES, 'String data is too large.'); return; }
    requireCheck(typeof item === 'object' && !seen.has(item), 'Only acyclic JSON data is accepted.');
    requireCheck(Array.isArray(item) || Object.getPrototypeOf(item) === Object.prototype || Object.getPrototypeOf(item) === null, 'Only plain JSON objects are accepted.');
    requireCheck(Object.getOwnPropertySymbols(item).length === 0, 'Symbol members are unsupported.');
    seen.add(item);
    const descriptors = Object.getOwnPropertyDescriptors(item);
    if (Array.isArray(item)) requireCheck(Object.keys(item).length === item.length, 'Sparse or extended arrays are unsupported.');
    for (const [key, descriptor] of Object.entries(descriptors)) {
      if (Array.isArray(item) && key === 'length') continue;
      requireCheck(descriptor.enumerable && 'value' in descriptor, 'Accessors and hidden fields are unsupported.');
      budget += key.length;
      requireCheck(budget <= MAX_CHECKPOINT_BYTES, 'Object data is too large.');
      visit(descriptor.value, depth + 1);
    }
    seen.delete(item);
  }
  visit(value, 0);
  requireCheck(Buffer.byteLength(JSON.stringify(value), 'utf8') <= MAX_CHECKPOINT_BYTES, 'Serialized checkpoint exceeds its byte limit.');
}

function validateRestoredState(state) {
  exactShape(state, ['schemaVersion', 'runId', 'revision', 'deployment', 'sourceClass', 'createdAt', 'agents', 'events', 'policy', 'syntheticActions', 'lastDecision', 'verification', 'demo'], 'State');
  requireCheck(state.schemaVersion === 1 && UUID.test(state.runId) && state.sourceClass === 'SIMULATED', 'Version, run reference, or evidence class is invalid.');
  requireCheck(typeof state.deployment === 'string' && state.deployment.trim() && state.deployment.length <= 120 && Number.isFinite(Date.parse(state.createdAt)), 'Deployment or timestamp is invalid.');
  requireCheck(canonical(state.policy) === canonical(POLICY), 'Hard policy bounds changed.');
  requireCheck(Array.isArray(state.agents) && state.agents.length > 0 && state.agents.length <= POLICY.maxAgents && Array.isArray(state.events) && state.events.length > 0 && state.events.length <= MAX_EVENTS, 'Registry or ledger size is invalid.');
  requireCheck(state.revision === state.events.length && Number.isSafeInteger(state.syntheticActions) && state.syntheticActions >= 0, 'Revision or counter is invalid.');
  requireCheck(verifyLedger(state.events).valid && state.events.every(event => event.runId === state.runId), 'Ledger digests or run references differ.');
  for (const agent of state.agents) {
    exactShape(agent, ['id', 'type', 'parentId', 'depth', 'capabilities', 'specialization', 'nonce', 'createdAt', 'genome', 'revoked', 'lineageHash'], 'Agent');
    requireCheck(UUID.test(agent.id) && UUID.test(agent.nonce) && (agent.parentId === null || UUID.test(agent.parentId)) && HASH.test(agent.lineageHash), 'Agent identity references are invalid.');
    requireCheck(TYPES.includes(agent.type) && agent.depth === TYPES.indexOf(agent.type) && SPECIALIZATIONS.includes(agent.specialization) && typeof agent.revoked === 'boolean' && Number.isFinite(Date.parse(agent.createdAt)), 'Agent generation, specialization, or timestamp is invalid.');
    requireCheck(Array.isArray(agent.capabilities) && agent.capabilities.length <= CAPABILITIES.length && new Set(agent.capabilities).size === agent.capabilities.length && agent.capabilities.every(item => CAPABILITIES.includes(item)), 'Agent capability scope is invalid.');
    exactShape(agent.genome, ['parentStateHash', 'inheritanceMask'], 'Genome');
    requireCheck((agent.parentId === null ? agent.genome.parentStateHash === null : HASH.test(agent.genome.parentStateHash)) && canonical(agent.genome.inheritanceMask) === canonical(agent.capabilities), 'Inherited state or mask is invalid.');
  }
  requireCheck(state.agents.filter(agent => agent.parentId === null).length === 1 && state.agents[0].parentId === null, 'Exactly one registered genesis is required.');
  requireCheck(inspectHatsLineage(state.agents, state.runId).status === 'PASS', 'Lineage recomputation failed.');
  requireCheck(state.agents.every(agent => state.agents.filter(child => child.parentId === agent.id).length <= POLICY.maxChildren), 'Child fanout exceeds policy.');
  // Replay registrations and consequential effects from retained telemetry. The
  // checksum alone is insufficient to establish internal state consistency.
  const registered = new Map();
  let counter = 0;
  let latestDecision = null;
  let lastTime = -Infinity;
  for (const event of state.events) {
    requireCheck(Date.parse(event.time) >= lastTime, 'Ledger time moved backwards.');
    lastTime = Date.parse(event.time);
    if (event.type === 'hats.created' || event.type === 'agent.spawned') {
      const agent = event.data?.agent;
      requireCheck(record(agent) && !registered.has(agent.id) && agent.revoked === false, 'Registration is missing or duplicated.');
      const target = state.agents.find(item => item.id === agent.id);
      requireCheck(target && canonical(immutable(agent)) === canonical(immutable(target)) && agent.createdAt === event.time, 'Registration differs from the current identity.');
      if (event.type === 'hats.created') requireCheck(event.seq === 1 && agent.parentId === null && agent.createdAt === state.createdAt && canonical(agent.capabilities) === canonical(CAPABILITIES) && canonical(event.data.policy) === canonical(POLICY), 'Genesis registration is invalid.');
      else {
        const parent = registered.get(agent.parentId);
        requireCheck(parent && !parent.revoked && event.data.parentId === parent.id && event.data.agentId === agent.id && event.data.childId === agent.id, 'Spawn parent or child reference is invalid.');
        const prior = { ...state, agents: [...registered.values()] };
        requireCheck(authority(prior, parent.id, 'spawn:agent').allowed, 'Spawn ancestry was not authorized.');
        requireCheck(agent.genome.parentStateHash === hash({ parent: immutable(parent), revoked: parent.revoked, revision: event.seq - 1, ledgerTip: event.previousHash }), 'Inherited parent-state digest differs from the spawn transition.');
        requireCheck([...registered.values()].filter(item => item.parentId === parent.id).length < POLICY.maxChildren && registered.size < POLICY.maxAgents, 'Spawn exceeded hard budgets.');
        requireCheck(state.events.filter(previous => previous.seq < event.seq && previous.type === 'agent.spawned' && Date.parse(event.time) - Date.parse(previous.time) < POLICY.spawnWindowMs).length < POLICY.spawnLimit, 'Spawn exceeded its time-window budget.');
      }
      registered.set(agent.id, copy(agent));
    } else if (event.type === 'authority.revoked') {
      const agent = registered.get(event.data?.agentId);
      requireCheck(agent && !agent.revoked, 'Revocation is missing or duplicated.');
      agent.revoked = true;
    } else if (event.type === 'action.executed') {
      const prior = { ...state, agents: [...registered.values()] };
      requireCheck(event.data?.action === 'invoke:synthetic' && authority(prior, event.data.agentId, 'invoke:synthetic').allowed, 'A recorded action was not authorized at execution.');
      counter += 1;
      requireCheck(event.data.counter === counter, 'Recorded counter transitions are invalid.');
    } else requireCheck(['spawn.denied', 'spawn.unknown', 'action.denied', 'demo.completed', 'verification.completed'].includes(event.type), 'An event type is unsupported.');
    if (event.data?.decision) {
      const result = event.data.decision;
      requireCheck(record(result) && ['AUTHORIZED', 'DENIED', 'UNKNOWN'].includes(result.status) && result.allowed === (result.status === 'AUTHORIZED') && typeof result.code === 'string' && typeof result.reason === 'string' && UUID.test(result.agentId) && typeof result.action === 'string' && result.evaluatedRevision === event.seq - 1, 'Decision fields are invalid.');
      if (result.allowed) {
        requireCheck(Array.isArray(result.lineage) && result.receipt === hash({ domain: 'unison-hats-transition-v1', runId: state.runId, revision: result.evaluatedRevision, agentId: result.agentId, action: result.action, lineage: result.lineage, ledgerTip: event.previousHash }), 'Transition digest differs.');
      } else requireCheck(result.receipt === null, 'Denied decisions must not carry an authorization receipt.');
      latestDecision = result;
    }
  }
  requireCheck(registered.size === state.agents.length && canonical([...registered.values()]) === canonical(state.agents), 'Registry does not match its transitions.');
  requireCheck(counter === state.syntheticActions && canonical(latestDecision) === canonical(state.lastDecision), 'Counter or latest decision lacks a matching transition.');
  if (state.demo !== null) {
    exactShape(state.demo, ['completed', 'steps', 'verdict', 'counterBeforeRevocation', 'counterAfterRevocation'], 'Demo');
    requireCheck(state.demo.completed === true && Array.isArray(state.demo.steps) && state.demo.steps.length === 11 && state.demo.counterBeforeRevocation === 1 && state.demo.counterAfterRevocation === 1, 'Demo assertions are invalid.');
    for (const step of state.demo.steps) {
      exactShape(step, ['label', 'status', 'code', 'expected', 'passed', 'eventSeq'], 'Demo step');
      const result = state.events[step.eventSeq - 1]?.data?.decision;
      requireCheck(typeof step.label === 'string' && result && step.status === result.status && step.code === result.code && ['AUTHORIZED', 'DENIED'].includes(step.expected) && step.passed === (step.status === step.expected), 'A demonstration assertion differs from its decision event.');
    }
    requireCheck(state.demo.verdict === (state.demo.steps.every(step => step.passed) ? 'PASS' : 'FAIL'), 'Demonstration verdict differs from its assertions.');
  }
  if (state.verification !== null) {
    exactShape(state.verification, ['verdict', 'checks', 'scope', 'generatedAt', 'originTrusted', 'signaturesVerified'], 'Verification');
    requireCheck(['PASS', 'FAIL', 'UNKNOWN'].includes(state.verification.verdict) && Array.isArray(state.verification.checks) && state.verification.checks.length >= 4 && state.verification.checks.length <= 5 && state.verification.originTrusted === false && state.verification.signaturesVerified === false, 'Verification claims are invalid.');
    const reported = [...state.events].reverse().find(event => event.type === 'verification.completed');
    requireCheck(reported && reported.data.verdict === state.verification.verdict && canonical(reported.data.checks) === canonical(state.verification.checks.map(({ id, status }) => ({ id, status }))), 'Verification lacks a matching observation.');
  }
}

/** Only trusted server persistence may call this seam; no HTTP import route. */
export function checkpointHats(state) {
  if (!intact(state)) checkpointError('State differs from its retained seal.');
  const body = { version: 1, state: copy(state), retained: { seal: owned.get(state).seal } };
  const result = { ...body, checksum: hash(body) };
  boundedJson(result);
  return result;
}

export function restoreHats(checkpoint, { now = Date.now } = {}) {
  boundedJson(checkpoint);
  exactShape(checkpoint, ['version', 'state', 'retained', 'checksum'], 'Checkpoint');
  exactShape(checkpoint.retained, ['seal'], 'Retained state');
  requireCheck(checkpoint.version === 1 && typeof now === 'function', 'Unsupported checkpoint version or clock.');
  requireCheck(checkpoint.checksum === hash({ version: checkpoint.version, state: checkpoint.state, retained: checkpoint.retained }) && checkpoint.retained.seal === hash(checkpoint.state), 'Checksum or retained state digest differs.');
  const state = copy(checkpoint.state);
  validateRestoredState(state);
  owned.set(state, { now, seal: checkpoint.retained.seal });
  return state;
}
