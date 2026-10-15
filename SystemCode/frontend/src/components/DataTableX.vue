<script setup lang="ts" generic="T extends object">
import { FilterMatchMode } from '@primevue/core/api'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
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
    striped-rows
    size="small"
    scrollable
  >
    <template #header>
      <div class="dtx-header">
        <slot name="toolbar" />
        <InputText
          v-if="!lazy && globalFilterFields?.length"
          v-model="filters.global.value"
          placeholder="Filter rows"
          aria-label="Filter rows"
          size="small"
        />
        <Button label="Export CSV" size="small" severity="secondary" outlined @click="exportCsv" />
      </div>
    </template>
    <template #empty>No rows match.</template>
    <slot />
  </DataTable>
</template>

<style scoped>
.dtx-header {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  justify-content: flex-end;
}
</style>
