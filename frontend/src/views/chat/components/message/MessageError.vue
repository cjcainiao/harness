<!--错误消息分隔线-->
<template>
  <div class="message-error" role="alert">
    <span class="error-line" />
    <span class="error-note">
      <TriangleAlert class="error-icon" :size="14" />
      <span class="error-text">{{ content }}</span>
    </span>
    <span class="error-line" />
  </div>
</template>

<script setup lang="ts">
import { TriangleAlert } from 'lucide-vue-next'

defineProps<{ content: string }>()
</script>

<style scoped>
.message-error {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  color: #d86464;
  font-size: 13px;
  line-height: 1.5;
}

.error-line {
  flex: 1 1 0;
  min-width: 12px;
  height: 1px;
  background: #ebecee;
}

.error-note {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  flex: none;
}

.error-icon {
  flex: none;
}

.error-text {
  min-width: 0;
  overflow-wrap: anywhere;
}
</style>
