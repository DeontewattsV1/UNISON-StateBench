import { createHash, randomUUID } from 'node:crypto';

// This engine only operates on synthetic capabilities and a demonstration action
// counter. It never controls a real credential, tool, payment, or identity.
const ACTION = 'release:funds';
const GENESIS = '0'.repeat(64);
const SCENARIOS = new Set(['queued', 'alternate', 'unknown']);
const EVIDENCE = new Set(['SIMULATED', 'OBSERVED', 'UNKNOWN']);
const MAX_CHECKPOINT_BYTES = 4 * 1024 * 1024;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const privateState = new WeakMap();

function canonical(value) {
  if (value === null || typeof value === 'boolean' || typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  }
  throw new TypeError('Evidence must contain JSON values only.');
}

function digest(value) {
  return createHash('sha256').update(canonical(value)).digest('hex');
}

function eventBody(event) {
  const { hash, ...body } = event;
  return body;
}

function clone(value) {
  return structuredClone(value);
}

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function metaFor(sandbox) {
  const meta = privateState.get(sandbox);
  if (!meta) throw new TypeError('Use createSandbox() to create an engine-owned sandbox.');
  return meta;
}

function inventory(sandbox) {
  return {
    runId: sandbox.runId,
    scenario: sandbox.scenario,
    registryComplete: sandbox.registryComplete,
    identity: sandbox.identity,
    nodes: sandbox.nodes,
    edges: sandbox.edges,
    grants: sandbox.grants.map(({ revoked, ...grant }) => grant),
  };
}

/**
 * Recompute each SHA-256 event digest and its sequence/reference links.
 * A valid local chain establishes internal consistency only: an attacker can
 * rewrite and rehash an unanchored exported chain. No signature is verified.
 */
export function verifyLedger(ledger) {
  const fail = (detail, firstInvalidSeq = null) => ({
    valid: false, status: 'FAIL', checkedEvents: 0, firstInvalidSeq, detail,
    originTrusted: false, signaturesVerified: false,
  });
  if (!Array.isArray(ledger)) return fail('The ledger must be an array.');
  if (ledger.length === 0) return {
    ...fail('No ledger events were supplied.'), status: 'UNKNOWN',
  };
  let previousHash = GENESIS;
  const ids = new Set();
  let runId;
  for (let index = 0; index < ledger.length; index += 1) {
    const event = ledger[index];
    const seq = index + 1;
    if (!event || typeof event !== 'object' || Array.isArray(event)) return fail('An event is not an object.', seq);
    if (event.seq !== seq) return fail('Event sequence is not contiguous.', seq);
    if (typeof event.id !== 'string' || !event.id || ids.has(event.id)) return fail('An event identifier is missing or repeated.', seq);
    if (typeof event.runId !== 'string' || !event.runId) return fail('An event has no execution-run reference.', seq);
    if (index === 0) runId = event.runId;
    if (event.runId !== runId) return fail('The ledger mixes execution-run references.', seq);
    if (typeof event.time !== 'string' || !Number.isFinite(Date.parse(event.time))) return fail('An event timestamp is malformed.', seq);
    if (typeof event.type !== 'string' || !event.type || typeof event.message !== 'string' || !EVIDENCE.has(event.evidence)) {
      return fail('An event has an invalid event type, message, or evidence label.', seq);
    }
    if (event.previousHash !== previousHash) return fail('The previous-digest reference does not match.', seq);
    try {
      if (event.hash !== digest(eventBody(event))) return fail('A recomputed event digest does not match.', seq);
    } catch {
      return fail('An event is not canonical JSON.', seq);
    }
    ids.add(event.id);
    previousHash = event.hash;
  }
  return {
    valid: true, status: 'PASS', checkedEvents: ledger.length, firstInvalidSeq: null,
    detail: `${ledger.length} event digests and sequence links recomputed. Origin is untrusted; no signatures or external trust anchor were verified.`,
    originTrusted: false, signaturesVerified: false,
  };
}

