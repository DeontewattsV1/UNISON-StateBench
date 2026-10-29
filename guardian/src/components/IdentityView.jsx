import { Fingerprint, Info } from 'lucide-react';

export default function IdentityView({ state, health }) {
  const identity = state?.identity || {};
  const fields = [
    ['Execution run', identity.runId || state?.runId, 'A sandbox execution; separate from a model or credential.'],
    ['Task instance', identity.taskId, 'The synthetic task being evaluated in this run.'],
    ['Model configuration', identity.model || health?.meta?.model || 'muse-wonder-1.0', 'Configured model ID. This is not evidence that a live inference occurred.'],
    ['Credential principal', identity.principal, 'A synthetic principal in the registered authority graph.'],
    ['Deployment', identity.deployment || (health?.mode === 'public-sandbox' ? 'Public sandbox' : 'Local sandbox'), 'No production system or external account is controlled by this demonstration.'],
    ['Legal owner', identity.owner, 'No independently verified ownership credential is registered.'],
  ];
  return <section className="panel identity-panel"><div className="section-heading"><h2>Agent identity</h2><Fingerprint size={23} className="blue" /></div><p className="view-intro">An execution run, a model, a credential, and an owner are different identities. Guardian keeps their evidence separate.</p><dl className="identity-list">{fields.map(([label, value, note]) => {
    const unknown = value === undefined || value === null || value === '' || String(value).toUpperCase() === 'UNKNOWN';
    return <div className="identity-row" key={label}><dt>{label}</dt><dd><code className={unknown ? 'unknown-value' : ''}>{unknown ? 'UNKNOWN' : typeof value === 'object' ? JSON.stringify(value) : value}</code><p>{note}</p></dd></div>;
  })}</dl><div className="scope-note"><Info size={18} /><p>Agent relationships are synthetic registrations. No real-person identity, cryptographic signature, or external owner attestation is established by this demo.</p></div></section>;
}
