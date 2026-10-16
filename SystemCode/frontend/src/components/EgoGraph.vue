<script setup lang="ts">
import cytoscape, { type Core } from 'cytoscape'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { EgoGraph } from '../api/types'

const props = defineProps<{ graph: EgoGraph }>()
const emit = defineEmits<{ select: [type: string, id: string] }>()

const el = ref<HTMLDivElement | null>(null)
let cy: Core | null = null

// Colour by node type, with the label in the node, so meaning never rests on colour alone.
const COLORS: Record<string, string> = {
  Member: '#2f6fb5',
  Club: '#5b6778',
  Class: '#3f9c6d',
  Instructor: '#8a5cc4',
  Event: '#c0392b',
  Offer: '#d4881c',
}

function draw() {
  cy?.destroy()
  if (!el.value) return
  cy = cytoscape({
    container: el.value,
    elements: [...props.graph.nodes, ...props.graph.edges],
    layout: { name: 'cose', animate: false, padding: 20 },
    style: [
      {
        selector: 'node',
        style: {
          label: 'data(label)',
          'background-color': (n) => COLORS[n.data('type')] ?? '#999',
          color: '#1c2430',
          'font-size': 10,
          'text-valign': 'bottom',
          'text-margin-y': 4,
          width: 22,
          height: 22,
        },
      },
      { selector: 'node[risk_band = "high"]', style: { 'border-width': 3, 'border-color': '#c0392b' } },
      {
        selector: 'edge',
        style: {
          label: 'data(type)',
          'font-size': 7,
          color: '#5b6778',
          width: 1.5,
          'line-color': '#c3cbd6',
          'target-arrow-shape': 'triangle',
          'target-arrow-color': '#c3cbd6',
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
    <div ref="el" class="ego" role="img" :aria-label="`Graph with ${graph.nodes.length} nodes and ${graph.edges.length} links`" />
    <ul class="legend">
      <li v-for="(color, type) in COLORS" :key="type"><span :style="{ background: color }" />{{ type }}</li>
      <li><span class="ring" />High-risk member</li>
    </ul>
  </div>
</template>

<style scoped>
.ego { height: 320px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); }
.legend { list-style: none; padding: 0; margin: 0.5rem 0 0; display: flex; flex-wrap: wrap; gap: 0.25rem 0.9rem; font-size: 0.8rem; color: var(--muted); }
.legend span { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 0.3rem; vertical-align: middle; }
.legend .ring { border: 2px solid #c0392b; background: transparent; }
</style>
