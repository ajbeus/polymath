// Shared domain types. The future Python backend should emit JSON matching these shapes.

export type SourceId = 'arxiv' | 'pubmed' | 'biorxiv'
export type BuildId = 'showcase' | 'full'

export interface RubricCriterion {
  /** Stable key, used as the key in Paper.rubric. */
  id: string
  label: string
  /** Weights within one lens should sum to 1. */
  weight: number
  /** Lens-specific plain-language definition, shown in tooltips. */
  description: string
}

export interface Lens {
  id: string
  name: string
  /** Short name for the toggle. */
  shortName: string
  description: string
  sources: SourceId[]
  keywords: string[]
  /** Example questions for the Ask box. */
  askExamples: string[]
  rubric: RubricCriterion[]
  /** Hex colour. Used for the page accent while this lens is active. */
  accent: string
  /** Which builds include this lens. */
  builds: BuildId[]
  order: number
}

export interface Paper {
  id: string
  lensId: string
  title: string
  authors: string[]
  source: SourceId
  /** ISO date (YYYY-MM-DD). */
  date: string
  /** 0..1 overall relevance, shown as a percentage. */
  score: number
  summary: string
  whyMatched: string
  /** criterion id -> 0..1. A criterion that has not been scored yet is absent (the real backend only scores relevance so far). */
  rubric: Record<string, number | undefined>
  /** Only set for real papers; sample papers never carry a URL. */
  url?: string
  /** True for placeholder papers. The UI surfaces this on the card. */
  isSample: boolean
}

export interface Digest {
  lensId: string
  /** ISO date of the Monday that starts the digest week. */
  weekOf: string
  generatedAt: string
  summary: string
  sinceLastVisit: { text: string; newPapers: number; reranked: number }
  recommended: Paper[]
  /** Everything else scored this week, highest first. */
  others: Paper[]
  isSample: boolean
}

export interface AskRequest {
  question: string
  /** null searches across every lens in the current build. */
  lensId: string | null
}

export interface AskResult {
  question: string
  lensId: string | null
  results: Paper[]
  tookMs: number
  note: string
  isSample: boolean
}

export interface CrossLensLink {
  id: string
  /** The shared method or idea. */
  method: string
  explanation: string
  lensIds: string[]
  papers: Array<Pick<Paper, 'id' | 'lensId' | 'title' | 'source' | 'date' | 'isSample'>>
  strength: number
  isSample: boolean
}

export type FeedbackAction = 'read' | 'skip' | 'save'

export interface FeedbackEvent {
  paperId: string
  lensId: string
  action: FeedbackAction
  /** false means the action was undone. */
  active: boolean
  at: string
}

export interface SourceStatus {
  source: SourceId
  indexed: number
  addedLast24h: number
  lastIngestAt: string | null
  state: 'ok' | 'delayed' | 'error'
}

export interface SystemStatus {
  isSample: boolean
  lastIngestAt: string | null
  nextIngestAt: string | null
  sources: SourceStatus[]
  perLens: Array<{ lensId: string; indexed: number }>
  /** null until the evaluation harness exists. */
  evaluation: {
    k: number
    precisionAtK: number
    ndcg: number
    citationValidity: number
    coverage: { polymath: number; generalChatbot: number }
    labeledQueries: number
    lastRunAt: string
  } | null
  cost: {
    budgetUsdPerDay: number
    days: Array<{ date: string; usd: number; tokensIn: number; tokensOut: number }>
  }
}
