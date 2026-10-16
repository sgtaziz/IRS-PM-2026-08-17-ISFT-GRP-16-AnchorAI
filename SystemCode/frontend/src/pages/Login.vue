<script setup lang="ts">
import { BrainCircuit, Route, ShieldCheck } from 'lucide-vue-next'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Password from 'primevue/password'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError } from '../api/client'
import AppLogo from '../components/AppLogo.vue'
import { useAuthStore } from '../stores/auth'

const POINTS = [
  { icon: BrainCircuit, title: 'Know who is slipping', text: 'Calibrated churn scores with the reasons behind every one.' },
  { icon: Route, title: 'Plan within budget', text: 'A weekly contact plan that respects staff hours, costs and guardrails.' },
  { icon: ShieldCheck, title: 'Explain every call', text: 'Rule traces, graph signals and a grounded assistant, all auditable.' },
]

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
  <div class="grid min-h-dvh bg-white lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
    <aside class="relative hidden overflow-hidden bg-navy-900 p-12 text-white lg:flex lg:flex-col xl:p-16">
      <div class="pointer-events-none absolute -top-40 -right-40 size-[36rem] rounded-full bg-brand-600/30 blur-3xl" aria-hidden="true" />
      <div class="pointer-events-none absolute -bottom-48 -left-24 size-[30rem] rounded-full bg-[#14a3a0]/20 blur-3xl" aria-hidden="true" />
      <AppLogo tone="light" :size="36" class="relative" />
      <div class="relative my-auto max-w-lg py-12">
        <p class="m-0 mb-4 text-sm font-semibold tracking-wider text-brand-300 uppercase">Gym retention planner</p>
        <h1 class="m-0 text-4xl leading-tight font-semibold tracking-tight text-white xl:text-5xl">
          Keep members before they drift away.
        </h1>
        <ul class="m-0 mt-10 flex list-none flex-col gap-6 p-0">
          <li v-for="p in POINTS" :key="p.title" class="flex gap-4">
            <span class="grid size-10 shrink-0 place-items-center rounded-xl bg-white/10 text-brand-200 ring-1 ring-white/15">
              <component :is="p.icon" :size="20" aria-hidden="true" />
            </span>
            <div>
              <p class="m-0 font-semibold text-white">{{ p.title }}</p>
              <p class="m-0 mt-0.5 text-sm text-ink-300">{{ p.text }}</p>
            </div>
          </li>
        </ul>
      </div>
      <p class="relative m-0 text-xs text-ink-400">NUS-ISS Intelligent Reasoning Systems · pseudonymous demo data</p>
    </aside>

    <main class="flex items-center justify-center px-5 py-12 sm:px-8">
      <form class="flex w-full max-w-sm flex-col gap-5" @submit.prevent="submit">
        <AppLogo class="mb-4 lg:hidden" :size="36" />
        <div>
          <h2 class="m-0 text-2xl font-semibold tracking-tight">Sign in</h2>
          <p class="m-0 mt-1 text-sm text-ink-500">Welcome back. Use your AnchorAI account.</p>
        </div>
        <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
        <div class="field">
          <label for="username" class="text-[0.8125rem] font-semibold text-ink-700">Username</label>
          <InputText id="username" v-model="username" autocomplete="username" autofocus required fluid />
        </div>
        <div class="field">
          <label for="password" class="text-[0.8125rem] font-semibold text-ink-700">Password</label>
          <Password
            input-id="password"
            v-model="password"
            :feedback="false"
            toggle-mask
            fluid
            autocomplete="current-password"
            required
          />
        </div>
        <Button type="submit" label="Sign in" :loading="loading" class="mt-1 h-11" />
        <div class="rounded-xl border border-ink-200 bg-ink-50 p-4 text-sm text-ink-600">
          <p class="m-0 flex flex-wrap items-baseline justify-between gap-2">
            <span class="font-semibold text-ink-800">Demo accounts</span>
            <span class="text-xs">password <code class="id-chip">anchorai</code></span>
          </p>
          <p class="m-0 mt-2 flex flex-wrap gap-1.5">
            <code v-for="u in ['admin', 'manager', 'staff1', 'staff2']" :key="u" class="id-chip">{{ u }}</code>
          </p>
        </div>
      </form>
    </main>
  </div>
</template>
