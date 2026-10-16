<script setup lang="ts">
import { CircleCheck, Plus, Trash2, TriangleAlert } from 'lucide-vue-next'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import MultiSelect from 'primevue/multiselect'
import RadioButton from 'primevue/radiobutton'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import { computed, reactive, ref, watch } from 'vue'
import type { FactInfo, Rule, RuleKind, RuleReport, Vocabulary } from '../api/types'
import { errorMessage } from '../composables/useAsync'
import { channelLabel, humanize, RULE_KIND_LABELS } from '../labels'
import { type ConditionRow, composeCondition, opsFor, OP_LABELS, parseAssertValue, parseCondition } from '../ruleForm'
import { draftText, saveText, validateText } from '../rulesApi'

const props = defineProps<{ visible: boolean; rule: Rule | null; rules: Rule[]; vocab: Vocabulary }>()
const emit = defineEmits<{ 'update:visible': [boolean]; saved: [] }>()

interface Form {
  id: string
  kind: RuleKind
  salience: number
  description: string
  source: string
  enabled: boolean
  rows: ConditionRow[]
  asserts: { name: string; value: string }[]
  offerId: string
  channel: string
  blockAll: boolean
  blockOffers: string[]
  note: string
}

const form = reactive<Form>({
  id: '',
  kind: 'playbook',
  salience: 30,
  description: '',
  source: '',
  enabled: true,
  rows: [],
  asserts: [],
  offerId: '',
  channel: '',
  blockAll: true,
  blockOffers: [],
  note: '',
})
const report = ref<RuleReport | null>(null)
const error = ref<string | null>(null)
const saving = ref(false)
const isNew = computed(() => props.rule === null)

const KINDS = (Object.keys(RULE_KIND_LABELS) as RuleKind[]).map((value) => ({ value, label: RULE_KIND_LABELS[value] }))
const factMap = computed(() => new Map(props.vocab.facts.map((f) => [f.name, f])))
const factOptions = computed(() => props.vocab.facts.map((f) => ({ name: f.name, label: factLabel(f) })))
const offerOptions = computed(() => props.vocab.offers.map((o) => ({ value: o.offer_id, label: o.name })))
const channelOptions = computed(() => {
  const offer = props.vocab.offers.find((o) => o.offer_id === form.offerId)
  const channels = offer?.channels.length ? offer.channels : props.vocab.channels
  return channels.map((value) => ({ value, label: channelLabel(value) }))
})
const inputFacts = computed(() => new Set(props.vocab.facts.filter((f) => !f.derived).map((f) => f.name)))

function factLabel(f: FactInfo) {
  const d = f.description
  return d.length <= 40 && !d.includes(':') ? d : humanize(f.name)
}

const typeOf = (fact: string) => factMap.value.get(fact)?.type
const choicesOf = (fact: string) => factMap.value.get(fact)?.choices ?? []
const isList = (row: ConditionRow) => row.op === 'in' || row.op === 'not in'

watch(
  () => [props.visible, props.rule] as const,
  ([visible]) => {
    if (!visible) return
    const r = props.rule
    form.id = r?.id ?? ''
    form.kind = r?.kind ?? 'playbook'
    form.salience = r?.salience ?? 30
    form.description = r?.description ?? ''
    form.source = r?.source ?? ''
    form.enabled = r?.enabled ?? true
    form.rows = (r?.when ?? []).map(parseCondition).filter((c): c is ConditionRow => c !== null)
    form.asserts = Object.entries(r?.then.assert ?? {}).map(([name, v]) => ({ name, value: String(v) }))
    form.offerId = r?.then.propose?.offer_id ?? ''
    form.channel = r?.then.propose?.channel ?? ''
    form.blockAll = r?.then.block ? r.then.block === 'all' : true
    form.blockOffers = Array.isArray(r?.then.block) ? [...r.then.block] : []
    form.note = ''
    error.value = null
    report.value = null
    if (!r) addRow()
  },
  { immediate: true },
)

watch(
  () => form.kind,
  (kind) => {
    if (kind === 'derive' && !form.asserts.length) form.asserts.push({ name: '', value: 'true' })
  },
)

