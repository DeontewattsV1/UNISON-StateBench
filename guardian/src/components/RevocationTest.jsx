import { Check, CircleCheck, CircleHelp, CircleX, Clock3, Play, Shield, ShieldCheck } from 'lucide-react';
import { Button, Status } from './ui.jsx';

function phases(state) {
  const types = (state?.events || []).map(event => String(event.type).toLowerCase());
  const hasBaseline = Boolean(state?.phase === 'authorized' || state?.baselineDone || state?.baselineExecuted || state?.queue?.length || types.some(type => type.includes('baseline')));
  const revoked = Boolean(state?.grants?.some(grant => grant.revoked) || types.some(type => type.includes('revok')));
  const replayed = Boolean(state?.queue?.some(item => ['blocked', 'denied', 'executed', 'completed', 'BLOCKED', 'DENIED', 'EXECUTED'].includes(item.status)) || types.some(type => type.includes('replay') || type.includes('queue') && (type.includes('blocked') || type.includes('denied'))));
  return { hasBaseline, revoked, replayed };
}

export default function RevocationTest({ state, pending, act }) {
  const { hasBaseline, revoked, replayed } = phases(state);
  const result = state?.results;
  const ResultIcon = result?.verdict === 'PASS' ? CircleCheck : result?.verdict === 'FAIL' ? CircleX : result ? CircleHelp : Clock3;
  const resultTitle = result?.verdict === 'PASS' ? 'Revocation verified' : result?.verdict === 'FAIL' ? 'Authority still reachable' : result ? 'Verification incomplete' : 'Awaiting verification';
  return <section className="panel revocation-panel" aria-labelledby="revocation-title">
    <h2 id="revocation-title">Revocation test</h2>
    <p className="panel-intro">Authority is checked again when an action commits.</p>
    <ol className="steps">
      <li className={hasBaseline ? 'step step--complete' : 'step step--current'}><span className="step-number">{hasBaseline ? <Check size={17} /> : '1'}</span><div><strong>Run baseline</strong><p>Execute the scenario with current permissions.</p></div></li>
      <li className={revoked ? 'step step--complete' : hasBaseline ? 'step step--current' : 'step'}><span className="step-number">{revoked ? <Check size={17} /> : '2'}</span><div><strong>Revoke authority</strong><p>Remove the planner’s root grant.</p></div></li>
      <li className={replayed ? 'step step--complete' : revoked ? 'step step--current' : 'step'}><span className="step-number">{replayed ? <Check size={17} /> : '3'}</span><div><strong>Replay queued action</strong><p>Attempt to execute the previously queued action.</p></div></li>
    </ol>
    <div className="workflow-actions"><Button icon={Shield} variant="outline" onClick={() => act('revoke')} disabled={!state || Boolean(pending) || revoked} loading={pending === 'revoke'}>Revoke authority</Button><Button icon={Play} onClick={() => act('replay')} disabled={!state || Boolean(pending) || !hasBaseline || replayed} loading={pending === 'replay'}>Replay queued action</Button></div>
    <div className="verification-result" aria-live="polite"><div className="result-label">Result{result && <Status value={result.verdict} />}</div><div className={`result-summary result-summary--${String(result?.verdict || 'pending').toLowerCase()}`}><ResultIcon size={30} strokeWidth={1.7} /><div><strong>{resultTitle}</strong><p>{result ? result.scope || 'Bounded to registered paths.' : 'Bounded to registered paths.'}</p></div></div>
      {result && <ul className="check-list">{result.checks?.map(check => <li key={check.id}><div><span>{check.label}</span><Status value={check.status} /></div><p>{check.detail}</p></li>)}</ul>}
      {result?.residualPaths?.length > 0 && <div className="residual-paths"><strong>Surviving path</strong>{result.residualPaths.map((path, index) => <code key={index}>{path.join(' → ')}</code>)}</div>}
      <Button icon={ShieldCheck} variant="text" onClick={() => act('verify')} disabled={!state || Boolean(pending)} loading={pending === 'verify'}>Run verification</Button>
    </div>
  </section>;
}
