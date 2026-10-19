<script setup lang="ts">
import { Lightbulb, ShieldAlert } from 'lucide-vue-next'
import AutoComplete from 'primevue/autocomplete'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import { computed, ref, watch } from 'vue'
import { ApiError, api, query } from '../api/client'
import type { Channel, ItemCheck, MemberHit, SavedPlan } from '../api/types'
import { errorMessage } from '../composables/useAsync'
import { channelLabel, ruleCode } from '../labels'
import { useGlossaryStore } from '../stores/glossary'

// Stream B (W15): add a contact to a draft plan, or swap the offer of a member already on it.
const props = defineProps<{ planId: number; memberId?: string | null }>()
const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ saved: [plan: SavedPlan] }>()
const glossary = useGlossaryStore()
glossary.load()

const member = ref<string | MemberHit | null>(null)
const hits = ref<MemberHit[]>([])
const offerId = ref<string | null>(null)
const channel = ref<Channel | null>(null)
const reason = ref('')
const check = ref<ItemCheck | null>(null)
const problems = ref<string[]>([])
const error = ref<string | null>(null)
const saving = ref(false)

watch(visible, (open) => {
  if (!open) return
  member.value = props.memberId ?? null
  offerId.value = channel.value = check.value = error.value = null
  reason.value = ''
  problems.value = []
})

const memberId = computed(() => (typeof member.value === 'string' ? member.value.trim().toUpperCase() : member.value?.member_id ?? ''))
const offers = computed(() => Object.keys(glossary.data?.offer_channels ?? {}).map((id) => ({ id, name: glossary.offer(id) })))
const channels = computed(() => (offerId.value ? glossary.data?.offer_channels[offerId.value] ?? [] : []).map((c) => ({ value: c, label: channelLabel(c) })))
watch(offerId, () => {
  if (channel.value && !channels.value.some((c) => c.value === channel.value)) channel.value = null
})

async function search(e: { query: string }) {
  try {
    hits.value = await api<MemberHit[]>(`/members/search${query({ q: e.query, limit: 8 })}`)
  } catch {
    hits.value = []
  }
}

// Live guardrail check (C's rules endpoint) as soon as member, offer and channel are chosen.
watch([memberId, offerId, channel], async ([m, o, c]) => {
  check.value = null
  error.value = null
  if (!m || !o || !c) return
  try {
    const [result] = await api<ItemCheck[]>('/rules/check', { method: 'POST', body: JSON.stringify({ items: [{ member_id: m, offer_id: o, channel: c }] }) })
    check.value = result
  } catch (e) {
    error.value = e instanceof ApiError && e.status === 404 ? `No member ${m}` : errorMessage(e)
  }
})

const blocked = computed(() => !!check.value && (!check.value.allowed || !check.value.channel_offered || !check.value.offer_active))
const ready = computed(() => !!check.value && !blocked.value && reason.value.trim().length >= 3)

async function save() {
  saving.value = true
  problems.value = []
  error.value = null
  try {
    const plan = await api<SavedPlan>(`/plan/${props.planId}/items`, {
      method: 'POST',
      body: JSON.stringify({ member_id: memberId.value, offer_id: offerId.value, channel: channel.value, reason: reason.value.trim() }),
    })
    emit('saved', plan)
    visible.value = false
  } catch (e) {
    // The server re-checks everything, including limits and phone on file, and lists each problem.
    const detail = e instanceof ApiError ? e.message : null
    error.value = detail ?? errorMessage(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog v-model:visible="visible" modal :header="memberId && props.memberId ? `Swap the offer for ${memberId}` : 'Add a contact'" class="w-full max-w-lg">
    <form class="flex flex-col gap-4" @submit.prevent="save">
      <label class="field">
        <span>Member</span>
        <AutoComplete
          v-model="member"
          :suggestions="hits"
          option-label="member_id"
          :disabled="!!props.memberId"
          placeholder="Member ID, e.g. M0042"
          fluid
          @complete="search"
        >
          <template #option="{ option }">{{ option.member_id }} · {{ option.segment }}</template>
        </AutoComplete>
      </label>
      <div class="grid grid-cols-2 gap-3">
        <label class="field">
          <span>Offer</span>
          <Select v-model="offerId" :options="offers" option-label="name" option-value="id" placeholder="Choose" fluid />
        </label>
        <label class="field">
          <span>Channel</span>
          <Select v-model="channel" :options="channels" option-label="label" option-value="value" placeholder="Choose" :disabled="!offerId" fluid />
        </label>
      </div>

      <div v-if="check" role="status" aria-live="polite">
        <Message v-if="blocked" severity="error">
          <div class="flex flex-col gap-1">
            <span v-for="v in check.violations" :key="v.rule_id" class="flex items-center gap-1.5">
              <ShieldAlert :size="14" /> {{ ruleCode(v.rule_id) }}: {{ v.description }}
            </span>
            <span v-if="!check.offer_active">This offer is switched off in the catalogue.</span>
            <span v-if="!check.channel_offered">This offer cannot be sent by {{ channelLabel(check.channel).toLowerCase() }}.</span>
          </div>
        </Message>
        <Message v-else-if="!check.on_playbook" severity="warn">
          <span class="flex items-center gap-1.5"><Lightbulb :size="14" /> Allowed, but no playbook rule proposes this offer for this member.</span>
        </Message>
        <Message v-else severity="success">Allowed, and a playbook rule proposes it.</Message>
      </div>

      <label class="field">
        <span>Reason (required)</span>
        <Textarea v-model="reason" rows="2" auto-resize placeholder="Why are you making this change?" fluid />
      </label>
      <Message v-if="error" severity="error">{{ error }}</Message>
      <div class="flex justify-end gap-2">
        <Button label="Cancel" severity="secondary" outlined type="button" @click="visible = false" />
        <Button type="submit" label="Save change" :disabled="!ready" :loading="saving" />
      </div>
    </form>
  </Dialog>
</template>
