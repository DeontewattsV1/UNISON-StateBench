// Traceability playground stage functions.
// Each stage is a pure function over a JSON-serialisable trace record.
// "implemented" stages are ports of logic that exists in a source repo.
// "concept" stages are illustrative only.

export const enc = new TextEncoder();

export function canonical(value: unknown): string {
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  if (value && typeof value === "object") {
    const obj = value as Record<string, unknown>;
    return (
      "{" +
      Object.keys(obj)
        .sort()
        .map((k) => JSON.stringify(k) + ":" + canonical(obj[k]))
        .join(",") +
      "}"
    );
  }
  return JSON.stringify(value === undefined ? null : value);
}

export async function sha256Hex(input: string | BufferSource): Promise<string> {
  const data = typeof input === "string" ? enc.encode(input) : input;
  const buf = await globalThis.crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export const hashOf = (obj: unknown) => sha256Hex(canonical(obj));

export type ClaimInput = {
  id?: string;
  statement?: string;
  epistemic_status?: string;
  value?: unknown;
  requirement_ids?: string[];
};

export function intakeClaim(
  claim: ClaimInput,
): ClaimInput & { id: string; statement: string; epistemic_status: "unknown"; value: null } {
  if (!claim || !claim.id || !claim.statement) throw new Error("claim requires id and statement");
  return { ...claim, id: claim.id, statement: claim.statement, epistemic_status: "unknown", value: null };
}

export type Observation = {
  observerId: string;
  requestId: string;
  observedAt: number;
  state: string;
};

export type EvidenceWindow = {
  requestId: string;
  start: number;
  end: number;
  expectedObserverIds: string[];
};

export function collectEvidence(window: EvidenceWindow, observations: Observation[]) {
  const inWindow = observations.filter(
    (o) => o.requestId === window.requestId && o.observedAt >= window.start && o.observedAt <= window.end,
  );
  return window.expectedObserverIds.map((observerId) => {
    const matches = inWindow.filter((o) => o.observerId === observerId);
    if (matches.length === 0) return { observerId, state: "UNVERIFIABLE" as const };
    if (matches.some((o) => o.state === "FAILED"))
      return { observerId, state: "FAILED" as const, observation: matches[0] };
    if (matches.length > 1 && new Set(matches.map((m) => m.state)).size > 1)
      return { observerId, state: "CONFLICTING" as const, observation: matches[0] };
    return { observerId, state: matches[0].state, observation: matches[0] };
  });
}

export function decideEvidence(slots: { state: string }[]) {
  if (slots.some((s) => s.state === "FAILED")) return "EVIDENCE_FAILED";
  if (slots.some((s) => s.state !== "SATISFIED")) return "EVIDENCE_UNVERIFIABLE";
  if (slots.length === 0) return "EVIDENCE_UNVERIFIABLE";
  return "ok";
}

export function linkRequirements(
  requirements: { id: string }[],
  evidence: { id: string; covers?: string[] }[],
) {
  const rows = requirements.map((r) => {
    const linked = evidence.filter((e) => (e.covers || []).includes(r.id)).map((e) => e.id);
    return { requirement: r.id, evidence: linked, covered: linked.length > 0 };
  });
  return { rows, uncovered: rows.filter((r) => !r.covered).map((r) => r.requirement) };
}

export const POLICY_RULES = {
  "RULE-001": { label: "CRITICAL_INFRASTRUCTURE", requires_approval: true, escalation_threshold: 0.6 },
  "RULE-002": { label: "RIGHTS_IMPACT", requires_approval: true, escalation_threshold: 0.5 },
  "RULE-003": { label: "TEMPORAL_SEPARATION", requires_approval: false, escalation_threshold: 0.75 },
  "RULE-004": { label: "PRIVACY", requires_approval: true, escalation_threshold: 0.65 },
  "RULE-005": { label: "IRREVERSIBILITY", requires_approval: true, escalation_threshold: 0.0 },
  "RULE-006": { label: "PQC_MIGRATION", requires_approval: true, escalation_threshold: 0.75 },
  "RULE-007": { label: "PROTECTED_GROUPS", requires_approval: true, escalation_threshold: 0.55 },
} as const;

export type GovCtx = {
  impact_severity?: number;
  is_reversible?: boolean;
  policy_labels?: string[];
  affects_critical_infrastructure?: boolean;
  affects_protected_groups?: boolean;
  action_type?: string;
  is_scenario_output?: boolean;
};

export function governanceGate(ctx: GovCtx, threshold = 0.75) {
  const severity = Number(ctx.impact_severity || 0);
  const reversible = ctx.is_reversible !== false;
  const labels = new Set(ctx.policy_labels || []);
  const applicable: string[] = [];
  for (const [id, r] of Object.entries(POLICY_RULES)) {
    if (labels.has(r.label)) applicable.push(id);
    if (!reversible && r.label === "IRREVERSIBILITY") applicable.push(id);
    if (ctx.affects_critical_infrastructure && r.label === "CRITICAL_INFRASTRUCTURE") applicable.push(id);
    if (ctx.affects_protected_groups && r.label === "PROTECTED_GROUPS") applicable.push(id);
  }
  const requires_approval =
    applicable.some((id) => POLICY_RULES[id as keyof typeof POLICY_RULES].requires_approval) ||
    severity >= threshold;
  let mode: "high_impact" | "assisted" | "advisory" | "bounded";
  if (!reversible || severity >= threshold || ctx.affects_critical_infrastructure) mode = "high_impact";
  else if (requires_approval) mode = "assisted";
  else if (["recommendation", "summary", "analysis"].includes(ctx.action_type || "recommendation"))
    mode = "advisory";
  else mode = "bounded";
  const escalation =
    mode === "high_impact" ||
    applicable.some(
      (id) => severity >= POLICY_RULES[id as keyof typeof POLICY_RULES].escalation_threshold,
    );
  const promotion_blocked = labels.has("TEMPORAL_SEPARATION") && ctx.is_scenario_output === true;
  return {
    mode,
    requires_approval,
    escalation,
    applicable_rules: applicable,
    human_review_level: mode === "high_impact" ? "enhanced" : requires_approval ? "standard" : "none",
    promotion_blocked,
  };
}

export type CollapseTransition = { id: string; from?: string; to: string; satisfied: boolean };
export type EpistemicSlot = { status: string; value?: unknown };

export function detectStateCollapses(
  transitions: CollapseTransition[],
  expected: Record<string, EpistemicSlot>,
  observed: Record<string, EpistemicSlot>,
) {
  const collapses: { kind: string; invariant: string; boundary: string }[] = [];
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

export const ALLOWED_CLEARANCE = new Set(["L1", "L2", "L3", "L4_SOVEREIGN"]);
export const ALLOWED_POLICY_ACTIONS = new Set([
  "INITIATE_L1_HEAL",
  "PURGE_MEMORY_AND_HALT",
  "LOCK_AND_ALERT",
  "NO_OP",
]);
export const ALLOWED_CAPABILITIES = new Set([
  "can_generate_code",
  "can_access_l3_controller",
  "can_reconfigure_l2",
  "can_bypass_leash",
]);

export type PhaseformSpec = {
  schema_version?: string;
  creator?: string;
  identity: { role?: string; clearance: string; project?: string };
  capabilities: Record<string, boolean>;
  policy_logic: Record<string, string>;
};

export function validatePhaseformPolicy(spec: PhaseformSpec) {
  for (const f of ["schema_version", "creator", "identity", "capabilities", "policy_logic"] as const)
    if (!(f in spec)) throw new Error(`root missing required field: ${f}`);
  for (const f of ["role", "clearance", "project"] as const)
    if (!(f in spec.identity)) throw new Error(`identity missing required field: ${f}`);
  if (!ALLOWED_CLEARANCE.has(spec.identity.clearance)) throw new Error("Unsupported clearance");
  for (const c of Object.keys(spec.capabilities))
    if (!ALLOWED_CAPABILITIES.has(c)) throw new Error("Unknown capability " + c);
  if (spec.capabilities.can_bypass_leash === true) throw new Error("can_bypass_leash=true is not allowed");
  for (const a of Object.values(spec.policy_logic))
    if (!ALLOWED_POLICY_ACTIONS.has(a)) throw new Error("Unsupported policy action " + a);
  return spec;
}

export function phaseformStep(spec: PhaseformSpec, eventName: string) {
  validatePhaseformPolicy(spec);
  const action = spec.policy_logic[eventName] || "NO_OP";
  return {
    event: eventName,
    mapped_action: action,
    log: [`event_received event=${eventName} mapped_action=${action}`, `action_execute name=${action}`],
  };
}

export const CHARSET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?-_:/";

export async function glyphMap(seed: string): Promise<Record<string, string>> {
  if (!seed) throw new Error("seed is required");
  const map: Record<string, string> = {};
  const used = new Set<string>();
  for (const ch of CHARSET) {
    let counter = 0;
    let glyph: string | null = null;
    while (glyph === null || used.has(glyph)) {
      const hex = await sha256Hex(`${seed}|${ch}|${counter}`);
      const pairs = hex.slice(0, 8).match(/../g);
      if (!pairs) throw new Error("hash slice failed");
      const bytes = pairs.map((h) => parseInt(h, 16));
      glyph = bytes
        .map((b) => String.fromCharCode(0xe000 + (b >> 4)) + String.fromCharCode(0xe000 + (b & 0x0f)))
        .join("");
      counter++;
    }
    used.add(glyph);
    map[ch] = glyph;
  }
  return map;
}

export function encodeMessage(map: Record<string, string>, msg: string) {
  return [...msg].map((c) => map[c] ?? c).join("");
}

export function decodeMessage(map: Record<string, string>, encoded: string) {
  const inv = Object.fromEntries(Object.entries(map).map(([k, v]) => [v, k]));
  let out = "";
  let i = 0;
  while (i < encoded.length) {
    const g = encoded.slice(i, i + 8);
    if (inv[g] !== undefined) {
      out += inv[g];
      i += 8;
    } else {
      out += encoded[i];
      i += 1;
    }
  }
  return out;
}

export function xorPad(data: number[], key: number[]) {
  if (data.length !== key.length) throw new Error("Ciphertext and key lengths do not match");
  return data.map((b, i) => (b ^ key[i]) >>> 0);
}

export const CONCEPT_STAGES = [
  {
    id: "agi-cp-capability",
    repo: "AGI-CP",
    label: "Capability request framing (concept)",
    note: "AGI-CP capability-request semantics are summarised; only the evidence window stage is a code port.",
  },
  {
    id: "ai-soul",
    repo: "AISoulFrameworkConcepts",
    label: "Framework concepts (concept)",
    note: "Concept document (PDF/text); no runnable code.",
  },
] as const;

export const RF_SCENARIOS = {
  baseline: { m: { a: 0.63, m: 0.42, g: 0.7, t: 0.28 }, ts: 0, ap: 1, dr: 0 },
  overload: { m: { a: 0.34, m: 0.84, g: 0.38, t: 0.82 }, ts: 0.15, ap: 0.68, dr: 0.08 },
  ritual: { m: { a: 0.79, m: 0.3, g: 0.88, t: 0.18 }, ts: -0.08, ap: 1.25, dr: -0.03 },
} as const;

export type Vec3 = { x: number; y: number; z: number };

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));
const v3 = {
  add: (a: Vec3, b: Vec3): Vec3 => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z }),
  sub: (a: Vec3, b: Vec3): Vec3 => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z }),
  mul: (a: Vec3, s: number): Vec3 => ({ x: a.x * s, y: a.y * s, z: a.z * s }),
  len: (v: Vec3) => Math.hypot(v.x, v.y, v.z),
};
const norm = (v: Vec3): Vec3 => {
  const l = v3.len(v) || 1;
  return { x: v.x / l, y: v.y / l, z: v.z / l };
};
const dist = (a: Vec3, b: Vec3) => v3.len(v3.sub(a, b));

