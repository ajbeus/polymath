const dateFmt = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
const shortFmt = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' })
const timeFmt = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })

const d = (iso: string) => new Date(iso.length === 10 ? iso + 'T12:00:00' : iso)

export const formatDate = (iso: string) => dateFmt.format(d(iso))
export const formatShort = (iso: string) => shortFmt.format(d(iso))
export const formatDateTime = (iso: string) => timeFmt.format(d(iso))
export const pct = (x: number, digits = 0) => `${(x * 100).toFixed(digits)}%`
export const num = (n: number) => n.toLocaleString('en-US')

export function sourceLabel(s: string) {
  return s === 'arxiv' ? 'arXiv' : s === 'pubmed' ? 'PubMed' : s === 'biorxiv' ? 'bioRxiv' : s
}

export function authorLine(authors: string[]) {
  if (authors.length <= 3) return authors.join(', ')
  return `${authors.slice(0, 2).join(', ')}, +${authors.length - 2} more`
}
