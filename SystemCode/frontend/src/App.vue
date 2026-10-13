<script setup lang="ts">
import { routes } from './router'
const nav = routes.filter((r) => !r.meta?.hidden)
</script>

<template>
  <div class="layout">
    <aside>
      <h1>AnchorAI</h1>
      <RouterLink v-for="r in nav" :key="r.path" :to="r.path">{{ r.name }}</RouterLink>
    </aside>
    <main><RouterView /></main>
  </div>
</template>
