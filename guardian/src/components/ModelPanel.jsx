import { useState } from 'react';
import { ChevronDown, Sparkles } from 'lucide-react';
import { Button } from './ui.jsx';

export default function ModelPanel({ health, pending, analyze, proposal, modelError }) {
  const [open, setOpen] = useState(false);
  const configured = health?.meta?.configured;
  const liveDisabled = health?.meta?.enabled === false;
  const content = proposal?.proposal || proposal;
  return <section className="panel model-panel"><button className="model-toggle" onClick={() => setOpen(value => !value)} aria-expanded={open}><span><Sparkles size={17} /><strong>Ask Muse</strong><span className="model-caption">Model proposal</span></span><ChevronDown size={17} className={open ? 'rotate' : ''} /></button>
    {open && <div className="model-body"><p>Muse Wonder can suggest what to inspect. The verifier makes the authority decision independently.</p><p className="provider-state">{liveDisabled ? 'Live model analysis is disabled on this public demo. Model API credentials are used only by a separately authenticated or local service.' : configured === true ? 'Meta API configured · muse-wonder-1.0' : configured === false ? 'Meta API key is not configured on the server.' : 'Checking Meta API configuration…'}</p><Button icon={Sparkles} variant="outline" disabled={Boolean(pending)} loading={pending === 'analyze'} onClick={analyze}>Analyze this sandbox</Button>{modelError && <p role="alert" className="model-error">{modelError}</p>}{proposal && <div className="proposal" aria-live="polite"><span className="evidence evidence--derived">MODEL PROPOSAL</span><p>{content.explanation || content.summary || 'The model returned a structured proposal.'}</p>{content.suggestedGrantIds?.length > 0 && <p><strong>Suggested grants to inspect:</strong> {content.suggestedGrantIds.join(', ')}</p>}{content.uncertainty && <p><strong>Limits:</strong> {content.uncertainty}</p>}<small>This output did not change any permissions.</small>{proposal.requestId && <p><strong>Response receipt:</strong> <code>{proposal.requestId}</code></p>}</div>}</div>}
  </section>;
}
