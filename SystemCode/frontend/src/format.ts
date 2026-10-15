export const pct = (v: number | null | undefined, digits = 0) =>
  v === null || v === undefined ? '—' : `${(v * 100).toFixed(digits)}%`

// A model probability is never certain, so rounding must not print 0% or 100%.
export const probability = (v: number, digits = 0) => {
  const step = 10 ** -digits
  const shown = Number((v * 100).toFixed(digits))
  if (shown >= 100) return `>${(100 - step).toFixed(digits)}%`
  if (shown <= 0) return `<${step.toFixed(digits)}%`
  return `${shown.toFixed(digits)}%`
}

export const money = (v: number) =>
  v.toLocaleString(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })

export const num = (v: number | null | undefined, digits = 2) =>
  v === null || v === undefined ? '—' : v.toFixed(digits)

export const date = (v: string | null | undefined) => (v ? new Date(v).toLocaleDateString() : '—')

export const dateTime = (v: string | null | undefined) => (v ? new Date(v).toLocaleString() : '—')
