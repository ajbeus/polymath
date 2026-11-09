import type { BuildId } from '../types'

/**
 * Build flavour. `showcase` (default) is safe to present: worm lab, fusion, math only.
 * `full` adds the personal lenses. Set with VITE_BUILD.
 */
export const BUILD: BuildId = import.meta.env.VITE_BUILD === 'full' ? 'full' : 'showcase'

export const APP_NAME: string = import.meta.env.VITE_APP_NAME || 'Polymath'
/** Name of the future conversational assistant. Not hardcoded anywhere else. */
export const ASSISTANT_NAME: string = import.meta.env.VITE_ASSISTANT_NAME || 'Ada'
