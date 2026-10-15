import { ref, shallowRef } from 'vue'
import { ApiError } from '../api/client'

export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return e.status === 503 ? e.message : `${e.message} (${e.status})`
  return e instanceof Error ? e.message : 'Something went wrong'
}

export function useAsync<T, A extends unknown[] = []>(fn: (...args: A) => Promise<T>) {
  const data = shallowRef<T | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  let latest = 0

  async function run(...args: A): Promise<T | null> {
    const call = ++latest
    loading.value = true
    error.value = null
    try {
      const result = await fn(...args)
      // Drop responses that arrive after a newer request, e.g. fast filter changes.
      if (call === latest) data.value = result
      return result
    } catch (e) {
      if (call === latest) error.value = errorMessage(e)
      return null
    } finally {
      if (call === latest) loading.value = false
    }
  }

  return { data, loading, error, run }
}
