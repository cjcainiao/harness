<template>
  <div class="message-stream">
    <div
      ref="scrollRef"
      class="message-scroll"
      aria-label="对话消息"
      tabindex="0"
      @scroll.passive="onScroll"
    >
      <div v-if="messages.length" class="message-list">
        <MessageTurn v-for="(turn, index) in messages" :key="turn.id" :turn="turn" :index="index" />
      </div>
    </div>
    <MessageNavigator
      v-if="showNavigator && anchors.length >= 4"
      :items="anchors"
      :active-id="activeId"
      @select="scrollToMessage"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MessageNavigator from './MessageNavigator.vue'
import MessageTurn from './MessageTurn.vue'
import type { ChatTurn } from './messageTypes'

const props = withDefaults(defineProps<{ messages: ChatTurn[]; showNavigator?: boolean }>(), {
  showNavigator: true,
})

const anchors = computed(() =>
  props.messages.map((turn) => ({
    id: turn.id,
    title: turn.prompt,
    preview: turn.blocks
      .filter((block) => block.type === 'text')
      .map((block) => block.content)
      .join(''),
  })),
)
const activeId = ref('')
const scrollRef = ref<HTMLElement>()
let scrollFrame = 0
let resizeObserver: ResizeObserver | undefined

function messageSections() {
  return Array.from(scrollRef.value?.querySelectorAll<HTMLElement>('[data-message-id]') ?? [])
}

function updateActive() {
  const scroll = scrollRef.value
  if (!scroll) return
  const sections = messageSections()
  if (sections.length === 0) {
    activeId.value = ''
    return
  }

  if (scroll.scrollTop + scroll.clientHeight >= scroll.scrollHeight - 2) {
    activeId.value = sections[sections.length - 1]?.dataset.messageId ?? ''
    return
  }

  const marker = scroll.getBoundingClientRect().top + Math.min(140, scroll.clientHeight * 0.35)
  let current = sections[0]?.dataset.messageId ?? ''
  for (const section of sections) {
    if (section.getBoundingClientRect().top > marker) break
    current = section.dataset.messageId ?? current
  }
  activeId.value = current
}

function onScroll() {
  if (scrollFrame) return
  scrollFrame = window.requestAnimationFrame(() => {
    scrollFrame = 0
    updateActive()
  })
}

function scrollToMessage(id: string, behavior: ScrollBehavior) {
  const scroll = scrollRef.value
  const section = messageSections().find((item) => item.dataset.messageId === id)
  if (!scroll || !section) return

  const top =
    scroll.scrollTop + section.getBoundingClientRect().top - scroll.getBoundingClientRect().top
  scroll.scrollTo({ top, behavior })
  activeId.value = id
}

function scrollToTop() {
  scrollRef.value?.scrollTo({ top: 0, behavior: 'smooth' })
}

function scrollToBottom() {
  const scroll = scrollRef.value
  scroll?.scrollTo({ top: scroll.scrollHeight, behavior: 'smooth' })
}

defineExpose({ scrollToTop, scrollToBottom })

watch(
  () => props.messages.length,
  async () => {
    await nextTick()
    updateActive()
  },
)

onMounted(async () => {
  await nextTick()
  const scroll = scrollRef.value
  if (!scroll) return
  if (props.messages.length) scroll.scrollTop = scroll.scrollHeight
  updateActive()
  resizeObserver = new ResizeObserver(updateActive)
  resizeObserver.observe(scroll)
})

onBeforeUnmount(() => {
  window.cancelAnimationFrame(scrollFrame)
  resizeObserver?.disconnect()
})
</script>

<style scoped>
.message-stream {
  position: relative;
  height: 100%;
  background: #fff;
}
.message-scroll {
  height: 100%;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.message-list {
  width: min(736px, calc(100% - 80px));
  margin: 0 auto;
  padding: 24px 0 214px;
}
@media (min-width: 1100px) {
  .message-list {
    transform: translateX(8px);
  }
}
@media (max-width: 600px) {
  .message-list {
    width: calc(100% - 62px);
    margin-left: 42px;
    padding-bottom: 300px;
  }
}
</style>
