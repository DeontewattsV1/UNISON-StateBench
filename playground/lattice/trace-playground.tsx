import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import clsx from "clsx";
import { Play, RotateCcw, Unlink } from "lucide-react";
import { rfProbeTrace, rfTurbCenter, type Vec3 } from "@/lib/trace/stages";
import {
  SAMPLE,
  runPipeline,
  verifyChainDetail,
  type Receipt,
  type Sample,
  type TraceResult,
  type TraceStep,
} from "@/lib/trace/pipeline";
import { STATIONS, type Station } from "@/lib/trace/stations";

type Geom = {
  w: number;
  h: number;
  pts: { x: number; y: number; tokenX: number; tokenY: number }[];
};

type StationState = "idle" | "pass" | "fail" | "concept" | "advisory" | "tamper" | "untrusted";

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

export function TracePlayground() {
  const [draft, setDraft] = useState<Sample>(() => structuredClone(SAMPLE));
  const [run, setRun] = useState<TraceResult | null>(null);
  const [chainOk, setChainOk] = useState<boolean | null>(null);
  const [breakAt, setBreakAt] = useState<number | null>(null);
  const [tampered, setTampered] = useState(false);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [selected, setSelected] = useState(0);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [applied, setApplied] = useState(() => JSON.stringify(SAMPLE));
  const [ledger, setLedger] = useState("");
  const [ledgerError, setLedgerError] = useState<string | null>(null);
  const [geom, setGeom] = useState<Geom | null>(null);

  const floorRef = useRef<HTMLDivElement>(null);
  const btnRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const timer = useRef<number | null>(null);
  const gen = useRef(0);

  const stop = useCallback(() => {
    if (timer.current != null) {
      window.clearInterval(timer.current);
      timer.current = null;
    }
  }, []);

  const play = useCallback(
    (n: number) => {
      stop();
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (reduce || n <= 1) {
        setCursor(Math.max(0, n - 1));
        setPlaying(false);
        return;
      }
      setPlaying(true);
      setCursor(0);
      let i = 0;
      timer.current = window.setInterval(() => {
        i += 1;
        if (i >= n) {
          stop();
          setPlaying(false);
          setCursor(n - 1);
          return;
        }
        setCursor(i);
      }, 170);
    },
    [stop],
  );

  const execute = useCallback(
    async (input: Sample) => {
      const id = ++gen.current;
      stop();
      setPlaying(false);
      setBusy(true);
      setError(null);
      setTampered(false);
      setBreakAt(null);
      try {
        const result = await runPipeline(structuredClone(input));
        if (gen.current !== id) return;
        const detail = await verifyChainDetail(result.steps);
        if (gen.current !== id) return;
        setRun(result);
        setChainOk(detail.ok);
        setBreakAt(detail.brokenAt);
        setApplied(JSON.stringify(input));
        setBusy(false);
        play(result.steps.length);
      } catch (e) {
        if (gen.current !== id) return;
        setBusy(false);
        setPlaying(false);
        setError(e instanceof Error ? e.message : "Trace failed");
      }
    },
    [play, stop],
  );

  useEffect(() => {
    void execute(structuredClone(SAMPLE));
    return () => {
      gen.current += 1;
      stop();
    };
  }, [execute, stop]);

  const measure = useCallback(() => {
    const floor = floorRef.current;
    if (!floor) return;
    const fr = floor.getBoundingClientRect();
    const pts = STATIONS.map((_, i) => {
      const el = btnRefs.current[i];
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return {
        x: r.left - fr.left + r.width / 2,
        y: r.top - fr.top + r.height / 2,
        tokenX: r.left - fr.left + r.width / 2,
        tokenY: r.top - fr.top,
      };
    });
    if (pts.some((p) => !p) || fr.width === 0) return;
    setGeom({ w: fr.width, h: fr.height, pts: pts as Geom["pts"] });
  }, []);

  useEffect(() => {
    measure();
    const floor = floorRef.current;
    if (!floor) return;
    const ro = new ResizeObserver(() => measure());
    ro.observe(floor);
    document.fonts?.ready.then(() => measure()).catch(() => undefined);
    return () => ro.disconnect();
  }, [measure]);

  async function tamper() {
    if (!run || tampered) return;
    const id = ++gen.current;
    stop();
    setPlaying(false);
    const steps = run.steps.map((step, i) => (i === 2 ? { ...step, output: { tampered: true } } : step));
    const detail = await verifyChainDetail(steps);
    if (gen.current !== id) return;
    setRun({ ...run, steps });
    setChainOk(detail.ok);
    setBreakAt(detail.brokenAt);
    setTampered(true);
    setCursor(steps.length - 1);
    setSelected(detail.brokenAt ?? 2);
  }

  function reset() {
    const fresh = structuredClone(SAMPLE);
    setDraft(fresh);
    setLedger(JSON.stringify(fresh, null, 2));
    setLedgerError(null);
    setSelected(0);
    void execute(fresh);
  }

  const ranSample = useMemo(() => {
    try {
      return JSON.parse(applied) as Sample;
    } catch {
      return SAMPLE;
    }
  }, [applied]);
  const dirty = JSON.stringify(draft) !== applied;
  const station = STATIONS[selected];
  const step = run?.steps[selected];
  const chainLabel = busy && !run ? "Arming" : playing ? "Tracing" : chainOk === false ? "Broken" : chainOk ? "Valid" : "—";
  const claimLabel = !run ? "Unknown" : run.receipt.promoted ? "Supported" : "Held";

  function stateFor(index: number, current: TraceStep | undefined): StationState {
    if (!run || !current) return "idle";
    if (playing && index > cursor) return "idle";
    if (tampered && breakAt !== null && index === breakAt) return "tamper";
    if (tampered && breakAt !== null && index > breakAt) return "untrusted";
    if (STATIONS[index].kind === "concept") return "concept";
    if (current.advisory) return current.pass ? "advisory" : "fail";
    if (!current.pass) return "fail";
    return "pass";
  }

  function segKind(index: number) {
    if (!run) return "wait";
    if (breakAt !== null && index + 1 === breakAt) return "cut";
    if (playing && index >= cursor) return "wait";
    if (breakAt !== null && index + 1 > breakAt) return "dim";
    return "live";
  }

  const token = geom?.pts[Math.min(cursor, geom.pts.length - 1)];

  return (
    <main className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 px-4 py-5 md:px-8 md:py-8">
      <header className="flex flex-col gap-5">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex items-center gap-3">
            <img src="/favicon.svg" alt="" width={36} height={36} className="size-9" />
            <div>
              <p className="kicker">UNISON</p>
              <h1 className="display text-4xl">Trace</h1>
            </div>
          </div>
          <div className="flex gap-6">
            <Readout kicker="Chain" value={chainLabel} hot={chainOk === false ? "fail" : chainOk ? "signal" : "bone"} />
            <Readout kicker="Claim" value={claimLabel} hot={run?.receipt.promoted ? "signal" : "amber"} />
          </div>
        </div>
        <p className="max-w-2xl text-sm text-pretty text-muted">
          Twelve agents. One claim. It enters as unknown. Each stage hashes canonical JSON with SHA-256 and
          chains that digest to the step before it. Tamper with one output and verification fails closed.
        </p>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void execute(draft)}>
            <Play className="size-4" aria-hidden="true" />
            Run trace
          </button>
          <button type="button" className="btn" disabled={busy} onClick={reset}>
            <RotateCcw className="size-4" aria-hidden="true" />
            Reset
          </button>
          <button type="button" className="btn btn-danger" disabled={!run || busy || playing || tampered} onClick={() => void tamper()}>
            <Unlink className="size-4" aria-hidden="true" />
            Tamper
          </button>
          {dirty && !busy ? <span className="self-center text-sm text-amber">Input changed</span> : null}
        </div>
        {error ? <p className="text-sm text-fail">{error}</p> : null}
        <p className="sr-only" aria-live="polite" id="chain-status">
          Chain {chainLabel}. Claim {claimLabel}.
          {station ? ` Selected ${station.label}.` : ""}
        </p>
      </header>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.45fr)_minmax(18rem,0.8fr)]">
        <section className="lattice" aria-labelledby="floor-title">
          <div className="mb-3 flex items-baseline justify-between gap-3">
            <h2 id="floor-title" className="kicker">
              Lattice
            </h2>
            <p className="text-xs text-muted">Diamond is the claim token</p>
          </div>
          <div className="floor-grid" ref={floorRef}>
            {geom ? (
              <svg className="rails" width={geom.w} height={geom.h} aria-hidden="true">
                {geom.pts.slice(0, -1).map((pt, i) => {
                  const next = geom.pts[i + 1];
                  return (
                    <line
                      key={STATIONS[i].id}
                      x1={pt.x}
                      y1={pt.y}
                      x2={next.x}
                      y2={next.y}
                      className={segKind(i)}
                    />
                  );
                })}
              </svg>
            ) : null}
            {token ? <span className="token" style={{ left: token.tokenX, top: token.tokenY }} aria-hidden="true" /> : null}
            {STATIONS.map((item, i) => {
              const current = run?.steps[i];
              const state = stateFor(i, current);
              return (
                <button
                  key={item.id}
                  type="button"
                  ref={(el) => {
                    btnRefs.current[i] = el;
                  }}
                  className={clsx("station", item.place)}
                  data-state={state}
                  data-selected={selected === i}
                  aria-pressed={selected === i}
                  onClick={() => setSelected(i)}
                >
                  <span className="flex w-full items-center justify-between gap-2">
                    <span className="font-mono text-xs text-muted">{item.index}</span>
                    <span className="pip" aria-hidden="true" />
                  </span>
                  <span className="w-full truncate text-sm font-medium">{item.short}</span>
                </button>
              );
            })}
          </div>
          <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
            <li className="flex items-center gap-2">
              <span className="pip pip-signal" /> Implemented
            </li>
            <li className="flex items-center gap-2">
              <span className="pip pip-amber" /> Concept
            </li>
            <li className="flex items-center gap-2">
              <span className="pip pip-fail" /> Broken
            </li>
          </ul>
        </section>

        <aside className="flex flex-col gap-4">
          {run ? <ReceiptCard receipt={run.receipt} tampered={tampered} chainOk={chainOk} /> : <p className="plate text-sm text-muted">Arming the chain…</p>}
          <Pressures draft={draft} setDraft={setDraft} />
          {station && step ? <Dossier station={station} step={step} draft={ranSample} /> : null}
        </aside>
      </div>
      <Ledger
        ledger={ledger}
        setLedger={setLedger}
        error={ledgerError}
        onOpen={() => {
          setLedger(JSON.stringify(draft, null, 2));
          setLedgerError(null);
        }}
        onApply={() => {
          try {
            const parsed = JSON.parse(ledger) as Sample;
            if (!parsed?.claim?.id || !parsed?.claim?.statement) throw new Error("claim requires id and statement");
            setDraft(parsed);
            setLedgerError(null);
          } catch (e) {
            setLedgerError(e instanceof Error ? e.message : "Invalid JSON");
          }
        }}
      />
      <p className="max-w-3xl text-xs text-pretty text-muted">
        Implemented means the logic is ported and checked here. It does not mean the source repository was
        re-verified. Concept stations are illustrative. The recognitive field advises and never gates promotion.
        Locally supported is not independent reproduction.
      </p>
    </main>
  );
}

