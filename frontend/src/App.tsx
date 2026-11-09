import { useEffect } from 'react'
import { api, SAMPLE_MODE } from './api'
import { Header } from './components/Header'
import { ErrorNote, Skeleton } from './components/ui'
import { APP_NAME } from './config/app'
import { PaperStateProvider } from './hooks/usePaperState'
import { useAsync } from './hooks/useAsync'
import { useRoute } from './hooks/useRoute'
import { useTheme } from './hooks/useTheme'
import { DigestView } from './views/DigestView'
import { SystemView } from './views/SystemView'

function Shell() {
  const { theme, toggle } = useTheme()
  const { route, go } = useRoute()
  const { data: lenses, error, reload } = useAsync(() => api.getLenses(), [])

  const active = lenses?.find((l) => route.view === 'digest' && l.id === route.lensId) ?? lenses?.[0]

  // The page accent follows the active lens; the system page uses the first lens's accent.
  useEffect(() => {
    if (active) document.documentElement.style.setProperty('--accent', active.accent)
  }, [active])

  if (error) return <div className="mx-auto max-w-xl p-8"><ErrorNote error={error} onRetry={reload} /></div>
  if (!lenses || !active) {
    return <div className="mx-auto max-w-6xl space-y-4 p-8" aria-busy><Skeleton className="h-8 w-48" /><Skeleton className="h-64 w-full" /></div>
  }

  return (
    <>
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-surface focus:px-3 focus:py-1">
        Skip to content
      </a>
      <Header
        lenses={lenses}
        activeLensId={active.id}
        route={route}
        theme={theme}
        onToggleTheme={toggle}
        onSelectLens={(id) => go({ view: 'digest', lensId: id })}
      />
      <main id="main" className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
        {route.view === 'system' ? <SystemView lenses={lenses} /> : <DigestView lens={active} lenses={lenses} />}
      </main>
      <footer className="mx-auto max-w-6xl px-4 pb-10 text-xs text-muted sm:px-6">
        {SAMPLE_MODE
          ? `${APP_NAME} front end · every paper shown is placeholder content until a backend is connected.`
          : `${APP_NAME} · live data from the local index. Stage-1 ranking only.`}
      </footer>
    </>
  )
}

export default function App() {
  return (
    <PaperStateProvider>
      <Shell />
    </PaperStateProvider>
  )
}
