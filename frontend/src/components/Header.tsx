import type { Lens } from '../types'
import { APP_NAME, ASSISTANT_NAME, BUILD } from '../config/app'
import { hrefFor, type Route } from '../hooks/useRoute'
import { usePaperState } from '../hooks/usePaperState'

interface Props {
  lenses: Lens[]
  activeLensId: string
  route: Route
  theme: 'light' | 'dark'
  onToggleTheme: () => void
  onSelectLens: (id: string) => void
}

function Mark() {
  return (
    <svg viewBox="0 0 32 32" className="size-7" aria-hidden>
      <rect width="32" height="32" rx="7" fill="var(--accent)" />
      <circle cx="16" cy="16" r="7" fill="none" stroke="var(--paper)" strokeWidth="2" />
      <circle cx="16" cy="16" r="2.5" fill="var(--paper)" />
    </svg>
  )
}

function LensTabs({ lenses, activeLensId, onSelect, disabled }: { lenses: Lens[]; activeLensId: string; onSelect: (id: string) => void; disabled: boolean }) {
  // Roving tabindex + arrow keys, per the WAI-ARIA tabs pattern.
  const onKeyDown = (e: React.KeyboardEvent, i: number) => {
    let n = i
    if (e.key === 'ArrowRight') n = (i + 1) % lenses.length
    else if (e.key === 'ArrowLeft') n = (i - 1 + lenses.length) % lenses.length
    else if (e.key === 'Home') n = 0
    else if (e.key === 'End') n = lenses.length - 1
    else return
    e.preventDefault()
    onSelect(lenses[n].id)
    requestAnimationFrame(() => document.getElementById(`lens-tab-${lenses[n].id}`)?.focus())
  }
  return (
    <div role="tablist" aria-label="Lens" className="scrollbar-none -mx-4 flex gap-1 overflow-x-auto px-4 sm:mx-0 sm:px-0">
      {lenses.map((l, i) => {
        const active = l.id === activeLensId && !disabled
        return (
          <button
            key={l.id}
            id={`lens-tab-${l.id}`}
            role="tab"
            aria-selected={active}
            aria-controls="main"
            tabIndex={active || (disabled && i === 0) ? 0 : -1}
            onClick={() => onSelect(l.id)}
            onKeyDown={(e) => onKeyDown(e, i)}
            title={l.description}
            className={`group flex shrink-0 items-center gap-2 border-b-2 px-3 py-2 text-sm transition-colors ${
              active ? 'border-accent font-medium text-ink' : 'border-transparent text-muted hover:text-ink'
            }`}
          >
            <span aria-hidden className="size-2.5 rounded-full" style={{ background: l.accent, opacity: active ? 1 : 0.55 }} />
            <span className="sm:hidden">{l.shortName}</span>
            <span className="hidden sm:inline">{l.name}</span>
          </button>
        )
      })}
    </div>
  )
}

export function Header({ lenses, activeLensId, route, theme, onToggleTheme, onSelectLens }: Props) {
  const { savedCount } = usePaperState()
  const navLink = (r: Route, label: string, current: boolean) => (
    <a
      href={hrefFor(r)}
      aria-current={current ? 'page' : undefined}
      className={`rounded px-2.5 py-1 text-sm ${current ? 'bg-accent-soft font-medium text-accent-ink' : 'text-muted hover:text-ink'}`}
    >
      {label}
    </a>
  )

  return (
    <header className="sticky top-0 z-20 border-b border-rule bg-paper/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-4 pt-3 sm:px-6">
        <a href="#/digest" className="flex items-center gap-2.5 rounded">
          <Mark />
          <span className="font-serif text-2xl font-medium tracking-tight">{APP_NAME}</span>
        </a>
        <nav aria-label="Primary" className="flex gap-1">
          {navLink({ view: 'digest', lensId: activeLensId }, 'Digest', route.view === 'digest')}
          {navLink({ view: 'system' }, 'System', route.view === 'system')}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          {savedCount > 0 && (
            <span className="hidden font-mono text-xs text-muted sm:inline" aria-live="polite">{savedCount} saved</span>
          )}
          <span
            className="hidden rounded border border-rule px-2 py-0.5 font-mono text-[11px] uppercase tracking-wider text-muted md:inline"
            title="Set with VITE_BUILD"
          >
            {BUILD} build
          </span>
          <button
            type="button"
            disabled
            aria-label={`Voice assistant ${ASSISTANT_NAME}: coming later`}
            className="flex cursor-not-allowed items-center gap-1.5 rounded-md border border-dashed border-rule px-2.5 py-1 text-sm text-muted opacity-70"
          >
            <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden>
              <rect x="9" y="3" width="6" height="11" rx="3" />
              <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
            </svg>
            <span className="hidden sm:inline">Voice</span>
            <span className="font-mono text-[10px] uppercase tracking-wider">coming later</span>
          </button>
          <button
            type="button"
            onClick={onToggleTheme}
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            className="grid size-8 place-items-center rounded-md border border-rule text-muted hover:text-ink"
          >
            {theme === 'dark' ? (
              <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden>
                <circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
              </svg>
            )}
          </button>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <LensTabs lenses={lenses} activeLensId={activeLensId} onSelect={onSelectLens} disabled={route.view === 'system'} />
      </div>
    </header>
  )
}
