import * as S from "./stages.js";

export const SAMPLE = {
  claim: { id: "CLM-001", statement: "Mutation M reduces state-collapse rate on case S04 below 0.10.",
    requirement_ids: ["REQ-1", "REQ-2"] },
  evidence: [
    { id: "EV-1", kind: "dataset", content: "trial matrix rows 1..162 (sample)", covers: ["REQ-1"] },
    { id: "EV-2", kind: "code", content: "benchmark/state_collapse.py@HEAD", covers: ["REQ-2"] },
  ],
  observations: [
    { observerId: "verifier-a", requestId: "CLM-001", observedAt: 10, state: "SATISFIED" },
    { observerId: "verifier-b", requestId: "CLM-001", observedAt: 12, state: "SATISFIED" },
  ],
  governance: { impact_severity: 0.3, is_reversible: true, action_type: "analysis",
    policy_labels: ["TEMPORAL_SEPARATION"], is_scenario_output: false },
  noncollapse: {
    transitions: [{ id: "T1", from: "evidence_attached", to: "claim_supported", satisfied: true }],
    expected: { claim_supported: { status: "known", value: true }, replication: { status: "unknown" } },
    observed: { claim_supported: { status: "known", value: true }, replication: { status: "unknown" } },
  },
  phaseform: { schema_version: "1.0", creator: "demo", identity: { role: "verifier", clearance: "L2", project: "unison" },
    capabilities: { can_generate_code: false }, policy_logic: { tamper_detected: "LOCK_AND_ALERT", ok: "NO_OP" } },
  phaseform_event: "ok",
  seed: "unison-demo-seed",
  recognitive: { scenario: "baseline", noise: 0.0045, seed: 7 },
  desktop: { seed: "celestial-desktop-seed" },
};

export async function runPipeline(input = SAMPLE, opts = {}) {
  const steps = [];
  let prev = "0".repeat(64);
  const add = async (id, repo, kind, output, pass = true) => {
    const output_hash = await S.hashOf(output);
    const link = await S.sha256Hex(prev + output_hash);
    steps.push({ id, repo, kind, pass, output, output_hash, prev_hash: prev, link_hash: link });
    prev = link;
  };

  const claim = S.intakeClaim(input.claim);
  await add("claim-intake", "UNISON-StateBench", "implemented", claim);

  const evidence = [];
  for (const e of input.evidence) evidence.push({ ...e, sha256: await S.sha256Hex(e.content) });
  await add("evidence-attach", "UNISON-StateBench", "implemented", evidence);

  const slots = S.collectEvidence({ requestId: claim.id, start: 0, end: 100,
    expectedObserverIds: ["verifier-a", "verifier-b"] }, input.observations);
  const evDecision = S.decideEvidence(slots);
  await add("evidence-window", "AGI-CP", "implemented", { slots, decision: evDecision }, evDecision === "ok");

  const rtm = S.linkRequirements(claim.requirement_ids.map((id) => ({ id })), evidence);
  await add("traceability-link", "traceability-matrix", "concept", rtm, rtm.uncovered.length === 0);

  const gov = S.governanceGate(input.governance);
  await add("governance-gate", "SOVEREIGN-LATTICE-GOVCORE", "implemented", gov, !gov.promotion_blocked);

  const nc = S.detectStateCollapses(input.noncollapse.transitions, input.noncollapse.expected, input.noncollapse.observed);
  await add("noncollapse-check", "UNISON-StateBench", "implemented", nc, nc.collapses.length === 0);

  let pf;
  try { pf = S.phaseformStep(input.phaseform, input.phaseform_event); pf.ok = true; }
  catch (e) { pf = { ok: false, error: String(e.message) }; }
  await add("phaseform-step", "phaseform_runtime_package_v6", "implemented", pf, pf.ok);

  const map = await S.glyphMap(input.seed);
  const encoded = S.encodeMessage(map, claim.statement);
  const decoded = S.decodeMessage(map, encoded);
  const bytes = [...S.enc.encode(encoded)];
  const key = opts.key || bytes.map(() => Math.floor(Math.random() * 256));
  const ct = S.xorPad(bytes, key);
  const rt = new TextDecoder().decode(new Uint8Array(S.xorPad(ct, key)));
  const roundTrip = decoded === claim.statement && rt === encoded;
  await add("linguistic-transform", "Linguistic-Encryption-System-Celestial-", "implemented",
    { encoded_sha256: await S.sha256Hex(encoded), ciphertext_sha256: await S.sha256Hex(new Uint8Array(ct)), round_trip: roundTrip }, roundTrip);

  // Recognitive-field probe: start point derived from the claim hash. Advisory only:
  // the field is a visual dynamical model, not evidence, so it never blocks or grants promotion.
  const ch = steps[0].output_hash;
  const start = { x: parseInt(ch.slice(0, 2), 16) / 255, y: parseInt(ch.slice(2, 4), 16) / 255, z: parseInt(ch.slice(4, 6), 16) / 255 };
  const rf = input.recognitive || {};
  const probe = S.rfProbe(start, { scenario: rf.scenario || "baseline", noise: rf.noise ?? 0.0045, seed: rf.seed ?? 7 });
  await add("recognitive-field", "Recognitive-field", "implemented", { advisory: true, scenario: rf.scenario || "baseline", start, ...probe });
  steps[steps.length - 1].advisory = true;

  // Celestial desktop agent: encode a command script, decode it, run it in an in-memory workspace.
  const codec = await S.desktopCodec((input.desktop || {}).seed || "celestial-desktop-seed");
  const script = `WRITE "${evidence[0].id}" TO "trace/evidence.txt"\nHASH "${evidence[0].content}"\nLIST FILES`;
  const glyphs = codec.encode(script);
  const decodedScript = codec.decode(glyphs);
  const run = await S.desktopExecute(decodedScript, {});
  const hashOk = run.transcript.includes(evidence[0].sha256);
  let traversalBlocked = false;
  try { S.resolveSafe("../outside.txt"); } catch { traversalBlocked = true; }
  const dOk = decodedScript === script && hashOk && traversalBlocked;
  await add("celestial-agent", "celestial_agent_desktop_upgrade", "implemented",
    { glyph_script_sha256: await S.sha256Hex(glyphs), round_trip: decodedScript === script, hash_matches_evidence: hashOk, traversal_blocked: traversalBlocked, transcript: run.transcript }, dOk);

  for (const c of S.CONCEPT_STAGES) await add(c.id, c.repo, "concept", { label: c.label, note: c.note });

  const blocking = steps.filter((s) => s.kind === "implemented" && !s.advisory && !s.pass).map((s) => s.id);
  const receipt = {
    receipt_type: "claim-promotion-receipt/0.1-demo",
    claim_id: claim.id,
    from_status: "unknown",
    to_status: blocking.length === 0 ? "locally_supported" : "unknown",
    promoted: blocking.length === 0,
    blocking_steps: blocking,
    note: "Demo receipt. 'locally_supported' is not independent reproduction (see verification-promotion-boundaries).",
    chain_head: prev,
    steps: steps.map((s) => ({ id: s.id, kind: s.kind, pass: s.pass, link_hash: s.link_hash })),
  };
  return { steps, receipt };
}

export async function verifyChain(steps) {
  let prev = "0".repeat(64);
  for (const s of steps) {
    if (s.prev_hash !== prev) return false;
    if ((await S.hashOf(s.output)) !== s.output_hash) return false;
    if ((await S.sha256Hex(prev + s.output_hash)) !== s.link_hash) return false;
    prev = s.link_hash;
  }
  return true;
}
