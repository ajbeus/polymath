import type {
  AskRequest, AskResult, CrossLensLink, Digest, FeedbackEvent, Lens, SystemStatus,
} from '../types'
import { httpApi } from './http'
import { mockApi } from './mock'

/**
 * The only surface the UI talks to. A future FastAPI backend implements the same
 * endpoints (suggested routes in the comments); swap `api` below and the UI is untouched.
 */
export interface PolymathApi {
  /** GET /lenses */
  getLenses(): Promise<Lens[]>
  /** GET /lenses/{lensId}/digest */
  getDigest(lensId: string): Promise<Digest>
  /** POST /ask */
  ask(req: AskRequest): Promise<AskResult>
  /** POST /feedback */
  sendFeedback(event: FeedbackEvent): Promise<void>
  /** GET /links?lens={lensId}&limit={n}  (cross-lens method links involving this lens) */
  getLinks(lensId: string, limit?: number): Promise<CrossLensLink[]>
  /** GET /status */
  getStatus(): Promise<SystemStatus>
}

/** Set VITE_API_URL to use the real backend; otherwise the fixture-backed mock is used. */
const API_URL = import.meta.env.VITE_API_URL

/** True while the UI shows fixture data. Controls the "Sample data" badges and sample wording. */
export const SAMPLE_MODE = !API_URL

export const api: PolymathApi = API_URL ? httpApi(API_URL) : mockApi