function auditState(sandbox) {
  const meta = metaFor(sandbox);
  const errors = [];
  try {
    if (digest(inventory(sandbox)) !== meta.inventoryHash) errors.push('Registered topology, grant scope, run identity, or completeness declaration changed outside the engine.');
  } catch {
    errors.push('Registered inventory is malformed.');
  }
  if (!Array.isArray(sandbox.grants) || sandbox.grants.some(grant => !isRecord(grant)
    || grant.revoked !== meta.revocations.get(grant.id))) {
    errors.push('Grant revocation state lacks a matching engine transition.');
  }
  if (sandbox.protectedActions !== meta.protectedActions) errors.push('The synthetic protected-action counter changed outside the engine.');
  if (sandbox.revision !== meta.revision) errors.push('The sandbox revision changed outside the engine.');
  try {
    if (canonical(sandbox.results) !== canonical(meta.verificationResult)) errors.push('The reported verification result changed without an engine finding.');
  } catch {
    errors.push('The reported verification result is malformed.');
  }
  try {
    if (canonical(sandbox.queue) !== canonical([...meta.jobs.values()])) errors.push('Queued-operation state changed outside the engine.');
  } catch {
    errors.push('Queued-operation state is malformed.');
  }
  const ledger = verifyLedger(sandbox.events);
  if (!ledger.valid) errors.push(ledger.detail);
  if (!Array.isArray(sandbox.events) || sandbox.events.length !== meta.ledgerLength || sandbox.events.at(-1)?.hash !== meta.ledgerTip) {
    errors.push('The ledger differs from the engine\'s server-retained tip.');
  }
  return { errors, ledger };
}

function assertState(sandbox) {
  const { errors } = auditState(sandbox);
  if (errors.length) {
    const error = new Error(`Sandbox integrity check failed: ${errors.join(' ')}`);
    error.code = 'STATE_INTEGRITY';
    throw error;
  }
}

function clearResult(sandbox) {
  sandbox.results = null;
  metaFor(sandbox).verificationResult = null;
}

function append(sandbox, type, evidence, message, data = {}) {
  const meta = metaFor(sandbox);
  const body = {
    seq: sandbox.events.length + 1,
    id: randomUUID(),
    runId: sandbox.runId,
    time: new Date().toISOString(),
    type, evidence, message,
    data: clone(data),
    previousHash: meta.ledgerTip,
  };
  const event = { ...body, hash: digest(body) };
  sandbox.events.push(event);
  meta.ledgerLength = sandbox.events.length;
  meta.ledgerTip = event.hash;
  sandbox.revision += 1;
  meta.revision = sandbox.revision;
}

function grantAuthority(sandbox, grantId, principal, action) {
  const grants = new Map(sandbox.grants.map(grant => [grant.id, grant]));
  const leaf = grants.get(grantId);
  if (!leaf) return { allowed: false, reason: 'The registered grant is missing.' };
  if (leaf.principal !== principal) return { allowed: false, reason: 'The grant belongs to a different principal.' };
  if (leaf.action !== action) return { allowed: false, reason: 'The action is outside the registered grant scope.' };
  const lineage = [];
  let grant = leaf;
  while (grant) {
    if (lineage.includes(grant.id)) return { allowed: false, reason: 'A delegation cycle has no rooted authority.', lineage };
    lineage.push(grant.id);
    if (grant.revoked) return { allowed: false, reason: `Ancestor grant ${grant.id} is revoked.`, lineage };
    if (grant.action !== action) return { allowed: false, reason: 'Delegation would widen the parent action scope.', lineage };
    if (grant.parentId === null) return { allowed: true, reason: 'Every grant in the registered lineage is active.', lineage };
    grant = grants.get(grant.parentId);
    if (!grant) return { allowed: false, reason: 'A delegation ancestor is missing.', lineage };
  }
  return { allowed: false, reason: 'No registered root authority was found.', lineage };
}

/** Extra read-only seam for adapters and invariant tests. */
export function evaluateAuthority(sandbox, grantId, principal, action = ACTION) {
  const audit = auditState(sandbox);
  if (audit.errors.length) return { allowed: false, reason: 'State integrity failed; authority is denied.', integrityErrors: audit.errors };
  return grantAuthority(sandbox, grantId, principal, action);
}

function activeEdge(sandbox, edge) {
  if (edge.grantId === null) return true;
  const grant = sandbox.grants.find(item => item.id === edge.grantId);
  return Boolean(grant && grantAuthority(sandbox, grant.id, grant.principal, ACTION).allowed);
}

function residualPaths(sandbox) {
  const paths = [];
  function visit(node, path) {
    if (node === 'protected-action') {
      paths.push(path);
      return;
    }
    for (const edge of sandbox.edges) {
      if (edge.source === node && activeEdge(sandbox, edge) && !path.includes(edge.target)) visit(edge.target, [...path, edge.target]);
    }
  }
  visit('operator', ['operator']);
  return paths;
}

