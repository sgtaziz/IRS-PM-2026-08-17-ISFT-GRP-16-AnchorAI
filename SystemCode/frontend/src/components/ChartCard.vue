<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import Card from 'primevue/card'
import VChart from 'vue-echarts'
import '../charts'
import PageState from './PageState.vue'

withDefaults(
  defineProps<{
    title: string
    option: EChartsOption | null
    loading?: boolean
    empty?: boolean
    emptyText?: string
    height?: string
  }>(),
  { loading: false, empty: false, emptyText: 'No data yet.', height: '280px' },
)
</script>

<template>
  <Card class="chart-card">
    <template #title>{{ title }}</template>
    <template #content>
      <PageState :loading="loading" :empty="empty || !option" :empty-text="emptyText">
        <VChart :option="option!" autoresize :style="{ height }" />
      </PageState>
      <slot />
    </template>
  </Card>
</template>

<style scoped>
.chart-card {
  min-width: 0;
}
</style>
