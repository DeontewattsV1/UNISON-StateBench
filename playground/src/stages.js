// Traceability playground stage functions.
// celestial_language port: concept and Python implementation credited to "TDD" (see source module).
// Each stage is a pure function over a JSON-serialisable trace record.
// "implemented" stages are ports of logic that exists in a source repo
// (file paths given in `source`); "concept" stages are illustrative only.

export const enc = new TextEncoder();

export function canonical(value) {
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  if (value && typeof value === "object") {
    return "{" + Object.keys(value).sort()
      .map((k) => JSON.stringify(k) + ":" + canonical(value[k])).join(",") + "}";
  }
  return JSON.stringify(value === undefined ? null : value);
}

export async function sha256Hex(input) {
  const data = typeof input === "string" ? enc.encode(input) : input;
  const buf = await globalThis.crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export const hashOf = (obj) => sha256Hex(canonical(obj));

// ---- Stage 1: claim intake (UNISON-StateBench epistemic status vocabulary)
export function intakeClaim(claim) {
  if (!claim || !claim.id || !claim.statement) throw new Error("claim requires id and statement");
  // A new claim always enters as UNKNOWN; it is never born KNOWN.
  return { ...claim, epistemic_status: "unknown", value: null };
}

// ---- Stage 2: evidence window (port of AGI-CP capability-gateway/src/auth/evidence.ts)
export function collectEvidence(window, observations) {
  const inWindow = observations.filter((o) =>
    o.requestId === window.requestId && o.observedAt >= window.start && o.observedAt <= window.end);
  return window.expectedObserverIds.map((observerId) => {
    const matches = inWindow.filter((o) => o.observerId === observerId);
    if (matches.length === 0) return { observerId, state: "UNVERIFIABLE" };
    if (matches.some((o) => o.state === "FAILED")) return { observerId, state: "FAILED", observation: matches[0] };
    if (matches.length > 1 && new Set(matches.map((m) => m.state)).size > 1)
      return { observerId, state: "CONFLICTING", observation: matches[0] };
    return { observerId, state: matches[0].state, observation: matches[0] };
  });
}
export function decideEvidence(slots) {
  if (slots.some((s) => s.state === "FAILED")) return "EVIDENCE_FAILED";
  if (slots.some((s) => s.state !== "SATISFIED")) return "EVIDENCE_UNVERIFIABLE";
  if (slots.length === 0) return "EVIDENCE_UNVERIFIABLE";
  return "ok";
}

// ---- Stage 3: requirement <-> evidence linking (traceability-matrix: concept only;
// the source repo contains an RTM document and an API scaffold, not linking code).
export function linkRequirements(requirements, evidence) {
  const rows = requirements.map((r) => {
    const linked = evidence.filter((e) => (e.covers || []).includes(r.id)).map((e) => e.id);
    return { requirement: r.id, evidence: linked, covered: linked.length > 0 };
  });
  return { rows, uncovered: rows.filter((r) => !r.covered).map((r) => r.requirement) };
}

// ---- Stage 4: governance gate (port of SOVEREIGN-LATTICE-GOVCORE
// govcore/governance/kernel.py GovernanceKernel.evaluate_operating_mode)
export const POLICY_RULES = {
  "RULE-001": { label: "CRITICAL_INFRASTRUCTURE", requires_approval: true, escalation_threshold: 0.6 },
  "RULE-002": { label: "RIGHTS_IMPACT", requires_approval: true, escalation_threshold: 0.5 },
  "RULE-003": { label: "TEMPORAL_SEPARATION", requires_approval: false, escalation_threshold: 0.75 },
  "RULE-004": { label: "PRIVACY", requires_approval: true, escalation_threshold: 0.65 },
  "RULE-005": { label: "IRREVERSIBILITY", requires_approval: true, escalation_threshold: 0.0 },
  "RULE-006": { label: "PQC_MIGRATION", requires_approval: true, escalation_threshold: 0.75 },
  "RULE-007": { label: "PROTECTED_GROUPS", requires_approval: true, escalation_threshold: 0.55 },
};
export function governanceGate(ctx, threshold = 0.75) {
  const severity = Number(ctx.impact_severity || 0);
  const reversible = ctx.is_reversible !== false;
  const labels = new Set(ctx.policy_labels || []);
  const applicable = [];
  for (const [id, r] of Object.entries(POLICY_RULES)) {
    if (labels.has(r.label)) applicable.push(id);
    if (!reversible && r.label === "IRREVERSIBILITY") applicable.push(id);
    if (ctx.affects_critical_infrastructure && r.label === "CRITICAL_INFRASTRUCTURE") applicable.push(id);
    if (ctx.affects_protected_groups && r.label === "PROTECTED_GROUPS") applicable.push(id);
  }
  const requires_approval = applicable.some((id) => POLICY_RULES[id].requires_approval) || severity >= threshold;
  let mode;
  if (!reversible || severity >= threshold || ctx.affects_critical_infrastructure) mode = "high_impact";
  else if (requires_approval) mode = "assisted";
  else if (["recommendation", "summary", "analysis"].includes(ctx.action_type || "recommendation")) mode = "advisory";
  else mode = "bounded";
  const escalation = mode === "high_impact" || applicable.some((id) => severity >= POLICY_RULES[id].escalation_threshold);
  // RULE-003 (TEMPORAL_SEPARATION): scenario outputs cannot be promoted to established fact.
  const promotion_blocked = labels.has("TEMPORAL_SEPARATION") && ctx.is_scenario_output === true;
  return { mode, requires_approval, escalation, applicable_rules: applicable,
    human_review_level: mode === "high_impact" ? "enhanced" : requires_approval ? "standard" : "none",
    promotion_blocked };
}

// ---- Stage 5: non-collapse check (port of UNISON-StateBench benchmark/state_collapse.py)
// transitions: [{id, from, to, satisfied}], expected/observed: {id: {status, value}}
export function detectStateCollapses(transitions, expected, observed) {
  const collapses = [];
  for (const t of transitions) {
    const o = observed[t.to];
    if (o && o.status === "known" && o.value === true && !t.satisfied)
      collapses.push({ kind: "unsupported_transition", invariant: t.to, boundary: t.id });
  }
  const boundaries = Object.entries(expected).filter(([, e]) => e.status === "unknown" || e.status === "absent");
  for (const [id] of boundaries.sort()) {
    if (observed[id] && observed[id].status === "known")
      collapses.push({ kind: "unknown_to_known", invariant: id, boundary: "EPISTEMIC:" + id });
  }
  const trials = transitions.length + boundaries.length;
  return { boundary_trials: trials, collapses, rate: trials ? Math.min(1, collapses.length / trials) : 0 };
}

// ---- Stage 6: phaseform runtime step (port of policy_schema.validate_phaseform_policy and
// PhaseFormOrchestrator.handle_event; public copy in Linguistic-Encryption-System-Celestial-)
export const ALLOWED_CLEARANCE = new Set(["L1", "L2", "L3", "L4_SOVEREIGN"]);
export const ALLOWED_POLICY_ACTIONS = new Set(["INITIATE_L1_HEAL", "PURGE_MEMORY_AND_HALT", "LOCK_AND_ALERT", "NO_OP"]);
export const ALLOWED_CAPABILITIES = new Set(["can_generate_code", "can_access_l3_controller", "can_reconfigure_l2", "can_bypass_leash"]);
export function validatePhaseformPolicy(spec) {
  for (const f of ["schema_version", "creator", "identity", "capabilities", "policy_logic"])
    if (!(f in spec)) throw new Error(`root missing required field: ${f}`);
  for (const f of ["role", "clearance", "project"])
    if (!(f in spec.identity)) throw new Error(`identity missing required field: ${f}`);
  if (!ALLOWED_CLEARANCE.has(spec.identity.clearance)) throw new Error("Unsupported clearance");
  for (const c of Object.keys(spec.capabilities)) if (!ALLOWED_CAPABILITIES.has(c)) throw new Error("Unknown capability " + c);
  if (spec.capabilities.can_bypass_leash === true) throw new Error("can_bypass_leash=true is not allowed");
  for (const a of Object.values(spec.policy_logic)) if (!ALLOWED_POLICY_ACTIONS.has(a)) throw new Error("Unsupported policy action " + a);
  return spec;
}
export function phaseformStep(spec, eventName) {
  validatePhaseformPolicy(spec);
  const action = spec.policy_logic[eventName] || "NO_OP";
  return { event: eventName, mapped_action: action, log: [`event_received event=${eventName} mapped_action=${action}`, `action_execute name=${action}`] };
}

// ---- Stage 7: linguistic transform (port of celestial_agent/celestial_language.py)
export const CHARSET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?-_:/";
export async function glyphMap(seed) {
  if (!seed) throw new Error("seed is required");
  const map = {}, used = new Set();
  for (const ch of CHARSET) {
    let counter = 0, glyph = null;
    while (glyph === null || used.has(glyph)) {
      const hex = await sha256Hex(`${seed}|${ch}|${counter}`);
      const bytes = hex.slice(0, 8).match(/../g).map((h) => parseInt(h, 16));
      glyph = bytes.map((b) => String.fromCharCode(0xe000 + (b >> 4)) + String.fromCharCode(0xe000 + (b & 0x0f))).join("");
      counter++;
    }
    used.add(glyph); map[ch] = glyph;
  }
  return map;
}
export function encodeMessage(map, msg) { return [...msg].map((c) => map[c] ?? c).join(""); }
export function decodeMessage(map, encoded) {
  // Every mapped glyph is exactly 8 code units; unmapped chars pass through unchanged.
  const inv = Object.fromEntries(Object.entries(map).map(([k, v]) => [v, k]));
  let out = "", i = 0;
  while (i < encoded.length) {
    const g = encoded.slice(i, i + 8);
    if (inv[g] !== undefined) { out += inv[g]; i += 8; } else { out += encoded[i]; i += 1; }
  }
  return out;
}
export function xorPad(data, key) {
  if (data.length !== key.length) throw new Error("Ciphertext and key lengths do not match");
  return data.map((b, i) => b ^ key[i]);
}

// ---- Concept stages: illustrative only, no runnable source code was ported.
export const CONCEPT_STAGES = [
  { id: "recognitive-field", repo: "Recognitive-field", label: "Recognition field (concept)",
    note: "Source repo is private and contains HTML visualisations only; shown as a labeled placeholder." },
  { id: "agi-cp-capability", repo: "AGI-CP", label: "Capability request framing (concept)",
    note: "AGI-CP capability-request semantics are summarised; only the evidence window stage is a code port." },
  { id: "ai-soul", repo: "AISoulFrameworkConcepts", label: "Framework concepts (concept)",
    note: "Concept document (PDF/text); no runnable code." },
  { id: "celestial-agent", repo: "celestial_agent_desktop_upgrade", label: "Desktop agent shell (concept)",
    note: "Source repo is private; not imported; shown as a placeholder only." },
];
