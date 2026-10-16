<script setup lang="ts">
import mark from '../assets/logo-mark.svg'

withDefaults(defineProps<{ wordmark?: boolean; tone?: 'light' | 'dark'; size?: number }>(), {
  wordmark: true,
  tone: 'dark',
  size: 32,
})
</script>

<template>
  <span class="inline-flex items-center gap-2.5 select-none">
    <img :src="mark" alt="" :width="size" :height="size" class="shrink-0" />
    <span
      v-if="wordmark"
      class="text-[1.15rem] font-bold tracking-tight whitespace-nowrap"
      :class="tone === 'light' ? 'text-white' : 'text-ink-900'"
    >
      Anchor<span :class="tone === 'light' ? 'text-brand-300' : 'text-brand-600'">AI</span>
    </span>
  </span>
</template>
