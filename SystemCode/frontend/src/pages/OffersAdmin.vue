<script setup lang="ts">
import Button from 'primevue/button'
import Card from 'primevue/card'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import { useToast } from 'primevue/usetoast'
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import type { CatalogView, Channel, Constraints, Offer, StaffRow } from '../api/types'
import ConfirmAction from '../components/ConfirmAction.vue'
import DataTableX from '../components/DataTableX.vue'
import PageState from '../components/PageState.vue'
import { errorMessage, useAsync } from '../composables/useAsync'
import { money } from '../format'

const CHANNELS: { label: string; value: Channel }[] = [
  { label: 'SMS', value: 'sms' },
  { label: 'Email', value: 'email' },
  { label: 'Call', value: 'call' },
  { label: 'In person', value: 'in_person' },
]
const BLANK: Offer = {
  offer_id: '',
  name: '',
  cost: 0,
  staff_minutes: 0,
  inventory: null,
  channels: ['sms'],
  eligibility: '',
  required_skill: '',
  active: true,
}

const toast = useToast()
const catalog = useAsync(() => api<CatalogView>('/admin/offers'))
const constraints = ref<Constraints | null>(null)
const staff = ref<StaffRow[]>([])

async function load() {
  const view = await catalog.run()
  if (view) {
    constraints.value = { ...view.constraints }
    staff.value = view.staff.map((s) => ({ ...s, skills: [...s.skills] }))
  }
}
onMounted(load)

const saved = (summary: string) => toast.add({ severity: 'success', summary, life: 3000 })
const failed = (summary: string, e: unknown) =>
  toast.add({ severity: 'error', summary, detail: errorMessage(e), life: 6000 })

const editing = ref<Offer | null>(null)
const isNew = ref(false)
const formError = ref<string | null>(null)
const saving = ref(false)

function openOffer(offer?: Offer) {
  isNew.value = !offer
  editing.value = offer ? { ...offer, channels: [...offer.channels] } : { ...BLANK, channels: [...BLANK.channels] }
  formError.value = null
}

