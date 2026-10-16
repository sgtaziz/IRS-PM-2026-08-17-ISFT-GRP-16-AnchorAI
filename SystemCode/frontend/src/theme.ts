import { definePreset } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'

// "Harbour" blue for the brand and the slate-tinted "ink" neutrals; style.css mirrors them.
export const brand = {
  50: '#eef6ff',
  100: '#d9eaff',
  200: '#bcdaff',
  300: '#8ec3ff',
  400: '#59a1fb',
  500: '#347ef6',
  600: '#1f60ea',
  700: '#184bd5',
  800: '#1a3fac',
  900: '#1b3a88',
  950: '#152553',
}

const ink = {
  0: '#ffffff',
  50: '#f7f8fb',
  100: '#eff1f6',
  200: '#e2e6ee',
  300: '#cbd2de',
  400: '#98a2b6',
  500: '#687389',
  600: '#4b556b',
  700: '#343d52',
  800: '#222a3c',
  900: '#151b2b',
  950: '#0b1020',
}

export const AnchorPreset = definePreset(Aura, {
  primitive: {
    borderRadius: { none: '0', xs: '4px', sm: '6px', md: '8px', lg: '10px', xl: '14px' },
  },
  semantic: {
    primary: { ...brand, color: brand[600], hoverColor: brand[700], activeColor: brand[800], contrastColor: '#ffffff' },
    surface: ink,
    focusRing: { width: '2px', style: 'solid', color: brand[500], offset: '2px', shadow: 'none' },
    text: { color: ink[800], hoverColor: ink[900], mutedColor: ink[500], hoverMutedColor: ink[600] },
    content: { borderColor: ink[200], hoverBackground: ink[50] },
    highlight: { background: brand[50], focusBackground: brand[100], color: brand[800], focusColor: brand[900] },
    formField: {
      paddingX: '0.75rem',
      paddingY: '0.5rem',
      borderColor: ink[300],
      hoverBorderColor: ink[400],
      color: ink[800],
      placeholderColor: ink[400],
      shadow: '0 1px 2px 0 rgba(21, 27, 43, 0.04)',
      sm: { fontSize: '0.8125rem', paddingX: '0.625rem', paddingY: '0.375rem' },
      focusRing: { width: '3px', style: 'solid', color: 'color-mix(in srgb, #347ef6 22%, transparent)', offset: '0', shadow: 'none' },
    },
    overlay: {
      select: { shadow: '0 12px 32px -8px rgba(21, 27, 43, 0.18), 0 4px 8px -4px rgba(21, 27, 43, 0.08)' },
      popover: { shadow: '0 12px 32px -8px rgba(21, 27, 43, 0.18), 0 4px 8px -4px rgba(21, 27, 43, 0.08)' },
      modal: { shadow: '0 24px 64px -12px rgba(11, 16, 32, 0.32)' },
    },
  },
  components: {
    card: {
      root: { borderRadius: '{border.radius.xl}', shadow: '0 1px 2px rgba(21, 27, 43, 0.05)' },
      body: { padding: '1.25rem', gap: '0.75rem' },
      title: { fontSize: '1rem', fontWeight: '600' },
      subtitle: { fontSize: '0.875rem' },
    },
    button: {
      root: { borderRadius: '{border.radius.md}', label: { fontWeight: '600' }, paddingY: '0.5rem', paddingX: '0.875rem' },
    },
    datatable: {
      header: { background: 'transparent', borderWidth: '0', padding: '0 0 0.75rem 0' },
      headerCell: { background: '{surface.50}', selectedBackground: '{surface.100}', color: '{text.muted.color}', selectedColor: '{primary.700}', padding: '0.625rem 0.875rem' },
      columnTitle: { fontWeight: '600' },
      bodyCell: { padding: '0.625rem 0.875rem' },
      row: { stripedBackground: '{surface.50}' },
    },
    tag: {
      root: { fontSize: '0.75rem', fontWeight: '600', padding: '0.2rem 0.55rem', borderRadius: '999px' },
    },
    tooltip: {
      root: { background: ink[900], color: '#ffffff', borderRadius: '{border.radius.md}', padding: '0.5rem 0.65rem', maxWidth: '20rem' },
    },
    dialog: { header: { padding: '1.25rem 1.5rem 0.75rem' }, content: { padding: '0 1.5rem 1.25rem' }, title: { fontSize: '1.125rem' } },
    drawer: { header: { padding: '1rem 1.25rem' }, content: { padding: '0 1.25rem 1.25rem' } },
    message: { root: { borderRadius: '{border.radius.lg}' } },
    paginator: { root: { background: 'transparent' } },
  },
})
