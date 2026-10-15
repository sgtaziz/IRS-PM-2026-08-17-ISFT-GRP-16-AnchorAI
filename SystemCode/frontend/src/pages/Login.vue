<script setup lang="ts">
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Password from 'primevue/password'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError } from '../api/client'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref<string | null>(null)

async function submit() {
  loading.value = true
  error.value = null
  try {
    await auth.login(username.value, password.value)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : null
    await router.replace(redirect ?? auth.homeRoute)
  } catch (e) {
    error.value =
      e instanceof ApiError && e.status === 401 ? 'Invalid username or password' : 'Could not reach the server'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <form class="login-card" @submit.prevent="submit">
    <h2>AnchorAI</h2>
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <label for="username">Username</label>
    <InputText id="username" v-model="username" autocomplete="username" autofocus required />
    <label for="password">Password</label>
    <Password
      input-id="password"
      v-model="password"
      :feedback="false"
      toggle-mask
      fluid
      autocomplete="current-password"
      required
    />
    <Button type="submit" label="Log in" :loading="loading" />
    <small class="hint">Demo users: admin, manager, staff1, staff2 · password <code>anchorai</code></small>
  </form>
</template>
