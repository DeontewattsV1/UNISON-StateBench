import { useEffect, useState } from 'react';
import { Activity, AlertCircle, Check, ChevronRight, Fingerprint, GitBranch, LockKeyhole, Play, RotateCcw, ShieldCheck } from 'lucide-react';
import { useHats } from '../hooks/useHats';
import { Button, Status } from './ui.jsx';
import './hats-lab.css';

const TYPES = ['Macro', 'Meso', 'Micro', 'Nano'];
const CAPABILITIES = ['invoke:synthetic', 'spawn:agent'];
const SPECIALIZATIONS = ['general', 'orchestrator', 'workflow', 'retrieval', 'bounded-task', 'analysis'];
const short = value => typeof value === 'string' ? value.slice(0, 8) : 'Unknown';
const agentLabel = agent => `${agent.type} · ${short(agent.id)}`;
const metric = (value, suffix = '') => value === null || value === undefined || !Number.isFinite(value) ? 'UNKNOWN' : `${Number.isInteger(value) ? value : Number(value.toFixed(2))}${suffix}`;

function DecisionStatus({ status }) {
  return <span className={`hats-decision-status hats-decision-status--${String(status).toLowerCase()}`}>{status || 'Not tested'}</span>;
}

function registeredState(agent, agents) {
  const visited = new Set();
  let cursor = agent;
  while (cursor) {
    if (visited.has(cursor.id)) return 'Unknown ancestry';
    visited.add(cursor.id);
    if (cursor.revoked) return cursor.id === agent.id ? 'Revoked' : 'Ancestor revoked';
    if (cursor.parentId === null) return 'Registered';
    cursor = agents.find(item => item.id === cursor.parentId);
  }
  return 'Unknown ancestry';
}

function AnalyticsLane({ analytics }) {
  const features = analytics?.features;
  return <section className="panel hats-lane hats-lane--analytic" aria-labelledby="hats-analytic-heading">
    <div className="hats-section-title"><Activity size={20} /><h2 id="hats-analytic-heading">Analytic lane</h2><span className="evidence">CONJECTURE</span></div>
    <p className="hats-description">Timing and topology heuristics explain recorded activity. They cannot grant permission.</p>
    <div className="hats-forecast"><span>Spawn pressure</span><strong>{analytics?.forecast?.spawnRisk || 'UNKNOWN'}</strong></div>
    <p className="hats-description">{analytics?.forecast?.reason || 'Awaiting recorded metadata.'}</p>
    <dl className="hats-measurements">
      <div><dt>Recent spawns</dt><dd>{metric(features?.recentSpawnCount)}</dd></div>
      <div><dt>Spawn rate / min</dt><dd>{metric(features?.spawnRatePerMinute)}</dd></div>
      <div><dt>Interval variance (ms²)</dt><dd>{metric(features?.requestIntervalVarianceMs2)}</dd></div>
      <div><dt>Lineage graph density</dt><dd>{metric(features?.lineageGraphDensity)}</dd></div>
      <div><dt>Timing coincidence</dt><dd>{metric(analytics?.coordination?.coincidenceRatio)}</dd></div>
      <div><dt>Recorded coverage</dt><dd>{analytics?.coverage?.status || 'UNKNOWN'}</dd></div>
    </dl>
    <p className="hats-footnote">Uncalibrated heuristics over synthetic metadata. Timing coincidence does not establish swarm consensus, human behavior, or agent origin.</p>
  </section>;
}