export function createSandbox(scenario = 'queued', { deployment = 'Local synthetic sandbox' } = {}) {
  if (!SCENARIOS.has(scenario)) throw new RangeError('Scenario must be queued, alternate, or unknown.');
  if (typeof deployment !== 'string' || !deployment.trim() || deployment.length > 120) {
    throw new RangeError('The server deployment label must be a nonempty string of at most 120 characters.');
  }
  const runId = randomUUID();
  const sandbox = {
    runId, scenario, revision: 0,
    registryComplete: scenario !== 'unknown',
    nodes: [
      { id: 'operator', label: 'Operator', kind: 'principal' },
      { id: 'planner', label: 'Planner', kind: 'agent' },
      { id: 'delegate', label: 'Delegate', kind: 'agent' },
      { id: 'queue', label: 'Queued worker', kind: 'queue' },
      { id: 'gateway', label: 'Tool gateway', kind: 'tool' },
      { id: 'protected-action', label: 'Protected action', kind: 'action' },
    ],
    edges: [
      { id: 'edge-root', source: 'operator', target: 'planner', label: 'Authorize', grantId: 'grant-primary' },
      { id: 'edge-delegate', source: 'planner', target: 'delegate', label: 'Delegate', grantId: 'grant-delegate' },
      { id: 'edge-direct', source: 'delegate', target: 'gateway', label: 'Invoke', grantId: 'grant-delegate' },
      { id: 'edge-queue', source: 'planner', target: 'queue', label: 'Enqueue', grantId: 'grant-queued' },
      { id: 'edge-replay', source: 'queue', target: 'gateway', label: 'Commit check', grantId: 'grant-queued' },
      { id: 'edge-action', source: 'gateway', target: 'protected-action', label: 'Synthetic only', grantId: null },
    ],
    grants: [
      { id: 'grant-primary', parentId: null, principal: 'planner', action: ACTION, revoked: false },
      { id: 'grant-delegate', parentId: 'grant-primary', principal: 'delegate', action: ACTION, revoked: false },
      { id: 'grant-queued', parentId: 'grant-primary', principal: 'queued-worker', action: ACTION, revoked: false },
    ],
    queue: [], events: [], results: null, protectedActions: 0,
    identity: {
      runId, taskId: randomUUID(), model: 'muse-wonder-1.0 (configured; not invoked)',
      principal: 'operator-demo', deployment, owner: 'UNKNOWN — no owner attestation',
    },
  };
  if (scenario === 'alternate') {
    sandbox.nodes.push({ id: 'service', label: 'Service account', kind: 'principal' });
    sandbox.grants.push({ id: 'grant-independent', parentId: null, principal: 'service-account', action: ACTION, revoked: false });
    sandbox.edges.push(
      { id: 'edge-service-root', source: 'operator', target: 'service', label: 'Independent grant', grantId: 'grant-independent' },
      { id: 'edge-service-tool', source: 'service', target: 'gateway', label: 'Alternate path', grantId: 'grant-independent' },
    );
  }
  privateState.set(sandbox, {
    inventoryHash: digest(inventory(sandbox)),
    registeredInventory: clone(inventory(sandbox)),
    revocations: new Map(sandbox.grants.map(grant => [grant.id, false])),
    jobs: new Map(), baselineDone: false, emptyReplayRecorded: false,
    protectedActions: 0, revision: 0, ledgerTip: GENESIS, ledgerLength: 0,
    verificationResult: null,
  });
  append(sandbox, 'run.created', 'SIMULATED', 'Created a synthetic authority sandbox. No external action or identity is verified.', {
    scenario, registryComplete: sandbox.registryComplete,
  });
  return sandbox;
}

