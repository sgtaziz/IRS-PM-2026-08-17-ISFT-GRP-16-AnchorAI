<script setup lang="ts">
import Button from 'primevue/button'
import ConfirmDialog from 'primevue/confirmdialog'
import Drawer from 'primevue/drawer'
import Toast from 'primevue/toast'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AssistantChat from './components/AssistantChat.vue'
import MemberSearch from './components/MemberSearch.vue'
import { routes } from './router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const menuOpen = ref(false)
const assistantOpen = ref(false)

// The floating assistant knows which member is open, and hides on its own page.
const showAssistant = computed(() => auth.isAuthenticated && !route.meta.public && route.name !== 'Assistant')
const pageMember = computed(() => (route.name === 'Member' ? String(route.params.id) : null))

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
  <template v-if="showAssistant">
    <Button class="assistant-fab" label="Ask the assistant" aria-haspopup="dialog" @click="assistantOpen = true" />
    <Drawer v-model:visible="assistantOpen" header="Assistant" position="right" class="assistant-drawer">
      <AssistantChat :member-id="pageMember" />
    </Drawer>
  </template>
</template>
