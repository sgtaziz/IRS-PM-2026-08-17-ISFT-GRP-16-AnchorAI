<script setup lang="ts">
import { UserCog } from 'lucide-vue-next'
import ComingSoon from '../components/ComingSoon.vue'
import PageHeader from '../components/PageHeader.vue'

const FEATURES = [
  'Create, edit and deactivate users',
  'Assign the staff, manager or admin role',
  'Reset a password',
  'Every change recorded in the audit log',
]
</script>

<template>
  <div class="page">
    <PageHeader title="Users" subtitle="Manage who can sign in to AnchorAI and what they can see." />
    <ComingSoon
      :icon="UserCog"
      title="User management is on its way"
      text="Add front-desk staff and trainers, set their roles and keep access tidy, with every change audited."
      :features="FEATURES"
      owner="Stream C · W43"
    />
  </div>
</template>