export function snapshot(sandbox) {
  const audit = auditState(sandbox);
  const safe = audit.errors.length === 0;
  const meta = metaFor(sandbox);
  if (!safe) {
    // Do not forward corrupt/null records to adapters or mistake their absence
    // for a disconnected graph. Retain the process-owned inventory for display,
    // suppress every active capability, and surface an explicit failure.
    const retained = meta.registeredInventory;
    const results = meta.verificationResult?.verdict === 'FAIL' ? meta.verificationResult : {
      verdict: 'FAIL',
      scope: 'The sandbox state is corrupt; no authority or revocation conclusion is established.',
      checks: [{ id: 'integrity', label: 'Sandbox state integrity', status: 'FAIL', detail: audit.errors.join(' ') }],
      residualPaths: [], originTrusted: false,
    };
    const queue = [...meta.jobs.values()];
    return clone({
      runId: retained.runId, scenario: retained.scenario, revision: meta.revision,
      registryComplete: retained.registryComplete,
      nodes: retained.nodes,
      edges: retained.edges.map(edge => ({ ...edge, active: false })),
      grants: retained.grants.map(grant => ({ ...grant, revoked: meta.revocations.get(grant.id), active: false })),
      queue, events: [], results, identity: retained.identity,
      phase: !meta.baselineDone ? 'ready' : meta.revocations.get('grant-primary') ? 'revoked' : 'authorized',
      integrityErrors: audit.errors,
      projectionSource: 'Retained process inventory; altered public state is suppressed.',
      ledgerVerification: audit.ledger,
      stats: {
        activeGrants: 0,
        queuedActions: queue.filter(job => job.status === 'pending').length,
        events: 0, protectedActions: meta.protectedActions,
      },
    });
  }
  const grants = sandbox.grants.map(grant => ({
    ...grant,
    active: safe && grantAuthority(sandbox, grant.id, grant.principal, grant.action).allowed,
  }));
  return clone({
    runId: sandbox.runId, scenario: sandbox.scenario, revision: sandbox.revision,
    registryComplete: sandbox.registryComplete,
    nodes: sandbox.nodes,
    edges: sandbox.edges.map(edge => ({ ...edge, active: safe && activeEdge(sandbox, edge) })),
    grants, queue: sandbox.queue, events: sandbox.events, results: metaFor(sandbox).verificationResult,
    identity: sandbox.identity,
    phase: !metaFor(sandbox).baselineDone ? 'ready' : sandbox.grants[0].revoked ? 'revoked' : 'authorized',
    integrityErrors: audit.errors,
    ledgerVerification: audit.ledger,
    stats: {
      activeGrants: grants.filter(grant => grant.active).length,
      queuedActions: sandbox.queue.filter(job => job.status === 'pending').length,
      events: sandbox.events.length, protectedActions: sandbox.protectedActions,
    },
  });
}

export function runBaseline(sandbox) {
  assertState(sandbox);
  const meta = metaFor(sandbox);
  if (meta.baselineDone) return snapshot(sandbox);
  const authorization = grantAuthority(sandbox, 'grant-delegate', 'delegate', ACTION);
  clearResult(sandbox);
  meta.baselineDone = true;
  if (!authorization.allowed) {
    append(sandbox, 'action.denied', 'SIMULATED', 'Baseline action denied because its current authority is invalid.', authorization);
    return snapshot(sandbox);
  }
  sandbox.protectedActions += 1;
  meta.protectedActions = sandbox.protectedActions;
  append(sandbox, 'action.executed', 'SIMULATED', 'Authorized baseline action incremented the synthetic counter.', {
    principal: 'delegate', action: ACTION, grantId: 'grant-delegate', authorization,
  });
  const job = {
    id: randomUUID(), principal: 'queued-worker', action: ACTION, grantId: 'grant-queued',
    status: 'pending', enqueuedRevision: sandbox.revision, enqueuedAt: new Date().toISOString(),
    authorizationAtEnqueue: true, authorizationAtCommit: null, attemptedAfterRevocation: null,
  };
  sandbox.queue.push(job);
  meta.jobs.set(job.id, clone(job));
  append(sandbox, 'action.queued', 'SIMULATED', 'Queued one operation. Enqueue-time authorization does not authorize a later commit.', {
    jobId: job.id, grantId: job.grantId, principal: job.principal, action: job.action,
  });
  return snapshot(sandbox);
}

export function revokeAuthority(sandbox) {
  assertState(sandbox);
  const meta = metaFor(sandbox);
  const root = sandbox.grants.find(grant => grant.id === 'grant-primary');
  if (root.revoked) return snapshot(sandbox);
  clearResult(sandbox);
  root.revoked = true;
  meta.revocations.set(root.id, true);
  append(sandbox, 'authority.revoked', 'SIMULATED', 'Revoked the primary grant. Every descendant now fails its ancestor check.', {
    grantId: root.id, queuedJobs: sandbox.queue.filter(job => job.status === 'pending').map(job => job.id),
    independentGrantsRevoked: false,
  });
  return snapshot(sandbox);
}

