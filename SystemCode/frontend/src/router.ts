import { createRouter, createWebHistory } from 'vue-router'

export const routes = [
  { path: '/', name: 'Dashboard', component: () => import('./pages/Dashboard.vue') },
  { path: '/segments', name: 'Segments', component: () => import('./pages/Segments.vue') },
  { path: '/members/:id', name: 'Member', component: () => import('./pages/MemberDetail.vue'), meta: { hidden: true } },
  { path: '/plan', name: 'Weekly plan', component: () => import('./pages/Plan.vue') },
  { path: '/scenarios', name: 'Scenarios', component: () => import('./pages/Scenarios.vue') },
  { path: '/rules', name: 'Rules', component: () => import('./pages/Rules.vue') },
  { path: '/assistant', name: 'Assistant', component: () => import('./pages/Assistant.vue') },
]

export const router = createRouter({ history: createWebHistory(), routes })
