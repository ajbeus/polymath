import type { Lens, Paper } from '../types'
import { authorLine, formatDate, pct, sourceLabel } from '../lib/format'
import { usePaperState } from '../hooks/usePaperState'
import { Tooltip } from './ui'

function ScoreRing({ score, lens, partial, sample }: { score: number; lens: Lens; partial: boolean; sample: boolean }) {
  const r = 19
  const c = 2 * Math.PI * r
  const breakdown = lens.rubric.map((k) => `${k.label} ${Math.round(k.weight * 100)}%`).join(', ')
  return (
    <Tooltip
      align="end"
      content={
        <>
          <strong className="font-medium">Relevance score: {pct(score)}</strong>
          <br />
          {partial
            ? 'Stage-1 score from keyword rules and text matching. Novelty, rigor and accessibility have not been scored yet. '
            : `A weighted blend of the rubric scores below for this lens (${breakdown}). `}
          Higher means a closer fit to the lens, not a verdict on whether the paper is correct.{sample ? ' Sample value.' : ''}
        </>
      }
    >
      <span className="relative grid size-12 place-items-center" aria-label={`Relevance ${pct(score)}`}>
        <svg viewBox="0 0 48 48" className="absolute inset-0 -rotate-90" aria-hidden>
          <circle cx="24" cy="24" r={r} fill="none" stroke="var(--rule)" strokeWidth="3" />
          <circle cx="24" cy="24" r={r} fill="none" stroke="var(--accent)" strokeWidth="3" strokeLinecap="round"
            strokeDasharray={c} strokeDashoffset={c * (1 - score)} />
        </svg>
        <span className="font-mono text-[13px] font-medium">{Math.round(score * 100)}<span className="text-[9px] text-muted">%</span></span>
      </span>
    </Tooltip>
  )
}

function RubricBars({ paper, lens }: { paper: Paper; lens: Lens }) {
  return (
    <dl className="grid grid-cols-2 gap-x-5 gap-y-2 sm:grid-cols-4">
      {lens.rubric.map((k) => {
        const v = paper.rubric[k.id]
        return (
          <div key={k.id}>
            <dt className="flex items-baseline justify-between text-[11px] text-muted">
              <Tooltip content={<><strong className="font-medium">{k.label}</strong> ({Math.round(k.weight * 100)}% of score): {k.description}</>}>
                <span className="underline decoration-dotted underline-offset-2">{k.label}</span>
              </Tooltip>
              <span className="font-mono text-ink">{v === undefined ? 'n/a' : Math.round(v * 100)}</span>
            </dt>
            <dd className="mt-1 h-1 overflow-hidden rounded-full bg-rule" role="img" aria-label={v === undefined ? `${k.label} not scored yet` : `${k.label} ${Math.round(v * 100)} out of 100`}>
              {v !== undefined && <div className="h-full rounded-full bg-accent" style={{ width: `${v * 100}%` }} />}
            </dd>
          </div>
        )
      })}
    </dl>
  )
}

interface Props {
  paper: Paper
  lens: Lens
  rank?: number
}

export function PaperCard({ paper, lens, rank }: Props) {
  const { flags, toggle } = usePaperState()
  const f = flags(paper.id)

  const btn = (action: 'read' | 'skip' | 'save', label: string, pressedLabel: string) => (
    <button
      type="button"
      aria-pressed={f[action]}
      onClick={() => toggle(paper, action)}
      className={`rounded-md border px-3 py-1 text-[13px] font-medium transition-colors ${
        f[action]
          ? 'border-accent bg-accent-soft text-accent-ink'
          : 'border-rule text-ink hover:border-accent hover:bg-accent-soft'
      }`}
    >
      {f[action] ? pressedLabel : label}
    </button>
  )

  return (
    <article
      aria-labelledby={`t-${paper.id}`}
      className={`rise relative rounded-lg border border-rule bg-surface p-5 pl-6 transition-opacity ${f.skip ? 'opacity-55' : ''}`}
    >
      <span aria-hidden className="absolute inset-y-3 left-0 w-[3px] rounded-r bg-accent" />
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-[11px] uppercase tracking-wider text-muted">
            {rank !== undefined && <span className="text-accent-ink">{String(rank).padStart(2, '0')}</span>}
            <span className="rounded bg-accent-soft px-1.5 py-0.5 text-accent-ink">{sourceLabel(paper.source)}</span>
            <time dateTime={paper.date}>{formatDate(paper.date)}</time>
            {paper.isSample && <span className="rounded border border-dashed border-warn px-1.5 py-0.5 text-warn">Sample</span>}
            {f.read && <span>· Read</span>}
          </p>
          <h3 id={`t-${paper.id}`} className="mt-1.5 font-serif text-xl font-medium leading-snug">{paper.title}</h3>
          <p className="mt-0.5 text-[13px] text-muted">
            {authorLine(paper.authors)} · <span className="font-mono text-[11px]">{paper.id}</span>
          </p>
        </div>
        <ScoreRing score={paper.score} lens={lens} sample={paper.isSample} partial={lens.rubric.some((k) => paper.rubric[k.id] === undefined)} />
      </div>

      <p className="mt-3 max-w-[68ch] text-[14.5px] leading-relaxed">{paper.summary}</p>
      <p className="mt-2 max-w-[68ch] border-l-2 border-rule pl-3 text-[13px] italic text-muted">
        <span className="not-italic font-medium text-ink">Why this matched: </span>{paper.whyMatched}
      </p>

      <div className="mt-4">
        <RubricBars paper={paper} lens={lens} />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2" role="group" aria-label={`Actions for ${paper.title}`}>
        {btn('read', 'Read', 'Marked read')}
        {btn('save', 'Save', 'Saved')}
        {btn('skip', 'Skip', 'Skipped')}
        {paper.isSample && <span className="ml-auto text-xs text-muted">No link: this paper does not exist.</span>}
        {paper.url && (
          <a
            href={paper.url}
            target="_blank"
            rel="noreferrer"
            className="ml-auto rounded-md px-2 py-1 text-[13px] font-medium text-accent-ink underline underline-offset-2 hover:bg-accent-soft"
          >
            Open on {sourceLabel(paper.source)}<span className="sr-only"> (new tab)</span> ↗
          </a>
        )}
      </div>
    </article>
  )
}
