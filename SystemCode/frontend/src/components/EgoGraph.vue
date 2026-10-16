<script setup lang="ts">
import cytoscape, { type Core } from 'cytoscape'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { EgoGraph, EventType } from '../api/types'
import { EVENT_LABELS, humanize } from '../labels'

const props = withDefaults(defineProps<{ graph: EgoGraph; height?: string }>(), { height: '360px' })
const emit = defineEmits<{ select: [type: string, id: string] }>()

const el = ref<HTMLDivElement | null>(null)
let cy: Core | null = null

// Colour by node type, with the label in the node, so meaning never rests on colour alone.
const COLORS: Record<string, string> = {
  Member: '#1f60ea',
  Club: '#687389',
  Class: '#14a3a0',
  Instructor: '#7c5cff',
  Event: '#d92d4b',
  Offer: '#f2a33a',
}

// Raw graph labels are codes ("C2", "instructor_left", "MEMBER_OF"); show readable ones.
function readable(e: EgoGraph['nodes'][number]) {
  const d = e.data
  if (d.source) return { data: { ...d, label: humanize(d.type).toLowerCase() } }
  if (d.type === 'Club') return { data: { ...d, label: `Club ${d.label}` } }
  if (d.type === 'Event') return { data: { ...d, label: EVENT_LABELS[d.label as EventType] ?? humanize(String(d.label)) } }
  return e
}

function draw() {
  cy?.destroy()
  if (!el.value) return
  cy = cytoscape({
    container: el.value,
    elements: [...props.graph.nodes, ...props.graph.edges].map(readable),
    layout: { name: 'cose', animate: false, padding: 24 },
    // A small neighbourhood would otherwise be zoomed until its labels look oversized.
    maxZoom: 1.4,
    minZoom: 0.3,
    style: [
      {
        selector: 'node',
        style: {
          label: 'data(label)',
          'background-color': (n) => COLORS[n.data('type')] ?? '#98a2b6',
          color: '#222a3c',
          'font-size': 11,
          'font-family': 'Inter, ui-sans-serif, system-ui, sans-serif',
          'font-weight': 500,
          'text-valign': 'bottom',
          'text-margin-y': 5,
          'text-background-color': '#ffffff',
          'text-background-opacity': 0.85,
          'text-background-padding': '2px',
          'text-background-shape': 'roundrectangle',
          'border-width': 2,
          'border-color': '#ffffff',
          width: 24,
          height: 24,
        },
      },
      { selector: 'node[risk_band = "high"]', style: { 'border-width': 3, 'border-color': '#d92d4b' } },
      { selector: 'node[type = "Member"]', style: { width: 30, height: 30, 'font-weight': 700 } },
      {
        selector: 'edge',
        style: {
          label: 'data(type)',
          'font-size': 8,
          color: '#98a2b6',
          'text-rotation': 'autorotate',
          width: 1.5,
          'line-color': '#cbd2de',
          'target-arrow-shape': 'triangle',
          'target-arrow-color': '#cbd2de',
          'curve-style': 'bezier',
        },
      },
    ],
  })
  cy.on('tap', 'node', (e) => {
    const d = e.target.data()
    emit('select', d.type, d.member_id ?? d.instructor_id ?? d.class_id ?? d.id)
  })
}

onMounted(draw)
watch(() => props.graph, draw)
onBeforeUnmount(() => cy?.destroy())
</script>

<template>
  <div>
    <div ref="el" class="ego" :style="{ height }" role="img" :aria-label="`Graph with ${graph.nodes.length} nodes and ${graph.edges.length} links`" />
    <ul class="m-0 mt-3 flex list-none flex-wrap gap-x-4 gap-y-1.5 p-0 text-xs text-ink-600">
      <li v-for="(color, type) in COLORS" :key="type" class="flex items-center gap-1.5">
        <span class="size-2.5 rounded-full" :style="{ background: color }" />{{ type }}
      </li>
      <li class="flex items-center gap-1.5"><span class="size-2.5 rounded-full border-2 border-risk-high" />High-risk member</li>
    </ul>
  </div>
</template>

<style scoped>
.ego {
  border: 1px solid var(--color-ink-200);
  border-radius: 0.75rem;
  background-color: var(--color-ink-50);
  background-image: radial-gradient(var(--color-ink-200) 1px, transparent 1px);
  background-size: 16px 16px;
}
</style>
