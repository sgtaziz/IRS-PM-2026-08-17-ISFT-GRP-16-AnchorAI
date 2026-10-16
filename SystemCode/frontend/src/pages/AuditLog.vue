<script setup lang="ts">
import Column from 'primevue/column'
import type { DataTablePageEvent } from 'primevue/datatable'
import Select from 'primevue/select'
import { onMounted, ref, watch } from 'vue'
import { api, query } from '../api/client'
import type { AuditPage, AuditRow } from '../api/types'
import DataTableX from '../components/DataTableX.vue'
import PageState from '../components/PageState.vue'
import { useAsync } from '../composables/useAsync'
import { dateTime } from '../format'

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
  <div class="page-head">
    <h2>Audit log</h2>
    <span class="sub">Every write: who, when, what, before and after</span>
  </div>
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
        <Select v-model="action" :options="page.data.value.actions" placeholder="All actions" show-clear size="small" aria-label="Filter by action" />
        <Select v-model="username" :options="page.data.value.usernames" placeholder="All users" show-clear size="small" aria-label="Filter by user" />
      </template>
      <Column field="ts" header="When"><template #body="{ data }">{{ dateTime(data.ts) }}</template></Column>
      <Column field="username" header="Who" />
      <Column field="action" header="Action" />
      <Column header="What"><template #body="{ data }">{{ data.entity }}{{ data.entity_id ? ` ${data.entity_id}` : '' }}</template></Column>
      <Column header="Change">
        <template #body="{ data }">
          <span v-if="!data.before && !data.after" class="muted">—</span>
          <details v-else>
            <summary class="change">{{ change(data) }}</summary>
            <div class="grid cols-2">
              <div><strong>Before</strong><pre>{{ data.before ? JSON.stringify(data.before, null, 2) : '—' }}</pre></div>
              <div><strong>After</strong><pre>{{ data.after ? JSON.stringify(data.after, null, 2) : '—' }}</pre></div>
            </div>
          </details>
        </template>
      </Column>
    </DataTableX>
  </PageState>
</template>

<style scoped>
.change { display: inline-block; max-width: 420px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 0.85rem; vertical-align: bottom; }
pre { font-size: 0.8rem; max-height: 240px; overflow: auto; }
</style>
