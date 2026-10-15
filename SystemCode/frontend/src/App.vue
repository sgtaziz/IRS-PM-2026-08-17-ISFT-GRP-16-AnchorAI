<script setup lang="ts">
import Button from 'primevue/button'
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { routes } from './router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const nav = computed(() =>
  routes.filter((r) => !r.meta?.hidden && (!r.meta?.roles || auth.hasRole(r.meta.roles))),
)

function logout() {
  auth.logout()
  router.push({ name: 'Login' })
}
</script>

<template>
  <div class="layout" :class="{ public: route.meta.public }">
    <aside v-if="!route.meta.public">
      <h1>AnchorAI</h1>
      <RouterLink v-for="r in nav" :key="r.path" :to="r.path">{{ r.name }}</RouterLink>
      <div v-if="auth.user" class="session">
        <span>{{ auth.user.full_name || auth.user.username }}</span>
        <small>{{ auth.user.role }}</small>
        <Button label="Log out" size="small" severity="secondary" @click="logout" />
      </div>
    </aside>
    <main><RouterView /></main>
  </div>
</template>
