// SPDX-License-Identifier: Apache-2.0
// Shared transport boundary. Checkpoints are never accepted from a client.
import {
  createHats, hatsSnapshot, spawnAgent, revokeAgent, adjudicateAgent,
  verifyHats, exportHatsEvidence, runHatsDemo,
} from './hats.mjs';
import { analyzeHats } from './hats-analytics.mjs';

export const HATS_COMMANDS = new Set(['state', 'evidence', 'reset', 'spawn', 'revoke', 'adjudicate', 'verify', 'demo']);
export const HATS_EVENT_LIMIT = 200;

function problem(code, message, status = 400) {
  return Object.assign(new Error(message), { code, status });
}

export function hatsResponse(state) {
  const snapshot = hatsSnapshot(state);
  return { ...snapshot, analytics: analyzeHats(snapshot) };
}

export function hatsCommand(state, name, input = {}) {
  if (!HATS_COMMANDS.has(name)) throw problem('NOT_FOUND', 'HATS route not found.', 404);
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw problem('INVALID_BODY', 'Send a JSON object.');
  if (['state', 'evidence', 'reset', 'verify', 'demo'].includes(name) && Object.keys(input).length) {
    throw problem('INVALID_BODY', 'This operation accepts no client state or options.');
  }
  if (!['state', 'evidence', 'reset'].includes(name) && hatsSnapshot(state).events.length >= HATS_EVENT_LIMIT) {
    throw problem('EVENT_LIMIT', 'Export evidence and reset the HATS lab to start a new run.', 429);
  }
  const operations = { spawn: spawnAgent, revoke: revokeAgent, adjudicate: adjudicateAgent, verify: verifyHats, demo: runHatsDemo };
  if (name === 'reset') state = createHats({ deployment: hatsSnapshot(state).deployment });
  else if (operations[name]) operations[name](state, input);
  const response = hatsResponse(state);
  if (response.events.length > HATS_EVENT_LIMIT) {
    throw problem('EVENT_LIMIT', 'This operation would exceed the event limit. Export evidence and reset the HATS lab.', 429);
  }
  const body = name === 'evidence'
    ? { ...exportHatsEvidence(state), analytics: response.analytics }
    : response;
  return { state, body };
}
