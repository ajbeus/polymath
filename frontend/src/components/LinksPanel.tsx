import { api, SAMPLE_MODE } from '../api'
import { useAsync } from '../hooks/useAsync'
import { hrefFor } from '../hooks/useRoute'
import type { Lens } from '../types'
import { sourceLabel } from '../lib/format'
import { ErrorNote, SampleBadge, Skeleton } from './ui'

export function LinksPanel({ lens, lenses }: { lens: Lens; lenses: Lens[] }) {
  const { data, loading, error, reload } = useAsync(() => api.getLinks(lens.id, 3), [lens.id])
  const lensById = (id: string) => lenses.find((l) => l.id === id)

  return (
    <section aria-labelledby="links-h" className="rounded-lg border border-rule bg-surface p-4">
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted">Cross-lens</p>
          <h2 id="links-h" className="font-serif text-xl font-medium leading-tight">Same method, different field</h2>
        </div>
        <SampleBadge />
      </div>

      {loading && <div className="space-y-3" aria-busy><Skeleton className="h-4 w-3/4" /><Skeleton className="h-12 w-full" /><Skeleton className="h-4 w-2/3" /></div>}
      {error && <ErrorNote error={error} onRetry={reload} />}
      {data && data.length === 0 && (
        <p className="text-sm text-muted">{SAMPLE_MODE ? 'No sample links involve this lens.' : 'No cross-lens links yet. Link discovery is not built.'}</p>
      )}
      {data && (
        <ul className="space-y-5">
          {data.map((link) => (
            <li key={link.id} className="rise border-t border-rule pt-4 first:border-t-0 first:pt-0">
              <div className="flex flex-wrap items-center gap-1.5">
                {link.lensIds.map((id, i) => {
                  const l = lensById(id)
                  return (
                    <span key={id} className="flex items-center gap-1.5">
                      {i > 0 && <span aria-hidden className="text-muted">↔</span>}
                      <a href={hrefFor({ view: 'digest', lensId: id })} className="flex items-center gap-1 rounded-full border border-rule px-2 py-0.5 text-xs hover:bg-accent-soft">
                        <span aria-hidden className="size-2 rounded-full" style={{ background: l?.accent }} />
                        {l?.shortName ?? id}
                      </a>
                    </span>
                  )
                })}
              </div>
              <h3 className="mt-2 font-serif text-[17px] font-medium leading-snug">{link.method}</h3>
              <p className="mt-1 text-[13px] leading-relaxed text-muted">{link.explanation}</p>
              <ul className="mt-2 space-y-1.5">
                {link.papers.map((p) => (
                  <li key={p.id} className="text-[13px] leading-snug">
                    <span className="font-mono text-[10px] uppercase tracking-wider text-accent-ink">{sourceLabel(p.source)}</span>{' '}
                    {p.title}
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
