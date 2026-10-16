<script setup lang="ts">
import { KeyRound, Pencil, Plus, UserCog } from 'lucide-vue-next'
import Button from 'primevue/button'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Password from 'primevue/password'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import { useToast } from 'primevue/usetoast'
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import type { Role, UserRow } from '../api/types'
import DataTableX from '../components/DataTableX.vue'
import PageHeader from '../components/PageHeader.vue'
import PageState from '../components/PageState.vue'
import SectionCard from '../components/SectionCard.vue'
import { errorMessage, useAsync } from '../composables/useAsync'
import { date } from '../format'
import { ROLE_LABELS } from '../labels'
import { useAuthStore } from '../stores/auth'

const ROLE_STYLE: Record<Role, string> = {
  admin: 'bg-violet-soft text-violet-ink',
  manager: 'bg-brand-50 text-brand-700',
  staff: 'bg-ink-100 text-ink-700',
}
const ROLES = (Object.keys(ROLE_LABELS) as Role[]).map((value) => ({ value, label: ROLE_LABELS[value] }))

const toast = useToast()
const auth = useAuthStore()
const users = useAsync(() => api<UserRow[]>('/admin/users'))
onMounted(users.run)

const saved = (summary: string) => toast.add({ severity: 'success', summary, life: 3000 })

type Mode = { kind: 'create' } | { kind: 'edit'; user: UserRow } | { kind: 'password'; user: UserRow }
const mode = ref<Mode | null>(null)
const form = ref({ username: '', full_name: '', role: 'staff' as Role, is_active: true, password: '' })
const formError = ref<string | null>(null)
const busy = ref(false)

function open(m: Mode) {
  mode.value = m
  formError.value = null
  const u = m.kind === 'create' ? null : m.user
  form.value = { username: u?.username ?? '', full_name: u?.full_name ?? '', role: u?.role ?? 'staff', is_active: u?.is_active ?? true, password: '' }
}

const isSelf = (u: UserRow) => u.id === auth.user?.id

