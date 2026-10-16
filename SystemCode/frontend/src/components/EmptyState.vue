<script setup lang="ts">
import { Inbox } from 'lucide-vue-next'
import type { Component } from 'vue'

withDefaults(defineProps<{ title?: string; text?: string; icon?: Component; compact?: boolean }>(), {
  icon: () => Inbox,
  compact: false,
})
</script>

<template>
  <div class="flex flex-col items-center text-center" :class="compact ? 'gap-2 px-4 py-6' : 'gap-3 px-6 py-12'">
    <span class="grid place-items-center rounded-2xl bg-ink-100 text-ink-500" :class="compact ? 'size-10' : 'size-12'">
      <component :is="icon" :size="compact ? 20 : 24" aria-hidden="true" />
    </span>
    <p v-if="title" class="m-0 text-[0.9375rem] font-semibold text-ink-800">{{ title }}</p>
    <p v-if="text" class="m-0 max-w-md text-sm text-ink-500">{{ text }}</p>
    <div v-if="$slots.default" class="mt-1 flex flex-wrap justify-center gap-2"><slot /></div>
  </div>
</template>