function Readout({ kicker, value, hot }: { kicker: string; value: string; hot: "signal" | "fail" | "amber" | "bone" }) {
  const tone =
    hot === "signal" ? "text-signal" : hot === "fail" ? "text-fail" : hot === "amber" ? "text-amber" : "text-bone";
  return (
    <div>
      <p className="kicker">{kicker}</p>
      <p className={clsx("display text-3xl", tone)}>{value}</p>
    </div>
  );
}

function ReceiptCard({
  receipt,
  tampered,
  chainOk,
}: {
  receipt: Receipt;
  tampered: boolean;
  chainOk: boolean | null;
}) {
  return (
    <section className="plate flex flex-col gap-2">
      <h2 className="kicker">Promotion receipt</h2>
      <p className="display text-3xl">{receipt.promoted ? "Locally supported" : "Still unknown"}</p>
      <p className="font-mono text-xs text-muted">
        {receipt.from_status} → {receipt.to_status}
      </p>
      {receipt.blocking_steps.length > 0 ? (
        <p className="text-sm">Held by {receipt.blocking_steps.join(", ")}</p>
      ) : (
        <p className="text-sm text-muted">No gating agent refused the claim.</p>
      )}
      {tampered ? (
        <p className="text-sm text-fail">
          The evidence-window output was edited after signing. The receipt was not rewritten.
          Verification is {chainOk ? "valid" : "broken"}.
        </p>
      ) : null}
      <p className="text-xs text-pretty text-muted">{receipt.note}</p>
      <p className="hash">head {receipt.chain_head}</p>
    </section>
  );
}

