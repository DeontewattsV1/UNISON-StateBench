# UNISON Kaggle ChatGPT plugin

This package connects UNISON-StateBench to **Kaggle's official MCP server**:

`https://www.kaggle.com/mcp`

It does not proxy or store Kaggle credentials. Kaggle handles account authorization through its own MCP/OAuth surface.

## Why use the official Kaggle MCP

Kaggle's MCP exposes live Notebook and Benchmark operations and supports OAuth authorization. Using the official server avoids creating a second credential-handling service and keeps Kaggle authorization under Kaggle's control.

## ChatGPT connection

If custom plugins / developer-mode MCP connections are available in your ChatGPT workspace:

1. Open **Settings → Security and login** and enable **Developer mode**.
2. Open **Plugins** and add an MCP connection.
3. Use:
   - Name: `Kaggle`
   - MCP URL: `https://www.kaggle.com/mcp`
4. Complete Kaggle OAuth authorization when prompted.
5. Install or load this plugin package so the `unison-empirical` skill is available alongside the Kaggle MCP connection.

The MCP endpoint can also be used directly without the skill package, but the skill encodes the frozen UNISON execution order and scientific boundaries.

## UNISON run sequence

```text
Kaggle OAuth
  -> runtime-snapshot.json
  -> verify source revision + plan digest
  -> freeze exact lineup
  -> explicit execution approval
  -> 162N live model calls
  -> per-model append-only JSONL
  -> results-manifest.json
  -> IPR/RCR/CRR/FHR/CAL/PLR/AIR/SCR
  -> 95% scenario-cluster confidence intervals
  -> failure topology
```

No empirical model-performance claim is valid before the final result-sealing and analysis steps complete.
