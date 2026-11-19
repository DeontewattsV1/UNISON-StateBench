// SPDX-License-Identifier: Apache-2.0
import { DatabaseSync } from 'node:sqlite';
import { createHats, checkpointHats, restoreHats, hatsSnapshot } from './hats.mjs';
import { hatsCommand } from './hats-service.mjs';

/** Local demo: SQLite memory database, separate from the public Durable Object. */
export function createHatsStore() {
  const db = new DatabaseSync(':memory:');
  db.exec(`CREATE TABLE hats_state (session_id TEXT PRIMARY KEY, checkpoint TEXT NOT NULL);
    CREATE TABLE hats_events (session_id TEXT NOT NULL, run_id TEXT NOT NULL,
      seq INTEGER NOT NULL, event_json TEXT NOT NULL, PRIMARY KEY(session_id, run_id, seq));`);
  return {
    delete(sessionId) {
      db.prepare('DELETE FROM hats_events WHERE session_id = ?').run(sessionId);
      db.prepare('DELETE FROM hats_state WHERE session_id = ?').run(sessionId);
    },
    close() { db.close(); },
    command(sessionId, name, input) {
      db.exec('BEGIN IMMEDIATE');
      try {
        const row = db.prepare('SELECT checkpoint FROM hats_state WHERE session_id = ?').get(sessionId);
        let state;
        if (row && name !== 'reset') {
          try {
            state = restoreHats(JSON.parse(row.checkpoint));
            const events = db.prepare('SELECT event_json FROM hats_events WHERE session_id = ? AND run_id = ? ORDER BY seq').all(sessionId, state.runId);
            if (JSON.stringify(events.map(event => JSON.parse(event.event_json))) !== JSON.stringify(hatsSnapshot(state).events)) throw new Error();
          } catch {
            throw Object.assign(new Error('Stored HATS evidence failed its integrity check. Reset the lab to start a new run.'), { code: 'CHECKPOINT_INVALID', status: 409 });
          }
        } else state = createHats();
        const result = hatsCommand(state, name, input);
        const snapshot = hatsSnapshot(result.state);
        if (name === 'reset') db.prepare('DELETE FROM hats_events WHERE session_id = ?').run(sessionId);
        const insert = db.prepare('INSERT OR IGNORE INTO hats_events(session_id, run_id, seq, event_json) VALUES (?, ?, ?, ?)');
        for (const event of snapshot.events) insert.run(sessionId, snapshot.runId, event.seq, JSON.stringify(event));
        db.prepare('INSERT INTO hats_state VALUES (?, ?) ON CONFLICT(session_id) DO UPDATE SET checkpoint = excluded.checkpoint').run(sessionId, JSON.stringify(checkpointHats(result.state)));
        db.exec('COMMIT');
        return result.body;
      } catch (error) {
        db.exec('ROLLBACK');
        throw error;
      }
    },
  };
}
