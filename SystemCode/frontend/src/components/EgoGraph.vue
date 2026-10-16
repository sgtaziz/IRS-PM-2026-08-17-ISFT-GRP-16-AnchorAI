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
const TINTS: Record<string, string> = {
  Member: '#e3edff',
  Club: '#eef0f4',
  Class: '#dff5f4',
  Instructor: '#eeeaff',
  Event: '#fde8ec',
  Offer: '#fdf1dc',
}

// Raw graph labels are codes ("C2", "instructor_left", "MEMBER_OF"); show readable ones.
function readable(e: EgoGraph['nodes'][number]) {
  const d = e.data
  if (d.source) return { data: { ...d, label: humanize(d.type).toLowerCase() } }
  if (d.type === 'Club') return { data: { ...d, label: `Club ${d.label}` } }
  if (d.type === 'Event') return { data: { ...d, label: EVENT_LABELS[d.label as EventType] ?? humanize(String(d.label)) } }
  return e
}

// Sizes in screen pixels: the layout is spread out for readable links, so labels must not shrink with the zoom.
const px = (n: number) => () => n / (cy?.zoom() ?? 1)

function draw() {
  cy?.destroy()
  if (!el.value) return
  cy = cytoscape({
    container: el.value,
    elements: [...props.graph.nodes, ...props.graph.edges].map(readable),
    // Long, well-separated links keep each link's label clear of the node labels around it.
    layout: {
      name: 'cose',
      animate: false,
      padding: 24,
      idealEdgeLength: () => 170,
      nodeRepulsion: () => 600_000,
      gravity: 0.2,
      numIter: 2000,
    },
    maxZoom: 2,
    minZoom: 0.2,
    style: [
      {
        // Names sit inside the node, so they never cover a link or its label.
        selector: 'node',
        style: {
          label: 'data(label)',
          shape: 'round-rectangle',
          width: 'label',
          height: px(14),
          padding: () => `${7 / (cy?.zoom() ?? 1)}px`,
          'background-color': (n) => TINTS[n.data('type')] ?? '#eef0f4',
          'border-width': px(1.5),
          'border-color': (n) => COLORS[n.data('type')] ?? '#98a2b6',
          color: '#222a3c',
          'font-size': px(12),
          'font-family': 'Inter, ui-sans-serif, system-ui, sans-serif',
          'font-weight': 500,
          'text-valign': 'center',
          'text-halign': 'center',
          'z-index-compare': 'manual',
          'z-index': 1,
        },
      },
      { selector: 'node[type = "Member"]', style: { 'font-weight': 700, 'border-width': px(2) } },
      { selector: 'node[risk_band = "high"]', style: { 'border-width': px(3), 'border-color': '#d92d4b' } },
      {
        selector: 'edge',
        style: {
          label: 'data(label)',
          'font-size': px(10),
          'font-family': 'Inter, ui-sans-serif, system-ui, sans-serif',
          color: '#4b556b',
          'text-rotation': 'autorotate',
          'text-background-color': '#ffffff',
          'text-background-opacity': 1,
          'text-background-padding': () => `${3 / (cy?.zoom() ?? 1)}px`,
          'text-background-shape': 'roundrectangle',
          'text-border-color': '#e2e6ee',
          'text-border-width': px(1),
          'text-border-opacity': 1,
          width: px(1.5),
          'arrow-scale': px(1),
          'line-color': '#cbd2de',
          'target-arrow-shape': 'triangle',
          'target-arrow-color': '#cbd2de',
          'curve-style': 'bezier',
          // Links end at the node's edge, so drawing them on top only keeps their labels visible.
          'z-index-compare': 'manual',
          'z-index': 2,
        },
      },
    ],
  })
  cy.on('zoom', () => cy?.style().update())
  cy.style().update()
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
        <span class="h-2.5 w-4 rounded-[4px] border-[1.5px]" :style="{ background: TINTS[type], borderColor: color }" />{{ type }}
      </li>
      <li class="flex items-center gap-1.5"><span class="h-2.5 w-4 rounded-[4px] border-2 border-risk-high bg-white" />High-risk member</li>
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
