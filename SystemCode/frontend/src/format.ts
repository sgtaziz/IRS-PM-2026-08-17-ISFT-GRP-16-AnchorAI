export const pct = (v: number | null | undefined, digits = 0) =>
  v === null || v === undefined ? '—' : `${(v * 100).toFixed(digits)}%`

export const money = (v: number) =>
  v.toLocaleString(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })

export const num = (v: number | null | undefined, digits = 2) =>
  v === null || v === undefined ? '—' : v.toFixed(digits)

export const date = (v: string | null | undefined) => (v ? new Date(v).toLocaleDateString() : '—')

export const dateTime = (v: string | null | undefined) => (v ? new Date(v).toLocaleString() : '—')
