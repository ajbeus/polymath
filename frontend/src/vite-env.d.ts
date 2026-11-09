/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_BUILD?: 'showcase' | 'full'
  readonly VITE_API_URL?: string
  readonly VITE_APP_NAME?: string
  readonly VITE_ASSISTANT_NAME?: string
}
interface ImportMeta {
  readonly env: ImportMetaEnv
}
