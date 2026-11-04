# Deception Simulation Guardrails

This package does **not** include a live autonomous deception engine.

It includes a **supervised local simulator** for governance and audit-path testing.

## What it does
- blocks below-threshold classifications
- returns null output when authorization is missing
- verifies a signed shadow-policy artifact
- checks a local authorization ticket
- emits one approved canned decoy response
- writes simulator events to the local audit log

## What it does not do
- no live network interception
- no autonomous deployment routing
- no dynamic attacker interaction
- no real-world deception content generation
- no production activation path

## Why
A live autonomous deception component would materially increase operational risk and requires separate legal, policy, and security review beyond what this package can safely implement.
