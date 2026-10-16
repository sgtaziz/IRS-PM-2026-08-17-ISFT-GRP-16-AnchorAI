<script setup lang="ts">
import { Check, Copy, RefreshCw, Sparkles, TriangleAlert } from 'lucide-vue-next'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import SelectButton from 'primevue/selectbutton'
import Textarea from 'primevue/textarea'
import { ref, watch } from 'vue'
import { api } from '../api/client'
import type { Channel, MessageDraft } from '../api/types'
import { errorMessage } from '../composables/useAsync'
import { channelLabel } from '../labels'
import { useGlossaryStore } from '../stores/glossary'

const props = defineProps<{ visible: boolean; memberId: string; offerId: string; channel: string }>()
const emit = defineEmits<{ 'update:visible': [boolean] }>()
const glossary = useGlossaryStore()

const CHANNELS: Channel[] = ['sms', 'email', 'call', 'in_person']
const channel = ref<Channel>('sms')
const draft = ref<MessageDraft | null>(null)
const subject = ref('')
const text = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const copied = ref(false)
let latest = 0

async function generate() {
  const ticket = ++latest
  loading.value = true
  error.value = null
  copied.value = false
  try {
    const d = await api<MessageDraft>('/drafts', {
      method: 'POST',
      body: JSON.stringify({ member_id: props.memberId, offer_id: props.offerId, channel: channel.value }),
    })
    if (ticket !== latest) return
    draft.value = d
    subject.value = d.subject ?? ''
    text.value = d.text
  } catch (e) {
    if (ticket !== latest) return
    draft.value = null
    error.value = errorMessage(e)
  } finally {
    if (ticket === latest) loading.value = false
  }
}

watch(
  () => props.visible,
  (open) => {
    if (!open) return
    channel.value = CHANNELS.includes(props.channel as Channel) ? (props.channel as Channel) : 'sms'
    draft.value = null
    generate()
  },
  { immediate: true },
)

async function copy() {
  const full = channel.value === 'email' && subject.value ? `Subject: ${subject.value}\n\n${text.value}` : text.value
  try {
    await navigator.clipboard.writeText(full)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    error.value = 'Could not copy. Select the text and copy it by hand.'
  }
}
</script>

<template>
  <Dialog
    :visible="visible"
    :header="`Draft message · ${glossary.offer(offerId)}`"
    modal
    :style="{ width: 'min(640px, 96vw)' }"
    @update:visible="(v: boolean) => emit('update:visible', v)"
  >
    <div class="flex flex-col gap-4">
      <SelectButton
        v-model="channel"
        :options="CHANNELS.map((c) => ({ value: c, label: channelLabel(c) }))"
        option-label="label"
        option-value="value"
        :allow-empty="false"
        aria-label="Channel"
        @update:model-value="generate"
      />

      <div v-if="error" class="flex items-start gap-2 rounded-lg border border-danger-line bg-danger-soft p-3 text-sm text-danger-ink" role="alert">
        <TriangleAlert :size="16" class="mt-0.5 shrink-0" aria-hidden="true" />
        <span>{{ error }}</span>
      </div>

      <div v-if="loading" class="flex flex-col gap-2" aria-busy="true" aria-live="polite">
        <span class="sr-only">Writing a draft…</span>
        <div class="skeleton h-9"></div>
        <div class="skeleton h-32"></div>
      </div>
      <template v-else-if="draft">
        <label v-if="channel === 'email'" class="flex flex-col gap-1 text-sm">
          <span class="font-medium text-ink-700">Subject</span>
          <InputText v-model="subject" fluid />
        </label>
        <label class="flex flex-col gap-1 text-sm">
          <span class="flex items-center justify-between font-medium text-ink-700">
            Message
            <span class="pill" :class="draft.source === 'llm' ? 'bg-violet-soft text-violet-ink' : 'bg-ink-100 text-ink-600'">
              <Sparkles v-if="draft.source === 'llm'" :size="12" aria-hidden="true" />
              {{ draft.source === 'llm' ? 'AI draft' : 'Template' }}
            </span>
          </span>
          <Textarea v-model="text" auto-resize rows="6" fluid />
          <span v-if="channel === 'sms'" class="text-xs text-ink-500">{{ text.length }} characters</span>
        </label>
        <details class="text-xs text-ink-500">
          <summary class="cursor-pointer">Facts used</summary>
          <ul class="m-0 mt-1 list-disc pl-5">
            <li v-for="line in draft.evidence" :key="line">{{ line }}</li>
          </ul>
        </details>
      </template>

      <p class="m-0 text-xs text-ink-500">Not sent. Copy it into your messaging tool and check it first.</p>
    </div>
    <template #footer>
      <Button label="Regenerate" severity="secondary" text :disabled="loading" @click="generate">
        <template #icon><RefreshCw :size="16" aria-hidden="true" /></template>
      </Button>
      <Button :label="copied ? 'Copied' : 'Copy'" :disabled="loading || !draft" @click="copy">
        <template #icon><component :is="copied ? Check : Copy" :size="16" aria-hidden="true" /></template>
      </Button>
    </template>
  </Dialog>
</template>

<style scoped>
.pill { display: inline-flex; align-items: center; gap: 0.25rem; padding: 0.1rem 0.5rem; border-radius: 999px; font-size: 0.72rem; font-weight: 600; }
.skeleton { border-radius: 0.5rem; background: var(--color-ink-100); animation: pulse 1.2s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: 0.5; } }
@media (prefers-reduced-motion: reduce) { .skeleton { animation: none; } }
</style>
