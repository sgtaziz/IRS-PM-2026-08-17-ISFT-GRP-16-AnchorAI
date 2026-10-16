<script setup lang="ts">
import { CircleCheck, FileCode2, FlaskConical, History, ListChecks, Pencil, Play, Plus, RotateCcw, Save, ScrollText, Trash2, TriangleAlert } from 'lucide-vue-next'
import Button from 'primevue/button'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'
import vTooltip from 'primevue/tooltip'
import { useToast } from 'primevue/usetoast'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api/client'
import type { Rule, RuleOutcome, RuleReport, RuleSet, RuleVersion, RuleVersionDetail, Vocabulary } from '../api/types'
import ConfirmAction from '../components/ConfirmAction.vue'
import DataTableX from '../components/DataTableX.vue'
import EmptyState from '../components/EmptyState.vue'
import PageHeader from '../components/PageHeader.vue'
import PageState from '../components/PageState.vue'
import RuleEditorDialog from '../components/RuleEditorDialog.vue'
import RuleTrace from '../components/RuleTrace.vue'
import SectionCard from '../components/SectionCard.vue'
import { errorMessage, useAsync } from '../composables/useAsync'
import { dateTime } from '../format'
import { channelLabel, humanize, RULE_KIND_LABELS, ruleCode } from '../labels'
import { draftText, isStale, saveText, validateText } from '../rulesApi'
import { useGlossaryStore } from '../stores/glossary'

const KIND_STYLE = {
  derive: 'bg-violet-soft text-violet-ink',
  playbook: 'bg-success-soft text-success-ink',
  guardrail: 'bg-danger-soft text-danger-ink',
} as const

const rules = useAsync(() => api<RuleSet>('/rules'))
const trace = useAsync((id: string) => api<RuleOutcome>(`/rules/trace/${encodeURIComponent(id)}`))
const memberId = ref('M0155')
const glossary = useGlossaryStore()
const vocab = useAsync(() => api<Vocabulary>('/rules/vocabulary'))
const versions = useAsync(() => api<RuleVersion[]>('/rules/versions'))
const toast = useToast()
const tab = ref('rules')
const highlightRule = useRoute().query.rule
const failed = (summary: string, e: unknown) => {
  if (isStale(e)) {
    toast.add({ severity: 'warn', summary: 'Rules changed since you opened them', detail: 'Reloaded the latest version. Review it and try again.', life: 7000 })
    reloadAll()
  } else toast.add({ severity: 'error', summary, detail: errorMessage(e), life: 6000 })
}
const baseVersion = computed(() => rules.data.value?.version ?? null)

async function reloadAll() {
  await Promise.all([rules.run(), versions.run(), vocab.run(), glossary.reload()])
  await loadYaml()
}
onMounted(async () => {
  glossary.load()
  versions.run()
  vocab.run()
  await rules.run()
  await loadYaml()
  await nextTick()
  document.querySelector('.rule-hl')?.scrollIntoView({ block: 'center', behavior: 'smooth' })
})

const editorOpen = ref(false)
const editing = ref<Rule | null>(null)
function openEditor(rule: Rule | null) {
  editing.value = rule
  editorOpen.value = true
}
async function saved() {
  toast.add({ severity: 'success', summary: 'New rule version saved', life: 3000 })
  await reloadAll()
}

interface Ask {
  title: string
  message: string
  confirm: string
  danger: boolean
  required: boolean
  run: (note: string) => Promise<unknown>
}
const ask = ref<Ask | null>(null)
const askNote = ref('')
const askBusy = ref(false)
function openAsk(a: Ask) {
  askNote.value = ''
  ask.value = a
}
async function confirmAsk() {
  const a = ask.value
  if (!a || (a.required && !askNote.value.trim())) return
  askBusy.value = true
  try {
    await a.run(askNote.value.trim())
    ask.value = null
    toast.add({ severity: 'success', summary: 'New rule version saved', life: 3000 })
    await reloadAll()
  } catch (e) {
    if (isStale(e)) ask.value = null
    failed('Could not save', e)
  } finally {
    askBusy.value = false
  }
}

