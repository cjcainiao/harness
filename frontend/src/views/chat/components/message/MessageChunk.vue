<template>
  <div class="message-chunk">
    <MarkdownContent :content="content" />
  </div>
</template>

<script setup lang="ts">
import MarkdownContent from '@/components/MarkdownContent.vue'

// 渲染一个正文块，内容由事件处理组件持续更新
defineProps<{ content: string }>()
</script>

<style scoped>
.message-chunk {
  min-width: 0;
}
</style>
