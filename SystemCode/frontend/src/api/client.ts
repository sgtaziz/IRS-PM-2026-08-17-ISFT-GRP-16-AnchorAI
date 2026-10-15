// Typed fetch helpers. Mirror the pydantic models in backend/anchorai/schemas.py.
const TOKEN_KEY = 'anchorai.token'

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY)
export const setToken = (token: string) => localStorage.setItem(TOKEN_KEY, token)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

// Injected by main.ts so this module stays free of router and store imports.
let onUnauthorized: () => void = () => {}
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  const token = getToken()
  const headers = new Headers(init?.headers)
  if (init?.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const res = await fetch(`/api${path}`, { ...init, headers })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const message = typeof body?.detail === 'string' ? body.detail : res.statusText
    // A failed login is also a 401; only a rejected session should log out.
    if (res.status === 401 && token) {
      clearToken()
      onUnauthorized()
    }
    throw new ApiError(res.status, message)
  }
  return res
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await request(path, init)
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export async function apiText(path: string, init?: RequestInit): Promise<string> {
  return (await request(path, init)).text()
}

export function query(params: Record<string, string | number | null | undefined>): string {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== null && v !== undefined && v !== '') q.set(k, String(v))
  const s = q.toString()
  return s ? `?${s}` : ''
}

export function downloadText(filename: string, text: string, type = 'text/csv') {
  const url = URL.createObjectURL(new Blob([text], { type }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
