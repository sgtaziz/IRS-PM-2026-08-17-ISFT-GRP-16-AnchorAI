import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import type { Role } from './api/types'
import { useAuthStore } from './stores/auth'

export type { Role }

declare module 'vue-router' {
  interface RouteMeta {
    public?: boolean
    hidden?: boolean
    roles?: Role[]
  }
}

export const routes: RouteRecordRaw[] = [
  { path: '/login', name: 'Login', component: () => import('./pages/Login.vue'), meta: { public: true, hidden: true } },
  { path: '/', name: 'Dashboard', component: () => import('./pages/Dashboard.vue'), meta: { roles: ['manager', 'admin'] } },
  { path: '/segments', name: 'Segments', component: () => import('./pages/Segments.vue'), meta: { roles: ['manager', 'admin'] } },
  { path: '/members', name: 'Members', component: () => import('./pages/Members.vue'), meta: { roles: ['manager', 'admin'] } },
  { path: '/members/:id', name: 'Member', component: () => import('./pages/Member360.vue'), meta: { roles: ['staff', 'manager', 'admin'], hidden: true } },
  { path: '/plan', name: 'Weekly plan', component: () => import('./pages/PlanBuilder.vue'), meta: { roles: ['manager', 'admin'] } },
  { path: '/scenarios', name: 'Scenarios', component: () => import('./pages/Scenarios.vue'), meta: { roles: ['manager', 'admin'] } },
  { path: '/graph', name: 'Knowledge graph', component: () => import('./pages/GraphExplorer.vue'), meta: { roles: ['manager', 'admin'] } },
  { path: '/my-contacts', name: 'My contacts', component: () => import('./pages/MyContacts.vue'), meta: { roles: ['staff', 'manager', 'admin'] } },
  { path: '/assistant', name: 'Assistant', component: () => import('./pages/Assistant.vue'), meta: { roles: ['staff', 'manager', 'admin'] } },
  { path: '/admin/rules', name: 'Rules', component: () => import('./pages/RulesAdmin.vue'), meta: { roles: ['admin'] } },
  { path: '/admin/offers', name: 'Offers & constraints', component: () => import('./pages/OffersAdmin.vue'), meta: { roles: ['admin'] } },
  { path: '/admin/data', name: 'Data & models', component: () => import('./pages/DataAdmin.vue'), meta: { roles: ['admin'] } },
  { path: '/admin/users', name: 'Users', component: () => import('./pages/UsersAdmin.vue'), meta: { roles: ['admin'] } },
  { path: '/admin/audit', name: 'Audit log', component: () => import('./pages/AuditLog.vue'), meta: { roles: ['admin'] } },
  { path: '/admin/settings', name: 'Settings', component: () => import('./pages/Settings.vue'), meta: { roles: ['admin'] } },
]

export const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (auth.token && !auth.user) {
    try {
      await auth.fetchMe()
    } catch {
      auth.logout()
    }
  }
  if (to.meta.public) {
    return auth.isAuthenticated && to.name === 'Login' ? auth.homeRoute : true
  }
  if (!auth.isAuthenticated) return { name: 'Login', query: { redirect: to.fullPath } }
  if (to.meta.roles && !auth.hasRole(to.meta.roles)) return auth.homeRoute
  return true
})
