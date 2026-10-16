import { BarChart, LineChart, PieChart, ScatterChart } from 'echarts/charts'
import {
  DatasetComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components'
import { registerTheme, use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'

use([
  BarChart,
  LineChart,
  PieChart,
  ScatterChart,
  DatasetComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
  CanvasRenderer,
])

export const palette = ['#1f60ea', '#14a3a0', '#f2a33a', '#7c5cff', '#e5486b', '#687389']
export const riskColors = { low: '#0f9d6b', medium: '#e09a1a', high: '#d92d4b' }
export const CHART_THEME = 'anchor'

const ink = { text: '#4b556b', muted: '#687389', line: '#e2e6ee', axis: '#cbd2de' }
const font = "Inter, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif"
const axis = {
  axisLine: { show: true, lineStyle: { color: ink.axis } },
  axisTick: { show: false },
  axisLabel: { color: ink.muted, fontSize: 12 },
  splitLine: { lineStyle: { color: ink.line, type: 'dashed' } },
  nameTextStyle: { color: ink.muted, fontSize: 12 },
}

registerTheme(CHART_THEME, {
  color: palette,
  backgroundColor: 'transparent',
  textStyle: { fontFamily: font, color: ink.text },
  categoryAxis: { ...axis, splitLine: { show: false } },
  valueAxis: { ...axis, axisLine: { show: false } },
  legend: { textStyle: { color: ink.text, fontSize: 12 }, icon: 'roundRect', itemWidth: 10, itemHeight: 10, itemGap: 16 },
  tooltip: {
    backgroundColor: '#151b2b',
    borderWidth: 0,
    padding: [8, 12],
    textStyle: { color: '#fff', fontSize: 12, fontFamily: font },
    extraCssText: 'border-radius:8px;box-shadow:0 8px 24px rgba(11,16,32,.25);',
    axisPointer: { lineStyle: { color: ink.axis }, shadowStyle: { color: 'rgba(31,96,234,0.06)' } },
  },
  bar: { itemStyle: { borderRadius: 3 }, barMaxWidth: 28 },
  line: { smooth: true, symbol: 'circle', symbolSize: 6, lineStyle: { width: 2.5 } },
  markLine: { lineStyle: { color: ink.muted } },
})
