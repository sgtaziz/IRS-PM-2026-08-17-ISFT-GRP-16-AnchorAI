<script setup lang="ts">
import { Check, Hammer } from 'lucide-vue-next'
import type { Component } from 'vue'

// Holds the place of a page another stream is still building, saying what it will do.
defineProps<{ icon: Component; title: string; text: string; features: string[]; owner: string }>()
</script>

<template>
  <section class="relative overflow-hidden rounded-card border border-ink-200 bg-card shadow-card">
    <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(60rem_20rem_at_100%_0%,var(--color-brand-50),transparent_70%)]" aria-hidden="true" />
    <div class="relative grid gap-8 p-6 md:p-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] lg:items-center">
      <div class="flex flex-col items-start gap-4">
        <span class="grid size-14 place-items-center rounded-2xl bg-brand-600 text-white shadow-raised">
          <component :is="icon" :size="28" aria-hidden="true" />
        </span>
        <span class="inline-flex items-center gap-1.5 rounded-full bg-warn-soft px-2.5 py-1 text-xs font-semibold text-warn-ink">
          <Hammer :size="13" aria-hidden="true" /> In development · {{ owner }}
        </span>
        <h2 class="m-0 text-xl font-semibold text-ink-900 md:text-2xl">{{ title }}</h2>
        <p class="m-0 max-w-xl text-[0.9375rem] leading-relaxed text-ink-600">{{ text }}</p>
      </div>
      <div class="rounded-xl border border-ink-200 bg-ink-50/70 p-5">
        <p class="m-0 mb-3 text-xs font-semibold tracking-wider text-ink-500 uppercase">What this page will do</p>
        <ul class="m-0 flex list-none flex-col gap-2.5 p-0">
          <li v-for="f in features" :key="f" class="flex gap-2.5 text-sm text-ink-700">
            <span class="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full bg-brand-100 text-brand-700">
              <Check :size="12" stroke-width="3" aria-hidden="true" />
            </span>
            {{ f }}
          </li>
        </ul>
      </div>
    </div>
  </section>
  <div class="mt-5 grid gap-5 opacity-70 md:grid-cols-3" aria-hidden="true">
    <div v-for="n in 3" :key="n" class="rounded-card border border-dashed border-ink-200 bg-card/60 p-5">
      <div class="mb-4 h-3 w-1/3 rounded-full bg-ink-100" />
      <div v-for="r in 4" :key="r" class="mb-3 flex items-center gap-3">
        <div class="size-7 shrink-0 rounded-lg bg-ink-100" />
        <div class="h-2.5 rounded-full bg-ink-100" :style="{ width: `${85 - ((n * 7 + r * 13) % 40)}%` }" />
      </div>
    </div>
  </div>
</template>
