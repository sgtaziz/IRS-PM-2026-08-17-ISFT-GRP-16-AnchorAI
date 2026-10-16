<script setup lang="ts">
defineProps<{ title: string; subtitle?: string }>()
</script>

<template>
  <header class="mb-6 flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
    <div class="min-w-0">
      <h1 class="m-0 text-2xl font-semibold tracking-tight text-ink-900">
        <slot name="title">{{ title }}</slot>
      </h1>
      <p v-if="subtitle || $slots.subtitle" class="m-0 mt-1 max-w-3xl text-[0.9375rem] text-ink-500">
        <slot name="subtitle">{{ subtitle }}</slot>
      </p>
    </div>
    <div v-if="$slots.actions" class="flex flex-wrap items-center gap-2">
      <slot name="actions" />
    </div>
  </header>
</template>
