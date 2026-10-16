<script setup lang="ts">
import { History } from 'lucide-vue-next'
import Column from 'primevue/column'
import type { DataTablePageEvent } from 'primevue/datatable'
import Select from 'primevue/select'
import { computed, onMounted, ref, watch } from 'vue'
import { api, query } from '../api/client'
import type { AuditPage, AuditRow } from '../api/types'
import DataTableX from '../components/DataTableX.vue'
import PageHeader from '../components/PageHeader.vue'
import PageState from '../components/PageState.vue'
import SectionCard from '../components/SectionCard.vue'
import { useAsync } from '../composables/useAsync'
import { dateTime } from '../format'
import { humanize } from '../labels'

const PAGE = 25
const action = ref<string | null>(null)
const username = ref<string | null>(null)
const offset = ref(0)

const page = useAsync(() =>
  api<AuditPage>(`/admin/audit${query({ action: action.value, username: username.value, limit: PAGE, offset: offset.value })}`),
)
onMounted(page.run)
watch([action, username], () => {
  offset.value = 0
  page.run()
})

const actionOptions = computed(() => (page.data.value?.actions ?? []).map((a) => ({ label: humanize(a), value: a })))

const ACTION_TONES: Record<string, string> = {
  delete: 'bg-danger-soft text-danger-ink',
  create: 'bg-success-soft text-success-ink',
  login: 'bg-ink-100 text-ink-600',
}
const actionTone = (a: string) => ACTION_TONES[a.split('.').at(-1) ?? ''] ?? 'bg-brand-50 text-brand-800'

function onPage(e: DataTablePageEvent) {
  offset.value = e.first
  page.run()
}

// The table pages on the server, so export walks every page that matches the filters.
async function exportCsv() {
  const items: AuditRow[] = []
  for (let from = 0; ; from += 200) {
    const batch = await api<AuditPage>(
      `/admin/audit${query({ action: action.value, username: username.value, limit: 200, offset: from })}`,
    )
    items.push(...batch.items)
    if (items.length >= batch.total || !batch.items.length) break
  }
  // Prefix cells a spreadsheet would run as a formula (=, +, -, @).
  const cell = (v: unknown) => {
    const text = String(v ?? '')
    return `"${(/^[=+\-@]/.test(text) ? `'${text}` : text).replaceAll('"', '""')}"`
  }
  const rows = items.map((r) => [r.ts, r.username, r.action, r.entity, r.entity_id, change(r)].map(cell).join(','))
  const csv = ['when,who,action,entity,entity_id,change', ...rows].join('\n')
  const link = document.createElement('a')
  link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
  link.download = 'audit-log.csv'
  link.click()
  URL.revokeObjectURL(link.href)
}

function change(r: AuditRow) {
  if (!r.before && !r.after) return '—'
  return JSON.stringify(r.after ?? r.before)
}
</script>

<template>
  <div class="page">
    <PageHeader title="Audit log" subtitle="Every write to AnchorAI: who did it, when, and what changed before and after." />
    <SectionCard :title="page.data.value ? `${page.data.value.total.toLocaleString()} entries` : 'Entries'" :icon="History">
      <PageState :loading="page.loading.value && !page.data.value" :error="page.error.value" @retry="page.run">
        <DataTableX
          v-if="page.data.value"
          :value="page.data.value.items"
          lazy
          :total-records="page.data.value.total"
          :rows="PAGE"
          :first="offset"
          :loading="page.loading.value"
          @page="onPage"
          @export="exportCsv"
        >
          <template #toolbar>
            <Select v-model="action" :options="actionOptions" option-label="label" option-value="value" placeholder="All actions" show-clear size="small" class="min-w-44" aria-label="Filter by action" />
            <Select v-model="username" :options="page.data.value.usernames" placeholder="All users" show-clear size="small" class="min-w-40" aria-label="Filter by user" />
          </template>
          <Column field="ts" header="When">
            <template #body="{ data }"><span class="text-ink-600 tabular-nums">{{ dateTime(data.ts) }}</span></template>
          </Column>
          <Column field="username" header="Who">
            <template #body="{ data }"><span class="font-medium text-ink-800">{{ data.username }}</span></template>
          </Column>
          <Column field="action" header="Action">
            <template #body="{ data }">
              <span class="rounded-full px-2.5 py-0.5 text-xs font-semibold" :class="actionTone(data.action)">{{ humanize(data.action) }}</span>
            </template>
          </Column>
          <Column header="What">
            <template #body="{ data }">
              {{ humanize(data.entity) }}
              <span v-if="data.entity_id" class="id-chip ml-1">{{ data.entity_id }}</span>
            </template>
          </Column>
          <Column header="Change">
            <template #body="{ data }">
              <span v-if="!data.before && !data.after" class="text-ink-400">—</span>
              <details v-else class="whitespace-normal">
                <summary class="change">{{ change(data) }}</summary>
                <div class="mt-2 grid gap-3 md:grid-cols-2">
                  <div><p class="m-0 mb-1 text-xs font-semibold text-ink-500 uppercase">Before</p><pre>{{ data.before ? JSON.stringify(data.before, null, 2) : '—' }}</pre></div>
                  <div><p class="m-0 mb-1 text-xs font-semibold text-ink-500 uppercase">After</p><pre>{{ data.after ? JSON.stringify(data.after, null, 2) : '—' }}</pre></div>
                </div>
              </details>
            </template>
          </Column>
        </DataTableX>
      </PageState>
    </SectionCard>
  </div>
</template>

<style scoped>
.change { display: inline-block; max-width: 28rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font: 0.78rem var(--font-mono); color: var(--color-ink-600); vertical-align: bottom; cursor: pointer; }
pre { margin: 0; padding: 0.6rem; font-size: 0.75rem; max-height: 240px; overflow: auto; background: var(--color-ink-50); border: 1px solid var(--color-ink-100); border-radius: 0.5rem; }
</style>
