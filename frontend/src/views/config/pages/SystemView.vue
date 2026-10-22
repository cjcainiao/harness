<!--系统配置页-->
<template>
  <div class="system-shell">
    <div class="system-page">
      <header class="page-header">
        <StackIllustration :icon="Settings2" compact />
        <h1>系统配置</h1>
      </header>
      <div class="system-content"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Settings2 } from 'lucide-vue-next'
import StackIllustration from '../components/StackIllustration.vue'
</script>

<style scoped>
.system-shell {
  min-height: 100%;
  background: #fff;
}
.system-page {
  max-width: 1080px;
  margin: 0 auto;
  padding: 48px 56px 96px;
  color: #171717;
}
.page-header {
  display: flex;
  align-items: center;
  gap: 14px;
}
.page-header h1 {
  font-size: 28px;
  font-weight: 680;
  letter-spacing: -0.035em;
  line-height: 1.25;
}
@media (max-width: 720px) {
  .system-page {
    padding: 30px 20px 64px;
  }
  .page-header h1 {
    font-size: 25px;
  }
}
</style>
