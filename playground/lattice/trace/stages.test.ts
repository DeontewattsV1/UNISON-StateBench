import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import * as S from "./stages.ts";
import { SAMPLE, runPipeline, verifyChain } from "./pipeline.ts";

test("canonical JSON is key-order independent", async () => {
  assert.equal(await S.hashOf({ a: 1, b: 2 }), await S.hashOf({ b: 2, a: 1 }));
});

test("claim intake forces unknown status", () => {
  const c = S.intakeClaim({ id: "x", statement: "s", epistemic_status: "known", value: true });
  assert.equal(c.epistemic_status, "unknown");
  assert.equal(c.value, null);
  assert.throws(() => S.intakeClaim({ id: "x" }));
});

test("AGI-CP evidence window semantics", () => {
  const w = { requestId: "r", start: 0, end: 10, expectedObserverIds: ["a", "b"] };
  assert.equal(
    S.decideEvidence(
      S.collectEvidence(w, [
        { observerId: "a", requestId: "r", observedAt: 1, state: "SATISFIED" },
        { observerId: "b", requestId: "r", observedAt: 2, state: "SATISFIED" },
      ]),
    ),
    "ok",
  );
  assert.equal(
    S.decideEvidence(
      S.collectEvidence(w, [{ observerId: "a", requestId: "r", observedAt: 1, state: "SATISFIED" }]),
    ),
    "EVIDENCE_UNVERIFIABLE",
  );
  assert.equal(
    S.decideEvidence(
      S.collectEvidence(w, [
        { observerId: "a", requestId: "r", observedAt: 1, state: "FAILED" },
        { observerId: "b", requestId: "r", observedAt: 2, state: "SATISFIED" },
      ]),
    ),
    "EVIDENCE_FAILED",
  );
  assert.equal(
    S.decideEvidence(
      S.collectEvidence(w, [
        { observerId: "a", requestId: "r", observedAt: 99, state: "SATISFIED" },
        { observerId: "b", requestId: "r", observedAt: 2, state: "SATISFIED" },
      ]),
    ),
    "EVIDENCE_UNVERIFIABLE",
  );
  assert.equal(S.decideEvidence([]), "EVIDENCE_UNVERIFIABLE");
});

test("requirement linking reports uncovered requirements", () => {
  const r = S.linkRequirements([{ id: "R1" }, { id: "R2" }], [{ id: "E", covers: ["R1"] }]);
  assert.deepEqual(r.uncovered, ["R2"]);
});

test("GovCore gate mirrors kernel.py modes", () => {
  assert.equal(S.governanceGate({ impact_severity: 0.1, action_type: "analysis" }).mode, "advisory");
  assert.equal(S.governanceGate({ impact_severity: 0.1, action_type: "deploy" }).mode, "bounded");
  assert.equal(S.governanceGate({ impact_severity: 0.1, policy_labels: ["PRIVACY"] }).mode, "assisted");
  const hi = S.governanceGate({ impact_severity: 0.1, is_reversible: false });
  assert.equal(hi.mode, "high_impact");
  assert.ok(hi.applicable_rules.includes("RULE-005"));
  assert.equal(hi.human_review_level, "enhanced");
  assert.equal(S.governanceGate({ impact_severity: 0.9 }).mode, "high_impact");
  assert.equal(
    S.governanceGate({ policy_labels: ["TEMPORAL_SEPARATION"], is_scenario_output: true }).promotion_blocked,
    true,
  );
});

test("UNISON non-collapse detection", () => {
  const ok = S.detectStateCollapses(
    [{ id: "T", to: "x", satisfied: true }],
    { y: { status: "unknown" } },
    { x: { status: "known", value: true }, y: { status: "unknown" } },
  );
  assert.equal(ok.collapses.length, 0);
  assert.equal(ok.boundary_trials, 2);
  const bad = S.detectStateCollapses(
    [{ id: "T", to: "x", satisfied: false }],
    { y: { status: "unknown" } },
    { x: { status: "known", value: true }, y: { status: "known", value: false } },
  );
  assert.deepEqual(
    bad.collapses.map((c) => c.kind),
    ["unsupported_transition", "unknown_to_known"],
  );
  assert.equal(bad.rate, 1);
});

