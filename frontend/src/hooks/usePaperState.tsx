import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { api } from '../api'
import type { FeedbackAction, Paper } from '../types'

export interface PaperFlags { read: boolean; skip: boolean; save: boolean }
/** Stored per paper. `paper` is a snapshot taken at the last change so Saved works without re-fetching. */
type Entry = PaperFlags & { paper?: Paper }
const EMPTY: PaperFlags = { read: false, skip: false, save: false }
const KEY = 'polymath.paperState'

interface Ctx {
  flags: (id: string) => PaperFlags
  toggle: (paper: Paper, action: FeedbackAction) => void
  savedCount: number
  /** Saved papers that have a stored snapshot. */
  savedPapers: Paper[]
  /** Ids of saved papers saved before snapshots existed; the Saved view looks these up. */
  savedIdsWithoutSnapshot: string[]
}
const PaperStateContext = createContext<Ctx | null>(null)

function load(): Record<string, Entry> {
  try { return JSON.parse(localStorage.getItem(KEY) ?? '{}') } catch { return {} }
}

/** Read / skip / save state. Local only for now; each change is also reported through the API layer. */
export function PaperStateProvider({ children }: { children: ReactNode }) {
  const [map, setMap] = useState<Record<string, Entry>>(load)

  const toggle = useCallback((paper: Paper, action: FeedbackAction) => {
    const cur = map[paper.id] ?? EMPTY
    const active = !cur[action]
    const next: Entry = { ...cur, [action]: active, paper }
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
    savedPapers: Object.values(map).filter((f) => f.save && f.paper).map((f) => f.paper as Paper),
    savedIdsWithoutSnapshot: Object.entries(map).filter(([, f]) => f.save && !f.paper).map(([id]) => id),
  }), [map, toggle])

  return <PaperStateContext.Provider value={value}>{children}</PaperStateContext.Provider>
}

export function usePaperState() {
  const ctx = useContext(PaperStateContext)
  if (!ctx) throw new Error('usePaperState must be used inside PaperStateProvider')
  return ctx
}
