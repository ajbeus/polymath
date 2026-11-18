import { api, SAMPLE_MODE } from '../api'
import { PaperCard } from '../components/PaperCard'
import { SampleBadge, SectionTitle } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { usePaperState } from '../hooks/usePaperState'
import { hrefFor } from '../hooks/useRoute'
import type { Lens, Paper } from '../types'

/** Sample papers only exist in mock mode and real ones only in live mode, so never mix them. */
const inThisMode = (p: Paper) => p.id.startsWith('SAMPLE-') === SAMPLE_MODE

export function SavedView({ lenses }: { lenses: Lens[] }) {
  const { flags, savedPapers, savedIdsWithoutSnapshot } = usePaperState()

  // Papers saved before snapshots were stored: recover them from the current digests when possible.
  const missing = savedIdsWithoutSnapshot.join(',')
  const { data: recovered } = useAsync(async () => {
    if (!missing) return [] as Paper[]
    const wanted = new Set(missing.split(','))
    const digests = await Promise.all(lenses.map((l) => api.getDigest(l.id).catch(() => null)))
    return digests.flatMap((d) => (d ? [...d.recommended, ...d.others] : [])).filter((p) => wanted.has(p.id))
  }, [missing])

  const byId = new Map<string, Paper>()
  for (const p of [...savedPapers, ...(recovered ?? [])]) byId.set(p.id, p)
  const papers = [...byId.values()].filter((p) => flags(p.id).save && inThisMode(p))
  const lost = savedIdsWithoutSnapshot.filter((id) => !byId.has(id) && inThisMode({ id } as Paper)).length

  return (
    <div className="max-w-3xl">
      <div className="flex flex-wrap items-center gap-3">
        <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted">Your reading list</p>
        <SampleBadge />
      </div>
      <h1 className="mt-1 font-serif text-4xl font-medium leading-tight tracking-tight sm:text-5xl">Saved papers</h1>
      <p className="mt-1 text-muted">Papers you saved from any lens. Un-save a paper to remove it from this list.</p>

      {papers.length === 0 && (
        <p className="mt-8 rounded-lg border border-dashed border-rule bg-surface p-4 text-sm text-muted">
          Nothing saved yet. Use the Save button on a paper card in a <a className="underline" href={hrefFor({ view: 'digest', lensId: null })}>digest</a>.
        </p>
      )}

      {lenses.map((lens) => {
        const mine = papers.filter((p) => p.lensId === lens.id)
        if (mine.length === 0) return null
        return (
          <section key={lens.id} aria-labelledby={`saved-${lens.id}`} className="mt-10">
            <SectionTitle kicker={`${mine.length} saved`}>
              <span id={`saved-${lens.id}`}>{lens.name}</span>
            </SectionTitle>
            <div className="space-y-4">
              {mine.map((p) => <PaperCard key={p.id} paper={p} lens={lens} />)}
            </div>
          </section>
        )
      })}

      {lost > 0 && (
        <p className="mt-8 text-xs text-muted">
          {lost} saved paper{lost === 1 ? '' : 's'} could not be shown: saved before this list existed and no longer in a current digest.
        </p>
      )}
    </div>
  )
}
