<div align="center">

<svg width="800" height="180" viewBox="0 0 800 180" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg5" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0a0014"/>
      <stop offset="100%" stop-color="#00081a"/>
    </linearGradient>
    <filter id="glow5">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <linearGradient id="phase" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#6366f1"/>
      <stop offset="50%" stop-color="#a855f7"/>
      <stop offset="100%" stop-color="#ec4899"/>
    </linearGradient>
  </defs>
  <rect width="800" height="180" fill="url(#bg5)" rx="16"/>
  <!-- Phase pipeline visualization -->
  <!-- Phase boxes -->
  <rect x="60" y="65" width="80" height="40" rx="6" fill="#1e1b4b" stroke="#6366f1" stroke-width="1.5"/>
  <text x="100" y="89" text-anchor="middle" font-family="monospace" font-size="9" fill="#818cf8">PHASE 1</text>
  <line x1="140" y1="85" x2="175" y2="85" stroke="#6366f1" stroke-width="1.5" marker-end="url(#arrow)"/>
  <rect x="180" y="65" width="80" height="40" rx="6" fill="#2d1b4e" stroke="#a855f7" stroke-width="1.5"/>
  <text x="220" y="89" text-anchor="middle" font-family="monospace" font-size="9" fill="#c084fc">PHASE 2</text>
  <line x1="260" y1="85" x2="295" y2="85" stroke="#a855f7" stroke-width="1.5"/>
  <rect x="300" y="65" width="80" height="40" rx="6" fill="#3b1a5e" stroke="#a855f7" stroke-width="2"/>
  <text x="340" y="89" text-anchor="middle" font-family="monospace" font-size="9" fill="#e879f9">PHASE 3</text>
  <line x1="380" y1="85" x2="415" y2="85" stroke="#ec4899" stroke-width="1.5"/>
  <rect x="420" y="65" width="80" height="40" rx="6" fill="#4a1060" stroke="#ec4899" stroke-width="1.5"/>
  <text x="460" y="89" text-anchor="middle" font-family="monospace" font-size="9" fill="#f472b6">PHASE 4</text>
  <line x1="500" y1="85" x2="535" y2="85" stroke="#ec4899" stroke-width="1.5"/>
  <rect x="540" y="65" width="80" height="40" rx="6" fill="#3d0f54" stroke="#ec4899" stroke-width="1.5"/>
  <text x="580" y="89" text-anchor="middle" font-family="monospace" font-size="9" fill="#f0abfc">PHASE 5</text>
  <line x1="620" y1="85" x2="655" y2="85" stroke="#a855f7" stroke-width="1.5"/>
  <rect x="660" y="65" width="80" height="40" rx="6" fill="#2d1b4e" stroke="#6366f1" stroke-width="1.5"/>
  <text x="700" y="89" text-anchor="middle" font-family="monospace" font-size="9" fill="#818cf8">PHASE 6</text>
  <!-- Phase bar underline -->
  <rect x="60" y="112" width="680" height="3" rx="2" fill="url(#phase)" opacity="0.6"/>
  <!-- Policy shield icon top -->
  <polygon points="400,22 420,32 420,50 400,58 380,50 380,32" fill="none" stroke="#a855f7" stroke-width="1.5" opacity="0.6"/>
  <text x="400" y="44" text-anchor="middle" font-family="monospace" font-size="9" fill="#c084fc">POL</text>
  <!-- Title -->
  <text x="400" y="168" text-anchor="middle" font-family="monospace" font-size="11" fill="#a855f7" letter-spacing="5" opacity="0.8">PHASEFORM · RUNTIME · v6</text>
</svg>

# ⚡ Phaseform Runtime Package v6

<img src="https://img.shields.io/badge/version-6.0-a855f7?style=for-the-badge&labelColor=0a0014"/>
<img src="https://img.shields.io/badge/language-Python_3.13-6366f1?style=for-the-badge&labelColor=0a0014"/>
<img src="https://img.shields.io/badge/type-Agent_Runtime-ec4899?style=for-the-badge&labelColor=0a0014"/>
<img src="https://img.shields.io/badge/crypto-policy_signing-a855f7?style=for-the-badge&labelColor=0a0014"/>

</div>

---

## Overview

**Phaseform** is a multi-phase agent runtime and policy orchestration engine. It governs how Celestial agents execute across ordered phases, validates cryptographically signed policies, and injects events between phase transitions.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  PHASEFORM RUNTIME v6                   │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Policy   │  │Orchestr- │  │  Event   │              │
│  │ Schema   │─▶│  ator    │─▶│ Injector │              │
│  │ Validator│  │          │  │          │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│        │              │              │                  │
│        ▼              ▼              ▼                  │
│  ┌─────────────────────────────────────────┐           │
│  │         CELESTIAL AGENT RUNTIME         │           │
│  │    agent_spec_crypto  ·  phase gates    │           │
│  └─────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

---

## Key Modules

| Module | Description |
|--------|-------------|
| `orchestrator.py` | Phase sequencing and transition logic |
| `policy_schema.py` | JSON schema validation for phase policies |
| `event_injector.py` | Injects synthetic events between phase gates |
| `celestial_agent/agent_spec_crypto.py` | Signs and verifies agent specifications |
| `_smoke_test.py` | Rapid end-to-end sanity check |

---

## Policies

```json
{
  "phase": 3,
  "intent": "activate_memory_layer",
  "confidence_threshold": 0.85,
  "signed_by": "creator_key",
  "escalation": "human_review"
}
```

Policies are cryptographically signed and validated before any phase executes. See `example_phaseform_policy_v2.json` for a full example.

---

## Quick Start

```bash
cd phaseform_runtime_package_v6
python3 _smoke_test.py
```

---

<div align="center">
<sub>Built by <a href="https://github.com/DeontewattsV1">DeontewattsV1</a> · Celestial Agent Ecosystem</sub>
</div>
