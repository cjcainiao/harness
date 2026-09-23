<template>
  <section class="message-turn" :data-message-id="turn.id" :aria-label="`第 ${index + 1} 轮对话`">
    <p class="message-question">{{ turn.prompt }}</p>
    <div class="message-answer">
      <div v-if="turn.duration != null" class="answer-meta">
        <span>用时 {{ turn.duration }}秒</span>
        <ChevronRight :size="13" aria-hidden="true" />
      </div>
      <MessageBlockRenderer v-for="block in turn.blocks" :key="block.id" :block="block" />
      <p v-if="turn.status === 'error' && turn.error" class="answer-error" role="alert">
        {{ turn.error }}
      </p>
      <div v-if="hasText" class="answer-actions" aria-hidden="true">
        <Copy :size="14" />
        <ThumbsUp :size="14" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ChevronRight, Copy, ThumbsUp } from 'lucide-vue-next'
import { computed } from 'vue'
import MessageBlockRenderer from './MessageBlockRenderer.vue'
import type { ChatTurn } from './messageTypes'

const props = defineProps<{ turn: ChatTurn; index: number }>()
const hasText = computed(() => props.turn.blocks.some((block) => block.type === 'text'))
</script>

<style scoped>
.message-turn {
  display: flex;
  flex-direction: column;
  gap: 50px;
  min-height: 210px;
  padding: 24px 0 10px;
}
.message-question {
  align-self: flex-end;
  max-width: 76%;
  padding: 11px 15px;
  border-radius: 16px;
  background: #0d0d0d;
  color: #fff;
  font-size: 14px;
  line-height: 20px;
  overflow-wrap: anywhere;
}
.message-answer {
  min-width: 0;
}
.answer-meta {
  display: flex;
  align-items: center;
  gap: 2px;
  padding-bottom: 7px;
  border-bottom: 1px solid #e8e9eb;
  color: #858a91;
  font-size: 12px;
  line-height: 18px;
}
.answer-error {
  margin-top: 16px;
  color: #c44444;
  font-size: 14px;
  line-height: 1.65;
}
.answer-actions {
  display: flex;
  gap: 12px;
  margin-top: 12px;
  color: #9299a1;
}
@media (max-width: 600px) {
  .message-turn {
    gap: 36px;
    min-height: 245px;
    padding-bottom: 60px;
  }
  .message-question {
    max-width: 88%;
  }
}
</style>
