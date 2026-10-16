<script setup lang="ts" generic="T extends object">
import { FilterMatchMode } from '@primevue/core/api'
import { Download, Search } from 'lucide-vue-next'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import { ref } from 'vue'

defineOptions({ inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    value: T[]
    dataKey?: string
    lazy?: boolean
    totalRecords?: number
    rows?: number
    loading?: boolean
    exportName?: string
    globalFilterFields?: string[]
    paginator?: boolean
  }>(),
  { dataKey: 'id', lazy: false, rows: 25, loading: false, exportName: 'export', paginator: true },
)
// Server-side tables export through the API so the file holds every filtered row, not one page.
const emit = defineEmits<{ export: [] }>()

const table = ref<InstanceType<typeof DataTable> | null>(null)
const filters = ref({ global: { value: null as string | null, matchMode: FilterMatchMode.CONTAINS } })

function exportCsv() {
  if (props.lazy) emit('export')
  else table.value?.exportCSV()
}
</script>

<template>
  <DataTable
    ref="table"
    v-bind="$attrs"
    v-model:filters="filters"
    :value="value"
    :data-key="dataKey"
    :lazy="lazy"
    :total-records="lazy ? totalRecords : undefined"
    :rows="rows"
    :paginator="paginator"
    :loading="loading"
    :global-filter-fields="lazy ? undefined : globalFilterFields"
    :export-filename="exportName"
    removable-sort
    scrollable
  >
    <template #header>
      <div class="flex flex-wrap items-center gap-2">
        <slot name="toolbar" />
        <div class="ml-auto flex flex-wrap items-center gap-2">
          <IconField v-if="!lazy && globalFilterFields?.length">
            <InputIcon><Search :size="15" /></InputIcon>
            <InputText v-model="filters.global.value" placeholder="Filter rows" aria-label="Filter rows" size="small" />
          </IconField>
          <Button label="Export CSV" size="small" severity="secondary" outlined @click="exportCsv">
            <template #icon><Download :size="15" /></template>
          </Button>
        </div>
      </div>
    </template>
    <template #empty><p class="m-0 py-8 text-center text-sm text-ink-500">No rows match.</p></template>
    <slot />
  </DataTable>
</template>