export function replayQueued(sandbox) {
  assertState(sandbox);
  const meta = metaFor(sandbox);
  const pending = sandbox.queue.filter(job => job.status === 'pending');
  if (!pending.length) {
    if (!meta.emptyReplayRecorded && !sandbox.queue.length) {
      append(sandbox, 'queue.empty', 'OBSERVED', 'No queued operation exists. Run the baseline before testing queued replay.');
      meta.emptyReplayRecorded = true;
    }
    return snapshot(sandbox);
  }
  clearResult(sandbox);
  for (const job of pending) {
    const authorization = grantAuthority(sandbox, job.grantId, job.principal, job.action);
    job.authorizationAtCommit = authorization.allowed;
    job.attemptedAfterRevocation = sandbox.grants.find(grant => grant.id === 'grant-primary').revoked;
    job.status = authorization.allowed ? 'executed' : 'blocked';
    job.completedAt = new Date().toISOString();
    if (authorization.allowed) {
      sandbox.protectedActions += 1;
      meta.protectedActions = sandbox.protectedActions;
    }
    meta.jobs.set(job.id, clone(job));
    append(sandbox, authorization.allowed ? 'queue.executed' : 'queue.blocked', 'SIMULATED', authorization.allowed
      ? 'The queued operation was authorized at commit and incremented the synthetic counter.'
      : 'Queued replay was blocked at commit. Its stale enqueue-time permission could not authorize execution.', {
      jobId: job.id, grantId: job.grantId, principal: job.principal, action: job.action,
      attemptedAfterRevocation: job.attemptedAfterRevocation, authorization,
    });
  }
  return snapshot(sandbox);
}

export function verifySandbox(sandbox) {
  const audit = auditState(sandbox);
  const sound = audit.errors.length === 0;
  const rootRevoked = sound && sandbox.grants.find(grant => grant.id === 'grant-primary')?.revoked;
  const paths = sound ? residualPaths(sandbox) : [];
  const tested = sound && sandbox.queue.some(job => job.attemptedAfterRevocation === true && job.status === 'blocked');
  const bypass = sound && sandbox.queue.some(job => job.attemptedAfterRevocation === true && job.status === 'executed');
  const checks = [
    { id: 'revocation', label: 'Primary authority revoked', status: rootRevoked ? 'PASS' : 'FAIL', detail: rootRevoked
      ? 'The primary grant has a matching engine-retained revocation transition.'
      : 'The primary authority has not been validly revoked.' },
    { id: 'paths', label: 'Registered paths disconnected', status: !sound || paths.length ? 'FAIL' : 'PASS', detail: !sound
      ? 'A changed or malformed inventory cannot establish disconnection.'
      : paths.length ? `${paths.length} registered route(s) still reach the protected action.`
        : 'No active route from the operator to the protected action remains in the registered graph.' },
    { id: 'queue', label: 'Queued replay denied at commit', status: bypass ? 'FAIL' : tested ? 'PASS' : 'UNKNOWN', detail: bypass
      ? 'A queued operation executed after primary revocation.'
      : tested ? 'The queued operation was retried after revocation and blocked before changing the synthetic counter.'
        : 'A post-revocation queued commit has not been tested. Run baseline, revoke authority, then replay the queued action.' },
    { id: 'ledger', label: 'Local ledger integrity', status: audit.ledger.valid && sound ? 'PASS' : 'FAIL', detail: audit.errors.length
      ? audit.errors.join(' ') : audit.ledger.detail },
    { id: 'inventory', label: 'Registry coverage declared', status: !sound ? 'FAIL' : sandbox.registryComplete ? 'PASS' : 'UNKNOWN', detail: !sound
      ? 'This run no longer matches its retained registration.'
      : sandbox.registryComplete ? 'This synthetic scenario declares its registered inventory complete; external and unregistered systems are outside the claim.'
        : 'The inventory is explicitly incomplete. Absence of a known path cannot prove global revocation.' },
  ];
  const verdict = checks.some(check => check.status === 'FAIL') ? 'FAIL'
    : checks.some(check => check.status === 'UNKNOWN') ? 'UNKNOWN' : 'PASS';
  sandbox.results = {
    verdict,
    scope: 'Registered synthetic routes in this sandbox only. No claim over external systems, unregistered paths, legal identity, or cryptographic origin.',
    checks, residualPaths: paths,
    generatedAt: new Date().toISOString(),
    originTrusted: false,
  };
  metaFor(sandbox).verificationResult = clone(sandbox.results);
  // Do not extend a damaged chain or replace the retained process anchor.
  if (sound) append(sandbox, 'verification.completed', 'OBSERVED', `Deterministic sandbox verification: ${verdict}.`, {
    verdict, checks: checks.map(({ id, status }) => ({ id, status })), residualPaths: paths,
    scope: sandbox.results.scope, originTrusted: false,
  });
  return snapshot(sandbox);
}