function toggle(r: Rule) {
  const enabled = !r.enabled
  openAsk({
    title: `${enabled ? 'Enable' : 'Disable'} rule`,
    message: `${enabled ? 'Enable' : 'Disable'} "${r.description}"? This saves a new rule version.`,
    confirm: enabled ? 'Enable' : 'Disable',
    danger: !enabled,
    required: false,
    run: (note) =>
      api<RuleVersion>(`/rules/${encodeURIComponent(r.id)}`, {
        method: 'PATCH',
        body: JSON.stringify({ enabled, note: note || null, base_version: baseVersion.value }),
      }),
  })
}

function remove(r: Rule) {
  const rest = (rules.data.value?.rules ?? []).filter((x) => x.id !== r.id)
  openAsk({
    title: 'Delete rule',
    message: `Delete "${r.description}"? You can roll back from the Versions tab.`,
    confirm: 'Delete',
    danger: true,
    required: true,
    run: (note) => saveText(draftText(rest), note, baseVersion.value),
  })
}

const yamlText = ref('')
const yamlBase = ref('')
const yamlReport = ref<RuleReport | null>(null)
const yamlBusy = ref(false)
const yamlNote = ref('')
const yamlTrace = useAsync((text: string, id: string) =>
  api<RuleOutcome>('/rules/test', { method: 'POST', body: JSON.stringify({ yaml_text: text, member_id: id }) }),
)
const yamlMember = ref('M0155')
const dirty = computed(() => yamlText.value !== yamlBase.value)

async function loadYaml() {
  const v = rules.data.value?.version
  if (v == null) return
  try {
    const detail = await api<RuleVersionDetail>(`/rules/versions/${v}`)
    yamlBase.value = yamlText.value = detail.yaml_text
    yamlReport.value = null
  } catch (e) {
    failed('Could not load the rule YAML', e)
  }
}

async function validateYaml() {
  yamlBusy.value = true
  try {
    yamlReport.value = await validateText(yamlText.value)
  } catch (e) {
    failed('Validation failed', e)
  } finally {
    yamlBusy.value = false
  }
}

const yamlBlocked = computed(
  () => !yamlReport.value || yamlReport.value.parse_errors.length > 0 || yamlReport.value.issues.some((i) => i.severity === 'error'),
)
watch(yamlText, () => (yamlReport.value = null))

function testYaml() {
  const id = yamlMember.value.trim().toUpperCase()
  if (id) yamlTrace.run(yamlText.value, id)
}

async function saveYaml() {
  if (!yamlNote.value.trim() || yamlBlocked.value) return
  yamlBusy.value = true
  try {
    await saveText(yamlText.value, yamlNote.value.trim(), baseVersion.value)
    yamlNote.value = ''
    toast.add({ severity: 'success', summary: 'New rule version saved', life: 3000 })
    await reloadAll()
  } catch (e) {
    failed('Could not save', e)
  } finally {
    yamlBusy.value = false
  }
}

const viewing = ref<RuleVersionDetail | null>(null)
async function view(v: RuleVersion) {
  try {
    viewing.value = await api<RuleVersionDetail>(`/rules/versions/${v.version}`)
  } catch (e) {
    failed('Could not load that version', e)
  }
}
async function activate(v: RuleVersion) {
  try {
    await api<RuleVersion>(`/rules/versions/${v.version}/activate`, { method: 'POST', body: JSON.stringify({ base_version: baseVersion.value }) })
    toast.add({ severity: 'success', summary: `Version ${v.version} is now active`, life: 3000 })
    await reloadAll()
  } catch (e) {
    failed('Could not activate', e)
  }
}