export function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function rfTurbCenter(scenario: string, tau = 0): Vec3 {
  const sc = RF_SCENARIOS[scenario as keyof typeof RF_SCENARIOS] ?? RF_SCENARIOS.baseline;
  return {
    x: clamp(0.52 + sc.ts + tau * 0.06, 0.18, 0.88),
    y: clamp(0.82 + Math.abs(tau) * 0.06, 0.2, 0.94),
    z: clamp(0.3 - tau * 0.08, 0.12, 0.88),
  };
}

export function rfFlow(
  p: Vec3,
  { scenario = "baseline", tau = 0, attr = { x: 0.8, y: 0.26, z: 0.8 } }: { scenario?: string; tau?: number; attr?: Vec3 } = {},
): Vec3 {
  const sc = RF_SCENARIOS[scenario as keyof typeof RF_SCENARIOS] ?? RF_SCENARIOS.baseline;
  const M = { ...sc.m, ap: sc.ap, dr: sc.dr };
  const turb = rfTurbCenter(scenario, tau);
  const dA = dist(p, attr);
  const dT = dist(p, turb);
  const pull = M.ap * (0.92 - Math.abs(tau) * 0.18 + (tau > 0 ? 0.06 : 0));
  const base = { x: 0.016 + tau * 0.014 + M.dr, y: 0.004 + Math.abs(tau) * 0.01, z: 0.018 - tau * 0.008 };
  if (dA < 0.62 && dT > 0.36) {
    const v = v3.mul(norm(v3.sub(attr, p)), 0.046 * pull);
    const orb = v3.mul(
      norm({ x: -(p.z - attr.z), y: 0.018 + tau * 0.01, z: p.x - attr.x }),
      0.022 + (1 - pull) * 0.005,
    );
    return v3.add(v, orb);
  } else if (dT < 0.54) {
    const sw = norm({
      x: (p.z - turb.z) * (1.55 + Math.abs(tau) * 0.35),
      y: (turb.y - p.y) * 0.62 + 0.08 + M.m * 0.03,
      z: -(p.x - turb.x) * (1.55 + Math.abs(tau) * 0.35),
    });
    const v = v3.mul(sw, 0.058 + M.t * 0.018);
    v.x += tau * 0.018;
    v.y += 0.005 + Math.abs(tau) * 0.01;
    return v;
  }
  return v3.add(base, v3.mul(norm(v3.sub(attr, p)), 0.014 * pull));
}

