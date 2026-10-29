# UNISON Guardian UI design specification

Source concept: an AI-generated desktop design at 1536 × 1024, compared with the implemented browser screen. The application renders native HTML/SVG components rather than a screenshot.

## Tokens and composition

- Midnight navy fixed sidebar, approximately 232 px wide; true-white workspace panels, pale cool-gray page and dotted graph canvas. No gradient or photographic assets.
- Blue primary controls and active graph links; navy ink; cool blue-gray body copy; pale gray borders, restrained 6–8 px corners, no decorative shadows.
- System/Inter-style sans family. Heading 34 px/700; panel headings 21 px/650; controls 14 px/550; body 14 px/1.5. Technical IDs 12 px monospace.
- Primary screen: top heading and two actions, slim scenario rail, two-column authority graph/revocation test, then evidence ledger. Sidebar nav and sandbox footer remain consistent.
- Graph is implemented using code-native node text, outline Lucide icons, and SVG directed paths. All UI text remains real HTML/SVG.

## Visible copy inventory

- Brand: UNISON / Guardian.
- Navigation: Authority graph; Evidence ledger; Agent identity; How it works.
- Header: Authority, made verifiable. / Test whether revoked permissions can still reach a protected action.
- Actions: Run baseline; Export evidence; Reset sandbox; Revoke authority; Replay queued action.
- Scenario: Queued delegation. Additional requested operating cases: Alternate authority path; Incomplete inventory.
- Authority graph; Registered paths. Nodes: Operator, Planner agent, Delegate agent, Tool gateway, Protected action, Queue.
- Revocation test; Authority is checked again when an action commits.
- Awaiting verification; Bounded to registered paths.
- Evidence ledger; Event; Evidence; Detail.
- Sidebar: Local sandbox; Synthetic actions only.
- Footer statement: A model proposal is never an authorization.

## Necessary functional extensions

- Run verification action provides a repeatable deterministic check after replay.
- Ask Muse is an expandable model-analysis section, required by the user's Meta integration requirement. Its output is explicitly a proposal, separated from deterministic results. Missing credentials are displayed as unavailable; no fake model output.
- Evidence rows use actual local runtime event time/ID and outcomes rather than sample image timestamps/IDs.
- Navigation reveals full ledger filters, identity separation, and verification boundaries.
- Mobile collapses sidebar to a top navigation and stacks graph/test panels, preserving graph legibility and avoiding page overflow.

## Components and state

- App shell and header; reusable button/notice/status primitives; scenario rail; authority graph; revocation workflow; model proposal; ledger; identity view; scope explainer.
- API state is the source of truth. No simulated API success, invented measurement, authority grant from model, or local persistence of credentials.
- Loading, pending actions, missing API credentials, and network failures have explicit readable states.

## Fidelity and interaction review

Compared the generated full-screen concept with actual Chromium screenshots at 1536 × 1024; mobile tested at 390 × 844. Browser extension JavaScript runtime was not exposed, so Playwright with local Chromium supplied rendering and interaction evidence.

| Comparison | Implemented result |
| --- | --- |
| Layout | Preserved navy sidebar, header/actions, scenario rail, two-column graph/test workspace, and lower ledger. |
| Typography | Enlarged graph node titles/body, ledger details, and controls after screenshot review; kept the concept's heading hierarchy. |
| Palette | Preserved navy, white panels, pale cool gray, blue actions, and thin neutral borders; no hero imagery or gradients. |
| Components/icons | Code-native graph nodes, directed paths, outline Lucide controls and information icon; no screenshot-based UI. |
| Copy | Core header, navigation and CTA copy retained. Runtime data replaces invented sample rows and timestamps. |
| Responsive layout | Sidebar collapses, workspace stacks, scenario select remains readable, graph and ledger scroll internally with no page overflow. |

Intentional functional extensions: Ask Muse and Run verification controls, observed action/queue counters, actual bounded check results, node inspection, incomplete-coverage explanation, and mobile graph scroll guidance. The main claim is limited to synthetic registered routes. A blocked queue attempt does not increase the displayed synthetic action counter.
