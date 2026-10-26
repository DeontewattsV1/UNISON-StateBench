# Market Microstructure Extension (experimental)

> **Status:** post-v0.1 research extension. This directory is **not** part of the frozen UNISON-StateBench v0.1 corpus, source revision, 162-call empirical matrix, or primary leaderboard metrics.

This extension integrates five related ideas into UNISON's state-preservation framework:

1. signal detection under noisy observations;
2. expected payoff under an explicit probability model;
3. Nash equilibrium as a best-response condition;
4. Kyle-style linear price impact under model assumptions;
5. spread / execution-cost formulas whose optimality must be separately established.

The purpose is **not** to claim a profitable trading strategy. The purpose is to test whether a model preserves the epistemic boundary between:

```text
illustration
!= candidate signal
!= benchmark-adjusted alpha
!= strategic equilibrium
!= model-conditional price impact
!= calibrated execution cost
!= empirically validated net edge
```

## Equations represented

Expected payoff:

`E[pi_i] = sum_j p_j * pi_i(s_j)`

Nash best-response condition:

`u_i(s_i*, s_-i*) >= u_i(s_i, s_-i*)`

Linear price-impact rule:

`P_t = P_0 + lambda * Q_t`

Single-auction Kyle-style coefficient under the specified variance notation:

`lambda = 1/2 * sqrt(Sigma_v / Sigma_u)`

Candidate spread expression:

`spread* = 2 * (c + lambda * sigma * sqrt(T))`

The last expression is intentionally represented as an **unverified model claim** unless the objective, variable definitions, unit consistency, and derivation are supplied.

## Non-collapse graph

```text
noisy observations
    |
    v
candidate signal
    |  requires benchmark/risk-model validation
    v
alpha established
    |
    |  strategic beliefs + payoffs
    v
best responses verified
    |
    v
Nash equilibrium established
    |
    |  order-flow model assumptions
    v
price-impact model applicable
    |
    |  calibration + units
    v
execution-cost estimate
    |
    |  objective + empirical out-of-sample evidence
    v
net strategy edge validated
```

Every arrow is a state transition. UNISON should penalize a model that skips a required transition.

## State-collapse failure families

- **signal-to-alpha collapse** — a visually smooth or persistent component is treated as validated alpha;
- **intersection-to-equilibrium collapse** — curve intersection is treated as Nash equilibrium without verifying best responses for all players and allowed deviations;
- **expectation-to-risk collapse** — expected payoff is treated as a complete downside-risk characterization;
- **assumption-to-law collapse** — a linear price-impact rule is treated as a universal market law;
- **conditional-result-to-transfer collapse** — the Kyle coefficient is moved to a different market setting without checking its assumptions;
- **formula-to-optimum collapse** — a spread expression is called optimal without a stated objective and derivation;
- **gross-to-net-edge collapse** — signal/payoff estimates are treated as tradeable edge without price impact, spread, fees, and risk.

These are scored with the existing UNISON IPR/SCR machinery rather than adding a new v0.1 primary metric.

## Unit boundary

If `Sigma_v` has units price^2 and `Sigma_u` has units quantity^2, then

`lambda` has units price / quantity,

so `lambda * Q_t` has units price.

For `lambda * sigma * sqrt(T)` to also have units price, `sigma` must carry units compatible with quantity / sqrt(time). If `sigma` instead denotes price volatility, the expression is not dimensionally justified under the same `lambda` definition.

## Experimental boundary

These cases are candidates for a future UNISON release. They must not be inserted into `cases/v0.1-corpus.json`, must not alter the frozen v0.1 oracle, and must not change the v0.1 plan digest.