test("phaseform policy validation and event mapping", () => {
  const p = structuredClone(SAMPLE.phaseform);
  assert.equal(S.phaseformStep(p, "tamper_detected").mapped_action, "LOCK_AND_ALERT");
  assert.equal(S.phaseformStep(p, "unmapped").mapped_action, "NO_OP");
  assert.throws(() => S.validatePhaseformPolicy({ ...p, capabilities: { can_bypass_leash: true } }));
  assert.throws(() => S.validatePhaseformPolicy({ ...p, identity: { ...p.identity, clearance: "L9" } }));
  assert.throws(() => S.validatePhaseformPolicy({ ...p, policy_logic: { e: "RM_RF" } }));
});

test("celestial glyph encoding matches the Python reference byte-for-byte", async () => {
  const fx = JSON.parse(fs.readFileSync(new URL("./fixtures/celestial_fixture.json", import.meta.url), "utf8")) as {
    seed: string;
    msg: string;
    encoded: string;
  };
  const map = await S.glyphMap(fx.seed);
  const encoded = S.encodeMessage(map, fx.msg);
  assert.equal(encoded, fx.encoded);
  assert.equal(S.decodeMessage(map, encoded), fx.msg);
  const data = [1, 2, 3];
  const key = [9, 8, 7];
  assert.deepEqual(S.xorPad(S.xorPad(data, key), key), data);
  assert.throws(() => S.xorPad([1], [1, 2]));
});

test("full pipeline promotes sample and chain verifies; tampering breaks it", async () => {
  const { steps, receipt } = await runPipeline(SAMPLE);
  assert.equal(receipt.promoted, true);
  assert.equal(steps.length, 12);
  assert.ok(await verifyChain(steps));
  steps[3].output = { tampered: true };
  assert.equal(await verifyChain(steps), false);
});

test("pipeline is reproducible", async () => {
  const a = await runPipeline(SAMPLE);
  const b = await runPipeline(SAMPLE);
  assert.equal(a.receipt.chain_head, b.receipt.chain_head);
});

test("pipeline blocks promotion on collapse", async () => {
  const input = structuredClone(SAMPLE);
  Object.assign(input.noncollapse.observed.replication, { status: "known", value: true });
  const { receipt } = await runPipeline(input);
  assert.equal(receipt.promoted, false);
  assert.deepEqual(receipt.blocking_steps, ["noncollapse-check"]);
});

test("Recognitive-field probe port: deterministic and scenario-sensitive", () => {
  const near = S.rfProbe({ x: 0.78, y: 0.28, z: 0.78 }, { noise: 0 });
  assert.equal(near.fate, "recovery");
  const a = S.rfProbe({ x: 0.3, y: 0.3, z: 0.3 }, { seed: 5 });
  const b = S.rfProbe({ x: 0.3, y: 0.3, z: 0.3 }, { seed: 5 });
  assert.deepEqual(a, b);
  const t = S.rfTurbCenter("baseline");
  assert.equal(S.rfProbe(t, { scenario: "overload", noise: 0 }).fate, "turbulence");
});

test("celestial desktop codec matches Python CelestialCodec byte-for-byte", async () => {
  const fx = JSON.parse(fs.readFileSync(new URL("./fixtures/desktop_fixture.json", import.meta.url), "utf8")) as {
    seed: string;
    msg: string;
    encoded: string;
  };
  const c = await S.desktopCodec(fx.seed);
  assert.equal(c.encode(fx.msg), fx.encoded);
  assert.equal(c.decode(fx.encoded), fx.msg);
});

test("celestial desktop runtime commands and workspace containment", async () => {
  const r = await S.desktopExecute(
    'MAKE FILE "a.txt"\nAPPEND "hi" TO "a.txt"\nREAD FILE "a.txt"\nHASH "hi"\nLIST FILES',
    {},
  );
  assert.match(r.transcript, /\nhi\n/);
  assert.match(r.transcript, new RegExp(await S.sha256Hex("hi")));
  await assert.rejects(S.desktopExecute('WRITE "x" TO "../escape.txt"', {}));
  await assert.rejects(S.desktopExecute("RM -RF", {}));
  assert.equal(S.resolveSafe("a/../b.txt"), "b.txt");
});

test("recognitive-field stage is advisory and never blocks promotion", async () => {
  const input = structuredClone(SAMPLE);
  input.recognitive = { scenario: "overload", noise: 0, seed: 1 };
  const { steps, receipt } = await runPipeline(input);
  assert.ok(steps.find((s) => s.id === "recognitive-field")?.advisory);
  assert.equal(receipt.promoted, true);
});
