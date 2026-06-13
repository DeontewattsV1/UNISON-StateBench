<div align="center">

<svg width="800" height="180" viewBox="0 0 800 180" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="bg4" cx="50%" cy="50%" r="70%">
      <stop offset="0%" stop-color="#001a1a"/>
      <stop offset="100%" stop-color="#000a0a"/>
    </radialGradient>
    <filter id="glow4">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <radialGradient id="pulse" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#00ffd5" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="#00ffd5" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="800" height="180" fill="url(#bg4)" rx="16"/>
  <!-- Concentric field rings -->
  <circle cx="400" cy="90" r="75" fill="none" stroke="#00ffd5" stroke-width="0.5" opacity="0.15"/>
  <circle cx="400" cy="90" r="60" fill="none" stroke="#00ffd5" stroke-width="0.5" opacity="0.2"/>
  <circle cx="400" cy="90" r="45" fill="none" stroke="#00ffd5" stroke-width="1" opacity="0.3"/>
  <circle cx="400" cy="90" r="30" fill="none" stroke="#00ffd5" stroke-width="1.5" opacity="0.5"/>
  <circle cx="400" cy="90" r="15" fill="url(#pulse)"/>
  <circle cx="400" cy="90" r="6" fill="#00ffd5" filter="url(#glow4)"/>
  <!-- Field perception points -->
  <circle cx="340" cy="65" r="4" fill="#00ffd5" opacity="0.6" filter="url(#glow4)"/>
  <circle cx="460" cy="65" r="4" fill="#00ffd5" opacity="0.6" filter="url(#glow4)"/>
  <circle cx="340" cy="115" r="4" fill="#00b8a0" opacity="0.6"/>
  <circle cx="460" cy="115" r="4" fill="#00b8a0" opacity="0.6"/>
  <circle cx="310" cy="90" r="3" fill="#00ffd5" opacity="0.4"/>
  <circle cx="490" cy="90" r="3" fill="#00ffd5" opacity="0.4"/>
  <!-- Scan lines -->
  <line x1="130" y1="55" x2="310" y2="75" stroke="#00ffd5" stroke-width="1" opacity="0.2" stroke-dasharray="4 4"/>
  <line x1="130" y1="90" x2="325" y2="90" stroke="#00ffd5" stroke-width="1" opacity="0.15" stroke-dasharray="4 4"/>
  <line x1="490" y1="90" x2="670" y2="90" stroke="#00ffd5" stroke-width="1" opacity="0.15" stroke-dasharray="4 4"/>
  <!-- V2/V3 labels -->
  <rect x="80" y="60" width="50" height="22" rx="4" fill="#001a1a" stroke="#00ffd5" stroke-width="1"/>
  <text x="105" y="75" text-anchor="middle" font-family="monospace" font-size="10" fill="#00ffd5">v2</text>
  <rect x="670" y="60" width="50" height="22" rx="4" fill="#001a1a" stroke="#00b8a0" stroke-width="1"/>
  <text x="695" y="75" text-anchor="middle" font-family="monospace" font-size="10" fill="#00b8a0">v3</text>
  <!-- Title -->
  <text x="400" y="168" text-anchor="middle" font-family="monospace" font-size="11" fill="#00ffd5" letter-spacing="6" opacity="0.7">RECOGNITIVE · FIELD · SYSTEM</text>
</svg>

# 🌐 Recognitive Field

<img src="https://img.shields.io/badge/version-v2_%7C_v3-00ffd5?style=for-the-badge&labelColor=001a1a"/>
<img src="https://img.shields.io/badge/runtime-browser-00b8a0?style=for-the-badge&labelColor=001a1a"/>
<img src="https://img.shields.io/badge/deps-zero-00ffd5?style=for-the-badge&labelColor=001a1a"/>
<img src="https://img.shields.io/badge/ecosystem-Celestial_Agent-00b8a0?style=for-the-badge&labelColor=001a1a"/>

</div>

---

## Overview

**Recognitive Field** is a spatial cognitive interface — a self-contained HTML visualization of environmental perception and awareness mapping for AI agents. Each "field" renders a live model of how an agent senses, weights, and responds to its environment.

Zero dependencies. Open in any browser and it runs.

---

## Files

| File | Version | Description |
|------|---------|-------------|
| `recognitive-field-v2.html` | v2 | Stable reference — core field rendering and interaction model |
| `recognitive-field-v3.html` | v3 | Current — enhanced perception layers, improved resolution and UX |

---

## Quick Start

```bash
# Just open in your browser
open recognitive-field-v3.html

# Or serve locally
python3 -m http.server 8080
# then visit http://localhost:8080/recognitive-field-v3.html
```

---

## What Is a Recognitive Field?

```
                    ┌─────────────────────────────┐
                    │      PERCEPTION SPACE        │
                    │                             │
                    │   ····················      │
                    │   ·    high weight   ·      │
                    │   ·  ┌────────────┐  ·      │
                    │   ·  │  AGENT     │  ·      │
                    │   ·  │  CORE      │  ·      │
                    │   ·  └────────────┘  ·      │
                    │   ·   low weight    ·      │
                    │   ····················      │
                    │                             │
                    └─────────────────────────────┘
```

The field maps the agent's awareness — closer objects carry higher perceptual weight, edge regions fade to ambient detection.

---

## Part of the Celestial Ecosystem

- [`celestial_agent_desktop_upgrade`](https://github.com/DeontewattsV1/celestial_agent_desktop_upgrade) — Full agent runtime
- [`phaseform_runtime_package_v6`](https://github.com/DeontewattsV1/phaseform_runtime_package_v6) — Phase policy engine
- [`AISoulFrameworkConcepts`](https://github.com/DeontewattsV1/AISoulFrameworkConcepts) — Foundational architecture

---

<div align="center">
<sub>Built by <a href="https://github.com/DeontewattsV1">DeontewattsV1</a></sub>
</div>
