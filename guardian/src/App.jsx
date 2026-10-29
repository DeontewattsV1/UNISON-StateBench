import { useState } from 'react';
import { BookOpen, Box, Download, FileText, Menu, Network, Play, RotateCcw, Shield, UserRound, X, AlertCircle } from 'lucide-react';
import { useSandbox } from './hooks/useSandbox';
import { Button } from './components/ui.jsx';
import AuthorityGraph from './components/AuthorityGraph.jsx';
import RevocationTest from './components/RevocationTest.jsx';
import Ledger from './components/Ledger.jsx';
import IdentityView from './components/IdentityView.jsx';
import HowItWorks from './components/HowItWorks.jsx';
import ModelPanel from './components/ModelPanel.jsx';

const navigation = [
  { id: 'graph', label: 'Authority graph', Icon: Network },
  { id: 'ledger', label: 'Evidence ledger', Icon: FileText },
  { id: 'identity', label: 'Agent identity', Icon: UserRound },
  { id: 'how', label: 'How it works', Icon: BookOpen },
];
const headers = {
  graph: ['Authority, made verifiable.', 'Test whether revoked permissions can still reach a protected action.'],
  ledger: ['Evidence you can inspect.', 'Trace state transitions and the local decisions behind each result.'],
  identity: ['Identity without assumptions.', 'Keep execution, configuration, credential, and ownership evidence distinct.'],
  how: ['From permission to proof.', 'Understand what the harness checks, and where its evidence ends.'],
};

function Sidebar({ view, setView, mode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  return <aside className={`sidebar ${mobileOpen ? 'sidebar--open' : ''}`}>
    <a className="brand" href="#graph" onClick={e => { e.preventDefault(); setView('graph'); setMobileOpen(false); }} aria-label="UNISON Guardian home"><Shield size={39} strokeWidth={1.55} /><span><strong>UNISON</strong><span>Guardian</span></span></a>
    <button className="mobile-menu" aria-label={mobileOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={mobileOpen} onClick={() => setMobileOpen(v => !v)}>{mobileOpen ? <X /> : <Menu />}</button>
    <nav className="navigation" aria-label="Main navigation">{navigation.map(({ id, label, Icon }) => <button key={id} className={`nav-item ${view === id ? 'is-active' : ''}`} aria-current={view === id ? 'page' : undefined} onClick={() => { setView(id); setMobileOpen(false); }}><Icon size={22} strokeWidth={1.5} /><span>{label}</span></button>)}</nav>
    <div className="sidebar-footer"><Box size={21} strokeWidth={1.45} /><div>{mode === 'public-sandbox' ? 'Public sandbox' : 'Local sandbox'}<span>Synthetic actions only</span></div></div>
  </aside>;
}

export default function App() {
  const [view, setView] = useState('graph');
  const { state, health, pending, error, proposal, modelError, refresh, act, analyze } = useSandbox();
  const [title, subtitle] = headers[view];
  const hasBaseline = Boolean(state?.queue?.length || state?.phase === 'authorized' || state?.phase === 'revoked');
  return <div className="app-shell">
    <Sidebar view={view} setView={setView} mode={health?.mode} />
    <main className="main-content" id="main-content">
      <header className="page-header"><div><h1>{title}</h1><p>{subtitle}</p></div><div className="header-actions">{view === 'graph' && <Button icon={Play} variant="primary" onClick={() => act('baseline')} disabled={!state || Boolean(pending) || hasBaseline} loading={pending === 'baseline'}>Run baseline</Button>}<a className="button button--outline" href="/api/evidence" download="unison-guardian-evidence.json"><Download size={18} aria-hidden="true" />Export evidence</a></div></header>
      {error && <div className="error-notice" role="alert"><AlertCircle size={19} /><span>{error}</span><button onClick={refresh}>Retry</button></div>}
      <section className="scenario-rail" aria-label="Sandbox scenario"><label htmlFor="scenario">Scenario</label><select id="scenario" value={state?.scenario || 'queued'} disabled={!state || Boolean(pending)} onChange={e => act('reset', { scenario: e.target.value })}><option value="queued">Queued delegation</option><option value="alternate">Alternate authority path</option><option value="unknown">Incomplete inventory</option></select><span className="rail-divider" /><Button icon={RotateCcw} onClick={() => act('reset', { scenario: state?.scenario || 'queued' })} disabled={Boolean(pending)} loading={pending === 'reset'}>Reset sandbox</Button></section>
      {view === 'graph' && <><div className="workspace-grid"><AuthorityGraph state={state} /><div className="inspection-column"><RevocationTest state={state} pending={pending} act={act} /><ModelPanel health={health} pending={pending} analyze={analyze} proposal={proposal} modelError={modelError} /></div></div><Ledger state={state} /></>}
      {view === 'ledger' && <Ledger state={state} full />}
      {view === 'identity' && <IdentityView state={state} health={health} />}
      {view === 'how' && <HowItWorks health={health} />}
    </main>
  </div>;
}