function addRow() {
  const first = props.vocab.facts[0]
  form.rows.push({ fact: first?.name ?? '', op: opsFor(first?.type)[0], value: '', list: [] })
}

function changeFact(row: ConditionRow, fact: string) {
  row.fact = fact
  row.value = typeOf(fact) === 'bool' ? 'true' : ''
  row.list = []
  if (!opsFor(typeOf(fact)).includes(row.op)) row.op = opsFor(typeOf(fact))[0]
}

const asNumber = (row: ConditionRow) => (row.value === '' ? null : Number(row.value))
const setNumber = (row: ConditionRow, v: number | null) => (row.value = v === null ? '' : String(v))
const setList = (row: ConditionRow, text: string) =>
  (row.list = text.split(',').map((s) => s.trim()).filter(Boolean))

const candidate = computed<Rule>(() => {
  const base = {
    id: form.id.trim(),
    kind: form.kind,
    salience: form.salience ?? 0,
    description: form.description.trim(),
    when: form.rows.map((r) => composeCondition(r, typeOf(r.fact))),
    source: form.source.trim(),
    enabled: form.enabled,
  }
  if (form.kind === 'derive') {
    const assertion = Object.fromEntries(form.asserts.filter((a) => a.name.trim()).map((a) => [a.name.trim(), parseAssertValue(a.value)]))
    return { ...base, then: { assert: assertion } }
  }
  if (form.kind === 'playbook') return { ...base, then: { propose: { offer_id: form.offerId, channel: form.channel, rule_id: '' } } }
  return { ...base, then: { block: form.blockAll ? 'all' : [...form.blockOffers] } }
})

const fullSet = computed(() => {
  const original = props.rule?.id
  const rest = props.rules.map((r) => (r.id === original ? candidate.value : r))
  return original ? rest : [...rest, candidate.value]
})

let timer: ReturnType<typeof setTimeout> | undefined
let latest = 0
watch(
  () => (props.visible ? draftText(fullSet.value) : null),
  (text) => {
    clearTimeout(timer)
    if (text === null) return
    timer = setTimeout(async () => {
      const call = ++latest
      try {
        const r = await validateText(text)
        if (call === latest) report.value = r
      } catch {
        if (call === latest) report.value = null
      }
    }, 350)
  },
)

const mine = computed(() => report.value?.issues.filter((i) => i.rule_id === candidate.value.id) ?? [])
const otherErrors = computed(() => report.value?.issues.filter((i) => i.rule_id !== candidate.value.id && i.severity === 'error') ?? [])
const blocking = computed(() => !!report.value && (report.value.parse_errors.length > 0 || report.value.issues.some((i) => i.severity === 'error')))
const missing = computed(() => {
  const r = candidate.value
  if (!r.id) return 'Give the rule an ID.'
  if (!r.description) return 'Describe the rule in a sentence.'
  if (!r.source) return 'Say where the rule comes from (source).'
  if (!r.when.length) return 'Add at least one condition.'
  if (!form.note.trim()) return 'Write a note for the version history.'
  return null
})
const canSave = computed(() => !missing.value && !blocking.value && !saving.value)

