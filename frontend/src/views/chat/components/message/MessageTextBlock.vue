<template>
  <div class="answer-text">
    <MarkdownContent :content="block.content" />
  </div>
</template>

<script setup lang="ts">
import MarkdownContent from '@/components/MarkdownContent.vue'
import type { TextMessageBlock } from './messageTypes'

defineProps<{ block: TextMessageBlock }>()
</script>

<style scoped>
.answer-text {
  margin-top: 16px;
}
</style>
