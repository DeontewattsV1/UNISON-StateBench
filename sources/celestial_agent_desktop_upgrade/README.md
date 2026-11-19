<div align="center">

<svg width="800" height="180" viewBox="0 0 800 180" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="bg6" cx="50%" cy="50%" r="70%">
      <stop offset="0%" stop-color="#00081a"/>
      <stop offset="100%" stop-color="#000510"/>
    </radialGradient>
    <filter id="glow6">
      <feGaussianBlur stdDeviation="5" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <radialGradient id="star1" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="100%" stop-color="#60a5fa" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="800" height="180" fill="url(#bg6)" rx="16"/>
  <!-- Star field -->
  <circle cx="80" cy="30" r="1" fill="white" opacity="0.6"/>
  <circle cx="150" cy="55" r="1.5" fill="white" opacity="0.8"/>
  <circle cx="220" cy="20" r="1" fill="white" opacity="0.4"/>
  <circle cx="600" cy="25" r="1.5" fill="white" opacity="0.7"/>
  <circle cx="680" cy="50" r="1" fill="white" opacity="0.5"/>
  <circle cx="740" cy="30" r="1" fill="white" opacity="0.8"/>
  <circle cx="720" cy="140" r="1" fill="white" opacity="0.4"/>
  <circle cx="100" cy="150" r="1" fill="white" opacity="0.6"/>
  <circle cx="50" cy="100" r="1.5" fill="white" opacity="0.5"/>
  <!-- Central celestial body -->
  <circle cx="400" cy="85" r="45" fill="#001830" stroke="#1d4ed8" stroke-width="1" opacity="0.6"/>
  <circle cx="400" cy="85" r="32" fill="#001040" stroke="#3b82f6" stroke-width="1.5"/>
  <circle cx="400" cy="85" r="18" fill="#002060" stroke="#60a5fa" stroke-width="1" filter="url(#glow6)"/>
  <circle cx="400" cy="85" r="8" fill="#3b82f6" filter="url(#glow6)"/>
  <!-- Orbit ring -->
  <ellipse cx="400" cy="85" rx="65" ry="20" fill="none" stroke="#60a5fa" stroke-width="1" stroke-dasharray="5 3" opacity="0.4"/>
  <!-- Satellite -->
  <circle cx="465" cy="85" r="5" fill="#93c5fd" filter="url(#glow6)"/>
  <!-- Constellation lines left -->
  <line x1="80" y1="30" x2="150" y2="55" stroke="#1d4ed8" stroke-width="0.5" opacity="0.3"/>
  <line x1="150" y1="55" x2="220" y2="20" stroke="#1d4ed8" stroke-width="0.5" opacity="0.3"/>
  <!-- Desktop frame bottom right -->
  <rect x="610" y="60" width="140" height="90" rx="6" fill="#050e1a" stroke="#1d4ed8" stroke-width="1.5" opacity="0.8"/>
  <rect x="610" y="60" width="140" height="16" rx="6" fill="#0a1f40"/>
  <rect x="738" y="66" width="6" height="6" rx="1" fill="#ef4444" opacity="0.7"/>
  <circle cx="618" cy="142" r="3" fill="#1d4ed8"/>
  <rect x="615" y="136" width="80" height="3" rx="1" fill="#1d4ed8" opacity="0.4"/>
  <rect x="615" y="125" width="120" height="3" rx="1" fill="#3b82f6" opacity="0.3"/>
  <rect x="615" y="115" width="100" height="3" rx="1" fill="#60a5fa" opacity="0.2"/>
  <rect x="615" y="105" width="110" height="3" rx="1" fill="#3b82f6" opacity="0.3"/>
  <text x="680" y="74" text-anchor="middle" font-family="monospace" font-size="8" fill="#60a5fa">CELESTIAL v2</text>
  <!-- Title -->
  <text x="400" y="168" text-anchor="middle" font-family="monospace" font-size="11" fill="#60a5fa" letter-spacing="5" opacity="0.8">CELESTIAL · AGENT · DESKTOP</text>
</svg>

# 🌌 Celestial Agent Desktop Upgrade

<img src="https://img.shields.io/badge/version-2.0-3b82f6?style=for-the-badge&labelColor=00081a"/>
<img src="https://img.shields.io/badge/language-Python_3.13-60a5fa?style=for-the-badge&labelColor=00081a"/>
<img src="https://img.shields.io/badge/platform-Desktop-1d4ed8?style=for-the-badge&labelColor=00081a"/>
<img src="https://img.shields.io/badge/type-AI_Agent_Runtime-93c5fd?style=for-the-badge&labelColor=00081a"/>

</div>

---

## Overview

**Celestial Agent Desktop Upgrade** is a standalone desktop runtime for the Celestial AI agent — a self-directed, task-executing agent designed to run locally, process commands, and operate autonomously on your machine.

This upgrade package brings the Celestial core to the desktop with improved command handling, cross-platform launch scripts, and an extensible architecture.

---

## Architecture

```
┌──────────────────────────────────────────┐
│           CELESTIAL DESKTOP v2           │
│                                          │
│  ┌─────────────┐   ┌───────────────────┐ │
│  │   app.py    │──▶│  celestial_core   │ │
│  │  (entry pt) │   │  (agent engine)   │ │
│  └─────────────┘   └───────────────────┘ │
│         │                   │            │
│         ▼                   ▼            │
│  ┌────────────┐   ┌──────────────────┐   │
│  │  CLI loop  │   │  Task Executor   │   │
│  │  commands  │   │  Memory · State  │   │
│  └────────────┘   └──────────────────┘   │
└──────────────────────────────────────────┘
```

---

## Files

| File | Description |
|------|-------------|
| `app.py` | Main entry point — launches the Celestial agent |
| `celestial_core.py` | Core agent engine — reasoning, memory, task execution |
| `run.sh` | macOS / Linux launch script |
| `run_windows.bat` | Windows launch script |
| `requirements.txt` | Python dependencies |
| `examples/demo_commands.txt` | Sample commands to get started |

---

## Quick Start

```bash
# macOS / Linux
pip install -r requirements.txt
./run.sh

# Windows
pip install -r requirements.txt
run_windows.bat
```

---

## Related

- [`phaseform_runtime_package_v6`](https://github.com/DeontewattsV1/phaseform_runtime_package_v6) — Phase policy engine
- [`files9`](https://github.com/DeontewattsV1/files9) — Recognitive field visualization
- [`AISoulFrameworkConcepts`](https://github.com/DeontewattsV1/AISoulFrameworkConcepts) — Foundational architecture

---

<div align="center">
<sub>Built by <a href="https://github.com/DeontewattsV1">DeontewattsV1</a> · Celestial Agent Ecosystem</sub>
</div>
