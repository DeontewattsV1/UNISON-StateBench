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
// PhaseFormOrchestrator.handle_event in sources/phaseform_runtime_package_v6/)
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
  { id: "agi-cp-capability", repo: "AGI-CP", label: "Capability request framing (concept)",
    note: "AGI-CP capability-request semantics are summarised; only the evidence window stage is a code port." },
  { id: "ai-soul", repo: "AISoulFrameworkConcepts", label: "Framework concepts (concept)",
    note: "Concept document (PDF/text); no runnable code." },
];

// ---- Recognitive-field: port of flow() / injectProbe() fate classification from
// sources/Recognitive-field/recognitive-field-v3.html. Random noise is replaced by a
// seeded PRNG (mulberry32) so the result is reproducible; noise=0 gives the deterministic field.
export const RF_SCENARIOS = {
  baseline: { m: { a: .63, m: .42, g: .70, t: .28 }, ts: 0, ap: 1, dr: 0 },
  overload: { m: { a: .34, m: .84, g: .38, t: .82 }, ts: .15, ap: .68, dr: .08 },
  ritual: { m: { a: .79, m: .30, g: .88, t: .18 }, ts: -.08, ap: 1.25, dr: -.03 },
};
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const v3 = { add: (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z }), sub: (a, b) => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z }),
  mul: (a, s) => ({ x: a.x * s, y: a.y * s, z: a.z * s }), len: (v) => Math.hypot(v.x, v.y, v.z) };
const norm = (v) => { const l = v3.len(v) || 1; return { x: v.x / l, y: v.y / l, z: v.z / l }; };
const dist = (a, b) => v3.len(v3.sub(a, b));
export function mulberry32(seed) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
export function rfTurbCenter(scenario, tau = 0) {
  const sc = RF_SCENARIOS[scenario];
  return { x: clamp(.52 + sc.ts + tau * .06, .18, .88), y: clamp(.82 + Math.abs(tau) * .06, .2, .94), z: clamp(.30 - tau * .08, .12, .88) };
}
export function rfFlow(p, { scenario = "baseline", tau = 0, attr = { x: .80, y: .26, z: .80 } } = {}) {
  const sc = RF_SCENARIOS[scenario]; const M = { ...sc.m, ap: sc.ap, dr: sc.dr };
  const turb = rfTurbCenter(scenario, tau);
  const dA = dist(p, attr), dT = dist(p, turb);
  const pull = M.ap * (.92 - Math.abs(tau) * .18 + (tau > 0 ? .06 : 0));
  const base = { x: .016 + tau * .014 + M.dr, y: .004 + Math.abs(tau) * .01, z: .018 - tau * .008 };
  if (dA < .62 && dT > .36) {
    const v = v3.mul(norm(v3.sub(attr, p)), .046 * pull);
    const orb = v3.mul(norm({ x: -(p.z - attr.z), y: .018 + tau * .01, z: (p.x - attr.x) }), .022 + (1 - pull) * .005);
    return v3.add(v, orb);
  } else if (dT < .54) {
    const sw = norm({ x: (p.z - turb.z) * (1.55 + Math.abs(tau) * .35), y: (turb.y - p.y) * .62 + .08 + M.m * .03, z: -(p.x - turb.x) * (1.55 + Math.abs(tau) * .35) });
    const v = v3.mul(sw, .058 + M.t * .018); v.x += tau * .018; v.y += .005 + Math.abs(tau) * .01;
    return v;
  }
  return v3.add(base, v3.mul(norm(v3.sub(attr, p)), .014 * pull));
}
export function rfProbe(start, { scenario = "baseline", tau = 0, noise = .0045, seed = 1, steps = 200 } = {}) {
  const attr = { x: .80, y: .26, z: .80 }; const rnd = mulberry32(seed);
  let pos = { ...start };
  for (let i = 0; i < steps; i++) {
    const f = rfFlow(pos, { scenario, tau, attr });
    f.x += (rnd() - .5) * noise; f.y += (rnd() - .5) * noise; f.z += (rnd() - .5) * noise;
    pos = { x: clamp(pos.x + f.x, 0, 1), y: clamp(pos.y + f.y, 0, 1), z: clamp(pos.z + f.z, 0, 1) };
  }
  const finalDist = dist(pos, attr);
  return { final: pos, final_distance: finalDist, fate: finalDist < .28 ? "recovery" : "turbulence" };
}

// ---- celestial_agent_desktop_upgrade: port of celestial_core.py CelestialCodec,
// SafeWorkspace.resolve_safe and AgentRuntime._execute_line (in-memory workspace; HASH,
// MAKE FILE, WRITE, APPEND, READ FILE, LIST FILES). MAKE FUNCTION is not ported.
export const DESKTOP_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?\"'_-:/\n";
export async function desktopCodec(seed) {
  if (!seed) throw new Error("Seed is required.");
  const c2g = {};
  for (const ch of DESKTOP_CHARS) {
    const hex = await sha256Hex(`${seed}:${ch}`);
    c2g[ch] = String.fromCharCode(0xe000 + parseInt(hex.slice(0, 2), 16)) + String.fromCharCode(0xe000 + parseInt(hex.slice(2, 4), 16));
  }
  const g2c = Object.fromEntries(Object.entries(c2g).map(([k, v]) => [v, k]));
  return {
    encode: (t) => [...t].map((c) => c2g[c] ?? c).join(""),
    decode: (g) => { let o = "", i = 0; while (i < g.length) { const p = g.slice(i, i + 2); if (g2c[p] !== undefined) { o += g2c[p]; i += 2; } else { o += g[i]; i++; } } return o; },
  };
}
export function resolveSafe(relativePath) {
  // POSIX-style normalisation equivalent to Path(root / rel).resolve() containment check.
  if (relativePath.startsWith("/")) throw new Error("Blocked path outside workspace.");
  const parts = [];
  for (const seg of relativePath.split("/")) {
    if (seg === "" || seg === ".") continue;
    if (seg === "..") { if (!parts.length) throw new Error("Blocked path outside workspace."); parts.pop(); }
    else parts.push(seg);
  }
  return parts.join("/");
}
export async function desktopExecute(commands, files = {}) {
  const out = [];
  const patterns = [
    [/^MAKE FILE "([^"]+)"$/, (p) => { files[resolveSafe(p)] = ""; return `Created file: ${p}`; }],
    [/^WRITE "([\s\S]*)" TO "([^"]+)"$/, (c, p) => { files[resolveSafe(p)] = c; return `Wrote ${c.length} chars to ${p}`; }],
    [/^APPEND "([\s\S]*)" TO "([^"]+)"$/, (c, p) => { const k = resolveSafe(p); files[k] = (files[k] || "") + c; return `Appended ${c.length} chars to ${p}`; }],
    [/^READ FILE "([^"]+)"$/, (p) => { const k = resolveSafe(p); if (!(k in files)) throw new Error(`File not found: ${p}`); return files[k]; }],
    [/^LIST FILES$/, () => Object.keys(files).sort().join("\n") || "(workspace is empty)"],
    [/^HASH "([\s\S]*)"$/, (c) => sha256Hex(c)],
  ];
  for (const raw of commands.split("\n")) {
    const line = raw.trim(); if (!line) continue;
    const hit = patterns.find(([re]) => re.test(line));
    if (!hit) throw new Error(`Unsupported command: ${line}`);
    out.push(`> ${line}`, await hit[1](...line.match(hit[0]).slice(1)));
  }
  return { transcript: out.join("\n"), files };
}