async function saveOffer() {
  const o = editing.value
  if (!o) return
  if (!/^[a-z0-9_]+$/.test(o.offer_id)) return (formError.value = 'ID: lowercase letters, digits and _ only.')
  if (!o.name.trim()) return (formError.value = 'Name is required.')
  if (!o.channels.length) return (formError.value = 'Pick at least one channel.')
  saving.value = true
  try {
    const path = isNew.value ? '/admin/offers/offers' : `/admin/offers/offers/${o.offer_id}`
    await api<Offer>(path, { method: isNew.value ? 'POST' : 'PUT', body: JSON.stringify(o) })
    editing.value = null
    saved(isNew.value ? 'Offer created' : 'Offer saved')
    await load()
  } catch (e) {
    formError.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

async function deleteOffer(o: Offer) {
  try {
    await api<void>(`/admin/offers/offers/${o.offer_id}`, { method: 'DELETE' })
    saved(`Deleted ${o.name}`)
    await load()
  } catch (e) {
    failed('Delete failed', e)
  }
}

async function saveStaff(s: StaffRow) {
  try {
    await api<StaffRow>(`/admin/offers/staff/${s.user_id}`, {
      method: 'PUT',
      body: JSON.stringify({ weekly_hours: s.weekly_hours, skills: s.skills }),
    })
    saved(`Saved ${s.full_name || s.username}`)
  } catch (e) {
    failed('Could not save staff member', e)
  }
}

async function saveConstraints() {
  if (!constraints.value) return
  try {
    await api<Constraints>('/admin/offers/constraints', { method: 'PUT', body: JSON.stringify(constraints.value) })
    saved('Constraints saved')
  } catch (e) {
    failed('Could not save constraints', e)
  }
}

const skillOptions = () => (catalog.data.value?.skills ?? []).map((s) => ({ label: s.replace('_', ' '), value: s }))
</script>

<template>
  <div class="page-head">
    <h2>Offers & constraints</h2>
    <span class="sub">Inputs the weekly plan reads; every change is audited</span>
  </div>
  <PageState :loading="catalog.loading.value && !catalog.data.value" :error="catalog.error.value" @retry="load">
    <template v-if="catalog.data.value">
      <Card class="block">
        <template #title>Offer catalogue</template>
        <template #content>
          <DataTableX
            :value="catalog.data.value.offers"
            data-key="offer_id"
            :paginator="false"
            :global-filter-fields="['offer_id', 'name', 'eligibility']"
            export-name="offers"
          >
            <template #toolbar>
              <Button label="Add offer" size="small" @click="openOffer()" />
            </template>
            <Column field="name" header="Offer" sortable>
              <template #body="{ data }">
                {{ data.name }} <small class="muted">{{ data.offer_id }}</small>
              </template>
            </Column>
            <Column field="cost" header="Cost" sortable>
              <template #body="{ data }">{{ money(data.cost) }}</template>
            </Column>
            <Column field="staff_minutes" header="Staff min" sortable />
            <Column field="inventory" header="Weekly stock">
              <template #body="{ data }">{{ data.inventory ?? 'Unlimited' }}</template>
            </Column>
            <Column field="channels" header="Channels">
              <template #body="{ data }">{{ data.channels.join(', ') }}</template>
            </Column>
            <Column field="required_skill" header="Skill">
              <template #body="{ data }">{{ data.required_skill || 'Anyone' }}</template>
            </Column>
            <Column field="eligibility" header="Eligibility" />
            <Column field="active" header="Status">
              <template #body="{ data }">
                <Tag :severity="data.active ? 'success' : 'secondary'" :value="data.active ? 'Active' : 'Inactive'" />
              </template>
            </Column>
            <Column header="Actions">
              <template #body="{ data }">
                <div class="row-actions">
                  <Button label="Edit" size="small" text @click="openOffer(data)" />
                  <ConfirmAction
                    label="Delete"
                    :message="`Delete ${data.name}? Past plans keep their record.`"
                    @confirm="deleteOffer(data)"
                  />
                </div>
              </template>
            </Column>
          </DataTableX>
        </template>
      </Card>

      <div class="grid cols-2">
        <Card>
          <template #title>Staff roster</template>
          <template #content>
            <PageState :empty="!staff.length" empty-text="No staff users yet. Add them on the Users page.">
              <table class="plain">
                <thead>
                  <tr><th scope="col">Staff</th><th scope="col">Hours / week</th><th scope="col">Skills</th><th></th></tr>
                </thead>
                <tbody>
                  <tr v-for="s in staff" :key="s.user_id">
                    <td>{{ s.full_name || s.username }}</td>
                    <td>
                      <InputNumber
                        v-model="s.weekly_hours"
                        :min="0"
                        :max="60"
                        :max-fraction-digits="1"
                        size="small"
                        input-class="narrow"
                        :aria-label="`Weekly hours for ${s.username}`"
                      />
                    </td>
                    <td>
                      <MultiSelect
                        v-model="s.skills"
                        :options="skillOptions()"
                        option-label="label"
                        option-value="value"
                        placeholder="None"
                        size="small"
                        display="chip"
                        :aria-label="`Skills for ${s.username}`"
                      />
                    </td>
                    <td><Button label="Save" size="small" outlined @click="saveStaff(s)" /></td>
                  </tr>
                </tbody>
              </table>
            </PageState>
          </template>
        </Card>

        <Card v-if="constraints">
          <template #title>Planning constraints</template>
          <template #content>
            <form class="form" @submit.prevent="saveConstraints">
              <label class="field">
                <span>Default weekly budget ($)</span>
                <InputNumber v-model="constraints.default_budget" :min="0" mode="currency" currency="USD" />
              </label>
              <label class="field">
                <span>Default staff minutes per week</span>
                <InputNumber v-model="constraints.default_staff_minutes" :min="0" />
              </label>
              <label class="field">
                <span>Max contacts per member per 30 days</span>
                <InputNumber v-model="constraints.max_contacts_per_member_per_30d" :min="0" />
              </label>
              <label class="field">
                <span>Max offers per member per 90 days</span>
                <InputNumber v-model="constraints.max_offers_per_member_per_90d" :min="0" />
              </label>
              <Button type="submit" label="Save constraints" />
            </form>
          </template>
        </Card>
      </div>
    </template>
  </PageState>

  <Dialog
    :visible="editing !== null"
    :header="isNew ? 'New offer' : 'Edit offer'"
    modal
    :style="{ width: 'min(560px, 94vw)' }"
    @update:visible="(v: boolean) => !v && (editing = null)"
  >
    <form v-if="editing" class="form" @submit.prevent="saveOffer">
      <Message v-if="formError" severity="error" :closable="false">{{ formError }}</Message>
      <label class="field">
        <span>Offer ID</span>
        <InputText v-model="editing.offer_id" :disabled="!isNew" placeholder="e.g. free_pt_session" />
      </label>
      <label class="field"><span>Name</span><InputText v-model="editing.name" /></label>
      <div class="two">
        <label class="field">
          <span>Cost ($)</span>
          <InputNumber v-model="editing.cost" :min="0" mode="currency" currency="USD" />
        </label>
        <label class="field">
          <span>Staff minutes</span>
          <InputNumber v-model="editing.staff_minutes" :min="0" />
        </label>
        <label class="field">
          <span>Weekly stock (blank = unlimited)</span>
          <InputNumber v-model="editing.inventory" :min="0" />
        </label>
        <label class="field">
          <span>Required skill</span>
          <Select
            v-model="editing.required_skill"
            :options="[{ label: 'Anyone', value: '' }, ...skillOptions()]"
            option-label="label"
            option-value="value"
          />
        </label>
      </div>
      <label class="field">
        <span>Channels</span>
        <MultiSelect v-model="editing.channels" :options="CHANNELS" option-label="label" option-value="value" display="chip" />
      </label>
      <label class="field">
        <span>Eligibility</span>
        <InputText v-model="editing.eligibility" placeholder="Who can receive it" />
      </label>
      <label class="switch">
        <ToggleSwitch v-model="editing.active" input-id="offer-active" />
        <span>Active</span>
      </label>
      <div class="dialog-actions">
        <Button label="Cancel" severity="secondary" text @click="editing = null" />
        <Button type="submit" :label="isNew ? 'Create offer' : 'Save offer'" :loading="saving" />
      </div>
    </form>
  </Dialog>
</template>

<style scoped>
.block {
  margin-bottom: 1rem;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.two {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}
.switch {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
.row-actions {
  display: flex;
  gap: 0.25rem;
}
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
:deep(.narrow) {
  width: 5rem;
}
</style>
