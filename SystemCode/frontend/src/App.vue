<script setup lang="ts">
import Button from 'primevue/button'
import ConfirmDialog from 'primevue/confirmdialog'
import Toast from 'primevue/toast'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MemberSearch from './components/MemberSearch.vue'
import { routes } from './router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const menuOpen = ref(false)

const nav = computed(() =>
  routes.filter((r) => !r.meta?.hidden && (!r.meta?.roles || auth.hasRole(r.meta.roles))),
)

watch(
  () => route.fullPath,
  () => (menuOpen.value = false),
)

function logout() {
  auth.logout()
  router.push({ name: 'Login' })
}
</script>

<template>
  <Toast />
  <ConfirmDialog />
  <div class="layout" :class="{ public: route.meta.public, 'menu-open': menuOpen }">
    <header v-if="!route.meta.public" class="topbar">
      <Button
        label="Menu"
        size="small"
        severity="secondary"
        :aria-expanded="menuOpen"
        aria-controls="sidebar"
        @click="menuOpen = !menuOpen"
      />
      <strong>AnchorAI</strong>
    </header>
    <aside v-if="!route.meta.public" id="sidebar">
      <h1>AnchorAI</h1>
      <MemberSearch v-if="auth.isAuthenticated" />
      <nav aria-label="Main">
        <RouterLink v-for="r in nav" :key="r.path" :to="r.path">{{ r.name }}</RouterLink>
      </nav>
      <div v-if="auth.user" class="session">
        <span>{{ auth.user.full_name || auth.user.username }}</span>
        <small>{{ auth.user.role }}</small>
        <Button label="Log out" size="small" severity="secondary" @click="logout" />
      </div>
    </aside>
    <main><RouterView /></main>
  </div>
</template>
