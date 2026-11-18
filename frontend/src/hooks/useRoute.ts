import { useCallback, useEffect, useState } from 'react'

export type Route = { view: 'digest'; lensId: string | null } | { view: 'system' } | { view: 'saved' }

function parse(hash: string): Route {
  const parts = hash.replace(/^#\/?/, '').split('/').filter(Boolean)
  if (parts[0] === 'system') return { view: 'system' }
  if (parts[0] === 'saved') return { view: 'saved' }
  return { view: 'digest', lensId: parts[0] === 'digest' && parts[1] ? decodeURIComponent(parts[1]) : null }
}

export const hrefFor = (r: Route) =>
  r.view === 'system' ? '#/system' : r.view === 'saved' ? '#/saved' : r.lensId ? `#/digest/${encodeURIComponent(r.lensId)}` : '#/digest'

/** Tiny hash router so views and lenses are linkable without a routing dependency. */
export function useRoute() {
  const [route, setRoute] = useState<Route>(() => parse(window.location.hash))
  useEffect(() => {
    const on = () => setRoute(parse(window.location.hash))
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  const go = useCallback((r: Route) => { window.location.hash = hrefFor(r) }, [])
  return { route, go }
}
