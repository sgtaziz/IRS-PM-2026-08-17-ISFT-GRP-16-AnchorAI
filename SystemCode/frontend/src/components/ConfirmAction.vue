<script setup lang="ts">
import Button from 'primevue/button'
import { useConfirm } from 'primevue/useconfirm'

const props = withDefaults(
  defineProps<{
    label: string
    message: string
    header?: string
    severity?: 'danger' | 'secondary' | 'warn' | 'primary'
    size?: 'small' | 'large'
    disabled?: boolean
  }>(),
  { header: 'Please confirm', severity: 'danger', size: 'small', disabled: false },
)
const emit = defineEmits<{ confirm: [] }>()
const confirm = useConfirm()

function ask() {
  confirm.require({
    header: props.header,
    message: props.message,
    acceptProps: { label: props.label, severity: props.severity === 'primary' ? undefined : props.severity },
    rejectProps: { label: 'Cancel', severity: 'secondary', outlined: true },
    accept: () => emit('confirm'),
  })
}
</script>

<template>
  <Button
    :label="label"
    :severity="severity === 'primary' ? undefined : severity"
    :size="size"
    :disabled="disabled"
    :outlined="severity !== 'primary'"
    @click="ask"
  />
</template>
