import { useCallback, useEffect, useState } from 'react'

interface State<T> { data: T | null; error: Error | null; loading: boolean }

/** Runs an async function whenever `deps` change. Stale results are discarded. */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [state, setState] = useState<State<T>>({ data: null, error: null, loading: true })
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    let cancelled = false
    setState({ data: null, error: null, loading: true })
    fn().then(
      (data) => { if (!cancelled) setState({ data, error: null, loading: false }) },
      (error: Error) => { if (!cancelled) setState({ data: null, error, loading: false }) },
    )
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce])

  const reload = useCallback(() => setNonce((n) => n + 1), [])
  return { ...state, reload }
}
