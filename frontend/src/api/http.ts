import type { PolymathApi } from './index'

/** PolymathApi backed by the FastAPI service. Same shapes as the mock; no UI changes needed. */
export function httpApi(baseUrl: string): PolymathApi {
  const base = baseUrl.replace(/\/$/, '')

  async function req<T>(path: string, init?: RequestInit): Promise<T> {
    let res: Response
    try {
      res = await fetch(base + path, init)
    } catch {
      throw new Error(`Cannot reach the backend at ${base}. Is it running?`)
    }
    if (!res.ok) throw new Error(`Backend returned ${res.status} for ${path}`)
    return res.status === 204 ? (undefined as T) : ((await res.json()) as T)
  }
  const post = (body: unknown): RequestInit => ({
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  return {
    getLenses: () => req('/lenses'),
    getDigest: (lensId) => req(`/lenses/${encodeURIComponent(lensId)}/digest`),
    ask: (r) => req('/ask', post(r)),
    sendFeedback: (e) => req('/feedback', post(e)),
    getLinks: (lensId, limit = 3) => req(`/links?lens=${encodeURIComponent(lensId)}&limit=${limit}`),
    getStatus: () => req('/status'),
  }
}