async function submit() {
  const m = mode.value
  if (!m) return
  const f = form.value
  if (m.kind !== 'edit' && f.password.length < 8) return (formError.value = 'Password needs at least 8 characters.')
  if (m.kind === 'create' && !/^[A-Za-z0-9._-]{3,40}$/.test(f.username)) {
    return (formError.value = 'Username: 3 to 40 letters, digits, dots, dashes or underscores.')
  }
  busy.value = true
  try {
    if (m.kind === 'create') {
      await api<UserRow>('/admin/users', { method: 'POST', body: JSON.stringify({ username: f.username, full_name: f.full_name, role: f.role, password: f.password }) })
      saved(`Created ${f.username}`)
    } else if (m.kind === 'edit') {
      const body = { full_name: f.full_name, ...(isSelf(m.user) ? {} : { role: f.role, is_active: f.is_active }) }
      await api<UserRow>(`/admin/users/${m.user.id}`, { method: 'PATCH', body: JSON.stringify(body) })
      saved(`Saved ${m.user.username}`)
    } else {
      await api<void>(`/admin/users/${m.user.id}/password`, { method: 'POST', body: JSON.stringify({ password: f.password }) })
      saved(`Password reset for ${m.user.username}`)
    }
    mode.value = null
    await users.run()
  } catch (e) {
    formError.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}

const title = () => (mode.value?.kind === 'create' ? 'New user' : mode.value?.kind === 'edit' ? 'Edit user' : 'Reset password')
</script>

<template>
  <div class="page">
    <PageHeader title="Users" subtitle="Manage who can sign in to AnchorAI and what they can see. Every change is audited." />
    <PageState :loading="users.loading.value && !users.data.value" :error="users.error.value" :empty="users.data.value?.length === 0" empty-text="No users yet." @retry="users.run">
      <SectionCard v-if="users.data.value" :title="`${users.data.value.length} users`" subtitle="Staff, managers and admins" :icon="UserCog">
        <DataTableX :value="users.data.value" data-key="id" :paginator="false" :global-filter-fields="['username', 'full_name', 'role']" export-name="users">
          <template #toolbar>
            <Button label="Add user" size="small" @click="open({ kind: 'create' })">
              <template #icon><Plus :size="15" /></template>
            </Button>
          </template>
          <Column field="full_name" header="Name" sortable>
            <template #body="{ data }">
              <div class="flex flex-col gap-0.5">
                <span class="font-semibold text-ink-800">{{ data.full_name || data.username }}<span v-if="isSelf(data)" class="ml-2 text-xs font-medium text-ink-500">(you)</span></span>
                <span class="text-xs text-ink-500">@{{ data.username }}</span>
              </div>
            </template>
          </Column>
          <Column field="role" header="Role" sortable>
            <template #body="{ data }">
              <span class="rounded-full px-2.5 py-0.5 text-xs font-semibold" :class="ROLE_STYLE[data.role as Role]">{{ ROLE_LABELS[data.role as Role] }}</span>
            </template>
          </Column>
          <Column field="is_active" header="Status" sortable>
            <template #body="{ data }">
              <span class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold" :class="data.is_active ? 'bg-success-soft text-success-ink' : 'bg-ink-100 text-ink-500'">
                <span class="size-1.5 rounded-full" :class="data.is_active ? 'bg-success' : 'bg-ink-400'" />{{ data.is_active ? 'Active' : 'Inactive' }}
              </span>
            </template>
          </Column>
          <Column field="created_at" header="Created" sortable>
            <template #body="{ data }">{{ date(data.created_at) }}</template>
          </Column>
          <Column header="Actions">
            <template #body="{ data }">
              <div class="flex gap-1">
                <Button label="Edit" size="small" text @click="open({ kind: 'edit', user: data })">
                  <template #icon><Pencil :size="14" /></template>
                </Button>
                <Button label="Reset password" size="small" text severity="secondary" @click="open({ kind: 'password', user: data })">
                  <template #icon><KeyRound :size="14" /></template>
                </Button>
              </div>
            </template>
          </Column>
        </DataTableX>
      </SectionCard>
    </PageState>
  </div>

  <Dialog :visible="mode !== null" :header="title()" modal :style="{ width: 'min(480px, 94vw)' }" @update:visible="(v: boolean) => !v && (mode = null)">
    <form v-if="mode" class="flex flex-col gap-4" @submit.prevent="submit">
      <Message v-if="formError" severity="error" :closable="false">{{ formError }}</Message>
      <p v-if="mode.kind === 'password'" class="m-0 text-sm text-ink-600">
        Set a new password for <strong>{{ mode.user.full_name || mode.user.username }}</strong>. Share it with them securely; it isn't shown again.
      </p>
      <template v-else>
        <label class="field">
          <span>Username</span>
          <InputText v-model="form.username" fluid :disabled="mode.kind === 'edit'" autocomplete="off" />
        </label>
        <label class="field"><span>Full name</span><InputText v-model="form.full_name" fluid /></label>
        <label class="field">
          <span>Role</span>
          <Select v-model="form.role" :options="ROLES" option-label="label" option-value="value" fluid :disabled="mode.kind === 'edit' && isSelf(mode.user)" />
        </label>
        <label v-if="mode.kind === 'edit'" class="flex items-center gap-2 text-sm">
          <ToggleSwitch v-model="form.is_active" :disabled="isSelf(mode.user)" />
          <span>Active (can sign in)</span>
        </label>
        <p v-if="mode.kind === 'edit' && isSelf(mode.user)" class="m-0 text-xs text-ink-500">You can't change your own role or deactivate your own account.</p>
      </template>
      <label v-if="mode.kind !== 'edit'" class="field">
        <span>{{ mode.kind === 'create' ? 'Password' : 'New password' }}</span>
        <Password v-model="form.password" fluid toggle-mask :feedback="false" autocomplete="new-password" input-class="w-full" />
        <small class="text-ink-500">At least 8 characters.</small>
      </label>
      <div class="flex justify-end gap-2">
        <Button label="Cancel" severity="secondary" text @click="mode = null" />
        <Button type="submit" :label="mode.kind === 'create' ? 'Create user' : mode.kind === 'edit' ? 'Save changes' : 'Reset password'" :loading="busy" />
      </div>
    </form>
  </Dialog>
</template>
