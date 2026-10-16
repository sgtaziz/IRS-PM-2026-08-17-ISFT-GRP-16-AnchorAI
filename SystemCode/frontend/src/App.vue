<script setup lang="ts">
import { ChevronRight, ChevronsUpDown, LogOut, Maximize2, Menu as MenuIcon, PanelLeftClose, PanelLeftOpen, Sparkles, X } from 'lucide-vue-next'
import ConfirmDialog from 'primevue/confirmdialog'
import Drawer from 'primevue/drawer'
import Menu from 'primevue/menu'
import Toast from 'primevue/toast'
import vTooltip from 'primevue/tooltip'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLogo from './components/AppLogo.vue'
import AssistantChat from './components/AssistantChat.vue'
import MemberSearch from './components/MemberSearch.vue'
import ThemeToggle from './components/ThemeToggle.vue'
import { initials, ROLE_LABELS } from './labels'
import { groupOf, NAV_GROUPS, NAV_ICONS } from './nav'
import { routes } from './router'
import { useAuthStore } from './stores/auth'

const COLLAPSE_KEY = 'anchorai.sidebar-collapsed'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const menuOpen = ref(false)
const assistantOpen = ref(false)
const userMenu = ref<InstanceType<typeof Menu> | null>(null)
const collapsed = ref(readCollapsed())

function readCollapsed() {
  try {
    return localStorage.getItem(COLLAPSE_KEY) === '1'
  } catch {
    return false
  }
}

function toggleCollapsed() {
  collapsed.value = !collapsed.value
  try {
    localStorage.setItem(COLLAPSE_KEY, collapsed.value ? '1' : '0')
  } catch {
    // A blocked storage only means the choice isn't remembered.
  }
}

// The floating assistant knows which member is open, and hides on its own page.
const showAssistant = computed(() => auth.isAuthenticated && !route.meta.public && route.name !== 'Assistant')
const pageMember = computed(() => (route.name === 'Member' ? String(route.params.id) : null))

const nav = computed(() =>
  routes.filter((r) => !r.meta?.hidden && (!r.meta?.roles || auth.hasRole(r.meta.roles))),
)

const groups = computed(() => {
  const named = NAV_GROUPS.map((g) => ({ label: g.label, items: nav.value.filter((r) => g.routes.includes(String(r.name))) }))
  const known = NAV_GROUPS.flatMap((g) => g.routes)
  const rest = nav.value.filter((r) => !known.includes(String(r.name)))
  return [...named, { label: 'More', items: rest }].filter((g) => g.items.length)
})

const crumbs = computed(() => {
  if (route.name === 'Member') {
    const back = auth.hasRole(['manager', 'admin']) ? '/members' : null
    return [{ label: 'Members', to: back }, { label: String(route.params.id), to: null }]
  }
  const name = String(route.name ?? '')
  return [{ label: groupOf(name), to: null }, { label: name, to: null }]
})

const userItems = computed(() => [{ label: 'Log out', command: logout }])

watch(
  () => route.fullPath,
  () => {
    // A link clicked in the assistant drawer should show its page, not stay hidden behind it.
    menuOpen.value = false
    assistantOpen.value = false
  },
)

function logout() {
  auth.logout()
  router.push({ name: 'Login' })
}
</script>