function action(r: Rule) {
  const t = r.then
  if (t.propose) return `Propose ${glossary.offer(t.propose.offer_id)} by ${channelLabel(t.propose.channel)}`
  if (t.block) return `Block ${t.block === 'all' ? 'all offers' : t.block.map(glossary.offer).join(', ')}`
  return `Conclude ${Object.entries(t.assert ?? {}).map(([k, v]) => (v === true ? humanize(k) : `${humanize(k)} = ${v}`)).join(', ')}`
}

function test() {
  const id = memberId.value.trim().toUpperCase()
  if (id) trace.run(id)
}
</script>

<template>
  <div class="page">
    <PageHeader title="Rules" subtitle="Forward-chaining rule base. Guardrails fire first, then higher salience, then more specific rules.">
      <template #actions>
        <span v-if="rules.data.value?.version" class="rounded-full bg-card px-3 py-1.5 text-sm font-medium text-ink-600 ring-1 ring-ink-200">
          Version {{ rules.data.value.version }}
        </span>
        <Button label="New rule" :disabled="!vocab.data.value" @click="openEditor(null)">
          <template #icon><Plus :size="15" /></template>
        </Button>
      </template>
    </PageHeader>
    <PageState :loading="rules.loading.value && !rules.data.value" :error="rules.error.value" :empty="rules.data.value?.rules.length === 0" @retry="rules.run">
      <template v-if="rules.data.value">
        <div v-if="!rules.data.value.issues.length" class="banner ok">
          <CircleCheck :size="18" class="shrink-0" aria-hidden="true" />
          <span><strong>Validation passed.</strong> No unknown facts, contradictions or unreachable rules.</span>
        </div>
        <div v-for="(i, n) in rules.data.value.issues" v-else :key="n" class="banner" :class="i.severity === 'error' ? 'error' : 'warn'">
          <TriangleAlert :size="18" class="shrink-0" aria-hidden="true" />
          <span><strong>{{ glossary.rule(i.rule_id) }}</strong> <span class="id-chip">{{ ruleCode(i.rule_id) }}</span>: {{ i.message }}</span>
        </div>

        <Tabs v-model:value="tab" class="mt-5">
          <TabList>
            <Tab value="rules"><span class="tab-label"><ListChecks :size="15" aria-hidden="true" />Rules</span></Tab>
            <Tab value="yaml"><span class="tab-label"><FileCode2 :size="15" aria-hidden="true" />Raw YAML</span></Tab>
            <Tab value="versions"><span class="tab-label"><History :size="15" aria-hidden="true" />Versions</span></Tab>
          </TabList>
          <TabPanels>
            <TabPanel value="rules">
              <div class="grid items-start gap-5 min-[2200px]:grid-cols-[minmax(0,2fr)_minmax(24rem,1fr)]">
                <SectionCard :title="`${rules.data.value.rules.length} rules`" subtitle="Sorted by salience" :icon="ScrollText">
                  <DataTableX
                    :value="rules.data.value.rules"
                    data-key="id"
                    export-name="rules"
                    :global-filter-fields="['id', 'description', 'source', 'kind']"
                    :rows="50"
                    sort-field="salience"
                    :sort-order="-1"
                  >
                    <Column header="On">
                      <template #body="{ data }">
                        <ToggleSwitch :model-value="data.enabled" :aria-label="`${data.enabled ? 'Disable' : 'Enable'} ${data.description}`" @update:model-value="toggle(data)" />
                      </template>
                    </Column>
                    <Column field="description" header="Rule" sortable>
                      <template #body="{ data }">
                        <div class="flex min-w-80 flex-col gap-1 whitespace-normal" :class="{ 'opacity-55': !data.enabled, 'rule-hl': data.id === highlightRule }">
                          <span class="font-medium text-ink-800">{{ data.description }}</span>
                          <span class="flex flex-wrap items-baseline gap-x-2 text-xs text-ink-500">
                            <span v-tooltip.top="data.id" class="id-chip">{{ ruleCode(data.id) }}</span>
                            <span v-if="!data.enabled" class="font-semibold">Disabled</span>
                            <span>Source: {{ data.source }}</span>
                          </span>
                        </div>
                      </template>
                    </Column>
                    <Column field="kind" header="Kind" sortable>
                      <template #body="{ data }">
                        <span class="rounded-full px-2.5 py-0.5 text-xs font-semibold" :class="KIND_STYLE[data.kind as Rule['kind']]">
                          {{ RULE_KIND_LABELS[data.kind as Rule['kind']] }}
                        </span>
                      </template>
                    </Column>
                    <Column field="salience" header="Salience" sortable>
                      <template #body="{ data }"><span class="tabular-nums">{{ data.salience }}</span></template>
                    </Column>
                    <Column header="When">
                      <template #body="{ data }">
                        <div class="flex flex-col items-start gap-1">
                          <code v-for="c in (data as Rule).when" :key="c" class="cond">{{ c }}</code>
                        </div>
                      </template>
                    </Column>
                    <Column header="Then">
                      <template #body="{ data }"><span class="block min-w-48 whitespace-normal">{{ action(data) }}</span></template>
                    </Column>
                    <Column header="Actions">
                      <template #body="{ data }">
                        <div class="flex gap-1">
                          <Button label="Edit" size="small" text :disabled="!vocab.data.value" @click="openEditor(data)">
                            <template #icon><Pencil :size="14" /></template>
                          </Button>
                          <Button label="Delete" :aria-label="`Delete ${data.description}`" size="small" severity="danger" text @click="remove(data)">
                            <template #icon><Trash2 :size="14" /></template>
                          </Button>
                        </div>
                      </template>
                    </Column>
                  </DataTableX>
                </SectionCard>

                <SectionCard title="Test on a member" subtitle="Run the active rule base and see the firing trace" :icon="FlaskConical" class="order-first min-[2200px]:order-none min-[2200px]:sticky min-[2200px]:top-[calc(var(--topbar-h)+1.5rem)]">
                  <form class="toolbar mb-5" @submit.prevent="test">
                    <label class="field min-w-40 flex-1">
                      <span>Member ID</span>
                      <InputText v-model="memberId" placeholder="M0155" fluid />
                    </label>
                    <Button type="submit" label="Run rules" :loading="trace.loading.value">
                      <template #icon><Play :size="15" /></template>
                    </Button>
                  </form>
                  <PageState :loading="trace.loading.value" :error="trace.error.value" :empty="!trace.data.value">
                    <template #empty>
                      <EmptyState :icon="FlaskConical" compact text="Run the rule base on a member to see the firing trace." />
                    </template>
                    <RuleTrace v-if="trace.data.value" :outcome="trace.data.value" />
                  </PageState>
                </SectionCard>
              </div>
            </TabPanel>

            <TabPanel value="yaml">
              <div class="grid items-start gap-5 2xl:grid-cols-[minmax(0,2fr)_minmax(24rem,1fr)]">
                <SectionCard title="Rule YAML" :subtitle="`Active version ${rules.data.value.version ?? '—'}. Edit, validate, test, then save as a new version.`" :icon="FileCode2">
                  <PageState :empty="rules.data.value.version == null" empty-text="No saved version yet. Create a rule to save the first one.">
                    <Textarea v-model="yamlText" class="yaml" rows="24" spellcheck="false" fluid aria-label="Rule YAML" />
                    <div v-if="yamlReport" class="mt-3 flex flex-col gap-2" aria-live="polite">
                      <div v-for="e in yamlReport.parse_errors" :key="e" class="banner error"><TriangleAlert :size="16" class="shrink-0" aria-hidden="true" />{{ e }}</div>
                      <div v-for="(i, n) in yamlReport.issues" :key="n" class="banner" :class="i.severity === 'error' ? 'error' : 'warn'">
                        <TriangleAlert :size="16" class="shrink-0" aria-hidden="true" /><span><strong>{{ i.rule_id }}</strong>: {{ i.message }}</span>
                      </div>
                      <div v-if="!yamlReport.parse_errors.length && !yamlReport.issues.length" class="banner ok">
                        <CircleCheck :size="16" class="shrink-0" aria-hidden="true" />Valid: {{ yamlReport.rule_count }} rules, no issues.
                      </div>
                    </div>
                    <div class="toolbar mt-4">
                      <Button label="Validate" severity="secondary" outlined :loading="yamlBusy" @click="validateYaml">
                        <template #icon><CircleCheck :size="15" /></template>
                      </Button>
                      <Button label="Revert" severity="secondary" text :disabled="!dirty" @click="yamlText = yamlBase">
                        <template #icon><RotateCcw :size="15" /></template>
                      </Button>
                      <label class="field min-w-56 flex-1">
                        <span>Note (required to save)</span>
                        <InputText v-model="yamlNote" placeholder="What changed and why" fluid />
                      </label>
                      <Button label="Save version" :disabled="!dirty || yamlBlocked || !yamlNote.trim()" :loading="yamlBusy" @click="saveYaml">
                        <template #icon><Save :size="15" /></template>
                      </Button>
                    </div>
                    <p v-if="dirty && !yamlReport" class="m-0 mt-2 text-sm text-ink-500">Validate the changes before saving.</p>
                  </PageState>
                </SectionCard>

                <SectionCard title="Test this draft" subtitle="Run the YAML above, saved or not, on a member" :icon="FlaskConical" class="2xl:sticky 2xl:top-[calc(var(--topbar-h)+1.5rem)]">
                  <form class="toolbar mb-5" @submit.prevent="testYaml">
                    <label class="field min-w-40 flex-1">
                      <span>Member ID</span>
                      <InputText v-model="yamlMember" placeholder="M0155" fluid />
                    </label>
                    <Button type="submit" label="Run draft" :loading="yamlTrace.loading.value">
                      <template #icon><Play :size="15" /></template>
                    </Button>
                  </form>
                  <PageState :loading="yamlTrace.loading.value" :error="yamlTrace.error.value" :empty="!yamlTrace.data.value">
                    <template #empty>
                      <EmptyState :icon="FlaskConical" compact text="Run the draft on a member to see which rules would fire." />
                    </template>
                    <RuleTrace v-if="yamlTrace.data.value" :outcome="yamlTrace.data.value" />
                  </PageState>
                </SectionCard>
              </div>
            </TabPanel>

            <TabPanel value="versions">
              <SectionCard title="Version history" subtitle="Every save creates a version. Activating an older one rolls back to it." :icon="History">
                <PageState :loading="versions.loading.value && !versions.data.value" :error="versions.error.value" :empty="versions.data.value?.length === 0" empty-text="No saved versions yet." @retry="versions.run">
                  <div v-if="versions.data.value" class="table-wrap">
                    <table class="plain">
                      <thead>
                        <tr><th scope="col">Version</th><th scope="col">Note</th><th scope="col">Saved by</th><th scope="col">When</th><th scope="col" class="num">Rules</th><th scope="col"><span class="sr-only">Actions</span></th></tr>
                      </thead>
                      <tbody>
                        <tr v-for="v in versions.data.value" :key="v.version">
                          <td>
                            <span class="flex items-center gap-2 font-semibold tabular-nums text-ink-800">
                              {{ v.version }}
                              <span v-if="v.is_active" class="rounded-full bg-success-soft px-2 py-0.5 text-xs font-semibold text-success-ink">Active</span>
                            </span>
                          </td>
                          <td class="max-w-md whitespace-normal">{{ v.note || '—' }}</td>
                          <td>{{ v.created_by ?? 'system' }}</td>
                          <td class="whitespace-nowrap">{{ dateTime(v.created_at) }}</td>
                          <td class="num">{{ v.rule_count }}</td>
                          <td>
                            <div class="flex justify-end gap-1">
                              <Button label="View YAML" size="small" text @click="view(v)" />
                              <ConfirmAction
                                v-if="!v.is_active"
                                label="Activate"
                                severity="primary"
                                header="Roll back rules"
                                :message="`Make version ${v.version} the active rule base? Plans and traces will use it straight away.`"
                                @confirm="activate(v)"
                              />
                            </div>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </PageState>
              </SectionCard>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </template>
    </PageState>
  </div>

  <RuleEditorDialog
    v-if="vocab.data.value && rules.data.value"
    v-model:visible="editorOpen"
    :rule="editing"
    :rules="rules.data.value.rules"
    :vocab="vocab.data.value"
    :base-version="baseVersion"
    @saved="saved"
    @stale="reloadAll"
  />

  <Dialog :visible="ask !== null" :header="ask?.title" modal :style="{ width: 'min(480px, 94vw)' }" @update:visible="(v: boolean) => !v && (ask = null)">
    <form v-if="ask" class="flex flex-col gap-4" @submit.prevent="confirmAsk">
      <p class="m-0 text-sm text-ink-700">{{ ask.message }}</p>
      <label class="field">
        <span>{{ ask.required ? 'Note (required)' : 'Note (optional)' }}</span>
        <InputText v-model="askNote" fluid placeholder="Why are you changing this?" autofocus />
      </label>
      <div class="flex justify-end gap-2">
        <Button label="Cancel" severity="secondary" text @click="ask = null" />
        <Button type="submit" :label="ask.confirm" :severity="ask.danger ? 'danger' : undefined" :loading="askBusy" :disabled="ask.required && !askNote.trim()" />
      </div>
    </form>
  </Dialog>

  <Dialog :visible="viewing !== null" :header="`Version ${viewing?.version} YAML`" modal :style="{ width: 'min(860px, 96vw)' }" @update:visible="(v: boolean) => !v && (viewing = null)">
    <p v-if="viewing" class="m-0 mb-3 text-sm text-ink-500">{{ viewing.note || 'No note' }} · {{ viewing.created_by ?? 'system' }} · {{ dateTime(viewing.created_at) }}</p>
    <pre v-if="viewing" class="yaml-view">{{ viewing.yaml_text }}</pre>
  </Dialog>
