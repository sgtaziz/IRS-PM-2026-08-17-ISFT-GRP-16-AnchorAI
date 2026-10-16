<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{
  label: string
  value: string | number
  hint?: string
  tone?: 'default' | 'warn' | 'good'
  icon?: Component
}>()

const TONES = {
  default: 'bg-brand-50 text-brand-600',
  warn: 'bg-danger-soft text-danger',
  good: 'bg-success-soft text-success',
}
</script>

<template>
  <div class="flex min-w-0 items-start gap-3.5 rounded-card border border-ink-200 bg-white p-4 shadow-card">
    <span v-if="icon" class="hidden size-10 shrink-0 place-items-center rounded-xl sm:grid" :class="TONES[tone ?? 'default']">
      <component :is="icon" :size="20" aria-hidden="true" />
    </span>
    <div class="flex min-w-0 flex-col gap-0.5">
      <span class="text-[0.8125rem] font-medium text-ink-500">{{ label }}</span>
      <strong class="text-[1.625rem] leading-tight font-semibold tracking-tight text-ink-900 tabular-nums">{{ value }}</strong>
      <small v-if="hint" class="text-xs text-ink-500">{{ hint }}</small>
    </div>
  </div>
</template>