function Pressures({ draft, setDraft }: { draft: Sample; setDraft: (value: Sample | ((d: Sample) => Sample)) => void }) {
  return (
    <section className="plate flex flex-col gap-3">
      <h2 className="kicker">Pressures</h2>
      <label className="grid gap-1">
        <span className="text-sm text-muted">Statement</span>
        <textarea
          className="ledger"
          rows={3}
          spellCheck={false}
          value={draft.claim.statement}
          onChange={(e) => setDraft({ ...draft, claim: { ...draft.claim, statement: e.target.value } })}
        />
      </label>
      <button
        type="button"
        className="lever"
        aria-pressed={draft.governance.is_scenario_output}
        onClick={() =>
          setDraft((d) => ({
            ...d,
            governance: { ...d.governance, is_scenario_output: !d.governance.is_scenario_output },
          }))
        }
      >
        <span>
          <span className="block text-sm">Scenario output</span>
          <span className="block text-xs text-muted">RULE-003 blocks promotion</span>
        </span>
        <span className="font-mono text-xs">{draft.governance.is_scenario_output ? "On" : "Off"}</span>
      </button>
      <button
        type="button"
        className="lever"
        aria-pressed={draft.noncollapse.observed.replication?.status === "known"}
        onClick={() =>
          setDraft((d) => ({
            ...d,
            noncollapse: {
              ...d.noncollapse,
              observed: {
                ...d.noncollapse.observed,
                replication:
                  d.noncollapse.observed.replication?.status === "known"
                    ? { status: "unknown" }
                    : { status: "known", value: true },
              },
            },
          }))
        }
      >
        <span>
          <span className="block text-sm">Collapse replication</span>
          <span className="block text-xs text-muted">Unknown recorded as known</span>
        </span>
        <span className="font-mono text-xs">
          {draft.noncollapse.observed.replication?.status === "known" ? "On" : "Off"}
        </span>
      </button>
      <label className="grid gap-1">
        <span className="text-sm text-muted">Recognitive scenario</span>
        <select
          className="select"
          value={draft.recognitive.scenario}
          onChange={(e) =>
            setDraft({ ...draft, recognitive: { ...draft.recognitive, scenario: e.target.value } })
          }
        >
          <option value="baseline">Baseline</option>
          <option value="overload">Overload</option>
          <option value="ritual">Ritual</option>
        </select>
      </label>
    </section>
  );
}