export function exportEvidence(sandbox) {
  const state = snapshot(sandbox);
  return {
    schemaVersion: 1,
    product: 'UNISON Guardian',
    exportedAt: new Date().toISOString(),
    evidenceClass: 'SIMULATED',
    authorityScope: 'Synthetic registered capabilities in one isolated demonstration sandbox.',
    origin: { trusted: false, signaturesVerified: false, externalAnchor: null },
    limitations: [
      'All identities, capabilities, actions, and scenarios are synthetic.',
      'Ledger digest consistency is not proof of origin, ownership, or a trustworthy external root.',
      'An exported ledger can be rewritten and rehashed; the server-retained tip is not an independent external trust anchor.',
      'Unknown and unregistered authority paths cannot be ruled out.',
      'No external provider call, credential revocation, or real protected action is attested by this bundle.',
    ],
    state,
    ledgerVerification: state.ledgerVerification,
  };
}

function invalidCheckpoint(reason) {
  const error = new Error(`Invalid trusted server checkpoint: ${reason}`);
  error.code = 'INVALID_CHECKPOINT';
  return error;
}

function requireCheckpoint(condition, reason) {
  if (!condition) throw invalidCheckpoint(reason);
}

function exactRecord(value, keys, label) {
  requireCheckpoint(isRecord(value), `${label} must be an object.`);
  const actual = Object.keys(value).sort();
  requireCheckpoint(actual.length === keys.length && actual.every((key, index) => key === [...keys].sort()[index]), `${label} has missing or unsupported members.`);
}

function safeInteger(value) {
  return Number.isSafeInteger(value) && value >= 0;
}

function dateString(value) {
  return typeof value === 'string' && Number.isFinite(Date.parse(value));
}

// Checkpoints cross a persistence boundary, not an evidence-import boundary.
// Admit only bounded JSON data, avoiding lossy JSON serialization of functions,
// sparse arrays, undefined values, nonfinite numbers, or special object types.
function checkpointData(value) {
  const seen = new Set();
  let characterBudget = 0;
  function visit(item, depth) {
    requireCheckpoint(depth <= 32, 'The checkpoint exceeds the supported nesting depth.');
    if (item === null || typeof item === 'boolean') return;
    if (typeof item === 'string') {
      characterBudget += item.length;
    } else if (typeof item === 'number') {
      requireCheckpoint(Number.isFinite(item), 'The checkpoint contains a nonfinite number.');
    } else {
      requireCheckpoint(typeof item === 'object', 'The checkpoint must contain JSON data only.');
      requireCheckpoint(!seen.has(item), 'The checkpoint contains a cyclic reference.');
      requireCheckpoint(Array.isArray(item) || Object.getPrototypeOf(item) === Object.prototype || Object.getPrototypeOf(item) === null,
        'The checkpoint contains a non-JSON object.');
      requireCheckpoint(Object.getOwnPropertySymbols(item).length === 0, 'The checkpoint contains symbol members.');
      seen.add(item);
      const descriptors = Object.getOwnPropertyDescriptors(item);
      if (Array.isArray(item)) {
        requireCheckpoint(Object.keys(item).length === item.length, 'The checkpoint contains a sparse or extended array.');
        for (let index = 0; index < item.length; index += 1) {
          requireCheckpoint(Object.hasOwn(descriptors[index] ?? {}, 'value'), 'The checkpoint contains an accessor.');
          visit(descriptors[index].value, depth + 1);
        }
      } else {
        for (const [key, descriptor] of Object.entries(descriptors)) {
          requireCheckpoint(Object.hasOwn(descriptor, 'value') && descriptor.enumerable, 'The checkpoint contains a non-data member.');
          characterBudget += key.length;
          visit(descriptor.value, depth + 1);
        }
      }
      seen.delete(item);
    }
    requireCheckpoint(characterBudget <= MAX_CHECKPOINT_BYTES, 'The checkpoint exceeds the 4 MiB size limit.');
  }
  visit(value, 0);
  const serialized = JSON.stringify(value);
  requireCheckpoint(new TextEncoder().encode(serialized).byteLength <= MAX_CHECKPOINT_BYTES, 'The checkpoint exceeds the 4 MiB size limit.');
  return JSON.parse(serialized);
}

function restoreEntries(entries, ids, label, validateValue) {
  requireCheckpoint(Array.isArray(entries) && entries.length === ids.length, `${label} has the wrong registration count.`);
  const values = new Map();
  for (const entry of entries) {
    requireCheckpoint(Array.isArray(entry) && entry.length === 2 && typeof entry[0] === 'string'
      && ids.includes(entry[0]) && !values.has(entry[0]), `${label} contains an invalid or repeated identifier.`);
    validateValue(entry[1], entry[0]);
    values.set(entry[0], entry[1]);
  }
  return values;
}

