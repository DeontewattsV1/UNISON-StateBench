import { readFile, stat } from 'node:fs/promises';
import { verifyLedger } from '../server/engine.mjs';
import { verifyHatsLineage } from '../server/hats.mjs';

const filename = process.argv[2];
if (!filename) {
  console.error('Usage: node scripts/verify-evidence.mjs evidence.json');
  process.exitCode = 2;
} else {
  try {
    if ((await stat(filename)).size > 4 * 1024 * 1024) throw new Error('Evidence exceeds 4 MiB.');
    const evidence = JSON.parse(await readFile(filename, 'utf8'));
    if (evidence?.schemaVersion !== 1 || evidence?.product !== 'UNISON Guardian' || !evidence.state?.runId) throw new Error('Unsupported evidence bundle.');
    const ledger = verifyLedger(evidence.state.events);
    const runMatches = evidence.state.events.every(event => event.runId === evidence.state.runId);
    const lineage = evidence.component === 'HATS' ? verifyHatsLineage(evidence.state) : null;
    const consistent = ledger.valid && runMatches && (!lineage || lineage.status === 'PASS');
    console.log(JSON.stringify({
      internalConsistency: consistent ? 'PASS' : lineage?.status === 'UNKNOWN' && ledger.valid && runMatches ? 'UNKNOWN' : 'FAIL',
      eventDigests: ledger,
      ...(lineage ? { lineageDigests: lineage } : {}),
      snapshotRunMatchesEvents: runMatches,
      reportedRuntimeVerdict: evidence.state.results?.verdict ?? evidence.state.verification?.verdict ?? 'NOT_RUN',
      reportedRuntimeVerdictIndependentlyVerified: false,
      originTrusted: false,
      note: 'Digest consistency does not authenticate an unanchored export, attest its snapshot, or independently validate its runtime verdict.',
    }, null, 2));
    if (!consistent) process.exitCode = 1;
  } catch {
    console.error('Could not verify this file as a Guardian evidence bundle.');
    process.exitCode = 1;
  }
}
