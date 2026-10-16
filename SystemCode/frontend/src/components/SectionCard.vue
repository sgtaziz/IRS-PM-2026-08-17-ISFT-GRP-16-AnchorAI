<script setup lang="ts">
import type { Component } from 'vue'

withDefaults(defineProps<{ title?: string; subtitle?: string; icon?: Component; flush?: boolean }>(), { flush: false })
</script>

<template>
  <section class="flex min-w-0 flex-col rounded-card border border-ink-200 bg-white shadow-card">
    <header v-if="title || $slots.actions" class="flex items-start gap-3 px-5 pt-4" :class="flush ? 'pb-4' : 'pb-1'">
      <span v-if="icon" class="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg bg-brand-50 text-brand-600">
        <component :is="icon" :size="17" aria-hidden="true" />
      </span>
      <div class="min-w-0 flex-1">
        <h2 class="m-0 text-base font-semibold text-ink-900">{{ title }}</h2>
        <p v-if="subtitle" class="m-0 mt-0.5 text-sm text-ink-500">{{ subtitle }}</p>
      </div>
      <div v-if="$slots.actions" class="flex shrink-0 flex-wrap items-center gap-2">
        <slot name="actions" />
      </div>
    </header>
    <div class="min-w-0 flex-1" :class="flush ? '' : 'px-5 pt-3 pb-5'">
      <slot />
    </div>
  </section>
</template>