export type ProbeOpts = { scenario?: string; tau?: number; noise?: number; seed?: number; steps?: number };

function rfIntegrate(start: Vec3, opts: ProbeOpts = {}) {
  const scenario = opts.scenario ?? "baseline";
  const tau = opts.tau ?? 0;
  const noise = opts.noise ?? 0.0045;
  const seed = opts.seed ?? 1;
  const steps = opts.steps ?? 200;
  const attr = { x: 0.8, y: 0.26, z: 0.8 };
  const rnd = mulberry32(seed);
  let pos = { ...start };
  const trail: Vec3[] = [{ ...pos }];
  for (let i = 0; i < steps; i++) {
    const f = rfFlow(pos, { scenario, tau, attr });
    f.x += (rnd() - 0.5) * noise;
    f.y += (rnd() - 0.5) * noise;
    f.z += (rnd() - 0.5) * noise;
    pos = {
      x: clamp(pos.x + f.x, 0, 1),
      y: clamp(pos.y + f.y, 0, 1),
      z: clamp(pos.z + f.z, 0, 1),
    };
    trail.push({ ...pos });
  }
  const finalDist = dist(pos, attr);
  return {
    final: pos,
    final_distance: finalDist,
    fate: finalDist < 0.28 ? ("recovery" as const) : ("turbulence" as const),
    trail,
  };
}

