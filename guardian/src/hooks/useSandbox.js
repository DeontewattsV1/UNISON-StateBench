import { useCallback, useEffect, useRef, useState } from 'react';

function stateFrom(data) {
  if (data?.state?.nodes) return data.state;
  if (data?.sandbox?.nodes) return data.sandbox;
  return data;
}

async function request(path, body, signal) {
  const response = await fetch(`/api/${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(data?.error?.message || data?.message || `The request could not complete (${response.status}).`);
    error.code = data?.error?.code;
    throw error;
  }
  return data;
}

export function useSandbox() {
  const [state, setState] = useState(null);
  const [health, setHealth] = useState(null);
  const [pending, setPending] = useState(null);
  const [error, setError] = useState(null);
  const [proposal, setProposal] = useState(null);
  const [modelError, setModelError] = useState(null);
  const mounted = useRef(true);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const next = await request('state');
      if (mounted.current) setState(stateFrom(next));
    } catch (err) {
      if (mounted.current) setError(err.message);
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    refresh();
    request('health').then(data => { if (mounted.current) setHealth(data); }).catch(() => {});
    return () => { mounted.current = false; };
  }, [refresh]);

  // A proposal is tied to the exact run and revision sent to the provider.
  // State changes invalidate it; model text never becomes current authority.
  useEffect(() => {
    if (!state) return;
    setProposal(current => current && (
      current.analyzedRunId !== state.runId ||
      current.analyzedRevision !== state.revision
    ) ? null : current);
  }, [state?.runId, state?.revision]);

  const act = useCallback(async (name, body = {}) => {
    if (pending) return;
    setPending(name);
    setError(null);
    try {
      let next = await request(name, body);
      if (name === 'replay') next = await request('verify', {});
      if (mounted.current) {
        setState(stateFrom(next));
        if (name === 'reset') { setProposal(null); setModelError(null); }
      }
    } catch (err) {
      if (mounted.current) setError(err.message);
    } finally {
      if (mounted.current) setPending(null);
    }
  }, [pending]);

  const analyze = useCallback(async () => {
    if (pending) return;
    setPending('analyze');
    setModelError(null);
    try {
      const result = await request('analyze', {});
      if (mounted.current) setProposal(result);
    } catch (err) {
      if (mounted.current) {
        setModelError(err.message);
        if (err.code === 'META_NOT_CONFIGURED') setHealth(h => ({ ...h, meta: { ...h?.meta, configured: false } }));
      }
    } finally {
      if (mounted.current) setPending(null);
    }
  }, [pending]);

  return { state, health, pending, error, proposal, modelError, refresh, act, analyze };
}
