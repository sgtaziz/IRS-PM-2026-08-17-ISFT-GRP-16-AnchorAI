import {
  CalendarCheck,
  CalendarX2,
  ChartPie,
  ClipboardList,
  Database,
  Gift,
  History,
  LayoutDashboard,
  MessagesSquare,
  Network,
  ScrollText,
  Settings,
  SlidersHorizontal,
  UserCog,
  Users,
  type LucideIcon,
} from 'lucide-vue-next'

// Sidebar grouping and icons by route name; a route missing here still shows, under "More".
export const NAV_GROUPS: { label: string; routes: string[] }[] = [
  { label: 'Insights', routes: ['Dashboard', 'Segments', 'Members'] },
  { label: 'Planning', routes: ['Weekly plan', 'Scenarios', 'Knowledge graph', 'Events & roster'] },
  { label: 'Front desk', routes: ['My contacts', 'Assistant'] },
  { label: 'Administration', routes: ['Rules', 'Offers & constraints', 'Data & models', 'Users', 'Audit log', 'Settings'] },
]

export const NAV_ICONS: Record<string, LucideIcon> = {
  Dashboard: LayoutDashboard,
  Segments: ChartPie,
  Members: Users,
  'Weekly plan': CalendarCheck,
  Scenarios: SlidersHorizontal,
  'Knowledge graph': Network,
  'Events & roster': CalendarX2,
  'My contacts': ClipboardList,
  Assistant: MessagesSquare,
  Rules: ScrollText,
  'Offers & constraints': Gift,
  'Data & models': Database,
  Users: UserCog,
  'Audit log': History,
  Settings,
}

export const groupOf = (name: string) => NAV_GROUPS.find((g) => g.routes.includes(name))?.label ?? 'More'
