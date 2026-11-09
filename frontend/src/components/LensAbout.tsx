import type { Lens } from '../types'
import { pct, sourceLabel } from '../lib/format'

/** Shows how the active lens scores papers. Rendered straight from the lens config. */
export function LensAbout({ lens }: { lens: Lens }) {
  return (
    <section aria-labelledby="about-h" className="rounded-lg border border-rule bg-surface p-4">
      <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted">Active lens</p>
      <h2 id="about-h" className="font-serif text-xl font-medium leading-tight">How this lens scores</h2>

      <div className="mt-3 flex h-2 overflow-hidden rounded-full" role="img" aria-label={`Rubric weights: ${lens.rubric.map((k) => `${k.label} ${pct(k.weight)}`).join(', ')}`}>
        {lens.rubric.map((k, i) => (
          <div key={k.id} style={{ width: `${k.weight * 100}%`, background: 'var(--accent)', opacity: 1 - i * 0.2 }} />
        ))}
      </div>
      <dl className="mt-3 space-y-2 text-[13px]">
        {lens.rubric.map((k) => (
          <div key={k.id}>
            <dt className="flex justify-between font-medium"><span>{k.label}</span><span className="font-mono text-muted">{pct(k.weight)}</span></dt>
            <dd className="text-muted">{k.description}</dd>
          </div>
        ))}
      </dl>

      <p className="mt-4 text-xs text-muted">Sources: {lens.sources.map(sourceLabel).join(', ')}</p>
      <ul className="mt-2 flex flex-wrap gap-1.5" aria-label="Lens keywords">
        {lens.keywords.map((k) => (
          <li key={k} className="rounded bg-accent-soft px-1.5 py-0.5 font-mono text-[11px] text-accent-ink">{k}</li>
        ))}
      </ul>
    </section>
  )
}
