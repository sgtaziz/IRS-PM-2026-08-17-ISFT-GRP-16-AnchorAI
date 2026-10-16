import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'
import type { Glossary } from '../api/types'
import { humanize } from '../labels'

// Readable names for rule, offer and fact ids, loaded once per session.
export const useGlossaryStore = defineStore('glossary', () => {
  const data = ref<Glossary | null>(null)
  let pending: Promise<void> | null = null

  function load() {
    pending ??= api<Glossary>('/rules/glossary')
      .then((g) => {
        data.value = g
      })
      .catch(() => {
        // Without it every id falls back to a humanised code; try again on the next page.
        pending = null
      })
    return pending
  }

  const rule = (id: string) => data.value?.rules[id] ?? humanize(id.replace(/^[A-Z]\d+_/, ''))
  const offer = (id: string) => data.value?.offers[id] ?? humanize(id)
  const fact = (name: string) => data.value?.facts[name] ?? humanize(name)

  return { data, load, rule, offer, fact }
})
