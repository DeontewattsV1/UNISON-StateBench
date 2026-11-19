import { useCallback, useEffect, useRef, useState } from 'react';

async function request(path, body, signal) {
  const response = await fetch(`/api/hats${path ? `/${path}` : ''}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.error?.message || `The HATS request could not complete (${response.status}).`);
  return data;
}

// Keep this lab independent of the revocation sandbox. A late read may never
// replace a newer mutation; a ref also locks controls before React re-renders.
export function useHats() {
  const [state, setState] = useState(null);
  const [pending, setPending] = useState(null);
  const [error, setError] = useState(null);
  const active = useRef(false);
  const busy = useRef(false);
  const sequence = useRef(0);

  const refresh = useCallback(async (signal) => {
    if (busy.current) return;
    const ticket = ++sequence.current;
    setError(null);
    try {
      const next = await request('', undefined, signal);
      if (active.current && ticket === sequence.current) setState(next);
    } catch (err) {
      if (active.current && ticket === sequence.current && err.name !== 'AbortError') setError(err.message);
    }
  }, []);

  useEffect(() => {
    active.current = true;
    const controller = new AbortController();
    refresh(controller.signal);
    return () => { active.current = false; sequence.current += 1; controller.abort(); };
  }, [refresh]);

  const act = useCallback(async (name, body = {}) => {
    if (busy.current) return null;
    busy.current = true;
    const ticket = ++sequence.current;
    setPending(name);
    setError(null);
    try {
      const next = await request(name, body);
      if (active.current && ticket === sequence.current) {
        setState(next);
        return next;
      }
      return null;
    } catch (err) {
      if (active.current && ticket === sequence.current) setError(err.message);
      return null;
    } finally {
      busy.current = false;
      if (active.current && ticket === sequence.current) setPending(null);
    }
  }, []);

  return { state, pending, error, act, refresh: () => refresh() };
}