function AuthorityLane({ decision, verification }) {
  return <section className="panel hats-lane hats-lane--authority" aria-labelledby="hats-authority-heading">
    <div className="hats-section-title"><ShieldCheck size={20} /><h2 id="hats-authority-heading">Authority lane</h2><span className="evidence evidence--observed">DETERMINISTIC</span></div>
    <p className="hats-description">Recompute lineage, check the current ancestor chain, enforce inherited scope and fixed resource limits.</p>
    <div className="hats-current-decision" aria-live="polite"><DecisionStatus status={decision?.status} /><strong>{decision?.code || 'No operation tested'}</strong><p>{decision?.reason || 'Run the guided demo, or spawn and test an agent below.'}</p></div>
    {decision?.receipt && <details className="hats-receipt"><summary>Inspect transition receipt</summary><code>{typeof decision.receipt === 'string' ? decision.receipt : JSON.stringify(decision.receipt, null, 2)}</code><p>A local digest receipt; no signature or external identity attestation.</p></details>}
    {verification && <div className="hats-verification"><div className="hats-section-title"><strong>Recomputed evidence</strong><Status value={verification.verdict} /></div><ul>{verification.checks?.map(check => <li key={check.id}><div><span>{check.label}</span><Status value={check.status} /></div><p>{check.detail}</p></li>)}</ul></div>}
  </section>;
}