function Dossier({ station, step, draft }: { station: Station; step: TraceStep; draft: Sample }) {
  const kind =
    station.kind === "concept" ? "Concept (illustrative)" : station.kind === "advisory" ? "Advisory" : "Implemented";
  return (
    <section className="plate flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="kicker">{station.index}</h2>
          <p className="display text-3xl">{station.label}</p>
        </div>
        <p className={clsx("font-mono text-xs", step.pass ? "text-signal" : "text-fail")}>{step.pass ? "Pass" : "Fail"}</p>
      </div>
      <p className="text-xs text-amber">{kind}</p>
      <p className="text-sm text-pretty text-muted">{station.blurb}</p>
      <p className="hash">{station.repo}</p>
      <Facts step={step} draft={draft} />
      <div>
        <p className="kicker">Output hash</p>
        <p className="hash">{step.output_hash}</p>
      </div>
      <div>
        <p className="kicker">Link hash</p>
        <p className="hash">{step.link_hash}</p>
      </div>
      <details>
        <summary className="cursor-pointer text-sm">Stage output</summary>
        <pre className="output mt-2">{JSON.stringify(step.output, null, 2)}</pre>
      </details>
    </section>
  );
}

function Facts({ step, draft }: { step: TraceStep; draft: Sample }) {
  const output = step.output;
  if (step.id === "governance-gate" && isRecord(output)) {
    const rules = Array.isArray(output.applicable_rules) ? output.applicable_rules.map(String).join(", ") : "—";
    return (
      <dl className="facts">
        <div>
          <dt>Mode</dt>
          <dd>{String(output.mode)}</dd>
        </div>
        <div>
          <dt>Review</dt>
          <dd>{String(output.human_review_level)}</dd>
        </div>
        <div>
          <dt>Promotion</dt>
          <dd>{output.promotion_blocked ? "Blocked" : "Open"}</dd>
        </div>
        <div>
          <dt>Rules</dt>
          <dd>{rules || "—"}</dd>
        </div>
      </dl>
    );
  }
  if (step.id === "noncollapse-check" && isRecord(output)) {
    const collapses = Array.isArray(output.collapses) ? output.collapses : [];
    return (
      <div className="text-sm">
        {collapses.length === 0 ? (
          <p>No collapses across {String(output.boundary_trials)} boundary trials.</p>
        ) : (
          <ul className="grid gap-1">
            {collapses.map((item, i) => {
              const row = item as { kind?: string; invariant?: string };
              return (
                <li key={i} className="font-mono text-xs text-fail">
                  {row.kind} · {row.invariant}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    );
  }
  if (step.id === "recognitive-field" && isRecord(output) && isRecord(output.start)) {
    return <FieldFact output={output} draft={draft} />;
  }
  if (step.id === "celestial-agent" && isRecord(output) && typeof output.transcript === "string") {
    return <pre className="output">{output.transcript}</pre>;
  }
  if (step.id === "evidence-attach" && Array.isArray(output)) {
    return (
      <ul className="grid gap-2">
        {output.map((item) => {
          const row = item as { id?: string; sha256?: string };
          return (
            <li key={row.id} className="hash">
              {row.id} {row.sha256}
            </li>
          );
        })}
      </ul>
    );
  }
  return null;
}

function FieldFact({ output, draft }: { output: Record<string, unknown>; draft: Sample }) {
  const start = output.start as Vec3;
  const scenario = typeof output.scenario === "string" ? output.scenario : "baseline";
  const traced = useMemo(
    () =>
      rfProbeTrace(start, {
        scenario,
        noise: typeof output.final === "object" ? draft.recognitive.noise : draft.recognitive.noise,
        seed: draft.recognitive.seed,
      }),
    [start, scenario, draft.recognitive.noise, draft.recognitive.seed],
  );
  const turb = rfTurbCenter(scenario);
  const points = traced.trail.map((p) => `${(p.x * 100).toFixed(2)},${((1 - p.z) * 100).toFixed(2)}`).join(" ");
  const fate = typeof output.fate === "string" ? output.fate : traced.fate;
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm">
        Fate <span className="font-mono text-xs">{fate}</span>
        <span className="text-muted"> · does not gate</span>
      </p>
      <svg className="field" viewBox="0 0 100 100" role="img" aria-label={`Field projection, fate ${fate}`}>
        <polyline className="field-path" points={points} />
        <circle className="field-attr" cx={80} cy={20} r="1.7" />
        <circle className="field-turb" cx={turb.x * 100} cy={(1 - turb.z) * 100} r="1.7" />
        <circle className="field-start" cx={start.x * 100} cy={(1 - start.z) * 100} r="1.4" />
      </svg>
      <p className="text-xs text-muted">X–Z projection. Bone attractor, amber turbulence, signal path.</p>
    </div>
  );
}

function Ledger({
  ledger,
  setLedger,
  error,
  onOpen,
  onApply,
}: {
  ledger: string;
  setLedger: (value: string) => void;
  error: string | null;
  onOpen: () => void;
  onApply: () => void;
}) {
  return (
    <details
      className="plate"
      onToggle={(e) => {
        if ((e.currentTarget as HTMLDetailsElement).open) onOpen();
      }}
    >
      <summary className="cursor-pointer text-sm">Ledger JSON</summary>
      <div className="mt-3 flex flex-col gap-2">
        <textarea className="ledger" spellCheck={false} value={ledger} onChange={(e) => setLedger(e.target.value)} />
        {error ? <p className="text-sm text-fail">{error}</p> : null}
        <button type="button" className="btn w-fit" onClick={onApply}>
          Load ledger
        </button>
      </div>
    </details>
  );
}
