import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, clearToken, getToken, setToken } from '../api/client'
import type { Role, TokenResponse, UserOut } from '../api/types'
import { useAssistantStore } from './assistant'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(getToken())
  const user = ref<UserOut | null>(null)

  const isAuthenticated = computed(() => user.value !== null)
  const role = computed(() => user.value?.role ?? null)
  const homeRoute = computed(() => (role.value === 'staff' ? '/my-contacts' : '/'))

  function hasRole(roles: Role[]) {
    return role.value !== null && roles.includes(role.value)
  }

  async function login(username: string, password: string) {
    logout()
    const res = await api<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    setToken(res.access_token)
    token.value = res.access_token
    user.value = res.user
  }

  async function fetchMe() {
    user.value = await api<UserOut>('/auth/me')
  }

  function logout() {
    clearToken()
    token.value = null
    user.value = null
    // The next person to log in on this browser shouldn't see this chat.
    useAssistantStore().reset()
  }

  return { token, user, isAuthenticated, role, homeRoute, hasRole, login, fetchMe, logout }
})