export default function HatsLab() {
  const { state, pending, error, act, refresh } = useHats();
  const [parentId, setParentId] = useState('');
  const [selectedId, setSelectedId] = useState('');
  const [childType, setChildType] = useState('Meso');
  const [capabilities, setCapabilities] = useState(CAPABILITIES);
  const [specialization, setSpecialization] = useState('general');
  const agents = state?.agents || [];
  const selected = agents.find(agent => agent.id === selectedId) || agents[0];
  const parent = agents.find(agent => agent.id === parentId) || agents[0];
  const analytics = state?.analytics || state?.analysis;
  const disabled = !state || Boolean(pending);
  const fresh = agents.length === 1 && state?.events?.length === 1 && state?.syntheticActions === 0 && !state?.demo;

  useEffect(() => {
    if (!agents.length) return;
    if (!agents.some(agent => agent.id === parentId)) {
      setParentId(agents[0].id);
      setChildType('Meso');
      setCapabilities([...agents[0].capabilities]);
    }
    if (!agents.some(agent => agent.id === selectedId)) setSelectedId(agents[0].id);
  }, [state?.runId, agents, parentId, selectedId]);

  function chooseParent(id) {
    const next = agents.find(agent => agent.id === id);
    setParentId(id);
    setChildType(TYPES[Math.min(TYPES.indexOf(next.type) + 1, TYPES.length - 1)]);
    setCapabilities([...next.capabilities]);
  }

  async function spawn() {
    const next = await act('spawn', { parentId: parent.id, type: childType, capabilities, specialization });
    if (next?.lastDecision?.allowed && next.agents.length > agents.length) setSelectedId(next.agents.at(-1).id);
  }

  return <div className="hats-lab">
    {error && <div className="error-notice" role="alert"><AlertCircle size={19} /><span>{error}</span><button onClick={refresh}>Retry HATS</button></div>}
    <section className="panel hats-demo-intro" aria-labelledby="hats-demo-heading"><div><span className="hats-eyebrow">HIERARCHICAL AGENT TRACKING SYSTEM</span><h2 id="hats-demo-heading">A small, falsifiable spawning sandbox.</h2><p>Build a Macro → Meso → Micro → Nano lineage, try the boundaries, then revoke its root. Every action is synthetic.</p></div><div className="hats-demo-actions"><Button icon={Play} variant="primary" disabled={disabled || !fresh} loading={pending === 'demo'} onClick={() => act('demo')}>Run HATS demo</Button><Button icon={RotateCcw} disabled={Boolean(pending)} loading={pending === 'reset'} onClick={() => act('reset')}>Reset HATS lab</Button>{state && !fresh && <span>Reset to run a fresh guided demonstration.</span>}</div></section>

    <section className="hats-metrics" aria-label="HATS run measurements"><div><GitBranch size={20} /><span>Registered agents</span><strong data-testid="hats-agent-count">{state ? agents.length : '…'}</strong></div><div><Fingerprint size={20} /><span>Deepest level</span><strong>{state ? `${Math.max(0, ...agents.map(agent => agent.depth))} / ${state.policy.maxDepth}` : '…'}</strong></div><div><LockKeyhole size={20} /><span>Synthetic actions</span><strong data-testid="hats-action-count">{state?.syntheticActions ?? '…'}</strong></div><div><ShieldCheck size={20} /><span>Ledger links</span><strong>{state?.ledgerVerification?.status || 'UNKNOWN'}</strong></div></section>

    {state?.demo?.completed && <section className="panel hats-demo-result" aria-labelledby="hats-demo-result-heading"><div className="hats-section-title"><Check size={20} /><h2 id="hats-demo-result-heading">Guided demonstration</h2><Status value={state.demo.verdict} /></div><ol>{state.demo.steps.map((step, index) => <li key={`${index}-${step.code}`}><span className={`hats-step-marker ${step.passed ? 'hats-step-marker--pass' : ''}`}>{step.passed ? <Check size={13} /> : index + 1}</span><span>{step.label}</span><DecisionStatus status={step.status} /></li>)}</ol><p className="hats-footnote">An expected denial is a passing boundary check. This result covers this registered synthetic run.</p></section>}

    <div className="hats-lanes"><AnalyticsLane analytics={analytics} /><AuthorityLane decision={state?.lastDecision} verification={state?.verification} /></div>

    <div className="hats-workspace"><section className="panel hats-lineage" aria-labelledby="hats-lineage-heading"><div className="hats-section-title"><GitBranch size={20} /><h2 id="hats-lineage-heading">Registered lineage</h2><span className="evidence">SIMULATED</span></div><p className="hats-description">Each digest binds this run, identity, parent, depth, nonce, genome and capability scope.</p><div className="hats-agent-list">{agents.map(agent => <button type="button" key={agent.id} className={`hats-agent ${selected?.id === agent.id ? 'hats-agent--selected' : ''}`} style={{ '--hats-depth': Math.min(agent.depth, 3) }} aria-pressed={selected?.id === agent.id} aria-label={`Inspect ${agentLabel(agent)}`} onClick={() => setSelectedId(agent.id)}><span className="hats-agent-symbol"><GitBranch size={17} /></span><span className="hats-agent-main"><strong>{agent.type}<code>{short(agent.id)}</code></strong><span>{agent.specialization} · depth {agent.depth}</span></span><span className={`hats-agent-state ${registeredState(agent, agents) !== 'Registered' ? 'hats-agent-state--revoked' : ''}`}>{registeredState(agent, agents)}</span><ChevronRight size={15} /></button>)}{!state && <p className="hats-description">Loading the isolated HATS registry…</p>}</div>{selected && <details className="hats-identity-details"><summary>Inspect {selected.type} lineage fields</summary><dl><div><dt>Agent ID</dt><dd><code>{selected.id}</code></dd></div><div><dt>Parent ID</dt><dd><code>{selected.parentId || 'Genesis root'}</code></dd></div><div><dt>Lineage hash</dt><dd><code>{selected.lineageHash}</code></dd></div><div><dt>Spawn nonce</dt><dd><code>{selected.nonce}</code></dd></div><div><dt>Parent state digest</dt><dd><code>{selected.genome?.parentStateHash || 'Genesis root'}</code></dd></div><div><dt>Inherited scope</dt><dd><code>{selected.capabilities.join(', ') || 'No capabilities'}</code></dd></div><div><dt>Inheritance mask</dt><dd><code>{selected.genome?.inheritanceMask?.join(', ') || 'None'}</code></dd></div></dl><p className="hats-footnote">Recomputable linkage is not an externally trusted origin or legal-owner attestation.</p></details>}</section>

    <section className="panel hats-controls" aria-labelledby="hats-controls-heading"><h2 id="hats-controls-heading">Test the boundaries</h2><p className="hats-description">Make a proposal; the authority lane checks it independently.</p><fieldset disabled={disabled}><legend>Spawn a child</legend><label htmlFor="hats-parent">Parent agent</label><select id="hats-parent" value={parent?.id || ''} onChange={event => chooseParent(event.target.value)}>{agents.map(agent => <option key={agent.id} value={agent.id}>{agentLabel(agent)}</option>)}</select><div className="hats-form-pair"><div><label htmlFor="hats-child-type">Child type</label><select id="hats-child-type" value={childType} onChange={event => setChildType(event.target.value)}>{TYPES.map(type => <option key={type}>{type}</option>)}</select></div><div><label htmlFor="hats-specialization">Specialization</label><select id="hats-specialization" value={specialization} onChange={event => setSpecialization(event.target.value)}>{SPECIALIZATIONS.map(value => <option key={value}>{value}</option>)}</select></div></div><span className="hats-field-label">Child capabilities</span><div className="hats-capabilities">{CAPABILITIES.map(capability => <label key={capability}><input type="checkbox" checked={capabilities.includes(capability)} onChange={event => setCapabilities(current => event.target.checked ? [...current, capability] : current.filter(value => value !== capability))} /><code>{capability}</code></label>)}</div><Button icon={GitBranch} disabled={disabled} loading={pending === 'spawn'} onClick={spawn}>Spawn child</Button></fieldset><fieldset disabled={disabled}><legend>Check current authority</legend><label htmlFor="hats-selected">Selected agent</label><select id="hats-selected" value={selected?.id || ''} onChange={event => setSelectedId(event.target.value)}>{agents.map(agent => <option key={agent.id} value={agent.id}>{agentLabel(agent)}</option>)}</select><div className="hats-operation-actions"><Button icon={Play} disabled={disabled} loading={pending === 'adjudicate'} onClick={() => act('adjudicate', { agentId: selected.id, action: 'invoke:synthetic' })}>Invoke synthetic action</Button><Button icon={LockKeyhole} disabled={disabled} loading={pending === 'revoke'} onClick={() => act('revoke', { agentId: selected.id })}>Revoke selected agent</Button></div></fieldset><div className="hats-policy"><strong>Fixed policy</strong><span>Depth ≤ {state?.policy?.maxDepth ?? 3} · children ≤ {state?.policy?.maxChildren ?? 3} · agents ≤ {state?.policy?.maxAgents ?? 12}</span><span>At most {state?.policy?.spawnLimit ?? 6} successful spawns / {(state?.policy?.spawnWindowMs ?? 60000) / 1000}s</span></div><Button icon={ShieldCheck} variant="outline" disabled={disabled} loading={pending === 'verify'} onClick={() => act('verify')}>Verify HATS</Button></section></div>

    <section className="panel hats-events" aria-labelledby="hats-events-heading"><div className="hats-section-title"><h2 id="hats-events-heading">HATS event ledger</h2><span className="muted">{state?.events?.length ?? 0} hash-linked events</span></div><p className="hats-description">Inspect the latest 16 records. Export HATS evidence for the complete run.</p><div className="hats-event-list">{state?.events?.slice(-16).reverse().map(event => <details key={event.id} className="hats-event"><summary><span className="hats-event-seq">{String(event.seq).padStart(2, '0')}</span><span className="hats-event-label"><strong>{event.type}</strong><span>{event.message}</span></span><span className={`evidence evidence--${event.evidence?.toLowerCase()}`}>{event.evidence}</span></summary><dl><div><dt>Timestamp</dt><dd>{event.time}</dd></div><div><dt>Event digest</dt><dd><code>{event.hash}</code></dd></div><div><dt>Previous digest</dt><dd><code>{event.previousHash}</code></dd></div></dl><pre>{JSON.stringify(event.data, null, 2)}</pre></details>)}</div></section>
    <div className="safety-note hats-scope-note"><ShieldCheck size={20} /><span>Metadata only. No prompts, response text, token streams, credentials, private headers, literal IP addresses or mouse trajectories are collected. These seeded actors are synthetic; this lab does not observe a live cluster.</span></div>
  </div>;
}