<template>
  <Toast position="bottom-left" />
  <ConfirmDialog />
  <RouterView v-if="route.meta.public" />
  <div v-else class="shell" :class="{ collapsed, 'menu-open': menuOpen }">
    <a href="#main" class="skip-link">Skip to content</a>
    <aside id="sidebar" class="sidebar" aria-label="Sidebar">
      <div class="flex h-[var(--topbar-h)] shrink-0 items-center justify-between gap-2 px-4">
        <RouterLink :to="auth.homeRoute" class="rounded-lg" aria-label="AnchorAI home">
          <AppLogo tone="light" :wordmark="!collapsed" />
        </RouterLink>
        <button type="button" class="icon-btn grid text-[#cbd2de] lg:hidden" aria-label="Close menu" @click="menuOpen = false">
          <X :size="18" />
        </button>
      </div>
      <nav aria-label="Main" class="flex flex-1 flex-col gap-4 overflow-y-auto px-3 pt-2 pb-4">
        <div v-for="g in groups" :key="g.label" class="flex flex-col gap-0.5">
          <p class="group-label">{{ g.label }}</p>
          <RouterLink
            v-for="r in g.items"
            :key="r.path"
            v-tooltip.right="collapsed ? String(r.name) : undefined"
            :to="r.path"
            class="nav-link"
            :aria-label="collapsed ? String(r.name) : undefined"
          >
            <component :is="NAV_ICONS[String(r.name)] ?? ChevronRight" :size="18" class="shrink-0" aria-hidden="true" />
            <span class="nav-text">{{ r.name }}</span>
          </RouterLink>
        </div>
      </nav>
      <div class="hidden shrink-0 border-t border-white/8 p-3 lg:block">
        <button
          type="button"
          class="nav-link w-full"
          :aria-label="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
          :aria-expanded="!collapsed"
          aria-controls="sidebar"
          @click="toggleCollapsed"
        >
          <component :is="collapsed ? PanelLeftOpen : PanelLeftClose" :size="18" class="shrink-0" aria-hidden="true" />
          <span class="nav-text">Collapse</span>
        </button>
      </div>
    </aside>
    <div v-if="menuOpen" class="fixed inset-0 z-30 bg-ink-950/40 backdrop-blur-[2px] lg:hidden" aria-hidden="true" @click="menuOpen = false" />

    <div class="flex min-w-0 flex-1 flex-col">
      <header class="topbar">
        <button
          type="button"
          class="icon-btn grid -ml-1.5 text-ink-600 lg:hidden"
          aria-label="Open menu"
          :aria-expanded="menuOpen"
          aria-controls="sidebar"
          @click="menuOpen = true"
        >
          <MenuIcon :size="20" />
        </button>
        <nav aria-label="Breadcrumb" class="hidden min-w-0 md:block">
          <ol class="m-0 flex list-none items-center gap-1.5 p-0 text-sm">
            <li v-for="(c, i) in crumbs" :key="i" class="flex min-w-0 items-center gap-1.5">
              <ChevronRight v-if="i" :size="14" class="shrink-0 text-ink-300" aria-hidden="true" />
              <RouterLink v-if="c.to" :to="c.to" class="truncate text-ink-500 no-underline hover:text-ink-800">{{ c.label }}</RouterLink>
              <span v-else class="truncate" :class="i === crumbs.length - 1 ? 'font-semibold text-ink-800' : 'text-ink-500'" :aria-current="i === crumbs.length - 1 ? 'page' : undefined">{{ c.label }}</span>
            </li>
          </ol>
        </nav>
        <RouterLink :to="auth.homeRoute" class="md:hidden" aria-label="AnchorAI home"><AppLogo :size="28" /></RouterLink>
        <div class="ml-auto flex min-w-0 items-center gap-2 sm:gap-3">
          <div class="w-10 sm:w-64 xl:w-80"><MemberSearch v-if="auth.isAuthenticated" /></div>
          <ThemeToggle />
          <button
            v-if="auth.user"
            type="button"
            class="flex items-center gap-2.5 rounded-lg p-1 text-left transition hover:bg-ink-100 sm:pr-2"
            aria-haspopup="menu"
            aria-controls="user-menu"
            @click="userMenu?.toggle($event)"
          >
            <span class="grid size-8 place-items-center rounded-full bg-brand-600 text-xs font-bold text-white" aria-hidden="true">
              {{ initials(auth.user.full_name || auth.user.username) }}
            </span>
            <span class="hidden min-w-0 flex-col leading-tight sm:flex">
              <span class="truncate text-sm font-semibold text-ink-800">{{ auth.user.full_name || auth.user.username }}</span>
              <span class="text-xs text-ink-500">{{ ROLE_LABELS[auth.user.role] }}</span>
            </span>
            <ChevronsUpDown :size="15" class="hidden text-ink-400 sm:block" aria-hidden="true" />
            <span class="sr-only">Account menu</span>
          </button>
          <Menu id="user-menu" ref="userMenu" :model="userItems" popup class="min-w-56">
            <template #start>
              <div v-if="auth.user" class="border-b border-ink-100 px-3 pt-2 pb-2.5">
                <p class="m-0 text-sm font-semibold text-ink-800">{{ auth.user.full_name || auth.user.username }}</p>
                <p class="m-0 text-xs text-ink-500">@{{ auth.user.username }} · {{ ROLE_LABELS[auth.user.role] }}</p>
              </div>
            </template>
            <template #itemicon><LogOut :size="15" class="text-ink-500" /></template>
          </Menu>
        </div>
      </header>
      <main id="main" tabindex="-1" class="app-main" :class="{ 'with-fab': showAssistant }">
        <RouterView />
      </main>
    </div>
  </div>

  <template v-if="showAssistant">
    <button
      v-show="!assistantOpen"
      v-tooltip.left="'Ask the assistant'"
      type="button"
      class="assistant-fab"
      aria-label="Ask the assistant"
      aria-haspopup="dialog"
      @click="assistantOpen = true"
    >
      <Sparkles :size="24" aria-hidden="true" />
    </button>
    <Drawer v-model:visible="assistantOpen" position="right" class="assistant-drawer">
      <template #header>
        <div class="flex min-w-0 flex-1 items-center gap-3">
          <span class="grid size-9 shrink-0 place-items-center rounded-xl bg-brand-600 text-white"><Sparkles :size="18" aria-hidden="true" /></span>
          <div class="min-w-0">
            <h2 class="m-0 text-base font-semibold">Assistant</h2>
            <p class="m-0 text-xs text-ink-500">Answers only from AnchorAI's data</p>
          </div>
          <RouterLink
            v-tooltip.bottom="'Open full page'"
            :to="{ path: '/assistant', query: pageMember ? { member: pageMember } : {} }"
            class="icon-btn grid ml-auto text-ink-500"
            aria-label="Open the assistant full page"
          >
            <Maximize2 :size="16" />
          </RouterLink>
        </div>
      </template>
      <AssistantChat :member-id="pageMember" compact />
    </Drawer>
  </template>
