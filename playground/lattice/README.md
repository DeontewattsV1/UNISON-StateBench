# UNISON Trace lattice

Source snapshot of the lattice demonstrator. A claim enters as `unknown`. Each station hashes canonical JSON with SHA-256 and chains that digest to the previous step. Tamper edits the evidence-window output after the receipt is signed; verification fails closed. The recognitive field is advisory and never gates promotion.

| Path | What |
|---|---|
| `trace/stages.ts` | Ported stage functions |
| `trace/pipeline.ts` | Sample claim, chain, receipt |
| `trace/stations.ts` | Twelve-station floor |
| `trace-playground.tsx` | Lattice UI |
| `styles.css` | Instrument palette |

```bash
node --experimental-strip-types --test trace/stages.test.ts
```

Implemented means the logic is ported and unit-tested here. It does not re-verify the source repositories. Concept stations are illustrative.