</template>

<style scoped>
.banner { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.5rem; padding: 0.75rem 1rem; border-radius: 0.75rem; font-size: 0.875rem; border: 1px solid; }
.banner.ok { background: var(--color-success-soft); border-color: var(--color-success-line); color: var(--color-success-ink); }
.banner.warn { background: var(--color-warn-soft); border-color: var(--color-warn-line); color: var(--color-warn-ink); }
.banner.error { background: var(--color-danger-soft); border-color: var(--color-danger-line); color: var(--color-danger-ink); }
.cond { padding: 0.1rem 0.4rem; border-radius: 5px; font-size: 0.75rem; white-space: nowrap; color: var(--color-ink-700); background: var(--color-ink-100); }
.rule-hl { padding: 0.4rem 0.6rem; margin: -0.4rem -0.6rem; border-radius: 0.5rem; background: var(--color-brand-100); }
.tab-label { display: inline-flex; align-items: center; gap: 0.4rem; }
:deep(.yaml) { font-family: var(--font-mono); font-size: 0.8125rem; line-height: 1.5; tab-size: 2; white-space: pre; overflow-x: auto; }
.yaml-view { margin: 0; max-height: 60vh; overflow: auto; padding: 1rem; border-radius: 0.75rem; background: var(--color-ink-50); border: 1px solid var(--color-ink-200); color: var(--color-ink-800); font: 0.8125rem/1.5 var(--font-mono); }
</style>
