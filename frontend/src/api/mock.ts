import type {
  AskRequest, AskResult, BuildId, CrossLensLink, Digest, FeedbackEvent, Lens, Paper, SystemStatus,
} from '../types'
import type { PolymathApi } from './index'
import statusFixture from './fixtures/status.json'

/*
 * Mock API. Reads JSON fixtures and adds an artificial delay.
 * Lens configs and fixtures are discovered by glob, so adding a lens means adding
 * lenses/<tier>/<id>.json and fixtures/<tier>/<id>.json, with no code changes.
 * The `showcase` build only globs the showcase folders, so full-only data is not bundled.
 */

// Written out literally so the bundler can drop the unused branch in showcase builds.
const lensModules = import.meta.env.VITE_BUILD === 'full'
  ? import.meta.glob(['../../../lenses/showcase/*.json', '../../../lenses/full/*.json'], { eager: true, import: 'default' })
  : import.meta.glob('../../../lenses/showcase/*.json', { eager: true, import: 'default' })

const fixtureModules = import.meta.env.VITE_BUILD === 'full'
  ? import.meta.glob(['./fixtures/showcase/*.json', './fixtures/full/*.json'], { import: 'default' })
  : import.meta.glob('./fixtures/showcase/*.json', { import: 'default' })

const linkModules = import.meta.env.VITE_BUILD === 'full'
  ? import.meta.glob(['./fixtures/links/showcase.json', './fixtures/links/full.json'], { eager: true, import: 'default' })
  : import.meta.glob('./fixtures/links/showcase.json', { eager: true, import: 'default' })

const build: BuildId = import.meta.env.VITE_BUILD === 'full' ? 'full' : 'showcase'

const LENSES: Lens[] = (Object.values(lensModules) as Lens[])
  .filter((l) => l.builds.includes(build))
  .sort((a, b) => a.order - b.order)

interface Fixture {
  digest: Omit<Digest, 'recommended' | 'others' | 'isSample'> & { recommendedIds: string[] }
  papers: Paper[]
}

async function loadFixture(lensId: string): Promise<Fixture> {
  const key = Object.keys(fixtureModules).find((k) => k.endsWith(`/${lensId}.json`))
  if (!key) throw new Error(`No fixture for lens "${lensId}"`)
  return (await fixtureModules[key]()) as Fixture
}

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))
const sendFeedbackLog: FeedbackEvent[] = []

const STOP = new Set(['what', 'is', 'are', 'the', 'a', 'an', 'new', 'on', 'in', 'of', 'for', 'and', 'to', 'about', 'any', 'recent', 'how', 'does', 'do', 'with', 'latest', 'papers', 'paper'])
const tokens = (s: string) => s.toLowerCase().split(/[^a-z0-9.]+/).filter((t) => t.length > 2 && !STOP.has(t))
const hash = (s: string) => { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) | 0; return Math.abs(h) }

export const mockApi: PolymathApi = {
  async getLenses() {
    await delay(120)
    return LENSES
  },

  async getDigest(lensId) {
    await delay(350)
    const { digest, papers } = await loadFixture(lensId)
    const { recommendedIds, ...rest } = digest
    const recommended = recommendedIds.map((id) => papers.find((p) => p.id === id)!).filter(Boolean)
    const others = papers.filter((p) => !recommendedIds.includes(p.id)).sort((a, b) => b.score - a.score)
    return { ...rest, recommended, others, isSample: true }
  },

  async ask(req: AskRequest): Promise<AskResult> {
    await delay(1100)
    const lensIds = req.lensId ? [req.lensId] : LENSES.map((l) => l.id)
    const q = tokens(req.question)
    const pool: Paper[] = []
    for (const id of lensIds) {
      const fx = await loadFixture(id)
      for (const p of fx.papers) {
        // Match against the paper's own text only, so papers that merely sit in the same lens don't tie.
        const hay = `${p.title} ${p.summary}`.toLowerCase()
        const matched = q.filter((t) => hay.includes(t))
        // Deterministic fake: more overlapping terms -> higher score, plus a small stable jitter.
        const jitter = (hash(p.id + req.question) % 60) / 1000
        const score = Math.min(0.97, 0.28 + 0.2 * matched.length + jitter + p.score * 0.15)
        pool.push({
          ...p,
          score: Math.round(score * 100) / 100,
          rubric: { ...p.rubric, relevance: Math.min(0.98, Math.round((0.3 + 0.22 * matched.length + jitter) * 100) / 100) },
          whyMatched: matched.length
            ? `Sample ranking: matched your terms "${[...new Set(matched)].slice(0, 4).join('", "')}" in this placeholder paper.`
            : 'Sample ranking: no direct term overlap with your question; shown only to fill the list.',
        })
      }
    }
    const results = pool.sort((a, b) => b.score - a.score).slice(0, 5)
    return {
      question: req.question,
      lensId: req.lensId,
      results,
      tookMs: 1100,
      note: 'Mock ranking by keyword overlap against sample papers. The real two-stage ranker is not connected yet.',
      isSample: true,
    }
  },

  async sendFeedback(event) {
    await delay(60)
    sendFeedbackLog.push(event)
    console.debug('[mock api] feedback', event)
  },

  async getLinks(lensId, limit = 3) {
    await delay(300)
    const ids = new Set(LENSES.map((l) => l.id))
    return (Object.values(linkModules).flat() as CrossLensLink[])
      .filter((l) => l.lensIds.includes(lensId) && l.lensIds.every((id) => ids.has(id)))
      .sort((a, b) => b.strength - a.strength)
      .slice(0, limit)
  },

  async getStatus(): Promise<SystemStatus> {
    await delay(300)
    // Per-lens counts are fake and derived from the lens id, so no lens names live in status.json.
    const perLens = LENSES.map((l) => ({ lensId: l.id, indexed: 1200 + (hash(l.id) % 4200) }))
    return { ...(statusFixture as Omit<SystemStatus, 'perLens'>), perLens }
  },
}
