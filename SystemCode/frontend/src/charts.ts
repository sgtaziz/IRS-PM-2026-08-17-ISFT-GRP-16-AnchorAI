import { BarChart, LineChart, PieChart, ScatterChart } from 'echarts/charts'
import {
  DatasetComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components'
import { use } from 'echarts/core'
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

export const palette = ['#2f6fb5', '#e07b39', '#3a9d6b', '#8a5cc2', '#c2475b', '#6b7a8f']
