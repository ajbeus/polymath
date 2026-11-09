import { api } from '../api'
import { AskPanel } from '../components/AskPanel'
import { LensAbout } from '../components/LensAbout'
import { LinksPanel } from '../components/LinksPanel'
import { PaperCard } from '../components/PaperCard'
import { ErrorNote, PaperSkeleton, SampleBadge, SectionTitle, Skeleton } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { formatDate, formatDateTime } from '../lib/format'
import type { Lens } from '../types'

export function DigestView({ lens, lenses }: { lens: Lens; lenses: Lens[] }) {
  const { data: digest, loading, error, reload } = useAsync(() => api.getDigest(lens.id), [lens.id])

  return (
    <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="min-w-0">
        {/* Digest header */}
        <section aria-labelledby="digest-h">
          <div className="flex flex-wrap items-center gap-3">
            <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted">
              {digest ? `Week of ${formatDate(digest.weekOf)}` : 'Weekly digest'}
            </p>
            <SampleBadge />
          </div>
          <h1 id="digest-h" className="mt-1 font-serif text-4xl font-medium leading-tight tracking-tight sm:text-5xl">
            {lens.name}
          </h1>
          <p className="mt-1 max-w-[62ch] text-muted">{lens.description}</p>

          {loading && (
            <div className="mt-6 space-y-2.5" aria-busy>
              <Skeleton className="h-4 w-full" /><Skeleton className="h-4 w-11/12" /><Skeleton className="h-4 w-3/5" />
            </div>
          )}
          {error && <div className="mt-6"><ErrorNote error={error} onRetry={reload} /></div>}
          {digest && (
            <div className="rise">
              <p className="mt-6 max-w-[64ch] font-serif text-[19px] leading-relaxed">{digest.summary}</p>
              <div className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-2 rounded-lg border border-rule bg-accent-soft px-4 py-3 text-sm">
                <p className="max-w-[60ch]">
                  <span className="font-medium">Since your last visit. </span>{digest.sinceLastVisit.text}
                </p>
                <dl className="ml-auto flex gap-5 font-mono text-xs">
                  <div><dt className="text-muted">new</dt><dd className="text-lg font-medium text-accent-ink">{digest.sinceLastVisit.newPapers}</dd></div>
                  <div><dt className="text-muted">re-ranked</dt><dd className="text-lg font-medium text-accent-ink">{digest.sinceLastVisit.reranked}</dd></div>
                </dl>
              </div>
              <p className="mt-2 font-mono text-[11px] text-muted">Generated {formatDateTime(digest.generatedAt)}</p>
            </div>
          )}
        </section>

        <AskPanel key={lens.id} lens={lens} lenses={lenses} />

        {/* Recommended */}
        <section aria-labelledby="rec-h" className="mt-12">
          <SectionTitle kicker="Recommended" right={<SampleBadge />}>
            <span id="rec-h">Start here</span>
          </SectionTitle>
          <div className="space-y-4" aria-busy={loading}>
            {loading && <><PaperSkeleton /><PaperSkeleton /><PaperSkeleton /></>}
            {digest?.recommended.map((p, i) => <PaperCard key={p.id} paper={p} lens={lens} rank={i + 1} />)}
            {digest && digest.recommended.length === 0 && (
              <p className="rounded-lg border border-dashed border-rule bg-surface p-4 text-sm text-muted">Nothing to recommend this week.</p>
            )}
          </div>
        </section>

        {digest && digest.others.length > 0 && (
          <section aria-labelledby="more-h" className="mt-12">
            <SectionTitle kicker="Also scored this week" right={<SampleBadge />}>
              <span id="more-h">The rest of the pile</span>
            </SectionTitle>
            <div className="space-y-4">
              {digest.others.map((p) => <PaperCard key={p.id} paper={p} lens={lens} />)}
            </div>
          </section>
        )}
      </div>

      <aside aria-label="Context" className="space-y-6 lg:sticky lg:top-32 lg:self-start">
        <LinksPanel lens={lens} lenses={lenses} />
        <LensAbout lens={lens} />
      </aside>
    </div>
  )
}
