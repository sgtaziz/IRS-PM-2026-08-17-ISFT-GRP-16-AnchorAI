<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import type { Component } from 'vue'
import VChart from 'vue-echarts'
import { useChartTheme } from '../charts'
import PageState from './PageState.vue'
import SectionCard from './SectionCard.vue'

withDefaults(
  defineProps<{
    title: string
    subtitle?: string
    icon?: Component
    option: EChartsOption | null
    loading?: boolean
    empty?: boolean
    emptyText?: string
    height?: string
  }>(),
  { loading: false, empty: false, emptyText: 'No data yet.', height: '280px' },
)
const chartTheme = useChartTheme()
</script>

<template>
  <SectionCard :title="title" :subtitle="subtitle" :icon="icon">
    <template v-if="$slots.actions" #actions><slot name="actions" /></template>
    <PageState :loading="loading" :empty="empty || !option" :empty-text="emptyText">
      <VChart :option="option!" :theme="chartTheme" autoresize :style="{ height }" />
    </PageState>
    <slot />
  </SectionCard>
</template>