export function rfProbe(start: Vec3, opts?: ProbeOpts) {
  const { trail: _trail, ...rest } = rfIntegrate(start, opts);
  return rest;
}

export function rfProbeTrace(start: Vec3, opts?: ProbeOpts) {
  return rfIntegrate(start, opts);
}

export const DESKTOP_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?\"'_-:/\n";

export async function desktopCodec(seed: string) {
  if (!seed) throw new Error("Seed is required.");
  const c2g: Record<string, string> = {};
  for (const ch of DESKTOP_CHARS) {
    const hex = await sha256Hex(`${seed}:${ch}`);
    c2g[ch] =
      String.fromCharCode(0xe000 + parseInt(hex.slice(0, 2), 16)) +
      String.fromCharCode(0xe000 + parseInt(hex.slice(2, 4), 16));
  }
  const g2c = Object.fromEntries(Object.entries(c2g).map(([k, v]) => [v, k]));
  return {
    encode: (t: string) => [...t].map((c) => c2g[c] ?? c).join(""),
    decode: (g: string) => {
      let o = "";
      let i = 0;
      while (i < g.length) {
        const p = g.slice(i, i + 2);
        if (g2c[p] !== undefined) {
          o += g2c[p];
          i += 2;
        } else {
          o += g[i];
          i++;
        }
      }
      return o;
    },
  };
}

