import { api, SAMPLE_MODE } from '../api'
import { APP_NAME } from '../config/app'
import { ErrorNote, SampleBadge, SectionTitle, Skeleton, Tooltip } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { formatDateTime, formatShort, num, pct, sourceLabel } from '../lib/format'
import type { Lens, SystemStatus } from '../types'

function Tile({ label, value, hint, children }: { label: string; value: string; hint: string; children?: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-rule bg-surface p-4">
      <dt className="text-[13px] text-muted">
        <Tooltip content={hint}><span className="underline decoration-dotted underline-offset-2">{label}</span></Tooltip>
      </dt>
      <dd className={`mt-1 font-serif font-medium leading-none ${value.length > 9 ? 'text-2xl' : 'text-4xl'}`}>{value}</dd>
      {children}
    </div>
  )
}

function StateDot({ state }: { state: 'ok' | 'delayed' | 'error' }) {
  const color = state === 'ok' ? 'bg-accent' : state === 'delayed' ? 'bg-warn' : 'bg-red-600'
  return <span className="flex items-center gap-1.5"><span aria-hidden className={`size-2 rounded-full ${color}`} />{state}</span>
}

function CostChart({ cost }: { cost: SystemStatus['cost'] }) {
  const w = 640, h = 180, pad = { l: 36, r: 8, t: 10, b: 24 }
  const max = Math.max(cost.budgetUsdPerDay, ...cost.days.map((d) => d.usd)) * 1.1
  const bw = (w - pad.l - pad.r) / cost.days.length
  const y = (v: number) => pad.t + (h - pad.t - pad.b) * (1 - v / max)
  return (
    <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={`Daily token cost for the last ${cost.days.length} days, in US dollars, against a ${cost.budgetUsdPerDay} dollar daily budget`} className="w-full">
      {[0, 0.5, 1, 1.5, 2].filter((t) => t <= max).map((t) => (
        <g key={t}>
          <line x1={pad.l} x2={w - pad.r} y1={y(t)} y2={y(t)} stroke="var(--rule)" strokeWidth="1" />
          <text x={pad.l - 6} y={y(t) + 3} textAnchor="end" fontSize="10" fill="var(--muted)" fontFamily="var(--font-mono)">${t}</text>
        </g>
      ))}
      {cost.days.map((d, i) => (
        <g key={d.date}>
          <rect x={pad.l + i * bw + 3} y={y(d.usd)} width={bw - 6} height={y(0) - y(d.usd)} rx="2" fill="var(--accent)" opacity={i === cost.days.length - 1 ? 1 : 0.7}>
            <title>{`${formatShort(d.date)}: $${d.usd.toFixed(2)}`}</title>
          </rect>
          {i % 2 === 0 && <text x={pad.l + i * bw + bw / 2} y={h - 8} textAnchor="middle" fontSize="9" fill="var(--muted)" fontFamily="var(--font-mono)">{formatShort(d.date)}</text>}
        </g>
      ))}
      <line x1={pad.l} x2={w - pad.r} y1={y(cost.budgetUsdPerDay)} y2={y(cost.budgetUsdPerDay)} stroke="var(--warn)" strokeWidth="1.5" strokeDasharray="5 4" />
      <text x={w - pad.r} y={y(cost.budgetUsdPerDay) - 4} textAnchor="end" fontSize="10" fill="var(--warn)" fontFamily="var(--font-mono)">budget ${cost.budgetUsdPerDay.toFixed(2)}/day</text>
    </svg>
  )
}

