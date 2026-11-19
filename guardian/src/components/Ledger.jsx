import { useMemo, useState } from 'react';
import { FileText, GitBranch, Search } from 'lucide-react';
import { SafetyNote } from './ui.jsx';

function titleFor(event) {
  if (event.title) return event.title;
  const titles = {
    'run.created': 'Sandbox created', 'action.executed': 'Baseline executed', 'action.queued': 'Action queued', 'authority.revoked': 'Authority revoked', 'queue.blocked': 'Queued action blocked', 'queue.executed': 'Queued action executed', 'queue.empty': 'Queue empty', 'action.denied': 'Action denied', 'verification.completed': 'Verification completed', sandbox_created: 'Sandbox created', authority_registered: 'Authority registered',
    graph_inventoried: 'Graph inventoried', baseline_executed: 'Baseline executed',
    action_queued: 'Action queued', authority_revoked: 'Authority revoked',
    queued_action_blocked: 'Queued action blocked', queued_action_executed: 'Queued action executed',
    verification_completed: 'Verification completed',
  };
  return titles[event.type] || String(event.type || 'Event').replaceAll(/[._-]/g, ' ').replace(/^\w/, s => s.toUpperCase());
}

function detailFor(event) {
  if (event.message) return event.message;
  if (event.detail) return event.detail;
  return JSON.stringify(event.data || {});
}

function EventRow({ event }) {
  const [open, setOpen] = useState(false);
  const date = new Date(event.time || event.timestamp || 0);
  const dateText = Number.isNaN(date.getTime()) ? 'Time unavailable' : date.toLocaleString(undefined, { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
  return <>
    <tr>
      <td><button className="event-button" onClick={() => setOpen(v => !v)} aria-expanded={open} title="Inspect event receipt">
        <span className="event-icon">{String(event.type).includes('author') ? <GitBranch size={20} /> : <FileText size={20} />}</span>
        <span><strong>{titleFor(event)}</strong><span className="event-time">{dateText}</span></span>
      </button></td>
      <td><span className={`evidence evidence--${String(event.evidence || 'UNKNOWN').toLowerCase()}`}>{event.evidence || 'UNKNOWN'}</span><code className="event-hash" title={event.hash}>{event.hash?.slice(0, 12) || 'No digest'}</code></td>
      <td className="event-detail">{detailFor(event)}</td>
    </tr>
    {open && <tr className="receipt-row"><td colSpan={3}><div className="receipt-details"><strong>Local event receipt · #{event.seq ?? '—'}</strong><dl><div><dt>Event ID</dt><dd>{event.id || 'Unknown'}</dd></div><div><dt>Digest</dt><dd>{event.hash || 'Unknown'}</dd></div><div><dt>Previous digest</dt><dd>{event.previousHash || 'Genesis'}</dd></div></dl><p>Digests support local integrity checks. They do not establish an independently trusted identity or an immutable external ledger.</p></div></td></tr>}
  </>;
}

export default function Ledger({ state, full = false }) {
  const [search, setSearch] = useState('');
  const [evidence, setEvidence] = useState('all');
  const events = useMemo(() => {
    let rows = state?.events || [];
    if (full) rows = rows.filter(event => (evidence === 'all' || event.evidence === evidence) && `${titleFor(event)} ${detailFor(event)} ${event.hash}`.toLowerCase().includes(search.toLowerCase()));
    return full ? [...rows].reverse() : rows.slice(-4);
  }, [state?.events, full, evidence, search]);
  return <section className={`panel ledger-panel ${full ? 'ledger-panel--full' : ''}`} aria-labelledby="ledger-title">
    <div className="section-heading"><h2 id="ledger-title">Evidence ledger</h2>{full && <span className="muted">{events.length} {events.length === 1 ? 'event' : 'events'}</span>}</div>
    {full && <div className="ledger-filters"><label className="search-field"><Search size={17} aria-hidden="true" /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search events or digests" aria-label="Search ledger events" /></label><label className="evidence-filter">Evidence<select value={evidence} onChange={e => setEvidence(e.target.value)}><option value="all">All evidence</option><option value="SIMULATED">Simulated</option><option value="OBSERVED">Observed</option><option value="UNKNOWN">Unknown</option></select></label></div>}
    <div className="table-scroll"><table className="ledger-table"><thead><tr><th>Event</th><th>Evidence</th><th>Detail</th></tr></thead><tbody>{events.map(event => <EventRow key={event.id || event.seq} event={event} />)}{events.length === 0 && <tr><td className="empty-table" colSpan={3}>{state ? 'No events match this view.' : 'Loading the local evidence ledger…'}</td></tr>}</tbody></table></div>
    <SafetyNote />
  </section>;
}
