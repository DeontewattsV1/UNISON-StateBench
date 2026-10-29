import { readFile } from 'node:fs/promises';
import { verifyLedger } from '../server/engine.mjs';

const filename = process.argv[2];
if (!filename) {
  console.error('Usage: node scripts/verify-evidence.mjs evidence.json');
  process.exitCode = 2;
} else {
  try {
    const evidence = JSON.parse(await readFile(filename, 'utf8'));
    if (evidence?.schemaVersion !== 1 || evidence?.product !== 'UNISON Guardian' || !evidence.state?.runId) throw new Error('Unsupported evidence bundle.');
    const ledger = verifyLedger(evidence.state.events);
    const runMatches = evidence.state.events.every(event => event.runId === evidence.state.runId);
    console.log(JSON.stringify({
      internalConsistency: ledger.valid && runMatches ? 'PASS' : 'FAIL',
      eventDigests: ledger,
      snapshotRunMatchesEvents: runMatches,
      reportedRuntimeVerdict: evidence.state.results?.verdict ?? 'NOT_RUN',
      reportedRuntimeVerdictIndependentlyVerified: false,
      originTrusted: false,
      note: 'Digest consistency does not authenticate an unanchored export, attest its snapshot, or independently validate its runtime verdict.',
    }, null, 2));
    if (!ledger.valid || !runMatches) process.exitCode = 1;
  } catch {
    console.error('Could not verify this file as a Guardian evidence bundle.');
    process.exitCode = 1;
  }
}