function Body({ s, lenses }: { s: SystemStatus; lenses: Lens[] }) {
  const e = s.evaluation
  const total = s.sources.reduce((a, x) => a + x.indexed, 0)
  const lensMax = Math.max(1, ...s.perLens.map((p) => p.indexed))
  const today = s.cost.days[s.cost.days.length - 1]
  const avg = s.cost.days.reduce((a, d) => a + d.usd, 0) / Math.max(1, s.cost.days.length)
  const tokens = s.cost.days.reduce((a, d) => a + d.tokensIn + d.tokensOut, 0)

  return (
    <div className="space-y-12">
      <section aria-labelledby="pipe-h">
        <SectionTitle kicker="Pipeline" right={<SampleBadge />}><span id="pipe-h">Ingest status</span></SectionTitle>
        <dl className="grid gap-3 sm:grid-cols-3">
          <Tile label="Last ingest" value={s.lastIngestAt ? formatDateTime(s.lastIngestAt) : 'Never'} hint="When the most recent successful pull from any source finished." />
          <Tile label="Next ingest" value={s.nextIngestAt ? formatDateTime(s.nextIngestAt) : 'Not scheduled'} hint="The next scheduled run. Ingest is run by hand until scheduling is built." />
          <Tile label="Papers indexed" value={num(total)} hint="Total papers stored with text and embeddings, across all sources." />
        </dl>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="overflow-x-auto rounded-lg border border-rule bg-surface">
            <table className="w-full text-sm">
              <caption className="px-4 pt-3 text-left font-mono text-[11px] uppercase tracking-wider text-muted">By source</caption>
              <thead className="text-left text-xs text-muted">
                <tr><th className="px-4 py-2 font-normal">Source</th><th className="px-2 py-2 text-right font-normal">Indexed</th><th className="px-2 py-2 text-right font-normal">+24h</th><th className="px-4 py-2 font-normal">State</th></tr>
              </thead>
              <tbody>
                {s.sources.map((x) => (
                  <tr key={x.source} className="border-t border-rule">
                    <th scope="row" className="px-4 py-2 text-left font-medium">{sourceLabel(x.source)}</th>
                    <td className="px-2 py-2 text-right font-mono">{num(x.indexed)}</td>
                    <td className="px-2 py-2 text-right font-mono text-muted">+{x.addedLast24h}</td>
                    <td className="px-4 py-2"><StateDot state={x.state} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="rounded-lg border border-rule bg-surface p-4">
            <p className="font-mono text-[11px] uppercase tracking-wider text-muted">By lens</p>
            <ul className="mt-2 space-y-2.5">
              {s.perLens.map((p) => {
                const l = lenses.find((x) => x.id === p.lensId)
                return (
                  <li key={p.lensId} className="text-sm">
                    <div className="flex justify-between"><span>{l?.name ?? p.lensId}</span><span className="font-mono">{num(p.indexed)}</span></div>
                    <div className="mt-1 h-1.5 rounded-full bg-rule"><div className="h-full rounded-full" style={{ width: `${(p.indexed / lensMax) * 100}%`, background: l?.accent ?? 'var(--accent)' }} /></div>
                  </li>
                )
              })}
            </ul>
          </div>
        </div>
      </section>

      <section aria-labelledby="eval-h">
        <SectionTitle kicker="Evaluation" right={<SampleBadge />}><span id="eval-h">How good is the ranking</span></SectionTitle>
        {!e ? (
          <p className="rounded-lg border border-dashed border-rule bg-surface p-4 text-sm text-muted">
            Not measured yet. Precision@k, nDCG, citation validity and coverage will appear here once the evaluation harness and its labeled set exist.
          </p>
        ) : (<>
        <p className="mb-3 max-w-[70ch] text-sm text-muted">
          {SAMPLE_MODE && 'Placeholder numbers. The evaluation harness does not exist yet; these are laid out where the real '}{SAMPLE_MODE ? `${e.labeledQueries}-query labeled set results will appear. ` : `${e.labeledQueries} labeled queries. `}Last run {formatDateTime(e.lastRunAt)}.
        </p>
        <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Tile label={`Precision@${e.k}`} value={pct(e.precisionAtK)} hint={`Of the top ${e.k} papers returned for each labeled query, the share a human marked relevant.`} />
          <Tile label="nDCG" value={e.ndcg.toFixed(2)} hint="Normalized discounted cumulative gain: rewards putting the most relevant papers nearest the top. 1.0 is a perfect ordering." />
          <Tile label="Citation validity" value={pct(e.citationValidity)} hint="Share of returned citations that resolve to a real paper in the index. The pitch is that this stays at 100%." />
          <Tile label="Coverage vs chatbot" value={`${pct(e.coverage.polymath)}`} hint="Share of labeled relevant papers found, compared with a general-purpose chatbot answering the same queries.">
            <div className="mt-3 space-y-1.5 text-[11px]" role="img" aria-label={`Coverage: ${APP_NAME} ${pct(e.coverage.polymath)}, general chatbot ${pct(e.coverage.generalChatbot)}`}>
              <div className="flex items-center gap-2"><span className="w-14 text-muted">{APP_NAME}</span><div className="h-2 flex-1 rounded-full bg-rule"><div className="h-full rounded-full bg-accent" style={{ width: pct(e.coverage.polymath) }} /></div></div>
              <div className="flex items-center gap-2"><span className="w-14 text-muted">Chatbot</span><div className="h-2 flex-1 rounded-full bg-rule"><div className="h-full rounded-full bg-muted" style={{ width: pct(e.coverage.generalChatbot) }} /></div></div>
            </div>
          </Tile>
        </dl>
        </>)}
      </section>

      <section aria-labelledby="cost-h">
        <SectionTitle kicker="Cost" right={<SampleBadge />}><span id="cost-h">Token cost per day</span></SectionTitle>
        {!today ? (
          <p className="rounded-lg border border-dashed border-rule bg-surface p-4 text-sm text-muted">
            No spend recorded. Token usage will be tracked once the Claude scorer is connected.
          </p>
        ) : (<>
        <dl className="mb-3 grid gap-3 sm:grid-cols-3">
          <Tile label="Latest day" value={`$${today.usd.toFixed(2)}`} hint="Spend on the most recent day, in US dollars." />
          <Tile label={`${s.cost.days.length}-day average`} value={`$${avg.toFixed(2)}`} hint="Mean daily spend over the window shown." />
          <Tile label="Tokens in window" value={`${(tokens / 1e6).toFixed(1)}M`} hint="Input plus output tokens across the window." />
        </dl>
        <div className="rounded-lg border border-rule bg-surface p-4"><CostChart cost={s.cost} /></div>
        </>)}
      </section>
    </div>
  )
}

export function SystemView({ lenses }: { lenses: Lens[] }) {
  const { data, loading, error, reload } = useAsync(() => api.getStatus(), [])
  return (
    <div>
      <div className="mb-8">
        <div className="flex items-center gap-3">
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted">System</p>
          <SampleBadge />
        </div>
        <h1 className="mt-1 font-serif text-4xl font-medium tracking-tight sm:text-5xl">Under the hood</h1>
        <p className="mt-1 max-w-[62ch] text-muted">Pipeline health, ranking quality, and what it costs to run. {SAMPLE_MODE ? 'All values are fake until the backend exists.' : 'Pipeline counts are live; evaluation and cost are not tracked yet.'}</p>
      </div>
      {loading && <div className="space-y-3" aria-busy><Skeleton className="h-24 w-full" /><Skeleton className="h-48 w-full" /></div>}
      {error && <ErrorNote error={error} onRetry={reload} />}
      {data && <Body s={data} lenses={lenses} />}
    </div>
  )
}
