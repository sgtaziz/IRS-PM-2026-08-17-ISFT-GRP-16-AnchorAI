<script setup lang="ts">
import type { ContactRow } from '../api/types'
import EmptyState from './EmptyState.vue'
import { date } from '../format'
import { channelLabel, humanize } from '../labels'

// Stream B: contacts from approved plans and their logged outcomes (GET /api/outcomes?member_id=).
defineProps<{ contacts: ContactRow[] }>()
</script>

<template>
  <EmptyState v-if="!contacts.length" compact text="No contacts in an approved plan yet." />
  <ul v-else class="m-0 flex list-none flex-col gap-3 p-0 text-sm">
    <li v-for="c in contacts" :key="`${c.plan_id}-${c.offer_id}`" class="flex flex-col gap-0.5">
      <span class="font-medium text-ink-800" :class="{ 'line-through': c.removed }">
        {{ c.offer_name }} · {{ channelLabel(c.channel) }}
      </span>
      <span class="text-ink-500">
        Week of {{ date(c.week_start) }}<template v-if="c.assigned_to"> · {{ c.assigned_to }}</template>
        <template v-if="c.removed"> · removed{{ c.override_reason ? `: ${c.override_reason}` : '' }}</template>
      </span>
      <span v-for="o in c.outcomes" :key="o.logged_at" class="text-ink-600">
        {{ humanize(o.outcome) }} on {{ date(o.logged_at) }}<template v-if="o.note">: {{ o.note }}</template>
      </span>
      <span v-if="!c.removed && !c.outcomes.length" class="text-ink-400">No outcome logged yet</span>
    </li>
  </ul>
</template>