async function save() {
  saving.value = true
  error.value = null
  try {
    await saveText(draftText(fullSet.value), form.note.trim())
    emit('update:visible', false)
    emit('saved')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    :visible="visible"
    :header="isNew ? 'New rule' : 'Edit rule'"
    modal
    :style="{ width: 'min(760px, 96vw)' }"
    @update:visible="(v: boolean) => emit('update:visible', v)"
  >
    <form class="flex flex-col gap-5" @submit.prevent="save">
      <div class="grid gap-3 sm:grid-cols-[1fr_12rem_7rem]">
        <label class="field">
          <span>Rule ID</span>
          <InputText v-model="form.id" fluid :disabled="!isNew" placeholder="e.g. P09_weekend_checkin" />
        </label>
        <label class="field">
          <span>Kind</span>
          <Select v-model="form.kind" :options="KINDS" option-label="label" option-value="value" fluid :disabled="!isNew" />
        </label>
        <label class="field">
          <span>Salience</span>
          <InputNumber v-model="form.salience" fluid show-buttons :min="0" :max="999" />
        </label>
      </div>
      <label class="field">
        <span>Description</span>
        <InputText v-model="form.description" fluid placeholder="One sentence a manager can read" />
      </label>
      <label class="field">
        <span>Source (required)</span>
        <InputText v-model="form.source" fluid placeholder="e.g. team assumption, club policy, paper" />
      </label>

      <fieldset class="group">
        <legend>When all of these hold</legend>
        <div v-for="(row, i) in form.rows" :key="i" class="cond-row">
          <Select
            :model-value="row.fact"
            :options="factOptions"
            option-label="label"
            option-value="name"
            filter
            fluid
            :aria-label="`Fact ${i + 1}`"
            @update:model-value="(v: string) => changeFact(row, v)"
          >
            <template #option="{ option }">
              <span class="flex w-full items-baseline justify-between gap-3">
                <span>{{ option.label }}</span><span class="id-chip">{{ option.name }}</span>
              </span>
            </template>
          </Select>
          <Select
            v-model="row.op"
            :options="opsFor(typeOf(row.fact)).map((o) => ({ value: o, label: OP_LABELS[o] }))"
            option-label="label"
            option-value="value"
            fluid
            :aria-label="`Comparison ${i + 1}`"
          />
          <template v-if="typeOf(row.fact) === 'number'">
            <InputNumber :model-value="asNumber(row)" :max-fraction-digits="4" fluid :aria-label="`Value ${i + 1}`" @update:model-value="(v: number | null) => setNumber(row, v)" />
          </template>
          <template v-else-if="typeOf(row.fact) === 'bool'">
            <Select v-model="row.value" :options="[{ v: 'true', l: 'Yes' }, { v: 'false', l: 'No' }]" option-label="l" option-value="v" fluid :aria-label="`Value ${i + 1}`" />
          </template>
          <template v-else-if="choicesOf(row.fact).length">
            <MultiSelect v-if="isList(row)" v-model="row.list" :options="choicesOf(row.fact)" display="chip" fluid :aria-label="`Values ${i + 1}`" />
            <Select v-else v-model="row.value" :options="choicesOf(row.fact)" fluid :aria-label="`Value ${i + 1}`" />
          </template>
          <template v-else>
            <InputText
              v-if="isList(row)"
              :model-value="row.list.join(', ')"
              fluid
              placeholder="a, b, c"
              :aria-label="`Values ${i + 1}`"
              @update:model-value="(v) => setList(row, String(v ?? ''))"
            />
            <InputText v-else v-model="row.value" fluid :aria-label="`Value ${i + 1}`" />
          </template>
          <Button severity="secondary" text rounded aria-label="Remove condition" @click="form.rows.splice(i, 1)">
            <template #icon><Trash2 :size="15" /></template>
          </Button>
        </div>
        <div>
          <Button label="Add condition" size="small" severity="secondary" outlined @click="addRow">
            <template #icon><Plus :size="14" /></template>
          </Button>
        </div>
      </fieldset>

      <fieldset class="group">
        <legend>Then</legend>
        <template v-if="form.kind === 'derive'">
          <p class="m-0 text-sm text-ink-500">Conclude one or more new facts that playbooks and guardrails can use.</p>
          <div v-for="(a, i) in form.asserts" :key="i" class="grid grid-cols-[1fr_8rem_auto] items-center gap-2">
            <InputText v-model="a.name" fluid placeholder="fact_name" :aria-label="`Derived fact ${i + 1}`" />
            <InputText v-model="a.value" fluid placeholder="true" :aria-label="`Derived value ${i + 1}`" />
            <Button severity="secondary" text rounded aria-label="Remove fact" :disabled="form.asserts.length === 1" @click="form.asserts.splice(i, 1)">
              <template #icon><Trash2 :size="15" /></template>
            </Button>
          </div>
          <div>
            <Button label="Add fact" size="small" severity="secondary" outlined @click="form.asserts.push({ name: '', value: 'true' })">
              <template #icon><Plus :size="14" /></template>
            </Button>
          </div>
          <p v-if="form.asserts.some((a) => inputFacts.has(a.name.trim()))" class="m-0 text-sm text-danger-ink">
            Derive rules cannot overwrite measured facts such as {{ form.asserts.find((a) => inputFacts.has(a.name.trim()))?.name }}.
          </p>
        </template>
        <div v-else-if="form.kind === 'playbook'" class="grid gap-3 sm:grid-cols-2">
          <label class="field">
            <span>Propose offer</span>
            <Select v-model="form.offerId" :options="offerOptions" option-label="label" option-value="value" fluid placeholder="Choose an offer" />
          </label>
          <label class="field">
            <span>Through channel</span>
            <Select v-model="form.channel" :options="channelOptions" option-label="label" option-value="value" fluid placeholder="Choose a channel" />
          </label>
        </div>
        <template v-else>
          <div class="flex flex-wrap gap-5 text-sm">
            <label class="flex items-center gap-2"><RadioButton v-model="form.blockAll" :value="true" name="block" />Block all offers</label>
            <label class="flex items-center gap-2"><RadioButton v-model="form.blockAll" :value="false" name="block" />Block specific offers</label>
          </div>
          <MultiSelect
            v-if="!form.blockAll"
            v-model="form.blockOffers"
            :options="offerOptions"
            option-label="label"
            option-value="value"
            display="chip"
            placeholder="Choose offers"
            fluid
          />
        </template>
      </fieldset>

      <div class="flex flex-col gap-2" aria-live="polite">
        <div v-for="e in report?.parse_errors ?? []" :key="e" class="note error"><TriangleAlert :size="16" class="shrink-0" aria-hidden="true" />{{ e }}</div>
        <div v-for="(i, n) in mine" :key="n" class="note" :class="i.severity === 'error' ? 'error' : 'warn'">
          <TriangleAlert :size="16" class="shrink-0" aria-hidden="true" />{{ i.message }}
        </div>
        <div v-for="(i, n) in otherErrors" :key="`o${n}`" class="note error">
          <TriangleAlert :size="16" class="shrink-0" aria-hidden="true" /><span><strong>{{ i.rule_id }}</strong>: {{ i.message }}</span>
        </div>
        <div v-if="report && !blocking && !mine.length" class="note ok"><CircleCheck :size="16" class="shrink-0" aria-hidden="true" />Rule set is valid.</div>
      </div>

      <label class="field">
        <span>Note for the version history (required)</span>
        <Textarea v-model="form.note" rows="2" auto-resize fluid placeholder="What changed and why" />
      </label>
      <div v-if="error" class="note error" role="alert"><TriangleAlert :size="16" class="shrink-0" aria-hidden="true" />{{ error }}</div>
      <div class="flex flex-wrap items-center justify-end gap-3">
        <span v-if="missing" class="mr-auto text-sm text-ink-500">{{ missing }}</span>
        <Button label="Cancel" severity="secondary" text @click="emit('update:visible', false)" />
        <Button type="submit" :label="isNew ? 'Create rule' : 'Save rule'" :loading="saving" :disabled="!canSave" />
      </div>
    </form>
  </Dialog>
</template>

<style scoped>
.group { display: flex; flex-direction: column; gap: 0.75rem; margin: 0; padding: 0.75rem 1rem 1rem; border: 1px solid var(--color-ink-200); border-radius: 0.75rem; min-width: 0; }
.group legend { padding-inline: 0.4rem; font-size: 0.8125rem; font-weight: 600; color: var(--color-ink-600); }
.cond-row { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(0, 0.9fr) minmax(0, 1.2fr) auto; gap: 0.5rem; align-items: center; }
@media (max-width: 640px) {
  .cond-row { grid-template-columns: repeat(2, minmax(0, 1fr)); padding-bottom: 0.75rem; border-bottom: 1px dashed var(--color-ink-200); }
  .cond-row > :first-child { grid-column: 1 / -1; }
  .cond-row > :last-child { grid-column: 1 / -1; justify-self: end; }
}
.note { display: flex; align-items: flex-start; gap: 0.5rem; padding: 0.55rem 0.8rem; border: 1px solid; border-radius: 0.6rem; font-size: 0.8125rem; }
.note.ok { background: var(--color-success-soft); border-color: var(--color-success-line); color: var(--color-success-ink); }
.note.warn { background: var(--color-warn-soft); border-color: var(--color-warn-line); color: var(--color-warn-ink); }
.note.error { background: var(--color-danger-soft); border-color: var(--color-danger-line); color: var(--color-danger-ink); }
</style>