function validateCheckpointJob(job) {
  requireCheckpoint(isRecord(job), 'A retained queued operation is malformed.');
  requireCheckpoint(['pending', 'executed', 'blocked'].includes(job.status), 'A retained queued operation has an unsupported status.');
  const keys = ['id', 'principal', 'action', 'grantId', 'status', 'enqueuedRevision', 'enqueuedAt',
    'authorizationAtEnqueue', 'authorizationAtCommit', 'attemptedAfterRevocation'];
  if (job.status !== 'pending') keys.push('completedAt');
  exactRecord(job, keys, 'The retained queued operation');
  requireCheckpoint(UUID.test(job.id) && job.principal === 'queued-worker' && job.action === ACTION && job.grantId === 'grant-queued'
    && safeInteger(job.enqueuedRevision) && dateString(job.enqueuedAt) && job.authorizationAtEnqueue === true,
  'The retained queued operation has an invalid identity, scope, or enqueue receipt.');
  if (job.status === 'pending') {
    requireCheckpoint(job.authorizationAtCommit === null && job.attemptedAfterRevocation === null, 'A pending operation carries a completion receipt.');
  } else {
    requireCheckpoint(dateString(job.completedAt) && typeof job.attemptedAfterRevocation === 'boolean'
      && job.authorizationAtCommit === (job.status === 'executed'), 'A completed operation carries an inconsistent commit receipt.');
    requireCheckpoint(job.status === 'blocked' ? job.attemptedAfterRevocation === true : job.attemptedAfterRevocation === false,
      'A queued completion contradicts the primary authority transition.');
  }
}

function validateCheckpointResult(result) {
  if (result === null) return;
  exactRecord(result, ['verdict', 'scope', 'checks', 'residualPaths', 'generatedAt', 'originTrusted'], 'The verification finding');
  requireCheckpoint(['PASS', 'FAIL', 'UNKNOWN'].includes(result.verdict) && typeof result.scope === 'string'
    && dateString(result.generatedAt) && result.originTrusted === false, 'The verification finding has invalid provenance or status.');
  const ids = ['revocation', 'paths', 'queue', 'ledger', 'inventory'];
  requireCheckpoint(Array.isArray(result.checks) && result.checks.length === ids.length, 'The verification finding has an incomplete check set.');
  for (let index = 0; index < result.checks.length; index += 1) {
    const check = result.checks[index];
    exactRecord(check, ['id', 'label', 'status', 'detail'], 'A verification check');
    requireCheckpoint(check.id === ids[index] && typeof check.label === 'string' && typeof check.detail === 'string'
      && ['PASS', 'FAIL', 'UNKNOWN'].includes(check.status), 'A verification check is malformed.');
  }
  const verdict = result.checks.some(check => check.status === 'FAIL') ? 'FAIL'
    : result.checks.some(check => check.status === 'UNKNOWN') ? 'UNKNOWN' : 'PASS';
  requireCheckpoint(verdict === result.verdict, 'The verification verdict contradicts its checks.');
  requireCheckpoint(Array.isArray(result.residualPaths) && result.residualPaths.every(path => Array.isArray(path)
    && path.length >= 2 && path.every(node => typeof node === 'string')), 'The residual-path finding is malformed.');
}

/**
 * Serialize sound, engine-owned state for trusted server storage only.
 * The unkeyed checksum detects corruption; it supplies no signature, identity,
 * origin authentication, or trust upgrade over an exported evidence bundle.
 */
export function checkpointSandbox(sandbox) {
  assertState(sandbox);
  const meta = metaFor(sandbox);
  const body = checkpointData({
    version: 1,
    state: sandbox,
    retained: {
      inventoryHash: meta.inventoryHash,
      registeredInventory: meta.registeredInventory,
      revocations: [...meta.revocations.entries()],
      jobs: [...meta.jobs.entries()],
      baselineDone: meta.baselineDone,
      emptyReplayRecorded: meta.emptyReplayRecorded,
      protectedActions: meta.protectedActions,
      revision: meta.revision,
      ledgerTip: meta.ledgerTip,
      ledgerLength: meta.ledgerLength,
      verificationResult: meta.verificationResult,
    },
  });
  return checkpointData({ ...body, checksum: digest(body) });
}