export function resolveSafe(relativePath: string) {
  if (relativePath.startsWith("/")) throw new Error("Blocked path outside workspace.");
  const parts: string[] = [];
  for (const seg of relativePath.split("/")) {
    if (seg === "" || seg === ".") continue;
    if (seg === "..") {
      if (!parts.length) throw new Error("Blocked path outside workspace.");
      parts.pop();
    } else parts.push(seg);
  }
  return parts.join("/");
}

export async function desktopExecute(commands: string, files: Record<string, string> = {}) {
  const out: string[] = [];
  const patterns: Array<[RegExp, (...args: string[]) => string | Promise<string>]> = [
    [
      /^MAKE FILE "([^"]+)"$/,
      (p) => {
        files[resolveSafe(p)] = "";
        return `Created file: ${p}`;
      },
    ],
    [
      /^WRITE "([\s\S]*)" TO "([^"]+)"$/,
      (c, p) => {
        files[resolveSafe(p)] = c;
        return `Wrote ${c.length} chars to ${p}`;
      },
    ],
    [
      /^APPEND "([\s\S]*)" TO "([^"]+)"$/,
      (c, p) => {
        const k = resolveSafe(p);
        files[k] = (files[k] || "") + c;
        return `Appended ${c.length} chars to ${p}`;
      },
    ],
    [
      /^READ FILE "([^"]+)"$/,
      (p) => {
        const k = resolveSafe(p);
        if (!(k in files)) throw new Error(`File not found: ${p}`);
        return files[k];
      },
    ],
    [/^LIST FILES$/, () => Object.keys(files).sort().join("\n") || "(workspace is empty)"],
    [/^HASH "([\s\S]*)"$/, (c) => sha256Hex(c)],
  ];
  for (const raw of commands.split("\n")) {
    const line = raw.trim();
    if (!line) continue;
    const hit = patterns.find(([re]) => re.test(line));
    if (!hit) throw new Error(`Unsupported command: ${line}`);
    const matched = line.match(hit[0]);
    out.push(`> ${line}`, await hit[1](...(matched ? matched.slice(1) : [])));
  }
  return { transcript: out.join("\n"), files };
}