</template>

<style scoped>
.shell { display: flex; min-height: 100dvh; }
.sidebar {
  position: sticky; top: 0; z-index: 40; display: flex; flex-direction: column; flex: none;
  width: var(--sidebar-w); height: 100dvh;
  background: linear-gradient(180deg, var(--color-navy-900), var(--color-navy-950));
  color: #cbd2de;
  transition: width 0.2s ease;
}
.collapsed .sidebar { width: var(--sidebar-w-collapsed); }
:global(.app-dark) .sidebar { border-right: 1px solid rgb(255 255 255 / 0.06); background: linear-gradient(180deg, #0a1428, #070d1c); }
.group-label {
  margin: 0 0 0.25rem; padding: 0 0.75rem; font-size: 0.6875rem; font-weight: 600;
  letter-spacing: 0.08em; text-transform: uppercase; color: rgb(152 162 182 / 0.8);
}
.collapsed .group-label { height: 1px; margin: 0.25rem 0.75rem 0.5rem; padding: 0; overflow: hidden; color: transparent; background: rgb(255 255 255 / 0.08); }
.nav-link {
  position: relative; display: flex; align-items: center; gap: 0.75rem; height: 2.25rem; padding: 0 0.75rem;
  border: 0; border-radius: 0.5rem; background: none; cursor: pointer;
  color: #cbd2de; font: 500 0.875rem/1 var(--font-sans); text-decoration: none; white-space: nowrap;
  transition: background 0.15s, color 0.15s;
}
.nav-link:hover { background: rgb(255 255 255 / 0.06); color: #fff; }
.nav-link:focus-visible { outline: 2px solid var(--color-brand-300); outline-offset: -2px; }
.nav-link.router-link-exact-active { background: rgb(255 255 255 / 0.1); color: #fff; }
.nav-link.router-link-exact-active::before {
  content: ''; position: absolute; left: -0.75rem; top: 0.5rem; bottom: 0.5rem; width: 3px;
  border-radius: 0 3px 3px 0; background: var(--color-brand-400);
}
.nav-link.router-link-exact-active svg { color: var(--color-brand-300); }
.collapsed .nav-link { justify-content: center; padding: 0; }
.collapsed .nav-text { display: none; }

.topbar {
  position: sticky; top: 0; z-index: 20; display: flex; align-items: center; gap: 1rem;
  height: var(--topbar-h); padding: 0 1rem; border-bottom: 1px solid var(--color-ink-200);
  background: color-mix(in srgb, var(--color-card) 86%, transparent); backdrop-filter: saturate(1.4) blur(10px);
}
@media (min-width: 640px) { .topbar { padding: 0 1.5rem; } }
@media (min-width: 1024px) { .topbar { padding: 0 2rem; } }

.app-main { flex: 1; min-width: 0; padding: var(--main-pt) var(--main-px) var(--main-pb); }
.app-main:focus { outline: none; }
/* Room for the assistant button, so it never covers the last row of a page. */
.app-main.with-fab { padding-bottom: calc(var(--main-pb) + 4.5rem); }

.icon-btn {
  place-items: center; width: 2.25rem; height: 2.25rem; border: 0; border-radius: 0.5rem;
  background: none; cursor: pointer;
}
.icon-btn:hover { background: rgb(127 127 127 / 0.12); }

.skip-link {
  position: fixed; left: 1rem; top: -4rem; z-index: 100; padding: 0.5rem 0.875rem; border-radius: 0.5rem;
  background: var(--color-brand-600); color: #fff; font-weight: 600; text-decoration: none;
}
.skip-link:focus { top: 1rem; }

@media (max-width: 1023.98px) {
  .sidebar { position: fixed; left: 0; width: min(18rem, 86vw) !important; transform: translateX(-100%); transition: transform 0.22s ease; }
  .menu-open .sidebar { transform: none; box-shadow: 0 0 40px rgb(0 0 0 / 0.3); }
  .collapsed .nav-text { display: inline; }
  .collapsed .nav-link { justify-content: flex-start; padding: 0 0.75rem; }
  .collapsed .group-label { height: auto; margin: 0 0 0.25rem; padding: 0 0.75rem; color: rgb(152 162 182 / 0.8); background: none; }
}

.assistant-fab {
  position: fixed; right: 1.5rem; bottom: 1.5rem; z-index: 50; display: grid; place-items: center;
  width: 3.5rem; height: 3.5rem; border: 0; border-radius: 999px; cursor: pointer; color: #fff;
  background: linear-gradient(135deg, #347ef6, #1a3fac);
  box-shadow: var(--shadow-fab); transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.assistant-fab:hover { transform: translateY(-2px) scale(1.03); }
.assistant-fab:focus-visible { outline: 3px solid var(--color-brand-300); outline-offset: 3px; }
@media (max-width: 640px) { .assistant-fab { right: 1rem; bottom: 1rem; } }
</style>

<style>
.assistant-drawer.p-drawer { width: min(32rem, 100vw); }
.assistant-drawer .p-drawer-content { display: flex; flex-direction: column; min-height: 0; padding-bottom: 1rem; }
.assistant-drawer .p-drawer-header { border-bottom: 1px solid var(--color-ink-100); margin-bottom: 0.75rem; gap: 0.5rem; }
</style>