/** Restore only checkpoints read by the server from its own trusted storage. */
export function restoreSandbox(checkpoint) {
  try {
    const saved = checkpointData(checkpoint);
    exactRecord(saved, ['version', 'state', 'retained', 'checksum'], 'The checkpoint envelope');
    requireCheckpoint(saved.version === 1, 'The checkpoint version is unsupported.');
    const { checksum, ...body } = saved;
    requireCheckpoint(typeof checksum === 'string' && /^[0-9a-f]{64}$/.test(checksum) && checksum === digest(body), 'The corruption checksum does not match.');
    const { state, retained } = body;
    exactRecord(state, ['runId', 'scenario', 'revision', 'registryComplete', 'nodes', 'edges', 'grants', 'queue', 'events', 'results', 'protectedActions', 'identity'], 'The sandbox state');
    exactRecord(retained, ['inventoryHash', 'registeredInventory', 'revocations', 'jobs', 'baselineDone', 'emptyReplayRecorded',
      'protectedActions', 'revision', 'ledgerTip', 'ledgerLength', 'verificationResult'], 'The retained process state');
    requireCheckpoint(UUID.test(state.runId) && SCENARIOS.has(state.scenario), 'The execution run or scenario is invalid.');
    requireCheckpoint(isRecord(state.identity) && UUID.test(state.identity.taskId), 'The task identity is invalid.');
    requireCheckpoint(typeof retained.baselineDone === 'boolean' && typeof retained.emptyReplayRecorded === 'boolean', 'The retained operation flags are malformed.');
    requireCheckpoint(safeInteger(state.revision) && safeInteger(retained.revision) && safeInteger(retained.ledgerLength)
      && safeInteger(state.protectedActions) && safeInteger(retained.protectedActions), 'The retained counters are malformed.');
    requireCheckpoint(Array.isArray(state.queue) && state.queue.length <= 1 && Array.isArray(state.events) && state.events.length > 0,
      'The operation queue or event history is malformed.');
    requireCheckpoint(state.revision === state.events.length && retained.ledgerLength === state.events.length,
      'The revision and retained ledger length do not match the event history.');
    // Checkpoints restore this engine's known scenario registrations, not an
    // arbitrary caller-supplied authority graph. Preserve its run/task IDs and
    // server-selected deployment label while validating the remaining template.
    const template = createSandbox(state.scenario, { deployment: state.identity.deployment });
    const expected = inventory(template);
    expected.runId = state.runId;
    expected.identity.runId = state.runId;
    expected.identity.taskId = state.identity.taskId;
    requireCheckpoint(canonical(retained.registeredInventory) === canonical(expected)
      && retained.inventoryHash === digest(expected), 'The sealed registration is missing, malformed, or inconsistent.');
    const grantIds = expected.grants.map(grant => grant.id);
    const revocations = restoreEntries(retained.revocations, grantIds, 'The retained revocation registry', (revoked, id) => {
      requireCheckpoint(typeof revoked === 'boolean' && (id === 'grant-primary' || revoked === false), 'A revocation transition is unsupported.');
    });
    state.queue.forEach(validateCheckpointJob);
    const jobs = restoreEntries(retained.jobs, state.queue.map(job => job.id), 'The retained queued-operation registry', (job, id) => {
      validateCheckpointJob(job);
      requireCheckpoint(job.id === id, 'A retained job key does not match its operation identity.');
    });
    validateCheckpointResult(state.results);
    validateCheckpointResult(retained.verificationResult);
    const rootRevoked = revocations.get('grant-primary');
    requireCheckpoint(state.events[0]?.type === 'run.created' && state.events[0]?.data?.scenario === state.scenario
      && state.events[0]?.data?.registryComplete === expected.registryComplete, 'The initial registration event is inconsistent.');
    requireCheckpoint(state.events.some(event => event?.type === 'authority.revoked') === rootRevoked,
      'The retained revocation flag lacks a matching transition event.');
    requireCheckpoint(state.events.some(event => ['action.executed', 'action.denied'].includes(event?.type)) === retained.baselineDone,
      'The retained baseline flag lacks a matching execution event.');
    requireCheckpoint(state.events.some(event => event?.type === 'queue.empty') === retained.emptyReplayRecorded,
      'The retained empty-queue flag lacks a matching observation.');
    requireCheckpoint((state.queue.length === 0 || retained.baselineDone)
      && (!state.queue.some(job => job.status === 'blocked') || rootRevoked), 'The queued-operation lifecycle contradicts its authority state.');
    const expectedActions = state.queue.length ? state.queue[0].status === 'executed' ? 2 : 1 : 0;
    requireCheckpoint(state.protectedActions === expectedActions, 'The protected-action count contradicts its retained operation receipts.');
    privateState.set(state, {
      ...retained, revocations, jobs,
    });
    const audit = auditState(state);
    requireCheckpoint(audit.errors.length === 0, `The restored state fails its retained consistency checks: ${audit.errors.join(' ')}`);
    return state;
  } catch (error) {
    if (error?.code === 'INVALID_CHECKPOINT') throw error;
    throw invalidCheckpoint('The checkpoint is malformed or fails retained-state validation.');
  }
}
