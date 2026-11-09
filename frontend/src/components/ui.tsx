import { SAMPLE_MODE } from '../api'
import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from 'react'

/** Visible on every surface that renders placeholder content. */
export function SampleBadge({ className = '' }: { className?: string }) {
  if (!SAMPLE_MODE) return null // real backend: nothing here is placeholder
  return (
    <Tooltip content="Placeholder content for layout and testing. Nothing here is a real paper, citation, or measurement.">
      <span
        className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border border-dashed border-warn px-2 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wider text-warn bg-warn-soft ${className}`}
      >
        <span aria-hidden className="size-1.5 rounded-full bg-warn" />
        Sample data
      </span>
    </Tooltip>
  )
}

/**
 * Keyboard-accessible tooltip: shown on hover and focus, dismissed with Escape.
 * The trigger is focusable so keyboard users can reach the explanation.
 */
export function Tooltip({ content, children, align = 'start' }: { content: ReactNode; children: ReactNode; align?: 'start' | 'end' }) {
  const id = useId()
  const [open, setOpen] = useState(false)
  const [shift, setShift] = useState(0)
  const popRef = useRef<HTMLSpanElement>(null)
  // Keep the popover inside the viewport.
  useLayoutEffect(() => {
    if (!open || !popRef.current) return
    const r = popRef.current.getBoundingClientRect()
    const base = r.left - shift
    const margin = 8
    const right = base + r.width
    if (right > window.innerWidth - margin) setShift(window.innerWidth - margin - right)
    else if (base < margin) setShift(margin - base)
    else setShift(0)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <span tabIndex={0} aria-describedby={id} className="inline-flex cursor-help rounded">
        {children}
      </span>
      <span
        role="tooltip"
        id={id}
        ref={popRef}
        style={{ transform: `translateX(${shift}px)` }}
        className={`pointer-events-none absolute top-full z-30 mt-1.5 w-64 max-w-[calc(100vw-2rem)] rounded-md border border-rule bg-surface p-2.5 text-left font-sans text-xs font-normal normal-case leading-snug tracking-normal text-ink shadow-lg ${align === 'end' ? 'right-0' : 'left-0'} ${open ? 'block' : 'hidden'}`}
      >
        {content}
      </span>
    </span>
  )
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div aria-hidden className={`skeleton ${className}`} />
}

export function PaperSkeleton() {
  return (
    <div className="rounded-lg border border-rule bg-surface p-5" aria-hidden>
      <div className="flex justify-between gap-4">
        <div className="flex-1 space-y-2.5">
          <Skeleton className="h-3 w-40" />
          <Skeleton className="h-5 w-4/5" />
          <Skeleton className="h-3 w-1/3" />
        </div>
        <Skeleton className="size-11 rounded-full" />
      </div>
      <div className="mt-4 space-y-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-11/12" />
        <Skeleton className="h-3 w-2/3" />
      </div>
    </div>
  )
}

export function SectionTitle({ kicker, children, right }: { kicker?: string; children: ReactNode; right?: ReactNode }) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-x-4 gap-y-2 border-b border-rule pb-2">
      <div>
        {kicker && <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted">{kicker}</p>}
        <h2 className="font-serif text-2xl font-medium leading-tight">{children}</h2>
      </div>
      {right}
    </div>
  )
}

export function ErrorNote({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-lg border border-rule bg-surface p-4 text-sm">
      <p className="font-medium">Something went wrong.</p>
      <p className="text-muted">{error.message}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-2 rounded border border-rule px-3 py-1 hover:bg-accent-soft">Try again</button>
      )}
    </div>
  )
}
