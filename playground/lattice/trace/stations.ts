export type StationKind = "implemented" | "concept" | "advisory";

export type Station = {
  id: string;
  index: string;
  short: string;
  label: string;
  repo: string;
  kind: StationKind;
  blurb: string;
  place: string;
};

/** Serpentine floor: row 1 left-to-right, row 2 right-to-left, row 3 left-to-right. */
export const STATIONS: Station[] = [
  {
    id: "claim-intake",
    index: "01",
    short: "Intake",
    label: "Claim intake",
    repo: "UNISON-StateBench",
    kind: "implemented",
    blurb: "A new claim always enters as unknown. It is never born known.",
    place: "col-start-1 row-start-1",
  },
  {
    id: "evidence-attach",
    index: "02",
    short: "Attach",
    label: "Evidence attach",
    repo: "UNISON-StateBench",
    kind: "implemented",
    blurb: "Each evidence item is hashed with SHA-256 before it can be cited.",
    place: "col-start-2 row-start-1",
  },
  {
    id: "evidence-window",
    index: "03",
    short: "Window",
    label: "Evidence window",
    repo: "AGI-CP",
    kind: "implemented",
    blurb: "Port of capability-gateway evidence collection. Expected observers must agree inside the window.",
    place: "col-start-3 row-start-1",
  },
  {
    id: "traceability-link",
    index: "04",
    short: "Matrix",
    label: "Traceability link",
    repo: "traceability-matrix",
    kind: "concept",
    blurb: "Illustrative. The source has RTM documents, not linking code.",
    place: "col-start-4 row-start-1",
  },
  {
    id: "governance-gate",
    index: "05",
    short: "Govern",
    label: "Governance gate",
    repo: "SOVEREIGN-LATTICE-GOVCORE",
    kind: "implemented",
    blurb: "Port of GovernanceKernel.evaluate_operating_mode, plus RULE-003: scenario output cannot be promoted.",
    place: "col-start-4 row-start-2",
  },
  {
    id: "noncollapse-check",
    index: "06",
    short: "Hold",
    label: "Non-collapse",
    repo: "UNISON-StateBench",
    kind: "implemented",
    blurb: "Simplified port of state_collapse.py. Unknown does not become known without a satisfied boundary.",
    place: "col-start-3 row-start-2",
  },
  {
    id: "phaseform-step",
    index: "07",
    short: "Phase",
    label: "Phaseform step",
    repo: "phaseform_runtime_package_v6",
    kind: "implemented",
    blurb: "Policy schema check and event-to-action mapping. No file I/O.",
    place: "col-start-2 row-start-2",
  },
  {
    id: "linguistic-transform",
    index: "08",
    short: "Glyph",
    label: "Linguistic transform",
    repo: "Linguistic-Encryption-System-Celestial-",
    kind: "implemented",
    blurb: "Glyph map plus a one-time pad derived from the demo seed, with a round-trip check.",
    place: "col-start-1 row-start-2",
  },
  {
    id: "recognitive-field",
    index: "09",
    short: "Field",
    label: "Recognitive field",
    repo: "Recognitive-field",
    kind: "advisory",
    blurb: "Seeded probe of the dynamical field. It is a visual model, not evidence, so it never gates promotion.",
    place: "col-start-1 row-start-3",
  },
  {
    id: "celestial-agent",
    index: "10",
    short: "Desk",
    label: "Celestial agent",
    repo: "celestial_agent_desktop_upgrade",
    kind: "implemented",
    blurb: "In-memory workspace: codec, safe paths, and the command parser. MAKE FUNCTION is not ported.",
    place: "col-start-2 row-start-3",
  },
  {
    id: "agi-cp-capability",
    index: "11",
    short: "Frame",
    label: "Capability frame",
    repo: "AGI-CP",
    kind: "concept",
    blurb: "Placeholder. Capability-request semantics are summarised; only the evidence window is a code port.",
    place: "col-start-3 row-start-3",
  },
  {
    id: "ai-soul",
    index: "12",
    short: "Soul",
    label: "Framework concepts",
    repo: "AISoulFrameworkConcepts",
    kind: "concept",
    blurb: "Placeholder. A concept document. No runnable code was ported.",
    place: "col-start-4 row-start-3",
  },
];
