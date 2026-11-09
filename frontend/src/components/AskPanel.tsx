import { useId, useState } from 'react'
import { api, SAMPLE_MODE } from '../api'
import { ASSISTANT_NAME } from '../config/app'
import type { AskResult, Lens } from '../types'
import { PaperCard } from './PaperCard'
import { ErrorNote, PaperSkeleton, SampleBadge, SectionTitle } from './ui'

interface Props {
  lens: Lens
  lenses: Lens[]
}

type Scope = 'lens' | 'all'

export function AskPanel({ lens, lenses }: Props) {
  const inputId = useId()
  const [question, setQuestion] = useState('')
  const [scope, setScope] = useState<Scope>('lens')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AskResult | null>(null)
  const [error, setError] = useState<Error | null>(null)

  async function run(q: string) {
    const text = q.trim()
    if (!text || loading) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      setResult(await api.ask({ question: text, lensId: scope === 'all' ? null : lens.id }))
    } catch (e) {
      setError(e as Error)
    } finally {
      setLoading(false)
    }
  }

  const lensFor = (id: string) => lenses.find((l) => l.id === id) ?? lens

  return (
    <section aria-labelledby="ask-h" className="mt-10">
      <SectionTitle kicker={`Ask ${ASSISTANT_NAME}`} right={<SampleBadge />}>
        <span id="ask-h">Ask anything</span>
      </SectionTitle>

      <form
        onSubmit={(e) => { e.preventDefault(); void run(question) }}
        className="rounded-lg border border-rule bg-surface p-4"
      >
        <label htmlFor={inputId} className="text-sm text-muted">
          Papers are ranked for your question instead of the {lens.shortName} lens default.
        </label>
        <div className="mt-2 flex flex-col gap-2 sm:flex-row">
          <input
            id={inputId}
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={lens.askExamples[0] ?? 'Type a question'}
            autoComplete="off"
            className="min-w-0 flex-1 rounded-md border border-rule bg-paper px-3 py-2 text-[15px] placeholder:text-muted/70"
          />
          <button
            type="submit"
            disabled={!question.trim() || loading}
            className="rounded-md bg-accent-ink px-4 py-2 text-sm font-medium text-paper disabled:opacity-50"
          >
            {loading ? 'Ranking…' : 'Rank papers'}
          </button>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-[13px]">
          <fieldset className="flex items-center gap-3">
            <legend className="sr-only">Search scope</legend>
            {(['lens', 'all'] as const).map((s) => (
              <label key={s} className="flex cursor-pointer items-center gap-1.5">
                <input type="radio" name="scope" checked={scope === s} onChange={() => setScope(s)} className="accent-[var(--accent)]" />
                {s === 'lens' ? `This lens only` : `All lenses (${lenses.length})`}
              </label>
            ))}
          </fieldset>
          <span className="flex flex-wrap items-center gap-1.5 text-muted">
            Try:
            {lens.askExamples.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => { setQuestion(ex); void run(ex) }}
                className="rounded-full border border-rule px-2.5 py-0.5 text-ink hover:border-accent hover:bg-accent-soft"
              >
                {ex}
              </button>
            ))}
          </span>
        </div>
      </form>

      <div aria-live="polite" aria-busy={loading} className="mt-4 space-y-4">
        {loading && (
          <>
            <p className="font-mono text-xs text-muted">{SAMPLE_MODE ? 'Ranking sample papers for your question…' : 'Searching the index…'}</p>
            <PaperSkeleton /><PaperSkeleton /><PaperSkeleton />
          </>
        )}
        {error && <ErrorNote error={error} onRetry={() => void run(question)} />}
        {result && (
          <>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm">
                <span className="text-muted">Top {result.results.length} for </span>
                <q className="font-serif text-lg">{result.question}</q>
              </p>
              <button onClick={() => setResult(null)} className="text-sm text-muted underline underline-offset-2 hover:text-ink">Clear</button>
            </div>
            <p className="text-xs text-muted">{result.note}</p>
            {result.results.length === 0 && <p className="rounded-lg border border-rule bg-surface p-4 text-sm">No papers matched.</p>}
            {result.results.map((p, i) => <PaperCard key={p.id} paper={p} lens={lensFor(p.lensId)} rank={i + 1} />)}
          </>
        )}
      </div>
    </section>
  )
}
