import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { api } from '../api'
import type { FeedbackAction, Paper } from '../types'

export interface PaperFlags { read: boolean; skip: boolean; save: boolean }
const EMPTY: PaperFlags = { read: false, skip: false, save: false }
const KEY = 'polymath.paperState'

interface Ctx {
  flags: (id: string) => PaperFlags
  toggle: (paper: Paper, action: FeedbackAction) => void
  savedCount: number
}
const PaperStateContext = createContext<Ctx | null>(null)

function load(): Record<string, PaperFlags> {
  try { return JSON.parse(localStorage.getItem(KEY) ?? '{}') } catch { return {} }
}

/** Read / skip / save state. Local only for now; each change is also reported through the API layer. */
export function PaperStateProvider({ children }: { children: ReactNode }) {
  const [map, setMap] = useState<Record<string, PaperFlags>>(load)

  const toggle = useCallback((paper: Paper, action: FeedbackAction) => {
    const cur = map[paper.id] ?? EMPTY
    const active = !cur[action]
    const next: PaperFlags = { ...cur, [action]: active }
    // Skip and save are opposites.
    if (active && action === 'skip') next.save = false
    if (active && action === 'save') next.skip = false
    const out = { ...map, [paper.id]: next }
    setMap(out)
    try { localStorage.setItem(KEY, JSON.stringify(out)) } catch { /* ignore */ }
    void api.sendFeedback({ paperId: paper.id, lensId: paper.lensId, action, active, at: new Date().toISOString() })
  }, [map])

  const value = useMemo<Ctx>(() => ({
    flags: (id) => map[id] ?? EMPTY,
    toggle,
    savedCount: Object.values(map).filter((f) => f.save).length,
  }), [map, toggle])

  return <PaperStateContext.Provider value={value}>{children}</PaperStateContext.Provider>
}

export function usePaperState() {
  const ctx = useContext(PaperStateContext)
  if (!ctx) throw new Error('usePaperState must be used inside PaperStateProvider')
  return ctx
}
